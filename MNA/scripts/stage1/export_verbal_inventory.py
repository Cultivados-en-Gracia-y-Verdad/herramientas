#!/usr/bin/env python3
"""
MNA Stage 1 inventory — complete verbal-token verification list.

PURPOSE
- Read the canonical MorphGNT source for one book.
- Export EVERY verbal token to TSV.
- Mark whether each verbal token is finite or non-finite.
- Make the finite count independently inspectable row by row.

WHY THIS EXISTS
A summary count can pass while still leaving one-count questions unresolved.
This inventory gives a complete visible list so disagreements such as
1027 vs. 1028 can be checked against the actual source rows.

ABSOLUTE LIMITS
This script does NOT determine predicates, clauses, subjects, trunk,
continuity, movement, outlines, theology, or commentary.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import audit_finite_verbs as audit
import build_finite_verbs as stage1

VERSION = "stage1-verbal-inventory-v1"


def export_inventory(book: str, source: Path, output_path: Path, mna_root: Path) -> dict[str, int]:
    if book not in stage1.BOOK_CODES:
        known = ", ".join(sorted(stage1.BOOK_CODES))
        raise ValueError(f"Unknown book '{book}'. Known books: {known}")

    book_code = stage1.BOOK_CODES[book]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counts = {
        "total_book_tokens_seen": 0,
        "total_verbal_tokens_seen": 0,
        "finite_counted": 0,
        "nonfinite_participle": 0,
        "nonfinite_infinitive": 0,
        "nonfinite_other": 0,
        "unrecognized_verbal_morphology": 0,
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "BOOK\tCH\tVS\tREFERENCE\tSOURCE_LINE\tTOKEN_IN_VERSE\tGREEK\tLEMMA\tPOS\tPARSING\tMORPH\tCATEGORY\tFINITE\tMOOD\tPERSON\tNUMBER\tRAW\n"
        )

        for morph in stage1.iter_morph_lines(source, book_code):
            counts["total_book_tokens_seen"] += 1
            if not morph.pos.startswith("V"):
                continue

            counts["total_verbal_tokens_seen"] += 1
            category = audit.classify_verbal_token(morph.pos, morph.parsing)
            counts[category] += 1

            features = stage1.finite_features(morph.pos, morph.parsing)
            finite = "yes" if features else "no"
            mood = features["mood"] if features else ""
            person = features["person_code"] if features else ""
            number = features["number_code"] if features else ""

            handle.write(
                "\t".join(
                    [
                        book,
                        str(morph.chapter),
                        str(morph.verse),
                        f"{book} {morph.chapter}:{morph.verse}",
                        str(morph.source_line_number),
                        str(morph.token_index_in_verse),
                        morph.greek,
                        morph.lemma,
                        morph.pos,
                        morph.parsing,
                        f"{morph.pos}{morph.parsing}",
                        category,
                        finite,
                        mood,
                        person,
                        number,
                        morph.raw,
                    ]
                )
                + "\n"
            )

    return counts


def print_visible_output(book: str, source: Path, output_path: Path, counts: dict[str, int]) -> None:
    print("MNA Stage 1 Inventory — Verbal Tokens")
    print(f"BOOK: {book}")
    print(f"SOURCE: {source}")
    print(f"OUTPUT: {output_path}")
    print(f"TOTAL BOOK TOKENS SEEN: {counts['total_book_tokens_seen']}")
    print(f"TOTAL VERBAL TOKENS SEEN: {counts['total_verbal_tokens_seen']}")
    print(f"FINITE COUNTED: {counts['finite_counted']}")
    print(f"NONFINITE PARTICIPLES: {counts['nonfinite_participle']}")
    print(f"NONFINITE INFINITIVES: {counts['nonfinite_infinitive']}")
    print(f"NONFINITE OTHER: {counts['nonfinite_other']}")
    print(f"UNRECOGNIZED VERBAL MORPHOLOGY: {counts['unrecognized_verbal_morphology']}")
    print("STATUS: INVENTORY WRITTEN")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export complete Stage 1 verbal inventory TSV.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source file path")
    parser.add_argument("--output", help="Explicit output TSV path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = stage1.mna_root_from_script()

    try:
        source = stage1.resolve_source(mna_root, book, args.source)
        output_path = Path(args.output) if args.output else mna_root / "audits" / "finite-verbs" / f"{book}-verbal-inventory.tsv"
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

        counts = export_inventory(book, source, output_path, mna_root)
        print_visible_output(book, source, output_path, counts)
        return 0 if counts["unrecognized_verbal_morphology"] == 0 else 3
    except Exception as exc:
        print("MNA Stage 1 Inventory FAILED", file=__import__("sys").stderr)
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
