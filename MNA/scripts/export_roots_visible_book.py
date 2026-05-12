#!/usr/bin/env python3

import argparse
from pathlib import Path

from roots_engine_v2_rewrite import render_json_file


def verse_sort_key(path: Path):
    try:
        chapter = int(path.parent.name)
    except ValueError:
        chapter = 999999
    try:
        verse = int(path.stem)
    except ValueError:
        verse = 999999
    return chapter, verse


def export_book(book: str, base_dir: Path, out_path: Path) -> int:
    book_dir = base_dir / book
    if not book_dir.exists():
        raise FileNotFoundError(f"Book directory not found: {book_dir}")

    json_files = sorted(book_dir.glob("*/*.json"), key=verse_sort_key)
    if not json_files:
        raise FileNotFoundError(f"No verse JSON files found under: {book_dir}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [f"# ROOTS Vista Estructural — {book}\n"]
    count = 0

    for path in json_files:
        chapter, verse = verse_sort_key(path)
        rendered = render_json_file(path).strip()
        parts.append(f"\n## {book} {chapter}:{verse}\n")
        parts.append("\n```text\n")
        parts.append(rendered)
        parts.append("\n```\n")
        count += 1

    out_path.write_text("".join(parts), encoding="utf-8")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Export all available verse-level ROOTS visible structures for one book."
    )
    parser.add_argument("book", help="Book folder name under MNA/data/interlinear, e.g. 1corintios")
    parser.add_argument(
        "--base-dir",
        default="MNA/data/interlinear",
        help="Base interlinear JSON directory. Default: MNA/data/interlinear",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output Markdown path. Default: MNA/outputs/roots-visible/{book}.md",
    )
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("MNA/outputs/roots-visible") / f"{args.book}.md"
    count = export_book(args.book, Path(args.base_dir), out_path)
    print(f"Exported {count} verses to {out_path}")


if __name__ == "__main__":
    main()
