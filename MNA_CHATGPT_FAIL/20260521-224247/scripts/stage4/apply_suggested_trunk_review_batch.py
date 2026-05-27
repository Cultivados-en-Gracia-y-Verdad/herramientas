#!/usr/bin/env python3
"""
MNA Stage 4 — Apply Suggested Trunk Review Batch

PURPOSE
- Apply multiple reviewed trunk decisions from a JSONL batch file.
- Avoid verse-by-verse command repetition.
- Preserve the same safety rules as the single-row review applier.

BATCH ROW FORMAT
{
  "reference": "1corintios 9:23",
  "review_result": "GOOD",
  "status": "REVIEWED_FOR_MANUAL_USE",
  "confidence": "MEDIUM-HIGH",
  "trunk_greek": "...",
  "trunk_translation": "",
  "notes": "...",
  "reviewer": "ChatGPT",
  "manual_use": true,
  "human_override": false
}

Safety rule:
- Existing human_override=true rows are not overwritten unless --force is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-apply-suggested-trunk-review-batch-v1"

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
        raise FileNotFoundError(f"File not found: {path}")

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


def validate_decision(decision: dict, line_number: int) -> None:
    required = ["reference", "review_result", "status", "confidence", "trunk_greek", "notes"]
    missing = [key for key in required if key not in decision]
    if missing:
        raise ValueError(f"Batch row {line_number} missing required fields: {missing}")

    if decision["review_result"] not in VALID_REVIEW_RESULTS:
        raise ValueError(f"Batch row {line_number} invalid review_result: {decision['review_result']}")
    if decision["status"] not in VALID_STATUS:
        raise ValueError(f"Batch row {line_number} invalid status: {decision['status']}")
    if decision["confidence"] not in VALID_CONFIDENCE:
        raise ValueError(f"Batch row {line_number} invalid confidence: {decision['confidence']}")


def apply_decision(row: dict, decision: dict) -> dict:
    updated = dict(row)
    updated["trunk_greek"] = decision["trunk_greek"]

    if "trunk_translation" in decision:
        updated["trunk_translation"] = decision.get("trunk_translation") or ""

    updated["status"] = decision["status"]
    updated["confidence"] = decision["confidence"]
    updated["review_result"] = decision["review_result"]
    updated["reviewer"] = decision.get("reviewer") or "ChatGPT"
    updated["review_notes"] = decision["notes"]
    updated["reviewed_for_manual_use"] = bool(decision.get("manual_use", True))
    updated["user_greek_review_required"] = False
    updated["user_review_scope"] = "Spanish/manual clarity only. Greek structural decision reviewed separately."
    updated["human_override"] = bool(decision.get("human_override", False))
    updated["review_version"] = VERSION
    return updated


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a batch of reviewed trunk decisions.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("batch_file", help="Path to JSONL batch review file")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing human_override=true rows")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        dataset_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        batch_path = Path(args.batch_file)
        if not batch_path.is_absolute():
            batch_path = (Path.cwd() / batch_path).resolve()

        metadata, rows = load_jsonl(dataset_path)
        _batch_metadata, decisions = load_jsonl(batch_path)

        if metadata is None:
            metadata = {"record_type": "metadata", "book": book}

        by_ref = {str(row.get("reference")): row for row in rows}

        applied = []
        skipped = []

        for line_number, decision in enumerate(decisions, start=1):
            validate_decision(decision, line_number)
            reference = str(decision["reference"])
            row = by_ref.get(reference)
            if row is None:
                skipped.append({"reference": reference, "reason": "reference_not_found"})
                continue
            if row.get("human_override") is True and not args.force:
                skipped.append({"reference": reference, "reason": "protected_human_override"})
                continue
            by_ref[reference] = apply_decision(row, decision)
            applied.append(reference)

        final_rows = sort_rows(list(by_ref.values()))

        metadata["record_type"] = "metadata"
        metadata["stage"] = "Stage 4 — Suggested Trunk"
        metadata["version"] = VERSION
        metadata["book"] = book
        metadata["last_batch_file"] = str(batch_path)
        metadata["last_batch_applied_count"] = len(applied)
        metadata["last_batch_skipped_count"] = len(skipped)
        metadata["policy"] = "Suggested trunk; Greek structural decisions reviewed separately; user review scope is Spanish/manual clarity."

        write_jsonl(dataset_path, metadata, final_rows)

        print("MNA Stage 4 — Apply Suggested Trunk Review Batch")
        print(f"BOOK: {book}")
        print(f"DATASET: {dataset_path}")
        print(f"BATCH: {batch_path}")
        print(f"APPLIED: {len(applied)}")
        print(f"SKIPPED: {len(skipped)}")
        if skipped:
            print("SKIPPED ITEMS:")
            for item in skipped:
                print(f"  - {item['reference']}: {item['reason']}")
        print()
        print("APPLIED PREVIEW:")
        for idx, reference in enumerate(applied[: args.preview_lines], start=1):
            row = by_ref[reference]
            print(f"{idx:>4}. {reference} | {row.get('confidence')} | {row.get('trunk_greek')}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 apply suggested trunk review batch FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
