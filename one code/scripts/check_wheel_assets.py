#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


REQUIRED_ASSETS = {
    "onecode/tui/styles.tcss",
    "onecode/contracts/shell_projection_v4_schema.json",
    "onecode/contracts/shell_projection_v4_cases.json",
    "onecode/contracts/shell_projection_v5_schema.json",
    "onecode/contracts/shell_projection_v5_cases.json",
}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: check_wheel_assets.py WHEEL_DIR", file=sys.stderr)
        return 2

    wheel_dir = Path(args[0])
    wheels = sorted(wheel_dir.glob("onecode-*.whl"))
    if len(wheels) != 1:
        print(f"expected exactly one onecode wheel in {wheel_dir}, found {len(wheels)}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())

    missing = sorted(REQUIRED_ASSETS - names)
    if missing:
        print("missing wheel assets: " + ", ".join(missing), file=sys.stderr)
        return 1

    print(f"wheel assets ok: {wheels[0].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
