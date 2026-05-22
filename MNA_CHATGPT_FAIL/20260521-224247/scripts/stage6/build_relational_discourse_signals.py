#!/usr/bin/env python3
"""
MNA Stage 6 — Relational Discourse Signal Builder

Purpose
-------
Observe surviving non-dependency relational discourse signals inside
independent-clause candidacy environments.

IMPORTANT
---------
This script does NOT:
- remove dependency,
- establish hierarchy,
- create parent/child structure,
- assign attachment targets,
- determine movement,
- determine labels,
- determine sections.

Stage 6 preserves observable discourse-flow signals only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

VERSION = "stage6-relational-discourse-signal-builder-v1"

OUTPUT_RECORD_TYPE = "relational_discourse_signal"

SIGNAL_OBSERVED = "SIGNAL_OBSERVED"
NO_CONNECTOR_OBSERVED = "NO_CONNECTOR_OBSERVED"
SIGNAL_PRESENT_CATEGORY_UNRESOLVED = "SIGNAL_PRESENT_CATEGORY_UNRESOLVED"

CONNECTOR_SIGNAL_MAP = {
    "καί": "continuity_signal",
    "δέ": "development_signal",
    "γάρ": "explanatory_signal",
    "οὖν": "inferential_signal",
    "ἀλλά": "contrast_signal",
    "ἀλλ’": "contrast_signal",
    "ἤ": "alternative_signal",
    "τε": "continuity_signal",
}


def root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            yield json.loads(stripped)


def build_signal_row(row: dict) -> dict:
    connector = row.get("connector_greek")

    if not connector:
        signal_category = "no_connector_signal"
        signal_status = NO_CONNECTOR_OBSERVED
    else:
        signal_category = CONNECTOR_SIGNAL_MAP.get(connector)
        if signal_category:
            signal_status = SIGNAL_OBSERVED
        else:
            signal_category = "unknown_signal"
            signal_status = SIGNAL_PRESENT_CATEGORY_UNRESOLVED

    return {
        "record_type": OUTPUT_RECORD_TYPE,
        "book": row.get("book"),
        "chapter": row.get("chapter"),
        "verse": row.get("verse"),
        "reference": f"{row.get('book')} {row.get('chapter')}:{row.get('verse')}",
        "unit_id": row.get("unit_id"),
        "clause_id": row.get("clause_id"),
        "finite_verb": row.get("finite_verb"),
        "connector_surface": connector,
        "connector_lemma": connector,
        "signal_category": signal_category,
        "signal_status": signal_status,
        "source_stage5_environment": row.get("candidacy_environment"),
        "notes": "Stage 6 preserves observable non-dependency relational discourse signals only.",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Stage 6 relational discourse signals.")
    parser.add_argument("book", help="Book slug, e.g. filipenses")
    args = parser.parse_args(argv)

    root = root_from_script()
    book = args.book.strip().lower()

    input_path = root / "datasets" / "stage5" / book / "trunk-candidacy-environments.jsonl"
    output_path = root / "datasets" / "stage6" / book / "relational-discourse-signals.jsonl"

    rows = [build_signal_row(row) for row in load_jsonl(input_path)]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 6 — Relational Discourse Signal Builder")
    print(f"VERSION: {VERSION}")
    print(f"BOOK: {book}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ROWS WRITTEN: {len(rows)}")
    print("POLICY: OBSERVATIONAL SIGNAL PRESERVATION ONLY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())