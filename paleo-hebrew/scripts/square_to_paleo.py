#!/usr/bin/env python3
"""Convert square Hebrew text to Paleo-Hebrew (Phoenician Unicode)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hebrew_text import normalize_hebrew, strip_niqqud
from letter_map import load_square_to_paleo


def convert(text: str, *, strip_vowels: bool = False) -> str:
    source = normalize_hebrew(text)
    if strip_vowels:
        source = strip_niqqud(source)

    mapping = load_square_to_paleo()
    return "".join(mapping.get(char, char) for char in source)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert square Hebrew to Paleo-Hebrew.")
    parser.add_argument("text", nargs="?", help="Hebrew text to convert")
    parser.add_argument("--input", "-i", type=Path, help="Input text file (UTF-8)")
    parser.add_argument("--output", "-o", type=Path, help="Output text file (UTF-8)")
    parser.add_argument("--strip-vowels", action="store_true", help="Remove niqqud/cantillation first")
    args = parser.parse_args()

    if args.input:
        text = args.input.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        parser.error("provide text argument or --input")

    result = convert(text, strip_vowels=args.strip_vowels)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + ("\n" if not result.endswith("\n") else ""), encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
