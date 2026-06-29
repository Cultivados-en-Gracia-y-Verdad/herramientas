#!/usr/bin/env python3
"""Validate BLE verse files (same line grammar as cgv-bible parseNblaContent)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSE_RE = re.compile(r"^(.+?)\s+(\d+):(\d+)\s+(.+)$")
HEADING_RE = re.compile(r"^#+\s*(.+?)\s+(\d+):(\d+)\s*$")


def parse_verses(content: str) -> list[tuple[str, int, int, str]]:
    verses: list[tuple[str, int, int, str]] = []
    for line in content.replace("\r\n", "\n").split("\n"):
        if not line.strip() or line.strip().startswith("<!--"):
            continue
        match = VERSE_RE.match(line) or HEADING_RE.match(line)
        if not match:
            continue
        book, ch, vs, text = match.group(1).strip(), int(match.group(2)), int(match.group(3)), (match.group(4) or "").strip()
        if book and ch and vs:
            verses.append((book, ch, vs, text))
    return verses


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a .ble.md verse file.")
    parser.add_argument("path", type=Path, help="path to .ble.md file")
    args = parser.parse_args()

    content = args.path.read_text(encoding="utf-8")
    verses = parse_verses(content)
    if not verses:
        print(f"error: no verses parsed from {args.path}")
        return 1

    empty = sum(1 for _, _, _, text in verses if not text)
    print(f"verses: {len(verses)}")
    print(f"empty text: {empty}")
    print(f"first: {verses[0][0]} {verses[0][1]}:{verses[0][2]}")
    print(f"last:  {verses[-1][0]} {verses[-1][1]}:{verses[-1][2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
