#!/usr/bin/env python3
"""
Remove redundant MNA Extra lines.

This script is intentionally narrow. It only removes an Extra line when the
verse alignment already covers every normalized word in that Extra span.

Usage:
  python3 clean_mna_extras.py path/to/mna-clean.md
  python3 clean_mna_extras.py path/to/mna-clean.md --write
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from validate_mna import Verse, list_multiset_diff, parse_mna_markdown, span_words, tokenize_spanish_words


@dataclass
class Removal:
    ref: str
    line_no: int
    span: str


def alignment_coverage(v: Verse) -> Counter[str]:
    covered: Counter[str] = Counter()
    for alignment in v.alignments:
        if alignment.atype == "merged-backward":
            continue
        covered.update(span_words(alignment.span))
    return covered


def required_extra_words(v: Verse) -> Counter[str]:
    nbla_words = tokenize_spanish_words(v.nbla)
    covered_words = list(alignment_coverage(v).elements())
    return Counter(list_multiset_diff(nbla_words, covered_words))


def removable_extra_lines(verses: list[Verse]) -> list[Removal]:
    removals: list[Removal] = []

    for verse in verses:
        needed = required_extra_words(verse)

        for span, line_no in verse.extras:
            words = span_words(span)
            if not words:
                continue

            extra_counts = Counter(words)
            fills_deficit = all(needed[word] >= count for word, count in extra_counts.items())

            if fills_deficit:
                needed.subtract(extra_counts)
                needed += Counter()
            else:
                removals.append(Removal(verse.ref, line_no, span))

    return removals


def remove_lines(text: str, removals: list[Removal]) -> str:
    remove_line_numbers = {removal.line_no for removal in removals}
    lines = text.splitlines(keepends=True)
    return "".join(
        line for idx, line in enumerate(lines, start=1)
        if idx not in remove_line_numbers
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove redundant MNA Extra lines.")
    parser.add_argument("path", type=Path, help="Path to MNA Markdown file")
    parser.add_argument("--write", action="store_true", help="Rewrite the file in place")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: file not found: {args.path}")
        return 1

    text = args.path.read_text(encoding="utf-8")
    verses = parse_mna_markdown(text)
    removals = removable_extra_lines(verses)

    if not removals:
        print("No redundant Extra lines found.")
        return 0

    for removal in removals:
        print(f"{removal.ref}: line {removal.line_no}: remove redundant Extra: {removal.span}")

    if args.write:
        args.path.write_text(remove_lines(text, removals), encoding="utf-8")
        print(f"Updated {args.path}")
    else:
        print("Dry run only. Re-run with --write to update the file.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
