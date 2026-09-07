#!/usr/bin/env python3
"""报告校验与哈希命令共享的产物完整性工具。"""

from __future__ import annotations

import hashlib
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO


HASH_PREFIX = "sha256:"
BUILD_HASH_DOMAIN = b"build-instant-qte-h5-directory-v1\0"


def _stream_digest(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return HASH_PREFIX + _stream_digest(handle)


def regular_files(root: Path) -> list[tuple[str, Path]]:
    if not root.is_dir():
        raise ValueError(f"目录不存在：{root}")
    files: list[tuple[str, Path]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"构建目录不允许符号链接：{relative}")
        if path.is_file():
            files.append((relative, path))
    return sorted(files, key=lambda item: item[0].encode("utf-8"))


def sha256_directory(root: Path) -> str:
    """哈希排序后的 POSIX 相对路径、字节长度与文件原始字节。"""
    digest = hashlib.sha256()
    digest.update(BUILD_HASH_DOMAIN)
    for relative, path in regular_files(root):
        name = relative.encode("utf-8")
        size = path.stat().st_size
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    return HASH_PREFIX + digest.hexdigest()


def _safe_member_name(raw: str) -> str:
    while raw.startswith("./"):
        raw = raw[2:]
    pure = PurePosixPath(raw)
    if not raw or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"归档成员路径不安全：{raw!r}")
    return pure.as_posix()


def _expected_archive_files(build_dir: Path) -> dict[str, tuple[int, str]]:
    expected: dict[str, tuple[int, str]] = {}
    prefix = build_dir.name
    for relative, path in regular_files(build_dir):
        expected[f"{prefix}/{relative}"] = (path.stat().st_size, sha256_file(path))
    return expected


def _compare(
    expected: dict[str, tuple[int, str]],
    actual: dict[str, tuple[int, str]],
) -> list[str]:
    problems: list[str] = []
    for missing in sorted(set(expected) - set(actual)):
        problems.append(f"归档缺少构建文件：{missing}")
    for extra in sorted(set(actual) - set(expected)):
        problems.append(f"归档含有构建外文件：{extra}")
    for name in sorted(set(expected) & set(actual)):
        if expected[name] != actual[name]:
            problems.append(f"归档文件内容与构建目录不一致：{name}")
    return problems


def _tar_files(path: Path) -> tuple[dict[str, tuple[int, str]], list[str]]:
    actual: dict[str, tuple[int, str]] = {}
    problems: list[str] = []
    try:
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                try:
                    name = _safe_member_name(member.name)
                except ValueError as exc:
                    problems.append(str(exc))
                    continue
                if member.issym() or member.islnk() or member.isdev():
                    problems.append(f"归档不允许链接或设备成员：{name}")
                    continue
                if member.isdir():
                    continue
                if not member.isfile():
                    problems.append(f"归档含不支持的成员类型：{name}")
                    continue
                if name in actual:
                    problems.append(f"归档成员重复：{name}")
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    problems.append(f"无法读取归档成员：{name}")
                    continue
                actual[name] = (member.size, HASH_PREFIX + _stream_digest(handle))
    except (OSError, tarfile.TarError) as exc:
        problems.append(f"无法读取 tar 归档：{exc}")
    return actual, problems


def _zip_files(path: Path) -> tuple[dict[str, tuple[int, str]], list[str]]:
    actual: dict[str, tuple[int, str]] = {}
    problems: list[str] = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            bad = archive.testzip()
            if bad:
                problems.append(f"ZIP CRC 校验失败：{bad}")
            for member in archive.infolist():
                try:
                    name = _safe_member_name(member.filename)
                except ValueError as exc:
                    problems.append(str(exc))
                    continue
                if member.is_dir():
                    continue
                mode = member.external_attr >> 16
                if mode and stat.S_ISLNK(mode):
                    problems.append(f"归档不允许符号链接：{name}")
                    continue
                if name in actual:
                    problems.append(f"归档成员重复：{name}")
                    continue
                with archive.open(member, "r") as handle:
                    actual[name] = (member.file_size, HASH_PREFIX + _stream_digest(handle))
    except (OSError, zipfile.BadZipFile) as exc:
        problems.append(f"无法读取 ZIP 归档：{exc}")
    return actual, problems


def verify_archive_matches_build(archive: Path, build_dir: Path) -> list[str]:
    """验证安全成员、CRC/压缩流，以及归档与本地 build 的逐文件一致性。"""
    try:
        expected = _expected_archive_files(build_dir)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    lowered = archive.name.lower()
    if lowered.endswith((".tar.gz", ".tgz", ".tar")):
        actual, problems = _tar_files(archive)
    elif lowered.endswith(".zip"):
        actual, problems = _zip_files(archive)
    else:
        return ["归档格式必须是 .tar.gz、.tgz、.tar 或 .zip。"]
    return problems + _compare(expected, actual)
