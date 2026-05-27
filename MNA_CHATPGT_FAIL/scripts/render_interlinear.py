#!/usr/bin/env python3

import json
import sys
from pathlib import Path


ROWS = [
    ("NBLA", "nbla"),
    ("Greek", "greek"),
    ("Translit", "translit"),
    ("Lemma", "lemma"),
    ("MorphGNT", "morphgnt"),
    ("RMAC", "rmac"),
    ("Strong’s", "strongs"),
]


def load_verse(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_widths(columns):
    widths = []

    for column in columns:
        values = [str(column.get(field, "")) for _, field in ROWS]
        width = max(len(v) for v in values)
        widths.append(width + 2)

    return widths


def render_row(label, field, columns, widths):
    print(label.ljust(12), end="")

    for column, width in zip(columns, widths):
        value = str(column.get(field, ""))
        print(value.ljust(width), end="")

    print()


def render(verse):
    print()
    print(verse["reference"])
    print()

    columns = verse["columns"]
    widths = compute_widths(columns)

    for label, field in ROWS:
        render_row(label, field, columns, widths)

    print()


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python3 scripts/render_interlinear.py data/interlinear/filemon/1/1.json")
        sys.exit(2)

    verse_path = Path(sys.argv[1])
    verse = load_verse(verse_path)
    render(verse)


if __name__ == "__main__":
    main()