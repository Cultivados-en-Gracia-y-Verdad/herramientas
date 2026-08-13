#!/usr/bin/env python3
"""Gate and human-approval state checks for the canonical book workflow."""
from __future__ import annotations
from pathlib import Path

from workflow_core import (
    APPROVED, WORKFLOW_VERSION, WorkflowError, current_bindings,
    load_json, load_yaml, phrase_rows, sha256_file, stable_digest,
)


def g0a_status(root: Path, book: str, paths: dict) -> tuple[bool, list[str]]:
    spine, phrases, report_path = Path(paths["spine"]), Path(paths["phrases"]), Path(paths["g0a_report"])
    errors = [f"missing: {p}" for p in (spine, phrases, report_path) if not p.is_file()]
    if errors:
        return False, errors
    doc = load_json(phrases)
    pending = [str(row.get("reference")) for row in phrase_rows(book, doc) if row.get("suggestionSource") != APPROVED]
    if pending:
        errors.append(f"phrases not G0A-approved: {pending[:8]}")
    report = load_yaml(report_path)
    if report.get("mode") != "APPLY" or report.get("book") != book or report.get("gate") != "G0A_TRANSLATION_APPROVAL":
        errors.append("G0A report identity is invalid")
    validation = report.get("validation", {})
    required = (
        "all_queue_items_approved", "queue_phrase_checksum_matches_current_artifact",
        "queue_spine_checksum_matches_current_artifact", "all_item_checksums_match",
    )
    if any(validation.get(key) is not True for key in required):
        errors.append("G0A report does not prove complete exact-artifact review")
    artifacts = report.get("artifacts", {})
    if artifacts.get("phrases_sha256_after") != sha256_file(phrases):
        errors.append("G0A report is stale for phrases")
    if artifacts.get("spine_sha256") != sha256_file(spine):
        errors.append("G0A report is stale for spine")
    return not errors, errors


def g0b_status(root: Path, book: str, paths: dict) -> tuple[bool, list[str]]:
    queue_path, spine, phrases, reverse = (Path(paths[key]) for key in ("g0b_queue", "spine", "phrases", "reverse"))
    errors = [f"missing: {p}" for p in (queue_path, spine, phrases, reverse) if not p.is_file()]
    if errors:
        return False, errors
    queue = load_yaml(queue_path)
    meta = queue.get("queue", {})
    if meta.get("book") != book or meta.get("gate") != "G0B_ALIGNMENT_VERIFICATION":
        errors.append("G0B queue identity is invalid")
    if meta.get("status") != "PASS":
        errors.append(f"G0B status is {meta.get('status')!r}, not PASS")
    items = queue.get("items", [])
    if not items or any(row.get("review", {}).get("decision") != "VERIFIED" for row in items):
        errors.append("G0B does not contain complete independent VERIFIED review")
    current = load_json(reverse)
    units = sum(len(link.get("units", [])) for link in current.get("links", []) if isinstance(link, dict))
    if len(items) != units:
        errors.append(f"G0B reviewed {len(items)} of {units} alignment units")
    for key, path in (("spine", spine), ("phrases", phrases), ("reverse_links", reverse)):
        if meta.get("artifacts", {}).get(key, {}).get("checksum_sha256") != sha256_file(path):
            errors.append(f"G0B queue is stale for {key}")
    return not errors, errors


def load_history(path: Path, book: str, key: str) -> dict:
    if not path.is_file():
        return {"schema_version": "0.1", "book": book, key: []}
    doc = load_yaml(path)
    if doc.get("book") != book or not isinstance(doc.get(key), list):
        raise WorkflowError(f"Invalid {key} history: {path}")
    return doc


def latest_final_review(root: Path, book: str, paths: dict) -> tuple[dict | None, list[str]]:
    doc = load_history(Path(paths["final_reviews"]), book, "reviews")
    if not doc["reviews"]:
        return None, ["book-level final review not recorded"]
    review = doc["reviews"][-1]
    errors = []
    if review.get("status") != "PASS" or review.get("workflow_version") != WORKFLOW_VERSION:
        errors.append("latest book final review is not a current PASS")
    if review.get("artifacts") != current_bindings(root, paths):
        errors.append("book final review is stale for current artifacts")
    return review, errors


def latest_approval(root: Path, book: str, paths: dict) -> tuple[dict | None, list[str]]:
    doc = load_history(Path(paths["approvals"]), book, "approvals")
    if not doc["approvals"]:
        return None, ["human book approval not recorded"]
    approval = doc["approvals"][-1]
    errors = []
    if approval.get("status") != "TRANSLATION_APPROVED" or approval.get("authority") != "human":
        errors.append("latest approval is not human TRANSLATION_APPROVED")
    if not approval.get("approved_by") or not approval.get("approved_at"):
        errors.append("latest approval lacks human provenance")
    review, review_errors = latest_final_review(root, book, paths)
    if review_errors or review is None or approval.get("final_review_digest") != stable_digest(review):
        errors.append("approval is not bound to the current final review")
    if approval.get("artifacts") != current_bindings(root, paths):
        errors.append("approval is stale for current artifacts")
    identity = approval.get("release_identity", {})
    for field in ("edition", "book_release_version", "source_revision", "translation_revision", "alignment_revision"):
        if not str(identity.get(field) or "").strip():
            errors.append(f"release identity missing {field}")
    return approval, errors
