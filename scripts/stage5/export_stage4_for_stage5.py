#!/usr/bin/env python3
"""
Stage 4 → Stage 5 Contract Exporter

This script normalizes Stage 4 audited records into the
Stage 5 survivability input contract.

The exporter is intentionally conservative.

It does not:
- infer semantic importance
- compress meaning
- reorder structure
- reinterpret Stage 4 decisions

It only normalizes structural records into a stable
Stage 5 JSONL contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class ExportError(Exception):
    """Raised for Stage 5 export contract violations."""


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue

            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ExportError(
                    f"Invalid JSONL at {path}:{line_no}: {exc}"
                ) from exc

            if not isinstance(obj, dict):
                raise ExportError(
                    f"Expected JSON object at {path}:{line_no}"
                )

            yield obj


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Stage 4 material into the Stage 5 contract.

    This exporter preserves uncertainty.
    Missing values are retained as null rather than guessed.
    """

    warnings = list(record.get("warnings") or [])
    flags = list(record.get("flags") or [])

    normalized = {
        "book": record.get("book"),
        "chapter": record.get("chapter"),
        "verse": record.get("verse"),
        "unit_id": (
            record.get("unit_id")
            or record.get("structure_id")
            or record.get("id")
        ),
        "clause_id": record.get("clause_id"),
        "finite_verb": record.get("finite_verb"),
        "connector": record.get("connector"),
        "connector_greek": record.get("connector_greek"),
        "dependency_status": (
            record.get("dependency_status")
            or record.get("independency_status")
        ),
        "stage4_decision": (
            record.get("stage4_decision")
            or record.get("decision")
        ),
        "stage4_reason": (
            record.get("stage4_reason")
            or record.get("reason")
        ),
        "warnings": warnings,
        "flags": flags,
        "audit_provenance": {
            "source_stage": 4,
            "exporter": "export_stage4_for_stage5.py",
        },
    }

    validate_contract(normalized)

    return normalized


def validate_contract(record: Dict[str, Any]) -> None:
    required = [
        "book",
        "chapter",
        "verse",
        "unit_id",
    ]

    missing = [
        field for field in required
        if record.get(field) in (None, "")
    ]

    if missing:
        raise ExportError(
            f"Missing required Stage 5 contract fields: {missing}"
        )



def write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                + "\n"
            )



def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export Stage 4 records into Stage 5 contract format."
    )

    parser.add_argument(
        "input_jsonl",
        type=Path,
        help="Stage 4 JSONL input",
    )

    parser.add_argument(
        "output_jsonl",
        type=Path,
        help="Stage 5 normalized JSONL output",
    )

    args = parser.parse_args(argv)

    try:
        normalized_records = (
            normalize_record(record)
            for record in load_jsonl(args.input_jsonl)
        )

        write_jsonl(normalized_records, args.output_jsonl)

    except ExportError as exc:
        print(f"Stage 5 export error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
