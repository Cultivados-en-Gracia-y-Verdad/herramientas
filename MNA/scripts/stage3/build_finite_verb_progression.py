#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage3-finite-verb-progression-builder-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row.get("chapter") or 0), int(row.get("verse") or 0), int(row.get("token_index") or 0))


def anchor_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("anchor_id")): r for r in rows if r.get("anchor_id")}


def candidate_anchor_id(row: dict[str, Any]) -> str:
    for key in ["anchor_id", "predicate_anchor_id", "unit_id", "clause_id"]:
        value = row.get(key)
        if value:
            return str(value)
    return ""


def is_independent_candidate(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or row.get("independency_status") or row.get("classification") or "").upper()
    if status in {"NO", "DEPENDENT", "NOT_INDEPENDENT", "SUBORDINATE"}:
        return False
    return True


def subject_signal(anchor: dict[str, Any]) -> str:
    explicit = str(anchor.get("explicit_subject_before") or "").strip()
    if explicit:
        return f"LEX:{explicit}"
    return f"MORPH:{anchor.get('person','')}:{anchor.get('number','')}"


def s_marker(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return ""
    if subject_signal(current) != subject_signal(previous):
        return "[S]"
    return ""


def m_marker(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return ""
    changes = []
    for field in ["tense", "voice", "mood"]:
        if str(current.get(field) or "") != str(previous.get(field) or ""):
            changes.append(field)
    if str(current.get("explicit_connector_before") or ""):
        changes.append("connector_before")
    if changes:
        return "[M]"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Stage 3 finite-verb progression observations.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    anchors_path = mna / "datasets" / "predicate-anchors" / f"{book}.jsonl"
    finite_path = mna / "datasets" / "finite-verbs" / f"{book}.jsonl"
    candidates_path = mna / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"
    out_path = mna / "datasets" / "stage3" / book / "finite-verb-progression.jsonl"

    anchors = sorted(load_jsonl(anchors_path), key=sort_key)
    finite_rows = sorted(load_jsonl(finite_path), key=sort_key)
    candidates = load_jsonl(candidates_path)

    # Add morphology fields from Stage 1 to Stage 2 anchor records by token location.
    finite_by_location = {(r["chapter"], r["verse"], r["token_index"]): r for r in finite_rows}
    for a in anchors:
        f = finite_by_location.get((a["chapter"], a["verse"], a["token_index"]))
        if f:
            for key in ["tense", "voice", "mood", "person", "number"]:
                a[key] = f.get(key, "")

    anchors_by_id = anchor_lookup(anchors)
    independent_ids = [candidate_anchor_id(r) for r in candidates if is_independent_candidate(r)]
    independent_ids = [i for i in independent_ids if i]

    ordered_independent_anchors = [a for a in anchors if a.get("anchor_id") in set(independent_ids)]

    rows = []
    previous = None
    for idx, anchor in enumerate(ordered_independent_anchors, start=1):
        s = s_marker(anchor, previous)
        m = m_marker(anchor, previous)
        rows.append({
            "record_type": "finite_verb_progression_observation",
            "book": book,
            "progression_order": idx,
            "anchor_id": anchor["anchor_id"],
            "chapter": anchor["chapter"],
            "verse": anchor["verse"],
            "token_index": anchor["token_index"],
            "greek_form": anchor["greek_form"],
            "lemma": anchor["lemma"],
            "morphology": anchor["morphology"],
            "tense": anchor.get("tense", ""),
            "voice": anchor.get("voice", ""),
            "mood": anchor.get("mood", ""),
            "person": anchor.get("person", ""),
            "number": anchor.get("number", ""),
            "explicit_connector_before": anchor.get("explicit_connector_before", ""),
            "explicit_subject_before": anchor.get("explicit_subject_before", ""),
            "subject_signal": subject_signal(anchor),
            "s_marker": s,
            "m_marker": m,
            "marker_policy": "CONSTRAINED_FINITE_VERB_PROGRESSION_OBSERVATION",
        })
        previous = anchor

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "record_type": "metadata",
            "builder_version": VERSION,
            "book": book,
            "source_anchors": str(anchors_path.relative_to(mna)),
            "source_independent_clause_candidates": str(candidates_path.relative_to(mna)),
            "rows_written": len(rows),
            "policy": "NO_TRUNK_NO_UNITS_NO_LABELS_NO_TITLES",
        }, ensure_ascii=False, sort_keys=True) + "\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 3 — Finite Verb Progression Builder")
    print(f"BOOK: {book}")
    print(f"ROWS WRITTEN: {len(rows)}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
