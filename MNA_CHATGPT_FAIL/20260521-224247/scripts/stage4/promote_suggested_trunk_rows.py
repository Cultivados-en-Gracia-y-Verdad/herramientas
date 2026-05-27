#!/usr/bin/env python3
"""
MNA Stage 4 — Promote Suggested Trunk Rows

PURPOSE
- Promote rows from suggested-trunk-drafts into suggested-trunk.
- Mark promoted rows as AI_REVIEWED only when they pass basic guardrails.
- Preserve existing accepted rows with human_override=true.

IMPORTANT
This script does NOT decide Greek syntax by itself.
It promotes existing draft suggestions into an accepted/review file for controlled use.

Safety rule:
- human_override=true rows are NEVER overwritten.
- incomplete-looking trunk spans are NEVER promoted as AI_REVIEWED.
- spans containing unresolved internal subordinators are review-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

VERSION = "stage4-promote-suggested-trunk-rows-v3-internal-subordinator-guard"

PROMOTED_STATUS = "AI_REVIEWED"
LOW_CONFIDENCE_STATUS = "NEEDS_EXTERNAL_GREEK_REVIEW"

OPEN_ENDING_TOKENS = {
    "ἵνα", "ὅτι", "καθὼς", "καθώς", "εἰ", "ἐὰν", "ὡς", "ὥστε",
    "μή", "μὴ", "οὐ", "οὐκ", "οὐχ", "καὶ", "δὲ", "γὰρ", "ἀλλὰ",
    "ἢ", "τε", "μέν", "μὲν", "πρὸς", "ἐν", "εἰς", "ἐκ", "διὰ", "περὶ",
    "ὑπὲρ", "ὑπὸ", "ἀπὸ", "μετὰ", "κατὰ", "παρὰ", "ἐπὶ",
}

INTERNAL_SUBORDINATOR_TOKENS = {
    "ἵνα", "ὅτι", "καθὼς", "καθώς", "ἐπειδὴ", "ἐπειδή", "εἰ", "ἐὰν", "ὅταν", "ὡς", "ὥστε"
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        return metadata, rows

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


def ref_key(row: dict) -> tuple[int, int]:
    return int(row.get("chapter", 0)), int(row.get("verse", 0))


def parse_ref_bound(value: Optional[str]) -> Optional[tuple[int, int]]:
    if not value:
        return None
    match = re.fullmatch(r"(\d+):(\d+)", value.strip())
    if not match:
        raise ValueError(f"Reference bound must be CHAPTER:VERSE, got: {value}")
    return int(match.group(1)), int(match.group(2))


def in_range(row: dict, start: Optional[tuple[int, int]], end: Optional[tuple[int, int]]) -> bool:
    key = ref_key(row)
    if start is not None and key < start:
        return False
    if end is not None and key > end:
        return False
    return True


def normalize_token(value: str) -> str:
    return re.sub(r"^[^\w\u0370-\u03ff\u1f00-\u1fff]+|[^\w\u0370-\u03ff\u1f00-\u1fff]+$", "", value.strip())


def incomplete_span_reasons(row: dict) -> list[str]:
    reasons = []
    trunk = str(row.get("trunk_greek") or "").strip()

    if not trunk:
        reasons.append("empty_trunk_greek")
        return reasons

    tokens = [normalize_token(tok) for tok in trunk.split() if normalize_token(tok)]
    if not tokens:
        reasons.append("no_tokens_after_normalization")
        return reasons

    last = tokens[-1]
    if last in OPEN_ENDING_TOKENS:
        reasons.append(f"open_ending_token:{last}")

    internal_subordinators = [tok for tok in tokens[:-1] if tok in INTERNAL_SUBORDINATOR_TOKENS]
    for tok in sorted(set(internal_subordinators)):
        reasons.append(f"internal_subordinator_present:{tok}")

    if row.get("needs_review") is True:
        reasons.append("draft_needs_review_true")

    return reasons


def promote_row(row: dict, reviewer: str, force_ai_review: bool) -> dict:
    promoted = dict(row)
    promoted["record_type"] = "suggested_trunk_row"
    promoted["stage"] = "Stage 4 — Suggested Trunk"
    promoted["version"] = VERSION

    guard_reasons = incomplete_span_reasons(row)
    promoted["promotion_guard_reasons"] = guard_reasons

    if guard_reasons and not force_ai_review:
        promoted["status"] = LOW_CONFIDENCE_STATUS
        promoted["needs_review"] = True
    elif row.get("confidence") == "LOW" and not force_ai_review:
        promoted["status"] = LOW_CONFIDENCE_STATUS
        promoted["needs_review"] = True
    else:
        promoted["status"] = PROMOTED_STATUS
        promoted["needs_review"] = bool(row.get("needs_review", False))

    promoted["reviewer"] = reviewer
    promoted["user_greek_review_required"] = False
    promoted["user_review_scope"] = "Spanish/manual clarity only; Greek structural decision reviewed by AI and flagged by confidence."
    promoted["human_override"] = bool(row.get("human_override", False))
    promoted["accepted_dataset_policy"] = "Protected accepted trunk row; do not overwrite human_override=true rows."
    promoted["trunk_claim"] = "SUGGESTED_AI_REVIEWED_NOT_PROVEN"
    return promoted


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0))))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote suggested trunk draft rows into accepted suggested-trunk dataset.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--from", dest="from_ref", help="Start reference bound, e.g. 1:10")
    parser.add_argument("--to", dest="to_ref", help="End reference bound, e.g. 1:17")
    parser.add_argument("--reviewer", default="ChatGPT", help="Reviewer label to write into promoted rows")
    parser.add_argument("--force-ai-review", action="store_true", help="Promote guarded/LOW rows as AI_REVIEWED anyway")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        start = parse_ref_bound(args.from_ref)
        end = parse_ref_bound(args.to_ref)

        draft_path = root / "datasets" / "suggested-trunk-drafts" / f"{book}.jsonl"
        accepted_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"

        _draft_metadata, draft_rows = load_jsonl(draft_path)
        _accepted_metadata, accepted_rows = load_jsonl(accepted_path)

        if not draft_rows:
            raise FileNotFoundError(f"No draft rows found. Run build_suggested_trunk_draft.py first: {draft_path}")

        accepted_by_ref = {str(row.get("reference")): row for row in accepted_rows}

        promoted_count = 0
        protected_count = 0
        skipped_count = 0
        guarded_count = 0

        for row in draft_rows:
            if not in_range(row, start, end):
                skipped_count += 1
                continue

            reference = str(row.get("reference"))
            existing = accepted_by_ref.get(reference)

            if existing and existing.get("human_override") is True:
                protected_count += 1
                continue

            promoted = promote_row(row, args.reviewer, args.force_ai_review)
            if promoted.get("promotion_guard_reasons"):
                guarded_count += 1
            accepted_by_ref[reference] = promoted
            promoted_count += 1

        final_rows = sort_rows(list(accepted_by_ref.values()))

        accepted_path.parent.mkdir(parents=True, exist_ok=True)

        status_counts = {}
        confidence_counts = {}
        for row in final_rows:
            status_counts[row.get("status")] = status_counts.get(row.get("status"), 0) + 1
            confidence_counts[row.get("confidence")] = confidence_counts.get(row.get("confidence"), 0) + 1

        metadata = {
            "record_type": "metadata",
            "stage": "Stage 4 — Suggested Trunk",
            "version": VERSION,
            "book": book,
            "producer_script": "scripts/stage4/promote_suggested_trunk_rows.py",
            "source_draft_dataset": str(draft_path.relative_to(root)),
            "rows_written": len(final_rows),
            "last_promoted_count": promoted_count,
            "last_guarded_count": guarded_count,
            "last_protected_human_override_count": protected_count,
            "last_skipped_out_of_range_count": skipped_count,
            "status_counts": status_counts,
            "confidence_counts": confidence_counts,
            "policy": "AI-reviewed suggested trunk; not mechanically proven; incomplete/internal-subordinator spans cannot be AI_REVIEWED unless forced; human_override=true rows are protected.",
            "user_greek_review_required": False,
            "user_review_scope": "Spanish/manual clarity only.",
        }

        with accepted_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
            for row in final_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        print("MNA Stage 4 — Promote Suggested Trunk Rows")
        print(f"BOOK: {book}")
        print(f"DRAFT: {draft_path}")
        print(f"ACCEPTED: {accepted_path}")
        print(f"RANGE: {args.from_ref or 'START'}–{args.to_ref or 'END'}")
        print(f"PROMOTED: {promoted_count}")
        print(f"GUARDED AS REVIEW-ONLY: {guarded_count}")
        print(f"PROTECTED HUMAN OVERRIDES: {protected_count}")
        print(f"ROWS WRITTEN: {len(final_rows)}")
        print(f"STATUS COUNTS: {status_counts}")
        print("POLICY: AI-reviewed suggested trunk; guarded incomplete/internal-subordinator spans remain review-only.")
        print()
        print("VISIBLE OUTPUT PREVIEW:")
        shown = 0
        for row in final_rows:
            if not in_range(row, start, end):
                continue
            shown += 1
            guards = row.get("promotion_guard_reasons") or []
            guard_text = f" | guards={guards}" if guards else ""
            print(
                f"{shown:>4}. {row.get('reference')} | {row.get('status')} | {row.get('confidence')} | "
                f"trunk={row.get('trunk_greek')}{guard_text}"
            )
            if shown >= args.preview_lines:
                break

        return 0

    except Exception as exc:
        print("MNA Stage 4 suggested trunk promotion FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
