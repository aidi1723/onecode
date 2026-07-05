#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path


def check_checksums(*, root: Path, checksum_path: Path) -> list[str]:
    results: list[str] = []
    root_resolved = root.resolve(strict=False)
    checksum_relative_path = checksum_path.resolve(strict=False).relative_to(root_resolved).as_posix()
    symlink_paths = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink())
    if symlink_paths:
        raise ValueError(f"symlink not allowed {symlink_paths[0]}")
    listed_paths: set[str] = set()
    for line_number, raw_line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.rstrip("\r\n")
        if line == "":
            continue
        parts = line.split("  ", maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(char not in "0123456789abcdef" for char in parts[0]) or not parts[1]:
            raise ValueError(f"malformed checksum line {line_number}")
        expected, relative_path = parts
        if any(ord(char) < 32 or ord(char) == 127 for char in relative_path):
            raise ValueError(f"path contains control characters on line {line_number}")
        if "\\" in relative_path:
            raise ValueError(f"non-posix path {relative_path}")
        target = root / relative_path
        target_resolved = target.resolve(strict=False)
        try:
            canonical_relative_path = target_resolved.relative_to(root_resolved).as_posix()
        except ValueError as exc:
            raise ValueError(f"{relative_path}: escapes release root") from exc
        if relative_path != canonical_relative_path:
            raise ValueError(f"non-canonical path {relative_path}")
        if relative_path == checksum_relative_path:
            raise ValueError("checksum manifest cannot list itself")
        if relative_path in listed_paths:
            raise ValueError(f"duplicate checksum path: {relative_path}")
        listed_paths.add(relative_path)
        if not target_resolved.exists():
            raise ValueError(f"missing {relative_path}")
        if not target_resolved.is_file():
            raise ValueError(f"not a file {relative_path}")
        actual = hashlib.sha256(target_resolved.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"{relative_path}: {actual} != {expected}")
        results.append(f"{relative_path}: OK")
    if not results:
        raise ValueError("no checksum entries")
    release_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    unlisted_paths = sorted(release_files - listed_paths - {checksum_relative_path})
    if unlisted_paths:
        raise ValueError(f"unlisted {unlisted_paths[0]}")
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate release checksums with Python hashlib.")
    parser.add_argument("--root", default="release/yizijue-lm-public")
    parser.add_argument("--checksums", default="release/checksums.txt")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root)
    checksum_path = root / args.checksums
    try:
        results = check_checksums(root=root, checksum_path=checksum_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
