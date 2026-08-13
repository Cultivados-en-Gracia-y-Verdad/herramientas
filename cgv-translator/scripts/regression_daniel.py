#!/usr/bin/env python3
"""Daniel golden-corpus regression for the CGV/LBF workflow.

This script is read-only with respect to canonical Daniel artifacts. Any mutation
used to exercise invalidation behavior happens only in memory.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # gate0 tooling already depends on PyYAML
    raise SystemExit("PyYAML is required. Install cgv-translator/gate0/requirements.txt") from exc

from render_lbf_release import render_release_bytes
from workflow_queues import alignment_errors


ROOT = Path(__file__).resolve().parents[1]
DANIEL_DIR = ROOT / "translations" / "oshb-spine" / "daniel"
PHRASES = DANIEL_DIR / "daniel-phrases.json"
SPINE = DANIEL_DIR / "daniel-oshb-spine.json"
REVERSE = DANIEL_DIR / "daniel-reverse-links.json"
FINAL_G0B_REVERSE = DANIEL_DIR / "daniel-reverse-links.final-g0b.json"
G0A_REPORT = ROOT / "gate0" / "reports" / "daniel-g0a-promotion-report.yaml"
G0B_RESULTS = ROOT / "gate0" / "review-results" / "daniel-g0b-final-verification-results.yaml"
QUEUE_GENERATOR = ROOT / "gate0" / "generate-review-queues.py"
MAIN_JS = ROOT / "public" / "main.js"

EXPECTED = {
    "phrases_sha256": "f5c7ce0d9d5deac3a305de2a11c997751100449e5c5ade13e40a96f7f8f189f7",
    "spine_sha256": "40f53bf5f46fad84e28d796b3b3b7527f8420d47707af311a5959993dd8592c6",
    "legacy_export_sha256": "535faa52140083da58afd831de1b61be05851da61bddec0073eda68e91d1e390",
    "phrases": 357,
    "source_tokens": 6035,
    "hebrew_tokens": 2333,
    "aramaic_tokens": 3702,
    "alignment_units": 5024,
    "legacy_g0b_items": 1181,
}


class RegressionFailure(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionFailure(message)
    print(f"PASS  {message}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_queue_generator():
    spec = importlib.util.spec_from_file_location("cgv_gate0_queue_generator", QUEUE_GENERATOR)
    if spec is None or spec.loader is None:
        raise RegressionFailure(f"Cannot import {QUEUE_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_save_cannot_self_approve() -> None:
    source = MAIN_JS.read_text(encoding="utf-8")
    forbidden = 'phrase.suggestionSource = phrase.workingText.trim() ? "lbf-approved" : "blank";'
    check(forbidden not in source, "Save does not assign lbf-approved")
    check('phrase.suggestionSource = "lbf-preliminary"' in source, "Changed saved Spanish becomes lbf-preliminary")
    check("spanishChanged" in source, "Save distinguishes changed from unchanged Spanish")
    check("previousSuggestionSource" in source, "Failed Save restores the prior approval state")


def check_book_artifacts() -> tuple[dict, dict, dict]:
    for path in (PHRASES, SPINE, REVERSE, G0A_REPORT):
        check(path.is_file(), f"Required artifact exists: {path.relative_to(ROOT)}")

    check(sha256_file(PHRASES) == EXPECTED["phrases_sha256"], "Daniel phrase artifact matches verified checksum")
    check(sha256_file(SPINE) == EXPECTED["spine_sha256"], "Daniel OSHB spine matches audited checksum")

    phrase_doc = load_json(PHRASES)
    spine_doc = load_json(SPINE)
    reverse_doc = load_json(REVERSE)
    phrases = phrase_doc.get("phrases", [])

    check(len(phrases) == EXPECTED["phrases"], "Daniel has 357 phrase/verse records")
    check(all(p.get("suggestionSource") == "lbf-approved" for p in phrases), "All Daniel phrase records are G0A-approved")
    check(all(str(p.get("spanish") or "").strip() for p in phrases), "No approved Daniel phrase is blank")

    refs = [p.get("reference") for p in phrases]
    check(len(refs) == len(set(refs)), "Daniel phrase references are unique")

    phrase_source_tokens = sum(len(p.get("sourceTokenIds", [])) for p in phrases)
    check(phrase_source_tokens == EXPECTED["source_tokens"], "Daniel phrases cover 6035 source tokens")

    verses = spine_doc.get("verses", {})
    check(len(verses) == EXPECTED["phrases"], "Daniel OSHB spine has 357 verses")
    spine_tokens = [token for verse in verses.values() for token in verse.get("tokens", [])]
    check(len(spine_tokens) == EXPECTED["source_tokens"], "Daniel OSHB spine has 6035 source tokens")
    language_counts = {
        "he": sum(token.get("lang") == "he" for token in spine_tokens),
        "arc": sum(token.get("lang") == "arc" for token in spine_tokens),
    }
    check(language_counts["he"] == EXPECTED["hebrew_tokens"], "Daniel Hebrew token count is 2333")
    check(language_counts["arc"] == EXPECTED["aramaic_tokens"], "Daniel Aramaic token count is 3702")

    structural_errors = alignment_errors("daniel", spine_doc, phrase_doc, reverse_doc)
    if structural_errors:
        preview = "; ".join(structural_errors[:8])
        raise RegressionFailure(f"Current Daniel reverse links fail canonical structural validation: {preview}")
    check(True, "Current Daniel reverse links pass canonical structural validation")

    links = reverse_doc.get("links", [])
    check(len(links) == EXPECTED["phrases"], "Daniel production alignment covers all 357 verses")
    unit_count = sum(len(link.get("units", [])) for link in links)
    check(unit_count == EXPECTED["alignment_units"], "Daniel production alignment has 5024 granular units")

    phrase_by_ref = {str(row.get("reference")): row for row in phrases}
    whole_verse_collapses = 0
    for link in links:
        units = link.get("units", [])
        if len(units) != 1:
            continue
        ref = str(link.get("reference") or "")
        row = phrase_by_ref.get(ref, {})
        unit = units[0]
        spanish = str(row.get("spanish") or "")
        if (
            str(unit.get("surface") or "") == spanish
            and unit.get("charStart") == 0
            and unit.get("charEnd") == len(spanish)
            and set(map(str, unit.get("sourceTokenIds", []))) == set(map(str, row.get("sourceTokenIds", [])))
        ):
            whole_verse_collapses += 1
    check(whole_verse_collapses == 0, "Daniel production alignment has no single-unit whole-verse collapses")

    return phrase_doc, spine_doc, reverse_doc


def check_g0a(phrase_doc: dict, spine_doc: dict) -> None:
    report = load_yaml(G0A_REPORT)
    validation = report.get("validation", {})
    promotion = report.get("promotion", {})
    after = report.get("status_counts_after", {})
    artifacts = report.get("artifacts", {})

    check(report.get("gate") == "G0A_TRANSLATION_APPROVAL", "G0A promotion report identifies the external translation gate")
    check(validation.get("queue_items") == 356, "G0A report contains 356 externally reviewed queue items")
    check(validation.get("decision_counts", {}).get("APPROVED") == 356, "All 356 G0A review items were APPROVED")
    check(validation.get("all_queue_items_approved") is True, "G0A report records complete external approval")
    check(validation.get("all_item_checksums_match") is True, "G0A reviewed evidence checksums were valid")
    check(validation.get("queue_phrase_checksum_matches_current_artifact") is True, "G0A review matched the promoted phrase artifact")
    check(validation.get("queue_spine_checksum_matches_current_artifact") is True, "G0A review matched the audited source spine")
    check(promotion.get("promoted_records") == 356, "External G0A promotion moved 356 preliminary records to approved")
    check(promotion.get("preexisting_nonqueue_approved_records") == 1, "Daniel retains one legacy pre-existing approved baseline record")
    check(after.get("lbf-approved") == 357, "G0A promotion result contains 357 approved records")
    check(artifacts.get("phrases_sha256_after") == EXPECTED["phrases_sha256"], "G0A promotion output checksum matches current Daniel phrases")
    check(artifacts.get("spine_sha256") == EXPECTED["spine_sha256"], "G0A promotion source checksum matches current Daniel spine")

    generator = load_queue_generator()
    baseline = generator.make_g0a("daniel", spine_doc, phrase_doc, SPINE, PHRASES)
    check(len(baseline["items"]) == 0, "Unchanged approved Daniel opens no new G0A work")

    changed = copy.deepcopy(phrase_doc)
    changed_phrase = changed["phrases"][0]
    changed_phrase["spanish"] = changed_phrase["spanish"] + " [regression-only change]"
    changed_phrase["suggestionSource"] = "lbf-preliminary"
    changed_queue = generator.make_g0a("daniel", spine_doc, changed, SPINE, PHRASES)
    check(len(changed_queue["items"]) == 1, "One changed Spanish phrase reopens exactly one G0A item")
    check(changed_queue["items"][0]["reference"] == phrase_doc["phrases"][0]["reference"], "G0A invalidation is limited to the changed reference")

    old_item = copy.deepcopy(changed_queue["items"][0])
    old_item["review"]["decision"] = "APPROVED"
    preserved_queue = {"items": [old_item]}
    same = copy.deepcopy(changed_queue["items"])
    preserved, reset = generator.preserve_review(same, preserved_queue)
    check(preserved == 1 and reset == 0, "Unchanged review evidence preserves G0A approval")

    changed_again = copy.deepcopy(changed_queue["items"])
    changed_again[0]["item_checksum"] = "changed-evidence-checksum"
    preserved, reset = generator.preserve_review(changed_again, preserved_queue)
    check(preserved == 0 and reset == 1, "Changed review evidence invalidates only the affected G0A approval")


def check_historical_g0b_evidence() -> None:
    """Retain Daniel's old G0B packet as history, never as current authority."""
    check(FINAL_G0B_REVERSE.is_file(), "Historical final-G0B alignment snapshot is retained as evidence")
    check(G0B_RESULTS.is_file(), "Historical final external G0B result packet is retained as evidence")
    check(REVERSE.read_bytes() != FINAL_G0B_REVERSE.read_bytes(), "Production alignment is no longer frozen to the historical final-G0B snapshot")

    results = load_yaml(G0B_RESULTS)
    packet = results.get("packet", {})
    items = results.get("items", [])

    check(packet.get("gate") == "G0B_ALIGNMENT_VERIFICATION", "Historical result packet identifies external G0B")
    check(len(items) == EXPECTED["legacy_g0b_items"], "Historical external G0B result contains 1181 review items")
    check(all(item.get("decision") == "VERIFIED" for item in items), "All historical external G0B items were VERIFIED")

    item_ids = [item.get("id") for item in items]
    check(all(item_ids), "Every historical external G0B result has an item id")
    check(len(item_ids) == len(set(item_ids)), "Historical external G0B result ids are unique")
    print("INFO  Historical Daniel G0B evidence does not certify the current 5024-unit production alignment.")


def check_render_continuity(phrase_doc: dict) -> None:
    candidate = render_release_bytes(phrase_doc)
    candidate_sha = sha256_bytes(candidate)
    print(f"INFO  Daniel continuity render SHA-256: {candidate_sha}")
    check(candidate_sha == EXPECTED["legacy_export_sha256"], "Rendered Daniel text matches the historical export bytes used for continuity evidence")
    print("INFO  Historical export continuity is not release approval; Daniel still requires the full book release gate.")


def main() -> int:
    try:
        print("Daniel CGV/LBF regression")
        print(f"root: {ROOT}")
        check_save_cannot_self_approve()
        phrase_doc, spine_doc, _reverse_doc = check_book_artifacts()
        check_g0a(phrase_doc, spine_doc)
        check_historical_g0b_evidence()
        check_render_continuity(phrase_doc)
    except RegressionFailure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FAIL  unexpected regression error: {exc}", file=sys.stderr)
        return 1

    print("PASS  Daniel workflow regression (release gate not implied)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
