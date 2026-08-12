#!/usr/bin/env python3
"""Regression proof for targeted alignment invalidation using approved Daniel.

No files are written. Daniel's historical final artifact predates promoted G0B
metadata, so this test first models the post-promotion state in memory and then
proves:
- unchanged Spanish keeps G0A complete;
- identical alignment evidence keeps verified state;
- changed alignment evidence marks only the affected link needs-review;
- G0B queues only the affected reference again.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def promote_in_memory(reverse_doc: dict) -> dict:
    """Model the state a modern successful G0B promotion would persist.

    This is deliberately test-only. It does not claim Daniel's historical file was
    promoted; it creates a clean verified baseline so mutation semantics can be
    tested independently of Daniel's legacy metadata format.
    """
    promoted = deepcopy(reverse_doc)
    for link in promoted.get("links", []):
        link["status"] = "verified"
        for unit in link.get("units", []):
            unit["status"] = "verified"
            if str(unit.get("method") or "") in {"gloss-match", "seed", ""}:
                unit["method"] = "external-verified"
    return promoted


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    base = root / "translations" / "oshb-spine" / "daniel"
    spine_path = base / "daniel-oshb-spine.json"
    phrase_path = base / "daniel-phrases.json"
    reverse_path = base / "daniel-reverse-links.json"

    edit = load_module("edit_alignment", root / "scripts" / "edit_alignment.py")
    queues = load_module("gate0_queues", root / "gate0" / "generate-review-queues.py")

    phrase_raw = phrase_path.read_bytes()
    spine_doc = json.loads(spine_path.read_text(encoding="utf-8"))
    phrase_doc = json.loads(phrase_raw.decode("utf-8"))
    historical_reverse = json.loads(reverse_path.read_text(encoding="utf-8"))
    reverse_doc = promote_in_memory(historical_reverse)

    phrases = phrase_doc.get("phrases", [])
    assert phrases, "Daniel phrases missing"
    assert all(item.get("suggestionSource") == "lbf-approved" for item in phrases), "Daniel G0A baseline is not fully approved"

    baseline_g0a = queues.make_g0a("daniel", spine_doc, phrase_doc, spine_path, phrase_path)
    assert baseline_g0a["summary"]["total"] == 0, "Approved Daniel unexpectedly requeued G0A"

    baseline_g0b = queues.make_g0b(
        "daniel",
        spine_doc,
        phrase_doc,
        reverse_doc,
        spine_path,
        phrase_path,
        reverse_path,
    )
    assert baseline_g0b["summary"]["total"] == 0, "Modeled verified Daniel unexpectedly requeued G0B"

    target_link = None
    target_unit = None
    for link in reverse_doc.get("links", []):
        if link.get("status") != "verified":
            continue
        for unit in link.get("units", []):
            if unit.get("sourceTokenIds"):
                target_link = link
                target_unit = unit
                break
        if target_link is not None:
            break
    assert target_link is not None and target_unit is not None, "No verified Daniel alignment unit found"

    reference = str(target_link["reference"])
    unit_id = str(target_unit["unitId"])
    original_tokens = [str(value) for value in target_unit.get("sourceTokenIds", [])]

    unchanged = deepcopy(reverse_doc)
    changed = edit.apply_source_token_edit(unchanged, reference, unit_id, original_tokens)
    assert changed is False, "Identical alignment evidence should not invalidate G0B"
    unchanged_link = next(item for item in unchanged["links"] if item.get("reference") == reference)
    unchanged_unit = next(item for item in unchanged_link["units"] if str(item.get("unitId")) == unit_id)
    assert unchanged_link.get("status") == "verified", "No-op alignment edit changed verified link state"
    assert unchanged_unit.get("status") == "verified", "No-op alignment edit changed verified unit state"

    candidate = deepcopy(reverse_doc)
    # Deterministic evidence change without writing it. Clearing this unit is
    # sufficient to exercise the invalidation boundary.
    changed = edit.apply_source_token_edit(candidate, reference, unit_id, [])
    assert changed is True, "Changed alignment evidence was not detected"
    candidate_link = next(item for item in candidate["links"] if item.get("reference") == reference)
    candidate_unit = next(item for item in candidate_link["units"] if str(item.get("unitId")) == unit_id)
    assert candidate_link.get("status") == "needs-review", "Affected link did not reopen G0B"
    assert candidate_unit.get("status") == "needs-review", "Affected unit did not reopen G0B"

    g0b = queues.make_g0b(
        "daniel",
        spine_doc,
        phrase_doc,
        candidate,
        spine_path,
        phrase_path,
        reverse_path,
    )
    queued = g0b.get("items", [])
    assert queued, "Changed verified alignment did not reappear in G0B queue"
    queued_refs = {str(item.get("reference")) for item in queued}
    assert queued_refs == {reference}, f"Alignment-only edit reopened unrelated G0B references: {sorted(queued_refs)}"

    assert sha256_bytes(phrase_path.read_bytes()) == sha256_bytes(phrase_raw), "Alignment regression mutated phrase artifact"
    after_g0a = queues.make_g0a("daniel", spine_doc, phrase_doc, spine_path, phrase_path)
    assert after_g0a["summary"]["total"] == 0, "Alignment-only edit invalidated G0A"

    print("PASS: modeled verified Daniel opens no G0B work")
    print("PASS: identical alignment preserves G0B verification")
    print(f"PASS: changed alignment reopens G0B only for {reference}")
    print("PASS: Daniel Spanish/G0A remains unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())