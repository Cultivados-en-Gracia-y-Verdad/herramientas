#!/usr/bin/env python3
"""
MNA Stage 1 audit — finite verb verification.

PURPOSE
- Read the same MorphGNT source used by Stage 1.
- Account for EVERY verbal token in the requested book.
- Classify each verbal token as:
  - finite_counted,
  - nonfinite_participle,
  - nonfinite_infinitive,
  - nonfinite_other,
  - unrecognized_verbal_morphology.
- Write a human-readable audit report.
- Print exact unrecognized verbal rows when any exist.
- Fail visibly if verbal accounting is inconsistent.

ABSOLUTE LIMITS
This audit does NOT determine predicates, clauses, subjects, trunk,
continuity, movement, outlines, theology, or commentary.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import build_finite_verbs as stage1

VERSION = "stage1-finite-verb-audit-v2"


def classify_verbal_token(pos: str, parsing: str) -> str:
    finite = stage1.finite_features(pos, parsing)
    if finite is not None:
        return "finite_counted"

    combined = f"{pos}{parsing}"

    # MorphGNT parsing format for verbs uses mood in the fourth grammatical
    # slot after V-. Examples:
    # V--PAN---- = present active infinitive
    # V--PAPNSM- = present active participle nominative singular masculine
    # V--AAPNSM- = aorist active participle nominative singular masculine
    if len(combined) >= 6:
        mood_slot = combined[5]
        if mood_slot == "N":
            return "nonfinite_infinitive"
        if mood_slot == "P":
            return "nonfinite_participle"

    return "unrecognized_verbal_morphology"


def audit_book(book: str, source: Path, output_path: Path, mna_root: Path) -> tuple[Counter, dict[str, list[stage1.MorphLine]], Counter]:
    if book not in stage1.BOOK_CODES:
        known = ", ".join(sorted(stage1.BOOK_CODES))
        raise ValueError(f"Unknown book '{book}'. Known books: {known}")

    book_code = stage1.BOOK_CODES[book]
    counts: Counter = Counter()
    examples: dict[str, list[stage1.MorphLine]] = defaultdict(list)
    morph_counts: Counter = Counter()

    for morph in stage1.iter_morph_lines(source, book_code):
        counts["total_book_tokens_seen"] += 1

        if not morph.pos.startswith("V"):
            continue

        counts["total_verbal_tokens_seen"] += 1
        category = classify_verbal_token(morph.pos, morph.parsing)
        counts[category] += 1
        morph_counts[f"{morph.pos}{morph.parsing}"] += 1

        # For unrecognized forms, keep all examples. For large normal categories,
        # keep only a bounded sample so the audit remains readable.
        if category == "unrecognized_verbal_morphology" or len(examples[category]) < 30:
            examples[category].append(morph)

    accounted = (
        counts["finite_counted"]
        + counts["nonfinite_participle"]
        + counts["nonfinite_infinitive"]
        + counts["nonfinite_other"]
        + counts["unrecognized_verbal_morphology"]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# MNA Stage 1 Audit — Finite Verbs: {book}\n\n")
        handle.write("## Source\n\n")
        handle.write(f"- source: `{stage1.relpath_or_abs(source, mna_root)}`\n")
        handle.write("- producer_script: `scripts/stage1/audit_finite_verbs.py`\n")
        handle.write(f"- producer_command: `python3 scripts/stage1/audit_finite_verbs.py {book}`\n")
        handle.write("- generated_at: `DETERMINISTIC-NOT-RUNTIME-STAMPED`\n")
        handle.write(f"- version: `{VERSION}`\n\n")

        handle.write("## Mechanical Rule\n\n")
        handle.write("A verbal token is counted as finite only when MorphGNT morphology marks finite mood and person/number.\n\n")
        handle.write("This audit accounts for every verbal token read from MorphGNT for the requested book.\n\n")

        handle.write("## Counts\n\n")
        for key in [
            "total_book_tokens_seen",
            "total_verbal_tokens_seen",
            "finite_counted",
            "nonfinite_participle",
            "nonfinite_infinitive",
            "nonfinite_other",
            "unrecognized_verbal_morphology",
        ]:
            handle.write(f"- {key}: {counts[key]}\n")
        handle.write(f"- accounted_verbal_tokens: {accounted}\n\n")

        handle.write("## Status\n\n")
        if accounted == counts["total_verbal_tokens_seen"] and counts["unrecognized_verbal_morphology"] == 0:
            handle.write("PASS: all verbal tokens are accounted for, and no verbal morphology is unrecognized.\n\n")
        elif accounted == counts["total_verbal_tokens_seen"]:
            handle.write("REVIEW: all verbal tokens are accounted for, but some verbal morphology is unrecognized.\n\n")
        else:
            handle.write("FAIL: verbal token accounting mismatch.\n\n")

        handle.write("## Rows by Category\n\n")
        for category in [
            "finite_counted",
            "nonfinite_participle",
            "nonfinite_infinitive",
            "nonfinite_other",
            "unrecognized_verbal_morphology",
        ]:
            handle.write(f"### {category}\n\n")
            if not examples[category]:
                handle.write("[none]\n\n")
                continue
            handle.write("| reference | greek | lemma | morph | source_line | raw |\n")
            handle.write("|---|---|---|---:|---:|---|\n")
            for morph in examples[category]:
                raw = morph.raw.replace("|", "\\|")
                handle.write(
                    f"| {book} {morph.chapter}:{morph.verse} | {morph.greek} | {morph.lemma} | {morph.pos}{morph.parsing} | {morph.source_line_number} | `{raw}` |\n"
                )
            handle.write("\n")

        handle.write("## Morphology Counts\n\n")
        handle.write("| morph | count |\n")
        handle.write("|---|---:|\n")
        for morph_code, count in sorted(morph_counts.items()):
            handle.write(f"| {morph_code} | {count} |\n")

    return counts, examples, morph_counts


def print_visible_output(book: str, source: Path, output_path: Path, counts: Counter, examples: dict[str, list[stage1.MorphLine]]) -> None:
    accounted = (
        counts["finite_counted"]
        + counts["nonfinite_participle"]
        + counts["nonfinite_infinitive"]
        + counts["nonfinite_other"]
        + counts["unrecognized_verbal_morphology"]
    )

    print("MNA Stage 1 Audit — Finite Verb Verification")
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
    print(f"ACCOUNTED VERBAL TOKENS: {accounted}")

    if counts["unrecognized_verbal_morphology"]:
        print()
        print("UNRECOGNIZED ROWS:")
        for morph in examples["unrecognized_verbal_morphology"]:
            print(
                f"- {book} {morph.chapter}:{morph.verse} | {morph.greek} | lemma={morph.lemma} | "
                f"morph={morph.pos}{morph.parsing} | line={morph.source_line_number}"
            )

    if accounted != counts["total_verbal_tokens_seen"]:
        print("STATUS: FAIL — verbal token accounting mismatch")
    elif counts["unrecognized_verbal_morphology"]:
        print("STATUS: REVIEW — all verbal tokens accounted, but some morphology unrecognized")
    else:
        print("STATUS: PASS — all verbal tokens accounted")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit MNA Stage 1 finite verb extraction.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source file path")
    parser.add_argument("--output", help="Explicit audit report path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = stage1.mna_root_from_script()

    try:
        source = stage1.resolve_source(mna_root, book, args.source)
        output_path = Path(args.output) if args.output else mna_root / "audits" / "finite-verbs" / f"{book}.md"
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

        counts, examples, _morph_counts = audit_book(book, source, output_path, mna_root)
        print_visible_output(book, source, output_path, counts, examples)

        accounted = (
            counts["finite_counted"]
            + counts["nonfinite_participle"]
            + counts["nonfinite_infinitive"]
            + counts["nonfinite_other"]
            + counts["unrecognized_verbal_morphology"]
        )
        if accounted != counts["total_verbal_tokens_seen"]:
            return 2
        if counts["unrecognized_verbal_morphology"]:
            return 3
        return 0
    except Exception as exc:
        print("MNA Stage 1 Audit FAILED", file=__import__("sys").stderr)
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
