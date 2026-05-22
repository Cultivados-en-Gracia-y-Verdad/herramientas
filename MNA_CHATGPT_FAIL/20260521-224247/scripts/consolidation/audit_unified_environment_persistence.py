#!/usr/bin/env python3
"""
MNA Consolidation — Unified Environment Persistence Audit

Purpose
-------
Audit observable persistence/transition behavior across adjacent unified
environments.

This is NOT movement detection.
This is NOT label detection.
This is NOT sectioning.
This is NOT hierarchy.

It only counts adjacent observable transitions so Stage 7 can later be grounded
in actual persistence behavior.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Optional

VERSION = "unified-environment-persistence-audit-v1"


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def transition_key(left: object, right: object) -> str:
    return f"{left if left is not None else 'None'} -> {right if right is not None else 'None'}"


def safe_counter_to_dict(counter: Counter) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit observable persistence across unified environments.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    input_path = root / "datasets" / "unified-observable-environments" / f"{book}.jsonl"
    audit_path = root / "audits" / "consolidation" / book / "unified-environment-persistence-audit.json"

    rows = sorted(load_jsonl(input_path), key=lambda r: int(r.get("sequence_index") or 0))

    signal_category_transitions = Counter()
    signal_status_transitions = Counter()
    survival_decision_transitions = Counter()
    environment_transitions = Counter()
    connector_transitions = Counter()
    mood_transitions = Counter()
    person_transitions = Counter()
    number_transitions = Counter()

    same_signal_category_pairs = 0
    changed_signal_category_pairs = 0
    same_environment_pairs = 0
    changed_environment_pairs = 0
    adjacent_pair_count = 0

    for left, right in zip(rows, rows[1:]):
        adjacent_pair_count += 1

        left_signal = left.get("stage6_signal_category")
        right_signal = right.get("stage6_signal_category")
        left_environment = left.get("stage5_candidacy_environment")
        right_environment = right.get("stage5_candidacy_environment")

        signal_category_transitions[transition_key(left_signal, right_signal)] += 1
        signal_status_transitions[transition_key(left.get("stage6_signal_status"), right.get("stage6_signal_status"))] += 1
        survival_decision_transitions[transition_key(left.get("stage5_survival_decision"), right.get("stage5_survival_decision"))] += 1
        environment_transitions[transition_key(left_environment, right_environment)] += 1
        connector_transitions[transition_key(left.get("connector_surface"), right.get("connector_surface"))] += 1
        mood_transitions[transition_key(left.get("mood"), right.get("mood"))] += 1
        person_transitions[transition_key(left.get("person"), right.get("person"))] += 1
        number_transitions[transition_key(left.get("number"), right.get("number"))] += 1

        if left_signal == right_signal:
            same_signal_category_pairs += 1
        else:
            changed_signal_category_pairs += 1

        if left_environment == right_environment:
            same_environment_pairs += 1
        else:
            changed_environment_pairs += 1

    audit = {
        "record_type": "unified_environment_persistence_audit",
        "validator_version": VERSION,
        "book": book,
        "rows": len(rows),
        "adjacent_pair_count": adjacent_pair_count,
        "policy": "OBSERVATIONAL_PERSISTENCE_COUNTS_ONLY_NO_MOVEMENT_OR_LABEL_CLAIMS",
        "same_signal_category_pairs": same_signal_category_pairs,
        "changed_signal_category_pairs": changed_signal_category_pairs,
        "same_environment_pairs": same_environment_pairs,
        "changed_environment_pairs": changed_environment_pairs,
        "signal_category_transitions": safe_counter_to_dict(signal_category_transitions),
        "signal_status_transitions": safe_counter_to_dict(signal_status_transitions),
        "survival_decision_transitions": safe_counter_to_dict(survival_decision_transitions),
        "environment_transitions": safe_counter_to_dict(environment_transitions),
        "connector_transitions": safe_counter_to_dict(connector_transitions),
        "mood_transitions": safe_counter_to_dict(mood_transitions),
        "person_transitions": safe_counter_to_dict(person_transitions),
        "number_transitions": safe_counter_to_dict(number_transitions),
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2, sort_keys=True)

    print("MNA Consolidation — Unified Environment Persistence Audit")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"ROWS: {len(rows)}")
    print(f"ADJACENT PAIRS: {adjacent_pair_count}")
    print(f"WROTE -> {audit_path}")
    print("POLICY: OBSERVATIONAL PERSISTENCE COUNTS ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())