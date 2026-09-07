#!/usr/bin/env python3
"""对静态 H5 交付目录执行可移植的入口与本地依赖检查。"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit


RESOURCE_LINK_RELS = {
    "apple-touch-icon",
    "icon",
    "manifest",
    "mask-icon",
    "modulepreload",
    "preload",
    "prefetch",
    "stylesheet",
}
REFERENCE_ATTRS = {
    "script": ("src",),
    "img": ("src",),
    "source": ("src",),
    "audio": ("src",),
    "video": ("src", "poster"),
    "iframe": ("src",),
    "object": ("data",),
    "embed": ("src",),
    "track": ("src",),
    "input": ("src",),
}
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
CSS_IMPORT_RE = re.compile(r"@import\s+(?!url\()[\"']([^\"']+)[\"']", re.IGNORECASE)
JS_COMMENT_RE = re.compile(r"/\*.*?\*/|(^|[^:])//[^\r\n]*", re.DOTALL | re.MULTILINE)
JS_IMPORT_RE = re.compile(
    r"(?:\b(?:import|export)\s+(?:[^;\n]*?\s+from\s*)?[\"']([^\"']+)[\"']"
    r"|\bimport\s*\(\s*[\"']([^\"']+)[\"']\s*\))",
    re.MULTILINE,
)
TOUCH_ACTION_RE = re.compile(r"(?:^|[;{])\s*touch-action\s*:", re.IGNORECASE)


def parse_srcset(value: str) -> list[str]:
    """解析常见 srcset；data URI 作为一个内嵌候选整体忽略后续歧义。"""
    urls: list[str] = []
    index = 0
    length = len(value)
    while index < length:
        while index < length and (value[index].isspace() or value[index] == ","):
            index += 1
        if index >= length:
            break
        start = index
        is_data = value[index : index + 5].lower() == "data:"
        while index < length and not value[index].isspace() and (is_data or value[index] != ","):
            index += 1
        candidate = value[start:index].strip()
        if candidate:
            urls.append(candidate)
        if is_data:
            # data URI 内允许逗号；无法无损区分无空格的下一个候选，内嵌资源无需静态文件检查。
            while index < length and value[index] != ",":
                index += 1
        else:
            while index < length and value[index] != ",":
                index += 1
    return urls


class EntryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, str]] = []
        self.inline_css: list[str] = []
        self.inline_modules: list[str] = []
        self.base_hrefs: list[str] = []
        self.has_viewport = False
        self._style_depth = 0
        self._module_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "meta" and attr_map.get("name", "").lower() == "viewport":
            self.has_viewport = bool(attr_map.get("content", "").strip())
        if tag == "base" and attr_map.get("href", "").strip():
            self.base_hrefs.append(attr_map["href"].strip())
        if tag == "link":
            rels = {part.lower() for part in attr_map.get("rel", "").split()}
            href = attr_map.get("href", "").strip()
            if href and rels & RESOURCE_LINK_RELS:
                self.references.append((tag, "href", href))
            imagesrcset = attr_map.get("imagesrcset", "")
            for reference in parse_srcset(imagesrcset):
                self.references.append((tag, "imagesrcset", reference))
        for attr in REFERENCE_ATTRS.get(tag, ()):
            value = attr_map.get(attr, "").strip()
            if value:
                self.references.append((tag, attr, value))
        if tag in {"img", "source"}:
            for reference in parse_srcset(attr_map.get("srcset", "")):
                self.references.append((tag, "srcset", reference))
        inline_style = attr_map.get("style", "").strip()
        if inline_style:
            self.inline_css.append(inline_style)
        if tag == "style":
            self._style_depth += 1
        if tag == "script" and not attr_map.get("src") and attr_map.get("type", "").lower() == "module":
            self._module_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "style" and self._style_depth:
            self._style_depth -= 1
        if tag == "script" and self._module_depth:
            self._module_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.inline_css.append(data)
        if self._module_depth:
            self.inline_modules.append(data)


class Result:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self._seen: set[tuple[str, str, str]] = set()

    def _append(self, target: list[dict[str, str]], code: str, path: str, message: str) -> None:
        key = (code, path, message)
        if key not in self._seen:
            self._seen.add(key)
            target.append({"code": code, "path": path, "message": message})

    def error(self, code: str, path: str, message: str) -> None:
        self._append(self.errors, code, path, message)

    def warning(self, code: str, path: str, message: str) -> None:
        self._append(self.warnings, code, path, message)


def reference_kind(reference: str) -> str:
    stripped = reference.strip()
    if stripped.startswith("#"):
        return "ignored"
    split = urlsplit(stripped)
    scheme = split.scheme.lower()
    if scheme in {"javascript", "mailto", "tel"}:
        return "ignored"
    if scheme == "file":
        return "file"
    if scheme == "data":
        return "embedded"
    if scheme == "blob":
        return "blob"
    if scheme or split.netloc:
        return "external"
    return "local"


def exact_case_mismatch(root: Path, candidate: Path) -> tuple[str, str] | None:
    """在大小写不敏感文件系统上也验证引用拼写。"""
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    current = root
    for part in relative.parts:
        try:
            names = [child.name for child in current.iterdir()]
        except OSError:
            return None
        if part not in names:
            matches = [name for name in names if name.casefold() == part.casefold()]
            if matches:
                return part, matches[0]
            return None
        current = current / part
    return None


def resolve_local(root: Path, base_dir: Path, reference: str, origin: str, result: Result) -> Path | None:
    kind = reference_kind(reference)
    display = f"{origin} -> {reference}"
    if kind == "file":
        result.error("E_FILE_URL", display, "包体不能依赖 file:// 资源。")
        return None
    if kind in {"ignored", "embedded"}:
        return None
    if kind == "blob":
        result.warning("W_BLOB_URL", display, "静态 blob: URL 刷新后不可复用；请确认它由运行时创建。")
        return None
    if kind == "external":
        result.warning("W_EXTERNAL", display, "发现外部资源；必须在浏览器验收中确认失败降级。")
        return None

    split = urlsplit(reference)
    raw_path = unquote(split.path)
    if not raw_path:
        return None
    if raw_path.startswith("/"):
        result.warning("W_ROOT_PATH", display, "根路径引用在子目录部署时可能失效，优先使用相对路径。")
        candidate = root / raw_path.lstrip("/")
    else:
        candidate = base_dir / raw_path
    candidate = Path(os.path.abspath(os.path.normpath(candidate)))

    try:
        candidate.relative_to(root)
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        result.error("E_PATH_ESCAPE", display, "资源路径越出交付目录。")
        return None

    mismatch = exact_case_mismatch(root, candidate)
    if mismatch:
        requested, actual = mismatch
        result.error("E_CASE_MISMATCH", display, f"路径大小写不一致：引用 {requested}，实际为 {actual}。")
    return resolved


def css_references(source: str) -> Iterable[str]:
    clean = CSS_COMMENT_RE.sub("", source)
    for _, reference in CSS_URL_RE.findall(clean):
        if reference.strip():
            yield reference.strip()
    for reference in CSS_IMPORT_RE.findall(clean):
        if reference.strip():
            yield reference.strip()


def js_references(source: str) -> Iterable[str]:
    clean = JS_COMMENT_RE.sub(lambda match: match.group(1) or "", source)
    for match in JS_IMPORT_RE.finditer(clean):
        reference = match.group(1) or match.group(2)
        if reference:
            yield reference.strip()


def check(root_arg: str, entry_arg: str) -> tuple[Result, dict[str, Any]]:
    result = Result()
    root = Path(root_arg).resolve()
    entry = (root / entry_arg).resolve()
    summary: dict[str, Any] = {
        "root": str(root),
        "entrypoint": str(entry),
        "file_count": 0,
        "total_bytes": 0,
        "local_references": 0,
        "external_references": 0,
        "embedded_references": 0,
        "checked_css_files": 0,
        "checked_module_files": 0,
    }

    if not root.is_dir():
        result.error("E_ROOT", str(root), "交付目录不存在或不是目录。")
        return result, summary
    try:
        entry.relative_to(root)
    except ValueError:
        result.error("E_ENTRY_ESCAPE", str(entry), "入口文件必须位于交付目录内。")
        return result, summary
    if not entry.is_file():
        result.error("E_ENTRY", str(entry), "入口文件不存在。")
        return result, summary
    if entry.stat().st_size == 0:
        result.error("E_ENTRY_EMPTY", str(entry), "入口文件为空。")
        return result, summary

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                summary["file_count"] += 1
                summary["total_bytes"] += path.stat().st_size
            except OSError:
                result.error("E_FILE_READ", str(path), "无法读取文件信息。")

    try:
        html = entry.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result.error("E_HTML_READ", str(entry), f"无法以 UTF-8 读取入口：{exc}")
        return result, summary

    parser = EntryParser()
    try:
        parser.feed(html)
    except Exception as exc:  # HTMLParser is permissive; preserve diagnostics if extension code fails.
        result.error("E_HTML_PARSE", str(entry), f"解析入口失败：{exc}")
        return result, summary

    if not parser.has_viewport:
        result.error("E_VIEWPORT", str(entry), "移动 H5 必须声明 viewport meta。")
    if parser.base_hrefs:
        result.error("E_BASE_URL", parser.base_hrefs[0], "可移植交付禁止使用 <base href>；请改为显式相对路径。")
        if len(parser.base_hrefs) > 1:
            result.warning("W_MULTIPLE_BASE", str(entry), "发现多个 <base href>；浏览器只采用首个有效值。")

    queue: deque[tuple[Path, str, str]] = deque(
        (entry.parent, reference, f"{entry.name}:{tag}[{attr}]")
        for tag, attr, reference in parser.references
    )
    for index, css in enumerate(parser.inline_css):
        queue.extend((entry.parent, reference, f"{entry.name}:inline-style-{index}") for reference in css_references(css))
    for index, module in enumerate(parser.inline_modules):
        queue.extend((entry.parent, reference, f"{entry.name}:inline-module-{index}") for reference in js_references(module))

    checked: set[Path] = set()
    css_sources = [CSS_COMMENT_RE.sub("", css) for css in parser.inline_css]
    while queue:
        base_dir, reference, origin = queue.popleft()
        kind = reference_kind(reference)
        if kind == "external":
            summary["external_references"] += 1
        elif kind == "embedded":
            summary["embedded_references"] += 1
        local_path = resolve_local(root, base_dir, reference, origin, result)
        if local_path is None:
            continue
        summary["local_references"] += 1
        if local_path in checked:
            continue
        checked.add(local_path)
        if not local_path.is_file():
            result.error("E_RESOURCE_MISSING", f"{origin} -> {reference}", "引用的本地资源不存在。")
            continue
        if local_path.stat().st_size == 0:
            result.error("E_RESOURCE_EMPTY", f"{origin} -> {reference}", "引用的本地资源为空。")
            continue

        suffix = local_path.suffix.lower()
        if suffix == ".css":
            try:
                source = local_path.read_text(encoding="utf-8")
                css_sources.append(CSS_COMMENT_RE.sub("", source))
                summary["checked_css_files"] += 1
                queue.extend(
                    (local_path.parent, nested, str(local_path.relative_to(root)))
                    for nested in css_references(source)
                )
            except (OSError, UnicodeDecodeError) as exc:
                result.error("E_CSS_READ", str(local_path), f"无法读取样式依赖：{exc}")
        elif suffix in {".js", ".mjs"}:
            try:
                source = local_path.read_text(encoding="utf-8")
                summary["checked_module_files"] += 1
                for nested in js_references(source):
                    if nested.startswith(("./", "../", "/")) or reference_kind(nested) != "local":
                        queue.append((local_path.parent, nested, str(local_path.relative_to(root))))
                    else:
                        result.warning("W_BARE_MODULE", f"{local_path.relative_to(root)} -> {nested}", "发现裸模块名；请确认 import map 或打包产物可用。")
            except (OSError, UnicodeDecodeError) as exc:
                result.error("E_JS_READ", str(local_path), f"无法读取模块依赖：{exc}")

    if not any(TOUCH_ACTION_RE.search(source) for source in css_sources):
        result.warning("W_TOUCH_ACTION", str(entry), "未发现有效 touch-action 声明；请在真机或移动仿真中确认页面不会抢走手势。")

    return result, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_dir", help="静态 H5 构建目录")
    parser.add_argument("--entry", default="index.html", help="相对构建目录的入口，默认 index.html")
    args = parser.parse_args()

    result, summary = check(args.build_dir, args.entry)
    output = {
        "valid": not result.errors,
        "errors": result.errors,
        "warnings": result.warnings,
        "summary": summary,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
