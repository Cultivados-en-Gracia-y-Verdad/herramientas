#!/usr/bin/env python3
"""G0A/G0B queue generation for the canonical book workflow."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workflow_core import (
    APPROVED, SCHEMA_VERSION, WorkflowError, artifact, phrase_mt_reference,
    phrase_rows, recompute_summary, stable_digest, token_index,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_g0a(root: Path, book: str, spine: dict, phrase_doc: dict, spine_path: Path, phrase_path: Path) -> dict:
    tokens = token_index(spine)
    items = []
    for row in phrase_rows(book, phrase_doc):
        status = str(row.get("suggestionSource") or "")
        if status == APPROVED:
            continue
        tids = [str(value) for value in row.get("sourceTokenIds", [])]
        if any(token_id not in tokens for token_id in tids):
            raise WorkflowError(f"{row.get('reference')}: source token missing from spine")
        source_tokens = [tokens[token_id] for token_id in tids]
        mt_ref = phrase_mt_reference(row, book)
        evidence = {
            "reference": row.get("reference"), "mt_reference": mt_ref,
            "spanish": row.get("spanish", ""), "sourceTokenIds": tids,
            "source_tokens": source_tokens,
        }
        items.append({
            "id": f"G0A-{len(items)+1:04d}",
            "review_key": f"G0A:{row.get('reference')}",
            "item_checksum": stable_digest(evidence),
            "gate": "G0A_TRANSLATION_APPROVAL",
            "reference": row.get("reference"), "mt_reference": mt_ref,
            "spanish": row.get("spanish", ""), "sourceTokenIds": tids,
            "source_tokens": source_tokens, "current_status": status,
            "review": {"decision": "PENDING", "reviewer": None, "runtime": None,
                       "model": None, "confidence": None, "evidence": "", "notes": "",
                       "reviewed_at": None},
        })
    queue = {
        "schema_version": SCHEMA_VERSION,
        "queue": {"id": f"{book}-G0A", "gate": "G0A_TRANSLATION_APPROVAL", "book": book,
                  "artifact_revision": "", "artifacts": {"spine": artifact(root, spine_path),
                  "phrases": artifact(root, phrase_path)}, "created_at": now_iso(), "status": "OPEN"},
        "summary": {}, "items": items,
    }
    recompute_summary(queue, "APPROVED")
    return queue


def alignment_errors(book: str, spine: dict, phrase_doc: dict, reverse: dict) -> list[str]:
    errors = []
    tokens = set(token_index(spine))
    rows = {str(row.get("reference")): row for row in phrase_rows(book, phrase_doc)}
    links = reverse.get("links")
    if not isinstance(links, list) or not links:
        return ["reverse-link artifact must contain links"]
    by_ref = {}
    for link in links:
        ref = str(link.get("reference") or "") if isinstance(link, dict) else ""
        if not ref or ref in by_ref:
            errors.append(f"invalid/duplicate alignment reference: {ref!r}")
        by_ref[ref] = link
    missing = sorted(set(rows) - set(by_ref))
    extra = sorted(set(by_ref) - set(rows))
    if missing: errors.append(f"verses missing alignment: {missing[:8]}")
    if extra: errors.append(f"unknown aligned verses: {extra[:8]}")
    for ref, row in rows.items():
        link = by_ref.get(ref)
        if not link: continue
        spanish = str(row.get("spanish") or "")
        expected = {str(value) for value in row.get("sourceTokenIds", [])}
        units = link.get("units")
        if not isinstance(units, list) or not units:
            errors.append(f"{ref}: alignment units missing")
            continue
        covered = set()
        for i, unit in enumerate(units, 1):
            uid = unit.get("unitId", i)
            surface = str(unit.get("surface") or "")
            tids = [str(value) for value in unit.get("sourceTokenIds", [])]
            if not surface: errors.append(f"{ref} unit {uid}: Spanish surface blank")
            if not tids: errors.append(f"{ref} unit {uid}: sourceTokenIds empty")
            if any(tid not in tokens or tid not in expected for tid in tids):
                errors.append(f"{ref} unit {uid}: invalid source token relationship")
            covered.update(tids)
            start, end = unit.get("charStart"), unit.get("charEnd")
            if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start <= end <= len(spanish)):
                errors.append(f"{ref} unit {uid}: invalid character span")
            elif spanish[start:end] != surface:
                errors.append(f"{ref} unit {uid}: surface does not match current Spanish")
        unaccounted = sorted(expected - covered)
        if unaccounted: errors.append(f"{ref}: unaccounted source tokens {unaccounted[:8]}")
    return errors


def make_g0b(root: Path, book: str, spine: dict, phrase_doc: dict, reverse: dict,
             spine_path: Path, phrase_path: Path, reverse_path: Path) -> dict:
    """Queue every unit; producer status never substitutes for independent G0B."""
    tokens = token_index(spine)
    rows = {str(row.get("reference")): row for row in phrase_rows(book, phrase_doc)}
    items = []
    for link in reverse.get("links", []):
        ref = str(link.get("reference") or "")
        row = rows.get(ref)
        if row is None: continue
        spanish = str(row.get("spanish") or "")
        for unit in link.get("units", []):
            tids = [str(value) for value in unit.get("sourceTokenIds", [])]
            source_tokens = [tokens[tid] for tid in tids if tid in tokens]
            start, end = unit.get("charStart"), unit.get("charEnd")
            actual = spanish[start:end] if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(spanish) else None
            evidence = {
                "reference": ref, "mt_reference": link.get("mtReference"), "unitId": unit.get("unitId"),
                "spanish_unit": unit.get("surface", ""), "actual_phrase_slice": actual,
                "char_start": start, "char_end": end, "sourceTokenIds": tids,
                "source_tokens": source_tokens,
            }
            items.append({
                "id": f"G0B-{len(items)+1:05d}", "review_key": f"G0B:{ref}:{unit.get('unitId')}",
                "item_checksum": stable_digest(evidence), "gate": "G0B_ALIGNMENT_VERIFICATION",
                "reference": ref, "mt_reference": link.get("mtReference"), "unitId": unit.get("unitId"),
                "spanish_unit": unit.get("surface", ""), "actual_phrase_slice": actual,
                "char_start": start, "char_end": end, "sourceTokenIds": tids, "source_tokens": source_tokens,
                "current_method": unit.get("method", "UNKNOWN"),
                "current_status": unit.get("status", link.get("status", "UNKNOWN")),
                "review": {"decision": "PENDING", "reviewer": None, "runtime": None, "model": None,
                           "confidence": None, "evidence": "", "notes": "", "reviewed_at": None},
            })
    queue = {
        "schema_version": SCHEMA_VERSION,
        "queue": {"id": f"{book}-G0B", "gate": "G0B_ALIGNMENT_VERIFICATION", "book": book,
                  "artifact_revision": "", "artifacts": {"spine": artifact(root, spine_path),
                  "phrases": artifact(root, phrase_path), "reverse_links": artifact(root, reverse_path)},
                  "created_at": now_iso(), "status": "OPEN"},
        "summary": {}, "items": items,
    }
    recompute_summary(queue, "VERIFIED")
    return queue
