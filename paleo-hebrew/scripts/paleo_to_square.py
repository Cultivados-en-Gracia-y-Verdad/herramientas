#!/usr/bin/env python3
"""Convert Paleo-Hebrew (Phoenician Unicode) back to square Hebrew."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hebrew_text import normalize_hebrew
from letter_map import load_paleo_to_square


def convert(text: str) -> str:
    mapping = load_paleo_to_square()
    return "".join(mapping.get(char, char) for char in normalize_hebrew(text))


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Paleo-Hebrew to square Hebrew.")
    parser.add_argument("text", nargs="?", help="Paleo text to convert")
    parser.add_argument("--input", "-i", type=Path, help="Input text file (UTF-8)")
    parser.add_argument("--output", "-o", type=Path, help="Output text file (UTF-8)")
    args = parser.parse_args()

    if args.input:
        text = args.input.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        parser.error("provide text argument or --input")

    result = convert(text)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + ("\n" if not result.endswith("\n") else ""), encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
