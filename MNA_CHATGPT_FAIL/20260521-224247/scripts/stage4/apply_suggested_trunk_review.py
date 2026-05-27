#!/usr/bin/env python3
"""
MNA Stage 4 — Apply Suggested Trunk Review

PURPOSE
- Apply reviewed structural decisions to datasets/suggested-trunk/<book>.jsonl.
- Avoid manual JSON editing for Greek trunk decisions.
- Preserve review notes, confidence, and reviewer identity.

IMPORTANT
This script does NOT generate Greek decisions.
It only records reviewed decisions already supplied by the reviewer.

Safety rule:
- Existing human_override=true rows are not overwritten unless --force is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-apply-suggested-trunk-review-v1"

VALID_REVIEW_RESULTS = {
    "GOOD",
    "TOO_SHORT",
    "TOO_LONG",
    "DEPENDENT_TAIL_LEFT",
    "MAIN_FORCE_MISSING",
    "UNCLEAR",
    "REVISED",
}

VALID_STATUS = {
    "AI_REVIEWED",
    "NEEDS_EXTERNAL_GREEK_REVIEW",
    "REVIEWED_FOR_MANUAL_USE",
}

VALID_CONFIDENCE = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "MEDIUM-HIGH",
    "MEDIUM-LOW",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        raise FileNotFoundError(f"Suggested trunk dataset not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def write_jsonl(path: Path, metadata: dict, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0))))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a reviewed trunk decision to suggested-trunk JSONL.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("reference", help="Reference string exactly as stored, e.g. '1corintios 1:10'")
    parser.add_argument("--review-result", required=True, choices=sorted(VALID_REVIEW_RESULTS))
    parser.add_argument("--status", default="REVIEWED_FOR_MANUAL_USE", choices=sorted(VALID_STATUS))
    parser.add_argument("--confidence", default="MEDIUM", choices=sorted(VALID_CONFIDENCE))
    parser.add_argument("--trunk-greek", help="Replacement Greek trunk, if revised")
    parser.add_argument("--trunk-translation", help="Optional Spanish/manual working translation")
    parser.add_argument("--notes", default="")
    parser.add_argument("--reviewer", default="ChatGPT")
    parser.add_argument("--manual-use", action="store_true", help="Mark reviewed_for_manual_use=true")
    parser.add_argument("--human-override", action="store_true", help="Mark human_override=true")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing human_override=true row")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"

        metadata, rows = load_jsonl(path)
        if metadata is None:
            metadata = {"record_type": "metadata", "book": book}

        matched = False
        for row in rows:
            if str(row.get("reference")) != args.reference:
                continue

            matched = True

            if row.get("human_override") is True and not args.force:
                raise PermissionError(
                    f"Refusing to overwrite human_override=true row for {args.reference}. Use --force if intentional."
                )

            if args.trunk_greek is not None:
                row["trunk_greek"] = args.trunk_greek

            if args.trunk_translation is not None:
                row["trunk_translation"] = args.trunk_translation

            row["status"] = args.status
            row["confidence"] = args.confidence
            row["review_result"] = args.review_result
            row["reviewer"] = args.reviewer
            row["review_notes"] = args.notes
            row["reviewed_for_manual_use"] = bool(args.manual_use)
            row["user_greek_review_required"] = False
            row["user_review_scope"] = "Spanish/manual clarity only. Greek structural decision reviewed separately."
            row["human_override"] = bool(args.human_override)
            row["review_version"] = VERSION
            break

        if not matched:
            raise KeyError(f"Reference not found in {path}: {args.reference}")

        rows = sort_rows(rows)

        metadata["record_type"] = "metadata"
        metadata["stage"] = "Stage 4 — Suggested Trunk"
        metadata["version"] = VERSION
        metadata["book"] = book
        metadata["last_reviewed_reference"] = args.reference
        metadata["last_review_result"] = args.review_result
        metadata["policy"] = "Suggested trunk; Greek structural decisions reviewed separately; user review scope is Spanish/manual clarity."

        write_jsonl(path, metadata, rows)

        print("MNA Stage 4 — Apply Suggested Trunk Review")
        print(f"BOOK: {book}")
        print(f"FILE: {path}")
        print(f"REFERENCE: {args.reference}")
        print(f"REVIEW RESULT: {args.review_result}")
        print(f"STATUS: {args.status}")
        print(f"CONFIDENCE: {args.confidence}")
        print(f"REVIEWED FOR MANUAL USE: {bool(args.manual_use)}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 apply suggested trunk review FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
