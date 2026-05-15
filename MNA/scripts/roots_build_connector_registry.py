#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — local connector registry

Purpose:
- inventory local connector evidence
- keep connectors subordinate to already-established clause structure
- support later Paso 9 label evidence without assigning labels here

Inputs:
- MNA/data/predications/<book>-predications.jsonl
- MNA/data/independent-stream/<book>-independent-stream.jsonl

Outputs:
- MNA/data/connectors/<book>-connector-registry.jsonl
- MNA/data/connectors/<book>-connector-registry.tsv
- MNA/data/connectors/<book>-connector-summary.tsv

Strict prohibitions:
- no semantic interpretation
- no theology
- no macro-structure inference
- no sectioning
- no Paso 9 label assignment
- no [M] assignment

This layer records ONLY local observable connector evidence.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Conservative initial connector map.
# This is intentionally small and provisional.
CONNECTOR_MAP = {
    "καί": ("coordinating", "coordination"),
    "δέ": ("coordinating", "coordination"),
    "ἀλλά": ("adversative", "coordination"),
    "οὐδέ": ("coordinating", "coordination"),
    "μηδέ": ("coordinating", "coordination"),
    "ἤ": ("coordinating", "coordination"),
    "γάρ": ("explanatory", "support"),
    "ὅτι": ("explanatory", "subordination"),
    "διό": ("inferential", "result"),
    "διότι": ("explanatory", "support"),
    "ὥστε": ("inferential", "result"),
    "οὖν": ("inferential", "result"),
    "ἵνα": ("purpose", "subordination"),
    "εἰ": ("conditional", "subordination"),
    "ἐάν": ("conditional", "subordination"),
    "ὅταν": ("temporal", "subordination"),
    "ὡς": ("comparative", "subordination"),
    "καθώς": ("comparative", "subordination"),
}


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("stream_index") or row.get("predication_index") or 0))


def normalize_token(value: Any) -> str:
    return str(value or "").strip().strip(",.;··—–“”‘’()[]{}«»").lower()


def token_candidates(row: dict[str, Any]) -> list[str]:
    """Extract possible Greek surface tokens from common row shapes.

    This stays permissive because upstream predication formats have evolved.
    It does not interpret; it only searches available Greek strings.
    """
    fields = [
        "greek",
        "greek_text",
        "clause_greek",
        "text_greek",
        "surface",
        "clause_text",
    ]

    tokens: list[str] = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, str):
            tokens.extend(value.split())

    # Some records store token arrays.
    for field in ["tokens", "greek_tokens"]:
        value = row.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    tokens.append(item)
                elif isinstance(item, dict):
                    token = item.get("text") or item.get("surface") or item.get("greek")
                    if token:
                        tokens.append(str(token))

    return tokens


def find_connectors(row: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for token in token_candidates(row):
        normalized = normalize_token(token)
        if normalized in CONNECTOR_MAP:
            found.append(normalized)
    return found


def link_direction(connector: str) -> str:
    if connector in {"γάρ", "διό", "διότι", "οὖν", "ὥστε"}:
        return "backward_local"
    if connector in {"ἵνα", "εἰ", "ἐάν", "ὅταν", "ὡς", "καθώς", "ὅτι"}:
        return "forward_or_embedded_local"
    return "parallel_local"


def build_registry(predications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = ordered(predications)
    registry: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        connectors = find_connectors(row)
        if not connectors:
            continue

        previous_row = rows[idx - 1] if idx > 0 else None
        next_row = rows[idx + 1] if idx + 1 < len(rows) else None

        for occurrence_index, connector in enumerate(connectors, start=1):
            connector_class, dependency_type = CONNECTOR_MAP[connector]
            direction = link_direction(connector)

            if direction == "backward_local":
                source = previous_row
                target = row
            elif direction == "parallel_local":
                source = previous_row
                target = row
            else:
                source = row
                target = next_row

            registry.append({
                "connector_registry_id": f"CN{len(registry)+1:05d}",
                "book": row.get("book"),
                "chapter": row.get("chapter"),
                "verse": row.get("verse"),
                "reference": f"{row.get('chapter')}:{row.get('verse')}",
                "stream_index": row.get("stream_index"),
                "predication_id": row.get("predication_id"),
                "connector_occurrence_index": occurrence_index,
                "connector_surface": connector,
                "connector_lemma": connector,
                "connector_class": connector_class,
                "dependency_type": dependency_type,
                "direction": direction,
                "source_predication_id": source.get("predication_id") if source else None,
                "target_predication_id": target.get("predication_id") if target else None,
                "source_reference": f"{source.get('chapter')}:{source.get('verse')}" if source else None,
                "target_reference": f"{target.get('chapter')}:{target.get('verse')}" if target else None,
                "explicit_connector": True,
                "scope_status": "local_candidate",
                "label_support_status": "not_assigned_here",
            })

    return registry


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters = {
        "connector_surface": Counter(str(row.get("connector_surface")) for row in rows),
        "connector_class": Counter(str(row.get("connector_class")) for row in rows),
        "dependency_type": Counter(str(row.get("dependency_type")) for row in rows),
        "direction": Counter(str(row.get("direction")) for row in rows),
    }

    summary: list[dict[str, Any]] = []
    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            summary.append({
                "summary_type": summary_type,
                "name": name,
                "count": count,
            })
    return summary


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def find_input_path(book: str) -> Path:
    root = mna_root()
    candidates = [
        root / "data" / "predications" / f"{book}-predications.jsonl",
        root / "data" / "independent-stream" / f"{book}-independent-stream.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No connector input found. Tried:\n" + "\n".join(str(p) for p in candidates))


def process_book(book: str) -> tuple[int, Path, Path, Path, Path]:
    in_path = find_input_path(book)
    rows = read_jsonl(in_path)
    registry = build_registry(rows)
    summary = build_summary(registry)

    out_dir = mna_root() / "data" / "connectors"
    jsonl_out = out_dir / f"{book}-connector-registry.jsonl"
    tsv_out = out_dir / f"{book}-connector-registry.tsv"
    summary_out = out_dir / f"{book}-connector-summary.tsv"

    write_jsonl(jsonl_out, registry)
    write_tsv(tsv_out, registry)
    write_tsv(summary_out, summary)

    return len(registry), in_path, jsonl_out, tsv_out, summary_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_build_connector_registry.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    count, in_path, jsonl_out, tsv_out, summary_out = process_book(book)

    print(f"read: {in_path}")
    print(f"connector_occurrences = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
