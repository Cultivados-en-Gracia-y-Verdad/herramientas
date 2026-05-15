#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — chapter-level finite predication wrapper

This script does NOT add new structural logic.
It simply runs the proven verse-level builder across every available verse
in a chapter and writes a combined JSONL file.

Usage from repository root:
    python3 MNA/scripts/roots_build_predications_chapter.py 1corintios 1

Usage from MNA directory:
    python3 scripts/roots_build_predications_chapter.py 1corintios 1

Default output:
    MNA/data/predications/<book>-<chapter>.jsonl
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import roots_build_predications as predications


def discover_verses(book: str, chapter: str) -> list[int]:
    root = predications.mna_root()
    token_dir = root / "data" / "g-tokens" / book

    if not token_dir.exists():
        raise FileNotFoundError(token_dir)

    pattern = re.compile(rf"^{re.escape(book)}-{int(chapter)}-(\d+)\.txt$")
    verses: list[int] = []

    for path in token_dir.glob(f"{book}-{int(chapter)}-*.txt"):
        match = pattern.match(path.name)
        if match:
            verses.append(int(match.group(1)))

    return sorted(set(verses))


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    if len(sys.argv) not in {3, 4}:
        print(
            "Usage:\n"
            "  python3 MNA/scripts/roots_build_predications_chapter.py <book> <chapter> [output.jsonl]\n"
            "\nExample:\n"
            "  python3 MNA/scripts/roots_build_predications_chapter.py 1corintios 1",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    chapter = str(int(sys.argv[2]))

    if len(sys.argv) == 4:
        output_path = Path(sys.argv[3])
    else:
        output_path = predications.mna_root() / "data" / "predications" / f"{book}-{chapter}.jsonl"

    verses = discover_verses(book, chapter)
    if not verses:
        raise FileNotFoundError(f"No verse token files found for {book} chapter {chapter}")

    all_records: list[dict[str, Any]] = []
    failures: list[tuple[int, str]] = []

    for verse in verses:
        try:
            records = predications.build_verse(book, chapter, str(verse))
            all_records.extend(records)
            print(f"PASS {book} {chapter}:{verse} | predications={len(records)}")
        except Exception as exc:
            failures.append((verse, str(exc)))
            print(f"FAIL {book} {chapter}:{verse} | {exc}")

    write_jsonl(all_records, output_path)

    print()
    print("SUMMARY")
    print(f"BOOK: {book}")
    print(f"CHAPTER: {chapter}")
    print(f"VERSES FOUND: {len(verses)}")
    print(f"PASS: {len(verses) - len(failures)}")
    print(f"FAIL: {len(failures)}")
    print(f"PREDICATIONS WRITTEN: {len(all_records)}")
    print(f"OUTPUT: {output_path}")

    if failures:
        print()
        print("FAILURES")
        for verse, error in failures:
            print(f"- {book} {chapter}:{verse} | {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
