#!/usr/bin/env python3
"""Fetch/merge all AHRC AHLB letter pages into data/ahrc/strongs.jsonl."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHRC_CATALOG = ROOT / "data" / "sources" / "ahrc.json"
PARSE = ROOT / "scripts" / "parse_ahlb_html.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import all AHLB letter pages.")
    parser.add_argument("--letters", nargs="*", help="Optional subset of letter slugs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(AHRC_CATALOG.read_text(encoding="utf-8"))
    pages = catalog.get("ahlb_letter_pages") or {}
    slugs = args.letters or list(pages.keys())

    for slug in slugs:
        url = pages.get(slug)
        if not url:
            print(f"skip unknown slug: {slug}", file=sys.stderr)
            continue
        cmd = [sys.executable, str(PARSE), "--url", url, "--slug", slug, "--merge"]
        print("RUN:", " ".join(cmd))
        if args.dry_run:
            continue
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc != 0:
            print(f"FAILED {slug} rc={rc}", file=sys.stderr)
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
