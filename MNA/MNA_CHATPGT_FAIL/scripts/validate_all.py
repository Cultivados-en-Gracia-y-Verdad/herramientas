#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path

BASE = Path(".")

ALIGN_ROOT = BASE / "data" / "alignments"
G_ROOT = BASE / "data" / "g-tokens"
S_ROOT = BASE / "data" / "s-tokens"
VALIDATOR = BASE / "scripts" / "validate_alignment.py"


def alignment_files_for_book(book):
    align_dir = ALIGN_ROOT / book

    if not align_dir.exists():
        print(f"ERROR: alignment directory not found: {align_dir}")
        raise SystemExit(1)

    return sorted(
        p for p in align_dir.glob("*.tsv")
        if not p.name.endswith(".original.tsv")
    )


def parse_stem(stem, fallback_book):
    parts = stem.split("-")

    if len(parts) != 3:
        raise ValueError(
            f"Cannot parse alignment filename: {stem}. "
            "Expected format: book-ch-vs.tsv"
        )

    book, ch, vs = parts
    return book or fallback_book, ch, vs


def validate_book(book):
    failures = []
    files = alignment_files_for_book(book)

    for alignment_file in files:
        stem = alignment_file.stem
        file_book, ch, vs = parse_stem(stem, book)

        token_name = f"{file_book}-{ch}-{vs}.txt"

        g_file = G_ROOT / file_book / token_name
        s_file = S_ROOT / file_book / token_name

        if not g_file.exists():
            failures.append((stem, f"Missing Greek token file: {g_file}"))
            continue

        if not s_file.exists():
            failures.append((stem, f"Missing Spanish token file: {s_file}"))
            continue

        result = subprocess.run(
            [
                "python3",
                str(VALIDATOR),
                str(g_file),
                str(s_file),
                str(alignment_file),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"PASS {stem}")
        else:
            print(f"FAIL {stem}")
            message = result.stdout.strip() or result.stderr.strip()
            failures.append((stem, message))

    return failures


def main():
    if len(sys.argv) == 2:
        books = [sys.argv[1]]
    else:
        books = sorted(
            p.name for p in ALIGN_ROOT.iterdir()
            if p.is_dir()
        )

    all_failures = []

    for book in books:
        print()
        print(f"BOOK: {book}")
        print("-" * (6 + len(book)))

        failures = validate_book(book)
        all_failures.extend((book, stem, message) for stem, message in failures)

    print()

    if all_failures:
        print("SUMMARY: FAIL")
        print()

        for book, stem, message in all_failures:
            print(f"--- {book}/{stem} ---")
            print(message)
            print()

        raise SystemExit(1)

    print("SUMMARY: ALL PASS")


if __name__ == "__main__":
    main()