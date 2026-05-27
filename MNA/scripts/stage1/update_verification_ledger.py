#!/usr/bin/env python3
"""
MNA Stage 1 — verification ledger updater.

PURPOSE
- Recompute Stage 1 verbal counts directly from MorphGNT.
- Update audits/stage1-verification-ledger.tsv for one book.
- Replace an existing book row instead of duplicating it.
- Keep the ledger deterministic and machine-readable.

ABSOLUTE LIMITS
This script does NOT determine predicates, clauses, subjects, trunk,
continuity, movement, outlines, theology, or commentary.

LEDGER RULE
A book may be written as PASS only when:
- every verbal token is accounted for, and
- unresolved/unrecognized verbal morphology is 0.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Optional

import build_finite_verbs as stage1

LEDGER_COLUMNS = [
    "BOOK",
    "SOURCE_FILE",
    "TOTAL_BOOK_TOKENS",
    "TOTAL_VERBAL_TOKENS",
    "FINITE_VERBS",
    "PARTICIPLES",
    "INFINITIVES",
    "NONFINITE_OTHER",
    "UNRESOLVED",
    "STATUS",
    "SCRIPT_VERSION",
    "DATE_VERIFIED",
]


def classify_verbal_token(pos: str, parsing: str) -> str:
    finite = stage1.finite_features(pos, parsing)
    if finite is not None:
        return "finite"

    combined = f"{pos}{parsing}"
    if len(combined) >= 6:
        mood_slot = combined[5]
        if mood_slot == "P":
            return "participle"
        if mood_slot == "N":
            return "infinitive"

    return "unresolved"


def compute_counts(book: str, source: Path) -> Counter:
    if book not in stage1.BOOK_CODES:
        known = ", ".join(sorted(stage1.BOOK_CODES))
        raise ValueError(f"Unknown book '{book}'. Known books: {known}")

    book_code = stage1.BOOK_CODES[book]
    counts: Counter = Counter()

    for morph in stage1.iter_morph_lines(source, book_code):
        counts["TOTAL_BOOK_TOKENS"] += 1

        if not morph.pos.startswith("V"):
            continue

        counts["TOTAL_VERBAL_TOKENS"] += 1
        category = classify_verbal_token(morph.pos, morph.parsing)

        if category == "finite":
            counts["FINITE_VERBS"] += 1
        elif category == "participle":
            counts["PARTICIPLES"] += 1
        elif category == "infinitive":
            counts["INFINITIVES"] += 1
        else:
            counts["UNRESOLVED"] += 1

    counts["NONFINITE_OTHER"] = 0
    return counts


def make_row(book: str, source: Path, counts: Counter, date_verified: str) -> dict[str, str]:
    accounted = (
        counts["FINITE_VERBS"]
        + counts["PARTICIPLES"]
        + counts["INFINITIVES"]
        + counts["NONFINITE_OTHER"]
        + counts["UNRESOLVED"]
    )

    if accounted != counts["TOTAL_VERBAL_TOKENS"]:
        status = "FAIL"
    elif counts["UNRESOLVED"] != 0:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "BOOK": book,
        "SOURCE_FILE": source.name,
        "TOTAL_BOOK_TOKENS": str(counts["TOTAL_BOOK_TOKENS"]),
        "TOTAL_VERBAL_TOKENS": str(counts["TOTAL_VERBAL_TOKENS"]),
        "FINITE_VERBS": str(counts["FINITE_VERBS"]),
        "PARTICIPLES": str(counts["PARTICIPLES"]),
        "INFINITIVES": str(counts["INFINITIVES"]),
        "NONFINITE_OTHER": str(counts["NONFINITE_OTHER"]),
        "UNRESOLVED": str(counts["UNRESOLVED"]),
        "STATUS": status,
        "SCRIPT_VERSION": stage1.VERSION,
        "DATE_VERIFIED": date_verified,
    }


def read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != LEDGER_COLUMNS:
            raise ValueError(
                "Ledger columns do not match expected schema. "
                f"Expected {LEDGER_COLUMNS}, found {reader.fieldnames}"
            )
        return list(reader)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda row: row["BOOK"])

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def update_ledger(book: str, source: Path, ledger_path: Path, date_verified: str) -> dict[str, str]:
    counts = compute_counts(book, source)
    new_row = make_row(book, source, counts, date_verified)

    rows = read_existing_rows(ledger_path)
    rows = [row for row in rows if row["BOOK"] != book]
    rows.append(new_row)
    write_rows(ledger_path, rows)

    return new_row


def print_visible_output(book: str, source: Path, ledger_path: Path, row: dict[str, str]) -> None:
    print("MNA Stage 1 — Verification Ledger Updated")
    print(f"BOOK: {book}")
    print(f"SOURCE: {source}")
    print(f"LEDGER: {ledger_path}")
    print(f"TOTAL BOOK TOKENS: {row['TOTAL_BOOK_TOKENS']}")
    print(f"TOTAL VERBAL TOKENS: {row['TOTAL_VERBAL_TOKENS']}")
    print(f"FINITE VERBS: {row['FINITE_VERBS']}")
    print(f"PARTICIPLES: {row['PARTICIPLES']}")
    print(f"INFINITIVES: {row['INFINITIVES']}")
    print(f"NONFINITE OTHER: {row['NONFINITE_OTHER']}")
    print(f"UNRESOLVED: {row['UNRESOLVED']}")
    print(f"STATUS: {row['STATUS']}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update MNA Stage 1 verification ledger for one book.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source file path")
    parser.add_argument("--ledger", help="Explicit ledger TSV path")
    parser.add_argument("--date", required=True, help="Verification date in YYYY-MM-DD format")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = stage1.mna_root_from_script()

    try:
        source = stage1.resolve_source(mna_root, book, args.source)
        ledger_path = Path(args.ledger) if args.ledger else mna_root / "audits" / "stage1-verification-ledger.tsv"
        if not ledger_path.is_absolute():
            ledger_path = (Path.cwd() / ledger_path).resolve()

        row = update_ledger(book, source, ledger_path, args.date)
        print_visible_output(book, source, ledger_path, row)
        return 0 if row["STATUS"] == "PASS" else 2
    except Exception as exc:
        print("MNA Stage 1 Ledger Update FAILED", file=__import__("sys").stderr)
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
