#!/usr/bin/env python3
"""Shared mechanics for the canonical cgv-translator book workflow."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_VERSION = "0.3"
SCHEMA_VERSION = "0.1"
PRELIMINARY = "lbf-preliminary"
APPROVED = "lbf-approved"
RESOLVED_INVESTIGATIONS = {"Approved", "Superseded"}


class WorkflowError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise WorkflowError(f"Expected JSON object: {path}")
    return value


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise WorkflowError(f"Expected YAML object: {path}")
    return value


def save_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    temp.replace(path)


def relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def normalize_book(book: str) -> str:
    value = str(book or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise WorkflowError(f"Invalid book id: {book!r}")
    return value


def safe_component(value: str, label: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", text):
        raise WorkflowError(f"{label} must be an explicit safe identifier, got {value!r}")
    return text


def resolve_paths(root: Path, book: str) -> dict[str, Path | str]:
    book = normalize_book(book)
    oshb = root / "translations" / "oshb-spine" / book
    tr = root / "translations" / "tr-spine" / book
    if (tr / f"{book}-tr-spine.json").is_file() and not (oshb / f"{book}-oshb-spine.json").is_file():
        layout = "tr"
        spine = tr / f"{book}-tr-spine.json"
        phrases_path = tr / f"{book}-phrases-tr.json"
        reverse = tr / f"{book}-reverse-links.json"
    else:
        layout = "oshb"
        spine = oshb / f"{book}-oshb-spine.json"
        phrases_path = oshb / f"{book}-phrases.json"
        reverse = oshb / f"{book}-reverse-links.json"
    return {
        "layout": layout,
        "spine": spine,
        "phrases": phrases_path,
        "reverse": reverse,
        "g0a_queue": root / "gate0" / "queues" / f"{book}-g0a-translation-review.yaml",
        "g0b_queue": root / "gate0" / "queues" / f"{book}-g0b-alignment-review.yaml",
        "g0a_report": root / "gate0" / "reports" / f"{book}-g0a-promotion-report.yaml",
        "investigations": root / "investigations" / book,
        "final_reviews": root / "workflow" / book / "book-final-reviews.yaml",
        "approvals": root / "workflow" / book / "approvals.yaml",
        "releases": root / "releases" / book,
    }


def artifact(root: Path, path: Path) -> dict:
    return {"path": relative(root, path), "checksum_sha256": sha256_file(path)}


def token_index(spine: dict) -> dict[str, dict]:
    verses = spine.get("verses")
    if not isinstance(verses, dict) or not verses:
        raise WorkflowError("Source spine must contain a non-empty verses object.")
    out: dict[str, dict] = {}
    for verse in verses.values():
        for token in verse.get("tokens", []) if isinstance(verse, dict) else []:
            token_id = str(token.get("sourceTokenId") or "")
            if not token_id:
                raise WorkflowError("Source token missing sourceTokenId.")
            out[token_id] = {
                "sourceTokenId": token_id,
                "surface": token.get("surface") or token.get("greek") or "",
                "lang": token.get("lang"),
                "lemma": token.get("lemma"),
                "morph": token.get("morph") if "morph" in token else token.get("rmac"),
                "gloss": token.get("gloss"),
            }
    if not out:
        raise WorkflowError("Source spine contains no source tokens.")
    return out


def phrase_rows(book: str, doc: dict) -> list[dict]:
    artifact_book = str(doc.get("bookId") or "").lower()
    if artifact_book and artifact_book != book:
        raise WorkflowError(f"Book mismatch: expected {book}, got {artifact_book}")
    rows = doc.get("phrases")
    if not isinstance(rows, list) or not rows:
        raise WorkflowError("Phrase artifact must contain a non-empty phrases list.")
    return rows


def translation_errors(book: str, doc: dict) -> list[str]:
    errors: list[str] = []
    try:
        rows = phrase_rows(book, doc)
    except WorkflowError as exc:
        return [str(exc)]
    seen: set[str] = set()
    for row in rows:
        ref = str(row.get("reference") or "")
        status = str(row.get("suggestionSource") or "")
        if not ref or ref in seen:
            errors.append(f"Invalid/duplicate reference: {ref!r}")
        seen.add(ref)
        if not str(row.get("spanish") or "").strip():
            errors.append(f"{ref}: Spanish is blank")
        if status not in {PRELIMINARY, APPROVED}:
            errors.append(f"{ref}: status {status!r} is not translation-ready")
        ids = row.get("sourceTokenIds")
        if not isinstance(ids, list) or not ids:
            errors.append(f"{ref}: sourceTokenIds missing")
    return errors


def phrase_mt_reference(row: dict, book: str) -> str | None:
    explicit = str(row.get("mtReference") or "").strip()
    if explicit:
        return explicit
    chapter, verse = row.get("mtChapter"), row.get("mtVerse")
    if chapter is None or verse is None:
        return None
    ref = str(row.get("reference") or "")
    match = re.match(r"^(.*?)\s+\d+:\d+$", ref)
    label = match.group(1).strip() if match else book.capitalize()
    return f"{label} {chapter}:{verse}"


def preserve_review(items: list[dict], old_queue: dict) -> tuple[int, int]:
    old_by_key = {
        str(row.get("review_key")): row
        for row in old_queue.get("items", [])
        if isinstance(row, dict) and row.get("review_key") and row.get("item_checksum")
    }
    preserved = reset = 0
    for item in items:
        old = old_by_key.get(str(item.get("review_key")))
        if old and old.get("item_checksum") == item.get("item_checksum"):
            review = old.get("review", {})
            if review.get("decision", "PENDING") != "PENDING":
                item["review"] = review
                preserved += 1
        elif old:
            reset += 1
    return preserved, reset


def recompute_summary(queue: dict, positive: str) -> None:
    decisions = [str(row.get("review", {}).get("decision") or "PENDING") for row in queue.get("items", [])]
    summary = {
        "total": len(decisions),
        "approved_or_verified": sum(value == positive for value in decisions),
        "pending": sum(value == "PENDING" for value in decisions),
        "needs_revision_or_relink": sum(value in {"NEEDS_REVISION", "NEEDS_RELINK"} for value in decisions),
        "rejected": sum(value == "REJECTED" for value in decisions),
        "escalated": sum(value == "ESCALATE" for value in decisions),
    }
    queue["summary"] = summary
    if summary["pending"] == summary["needs_revision_or_relink"] == summary["rejected"] == summary["escalated"] == 0:
        queue["queue"]["status"] = "PASS"
    elif summary["pending"] == 0:
        queue["queue"]["status"] = "REVIEW_REQUIRED"
    else:
        queue["queue"]["status"] = "OPEN"


def current_bindings(root: Path, paths: dict[str, Path | str]) -> dict:
    return {
        "spine": artifact(root, Path(paths["spine"])),
        "phrases": artifact(root, Path(paths["phrases"])),
        "reverse_links": artifact(root, Path(paths["reverse"])),
        "g0a_report": artifact(root, Path(paths["g0a_report"])),
        "g0b_queue": artifact(root, Path(paths["g0b_queue"])),
    }


def latest_decision_fields(markdown: str) -> dict[str, str]:
    parts = re.split(r"(?=^## Version\s+)", markdown, flags=re.MULTILINE)
    candidate = parts[-1] if parts else markdown
    def field(name: str) -> str:
        match = re.search(rf"^{re.escape(name)}:\s*(.*)$", candidate, flags=re.MULTILINE)
        return match.group(1).strip() if match else ""
    return {
        "status": field("Status"),
        "approvalAuthority": field("Approval Authority"),
        "approvedBy": field("Approved By"),
        "approvedAt": field("Approved At"),
        "scope": field("Scope"),
    }


def investigation_status(paths: dict[str, Path | str]) -> tuple[bool, dict]:
    directory = Path(paths["investigations"])
    summary = {"total": 0, "resolved": 0, "open": [], "invalid": []}
    if not directory.is_dir():
        return True, summary
    for inv in sorted(directory.glob("INV-*")):
        if not inv.is_dir():
            continue
        summary["total"] += 1
        decision = inv / "decision.md"
        if not decision.is_file():
            summary["invalid"].append(f"{inv.name}: decision.md missing")
            continue
        fields = latest_decision_fields(decision.read_text(encoding="utf-8"))
        status = fields["status"]
        if status not in RESOLVED_INVESTIGATIONS:
            summary["open"].append(f"{inv.name}:{status or '<missing>'}")
            continue
        if status == "Approved" and (
            fields["approvalAuthority"].lower() != "human"
            or not fields["approvedBy"]
            or not fields["approvedAt"]
            or not fields["scope"]
        ):
            summary["invalid"].append(f"{inv.name}: Approved decision lacks human provenance/scope")
            continue
        summary["resolved"] += 1
    return not summary["open"] and not summary["invalid"], summary
