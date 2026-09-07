#!/usr/bin/env python3
"""计算本 Skill 规定的文件或构建目录 sha256 摘要。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_tools import sha256_directory, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="按原始字节计算文件摘要")
    group.add_argument("--directory", help="按规范 manifest 计算构建目录摘要")
    args = parser.parse_args()

    try:
        if args.file:
            target = Path(args.file).resolve()
            if not target.is_file():
                raise ValueError(f"文件不存在：{target}")
            digest = sha256_file(target)
            kind = "file"
        else:
            target = Path(args.directory).resolve()
            digest = sha256_directory(target)
            kind = "directory"
    except (OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"valid": True, "kind": kind, "path": str(target), "hash": digest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
