#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G7_EDITORIAL mechanical gate — speaker/hearing witness required.

Editor + Corrector work is not a G7 PASS by itself. This script must exit 0.

    python3 scripts/verify-g7-editorial.py \\
        --manual curriculo/23.Apocalipsis/manual/manual.md

Exit: 0 PASS · 1 FAIL · 2 usage
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description="G7 mechanical editorial verification.")
    ap.add_argument("--manual", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if not args.manual.is_file():
        print(f"error: no such manual: {args.manual}", file=sys.stderr)
        return 2

    out = args.out
    if out is None:
        out = args.manual.resolve().parent.parent / "reports" / "SPEAKER_HEARING_REPORT.md"

    cmd = [
        sys.executable,
        str(HERE / "verify-speaker-hearing.py"),
        "--manual",
        str(args.manual),
        "--gate",
        "g7",
        "--out",
        str(out),
    ]
    r = subprocess.run(cmd)
    if r.returncode == 0:
        print("G7_EDITORIAL mechanical: PASS (speaker/hearing)")
    else:
        print("G7_EDITORIAL mechanical: FAIL — see SPEAKER_HEARING_REPORT.md", file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
