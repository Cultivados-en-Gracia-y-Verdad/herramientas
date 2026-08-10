#!/usr/bin/env python3
"""
Promote fully reviewed G0A phrase records from lbf-preliminary to lbf-approved.

Safety properties:
- Requires every G0A queue item to be APPROVED.
- Requires zero PENDING / NEEDS_REVISION / REJECTED / ESCALATE items.
- Requires the queue-level phrase artifact checksum to match the current phrase file.
- Recomputes every item checksum from the current phrase record and source-token evidence.
- Promotes only phrase records represented by APPROVED G0A items.
- Preserves pre-existing lbf-approved records.
- Never modifies Hebrew/Aramaic source fields or Spanish text.
- Writes an audit report and archives the final review queue.
- Dry-run by default. Use --apply to modify the phrase artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_item_checksum(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_dicts(value):
    """Yield every dict recursively from an arbitrary JSON structure."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def build_spine_token_map(spine_doc: dict) -> dict[str, dict]:
    """
    Build a sourceTokenId -> full source evidence map from the OSHB/WLC spine.

    The spine layout may evolve, so this intentionally discovers token objects
    by sourceTokenId instead of depending on a single container shape.
    """
    token_map = {}
    conflicts = []

    for row in iter_dicts(spine_doc):
        token_id = row.get("sourceTokenId")
        if not token_id:
            continue

        normalized = {
            "sourceTokenId": token_id,
            "surface": row.get("surface") or row.get("greek") or "",
            "lang": row.get("lang"),
            "lemma": row.get("lemma"),
            "morph": row.get("morph")
            if "morph" in row
            else row.get("rmac"),
            "gloss": row.get("gloss"),
        }

        existing = token_map.get(token_id)
        if existing is None:
            token_map[token_id] = normalized
        elif existing != normalized:
            conflicts.append(token_id)

    if conflicts:
        raise ValueError(
            "Conflicting duplicate sourceTokenId records in spine: "
            + ", ".join(sorted(set(conflicts))[:20])
        )

    if not token_map:
        raise ValueError(
            "No sourceTokenId records found in the supplied spine."
        )

    return token_map


def normalize_source_tokens(phrase: dict, spine_tokens: dict) -> list[dict]:
    out = []
    for token_id in phrase.get("sourceTokenIds", []):
        row = spine_tokens.get(token_id)
        if row is None:
            raise ValueError(
                f"{phrase.get('reference')}: sourceTokenId {token_id!r} "
                "is missing from the OSHB/WLC spine"
            )
        out.append(row)
    return out


def phrase_mt_reference(phrase: dict, book_title: str) -> str | None:
    if phrase.get("mtReference"):
        return phrase["mtReference"]

    chapter = phrase.get("mtChapter")
    verse = phrase.get("mtVerse")
    if chapter is not None and verse is not None:
        return f"{book_title} {chapter}:{verse}"
    return None


def evidence_payload(
    phrase: dict,
    book_title: str,
    spine_tokens: dict,
) -> dict:
    return {
        "reference": phrase.get("reference"),
        "mt_reference": phrase_mt_reference(phrase, book_title),
        "spanish": phrase.get("spanish", ""),
        "sourceTokenIds": phrase.get("sourceTokenIds", []),
        "source_tokens": normalize_source_tokens(phrase, spine_tokens),
    }


def fail(message: str) -> None:
    print(f"BLOCKED: {message}", file=sys.stderr)
    raise SystemExit(2)


def atomic_write_json(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote fully approved G0A phrase records to lbf-approved."
    )
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--phrases", required=True, type=Path)
    parser.add_argument(
        "--spine",
        required=True,
        type=Path,
        help="OSHB/WLC spine used when the G0A queue was generated.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help=(
            "Audit report path. Default: "
            "gate0/reports/<book>-g0a-promotion-report.yaml"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually modify the phrase artifact. Without this flag, dry-run only.",
    )
    args = parser.parse_args()

    queue_path = args.queue.resolve()
    phrases_path = args.phrases.resolve()
    spine_path = args.spine.resolve()

    if not queue_path.is_file():
        fail(f"queue not found: {queue_path}")
    if not phrases_path.is_file():
        fail(f"phrases not found: {phrases_path}")
    if not spine_path.is_file():
        fail(f"spine not found: {spine_path}")

    queue_doc = load_yaml(queue_path)
    phrases_doc = load_json(phrases_path)
    spine_doc = load_json(spine_path)

    queue_meta = queue_doc.get("queue", {})
    if queue_meta.get("gate") != "G0A_TRANSLATION_APPROVAL":
        fail(
            "queue gate is not G0A_TRANSLATION_APPROVAL: "
            f"{queue_meta.get('gate')!r}"
        )

    book_id = queue_meta.get("book") or phrases_doc.get("bookId")
    if not book_id:
        fail("book id is missing from queue and phrases artifact")

    artifact_book = phrases_doc.get("bookId")
    if artifact_book and artifact_book != book_id:
        fail(
            f"book mismatch: queue={book_id!r}, phrases={artifact_book!r}"
        )

    # Current Daniel-style reference capitalization; generalized safely.
    book_title = str(book_id).capitalize()

    items = queue_doc.get("items", [])
    if not items:
        fail("G0A queue has no items")

    decisions = {}
    for item in items:
        decision = item.get("review", {}).get("decision", "PENDING")
        decisions[decision] = decisions.get(decision, 0) + 1

    not_approved = [
        item
        for item in items
        if item.get("review", {}).get("decision") != "APPROVED"
    ]
    if not_approved:
        detail = ", ".join(
            f"{i.get('reference')}={i.get('review', {}).get('decision')}"
            for i in not_approved[:12]
        )
        if len(not_approved) > 12:
            detail += f", ... +{len(not_approved)-12} more"
        fail(
            f"{len(not_approved)} G0A item(s) are not APPROVED: {detail}"
        )

    # Whole-artifact freshness check.
    queue_phrase_meta = queue_meta.get("artifacts", {}).get("phrases", {})
    expected_artifact_sha = queue_phrase_meta.get("checksum_sha256")
    actual_artifact_sha = sha256_file(phrases_path)

    if not expected_artifact_sha:
        fail("queue does not record the phrase artifact checksum")
    if expected_artifact_sha != actual_artifact_sha:
        fail(
            "phrase artifact is stale relative to queue: "
            f"queue={expected_artifact_sha}, current={actual_artifact_sha}"
        )


    queue_spine_meta = queue_meta.get("artifacts", {}).get("spine", {})
    expected_spine_sha = queue_spine_meta.get("checksum_sha256")
    actual_spine_sha = sha256_file(spine_path)

    if not expected_spine_sha:
        fail("queue does not record the spine artifact checksum")
    if expected_spine_sha != actual_spine_sha:
        fail(
            "spine artifact is stale relative to queue: "
            f"queue={expected_spine_sha}, current={actual_spine_sha}"
        )

    try:
        spine_tokens = build_spine_token_map(spine_doc)
    except ValueError as exc:
        fail(str(exc))

    phrase_records = phrases_doc.get("phrases")
    if not isinstance(phrase_records, list):
        fail("phrases artifact does not contain a 'phrases' list")

    phrase_by_reference = {}
    duplicate_refs = []
    for phrase in phrase_records:
        reference = phrase.get("reference")
        if not reference:
            fail("phrase record missing reference")
        if reference in phrase_by_reference:
            duplicate_refs.append(reference)
        phrase_by_reference[reference] = phrase

    if duplicate_refs:
        fail(
            "duplicate phrase references: "
            + ", ".join(sorted(set(duplicate_refs)))
        )

    # Per-item freshness/evidence check.
    checksum_errors = []
    missing_refs = []
    for item in items:
        reference = item.get("reference")
        phrase = phrase_by_reference.get(reference)
        if phrase is None:
            missing_refs.append(reference)
            continue

        current_checksum = stable_item_checksum(
            evidence_payload(phrase, book_title, spine_tokens)
        )
        if current_checksum != item.get("item_checksum"):
            checksum_errors.append(
                {
                    "reference": reference,
                    "queue_checksum": item.get("item_checksum"),
                    "current_checksum": current_checksum,
                }
            )

    if missing_refs:
        fail(
            "approved queue references missing from phrase artifact: "
            + ", ".join(str(x) for x in missing_refs[:20])
        )

    if checksum_errors:
        sample = "; ".join(
            f"{x['reference']}: queue={x['queue_checksum']} "
            f"current={x['current_checksum']}"
            for x in checksum_errors[:5]
        )
        fail(
            f"{len(checksum_errors)} item checksum mismatch(es): {sample}"
        )

    approved_refs = {item["reference"] for item in items}

    before_counts = {}
    for phrase in phrase_records:
        status = phrase.get("suggestionSource", "<missing>")
        before_counts[status] = before_counts.get(status, 0) + 1

    promotable = []
    already_approved_reviewed = []
    for reference in sorted(approved_refs):
        phrase = phrase_by_reference[reference]
        status = phrase.get("suggestionSource")
        if status == "lbf-approved":
            already_approved_reviewed.append(reference)
        elif status == "lbf-preliminary":
            promotable.append(reference)
        else:
            fail(
                f"{reference}: unexpected suggestionSource {status!r}; "
                "expected lbf-preliminary or lbf-approved"
            )

    # Do not mutate until every validation has succeeded.
    promoted = []
    if args.apply:
        for reference in promotable:
            phrase_by_reference[reference]["suggestionSource"] = "lbf-approved"
            promoted.append(reference)

    after_counts = dict(before_counts)
    if args.apply:
        after_counts["lbf-preliminary"] = (
            after_counts.get("lbf-preliminary", 0) - len(promoted)
        )
        after_counts["lbf-approved"] = (
            after_counts.get("lbf-approved", 0) + len(promoted)
        )

    now = datetime.now(timezone.utc).isoformat()

    # gate0 is normally the parent of queues/.
    gate0_dir = (
        queue_path.parent.parent
        if queue_path.parent.name == "queues"
        else queue_path.parent
    )

    report_path = (
        args.report.resolve()
        if args.report
        else gate0_dir
        / "reports"
        / f"{book_id}-g0a-promotion-report.yaml"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    evidence_dir = gate0_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    archived_queue_path = (
        evidence_dir / f"{book_id}-g0a-final-review.yaml"
    )

    pre_sha = actual_artifact_sha

    if args.apply:
        # Archive final review evidence before changing producer state.
        shutil.copy2(queue_path, archived_queue_path)

        # Backup producer artifact once per promotion invocation.
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = phrases_path.with_name(
            f"{phrases_path.stem}.pre-g0a-promotion-{timestamp}"
            f"{phrases_path.suffix}"
        )
        shutil.copy2(phrases_path, backup_path)

        atomic_write_json(phrases_path, phrases_doc)
        post_sha = sha256_file(phrases_path)
    else:
        backup_path = None
        post_sha = None

    report = {
        "schema_version": "0.1",
        "generated_at": now,
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "book": book_id,
        "gate": "G0A_TRANSLATION_APPROVAL",
        "validation": {
            "queue_items": len(items),
            "decision_counts": decisions,
            "all_queue_items_approved": True,
            "queue_phrase_checksum_matches_current_artifact": True,
            "queue_spine_checksum_matches_current_artifact": True,
            "all_item_checksums_match": True,
            "missing_references": 0,
            "checksum_mismatches": 0,
        },
        "promotion": {
            "reviewed_approved_records": len(approved_refs),
            "promotable_preliminary_records": len(promotable),
            "already_approved_reviewed_records": len(
                already_approved_reviewed
            ),
            "promoted_records": len(promoted),
            "preexisting_nonqueue_approved_records": sum(
                1
                for p in phrase_records
                if p.get("suggestionSource") == "lbf-approved"
                and p.get("reference") not in approved_refs
            )
            if not args.apply
            else max(
                0,
                after_counts.get("lbf-approved", 0) - len(approved_refs),
            ),
        },
        "status_counts_before": before_counts,
        "status_counts_after": after_counts,
        "artifacts": {
            "queue": str(queue_path),
            "queue_sha256": sha256_file(queue_path),
            "phrases": str(phrases_path),
            "phrases_sha256_before": pre_sha,
            "spine": str(spine_path),
            "spine_sha256": actual_spine_sha,
            "phrases_sha256_after": post_sha,
            "archived_final_queue": (
                str(archived_queue_path) if args.apply else None
            ),
            "backup_phrase_artifact": (
                str(backup_path) if backup_path else None
            ),
        },
        "promoted_references": promoted if args.apply else promotable,
    }

    report_path.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print("G0A PROMOTION")
    print(f"mode: {'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"book: {book_id}")
    print(f"queue items: {len(items)}")
    print(f"approved queue items: {decisions.get('APPROVED', 0)}")
    print(f"current phrase checksum: MATCH")
    print(f"current spine checksum: MATCH")
    print(f"item checksums: MATCH ({len(items)}/{len(items)})")
    print(f"promotable: {len(promotable)}")
    print(f"already approved among reviewed: {len(already_approved_reviewed)}")

    if args.apply:
        print(f"promoted: {len(promoted)}")
        print(
            "lbf-approved after: "
            f"{after_counts.get('lbf-approved', 0)}"
        )
        print(
            "lbf-preliminary after: "
            f"{after_counts.get('lbf-preliminary', 0)}"
        )
        print(f"archived queue: {archived_queue_path}")
        print(f"backup: {backup_path}")
    else:
        print("No files modified. Re-run with --apply to promote.")

    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
