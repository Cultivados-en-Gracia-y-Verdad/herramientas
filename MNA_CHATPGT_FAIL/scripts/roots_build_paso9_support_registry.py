#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — Paso 9 support registry

Purpose:
- aggregate conservative local Paso 9 evidence
- support later human-readable Paso 9 outputs
- avoid automatic discourse labeling

This layer DOES NOT:
- assign final labels
- determine macro structure
- determine sections
- assign [M]
- interpret semantics/theology

This layer ONLY aggregates observable local evidence.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


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
    return sorted(
        rows,
        key=lambda row: int(
            row.get("stream_index")
            or row.get("predication_index")
            or row.get("id")
            or 0
        ),
    )


# ---------------------------------------------------------
# Loading layers
# ---------------------------------------------------------


def load_predications(book: str) -> list[dict[str, Any]]:
    root = mna_root()

    candidates = [
        root / "data" / "predications" / f"{book}-predications.jsonl",
        root / "data" / "independent-stream" / f"{book}-independent-stream.jsonl",
    ]

    for path in candidates:
        if path.exists():
            return ordered(read_jsonl(path))

    raise FileNotFoundError(
        "No predication source found. Tried:\n"
        + "\n".join(str(p) for p in candidates)
    )



def load_connectors(book: str) -> list[dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "connectors"
        / f"{book}-connector-registry.jsonl"
    )

    if not path.exists():
        return []

    return ordered(read_jsonl(path))



def load_continuity(book: str) -> list[dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "subject-continuity-audit"
        / f"{book}-subject-continuity-audit.jsonl"
    )

    if not path.exists():
        return []

    return ordered(read_jsonl(path))


# ---------------------------------------------------------
# Indexing
# ---------------------------------------------------------


def predication_key(row: dict[str, Any]) -> str:
    return str(
        row.get("predication_id")
        or row.get("stream_index")
        or row.get("id")
    )



def connector_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        key = str(row.get("target_predication_id") or "")
        if not key:
            continue

        index.setdefault(key, []).append(row)

    return index



def continuity_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for row in rows:
        key = str(
            row.get("predication_id")
            or row.get("stream_index")
            or row.get("id")
        )

        if key:
            index[key] = row

    return index


# ---------------------------------------------------------
# Evidence fusion
# ---------------------------------------------------------


def connector_support(rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    candidates: list[str] = []
    evidence: list[str] = []

    for row in rows:
        connector_class = str(row.get("connector_class") or "")
        connector_surface = str(row.get("connector_surface") or "")

        evidence.append(f"connector:{connector_surface}:{connector_class}")

        if connector_class == "conditional":
            candidates.append("CONDICIÓN")

        elif connector_class == "purpose":
            candidates.append("PROPÓSITO")

        elif connector_class == "inferential":
            candidates.append("RESULTADO")

        elif connector_class == "explanatory":
            candidates.extend(["RAZÓN", "ACLARA"])

        elif connector_class == "comparative":
            candidates.append("ACLARA")

    return candidates, evidence



def continuity_support(row: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    if row is None:
        return ["EXPONE"], ["continuity:none"]

    continuity_status = str(row.get("continuity_status") or "")
    audit_status = str(row.get("continuity_audit_status") or "")

    evidence = [
        f"continuity:{continuity_status}",
        f"audit:{audit_status}",
    ]

    if continuity_status == "same":
        return ["EXPONE"], evidence

    if continuity_status == "shift":
        return ["ACLARA"], evidence

    return ["EXPONE"], evidence



def dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)

    return out



def determine_confidence(connector_candidates: list[str], continuity_candidates: list[str]) -> str:
    overlap = set(connector_candidates) & set(continuity_candidates)

    if overlap:
        return "moderate"

    if connector_candidates:
        return "moderate"

    return "low"


# ---------------------------------------------------------
# Registry build
# ---------------------------------------------------------


def build_registry(
    predications: list[dict[str, Any]],
    connectors: list[dict[str, Any]],
    continuity_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    connector_map = connector_index(connectors)
    continuity_map = continuity_index(continuity_rows)

    registry: list[dict[str, Any]] = []

    for idx, predication in enumerate(predications, start=1):
        key = predication_key(predication)

        connector_rows = connector_map.get(key, [])
        continuity_row = continuity_map.get(key)

        connector_candidates, connector_evidence = connector_support(connector_rows)
        continuity_candidates, continuity_evidence = continuity_support(continuity_row)

        candidate_labels = dedupe(
            connector_candidates + continuity_candidates
        )

        if not candidate_labels:
            candidate_labels = ["EXPONE"]

        confidence = determine_confidence(
            connector_candidates,
            continuity_candidates,
        )

        registry.append({
            "paso9_support_id": f"P9{idx:05d}",
            "book": predication.get("book"),
            "chapter": predication.get("chapter"),
            "verse": predication.get("verse"),
            "reference": f"{predication.get('chapter')}:{predication.get('verse')}",
            "stream_index": predication.get("stream_index"),
            "predication_id": predication.get("predication_id"),
            "connector_support": json.dumps(connector_candidates, ensure_ascii=False),
            "continuity_support": json.dumps(continuity_candidates, ensure_ascii=False),
            "candidate_labels": json.dumps(candidate_labels, ensure_ascii=False),
            "confidence": confidence,
            "evidence_sources": json.dumps(
                connector_evidence + continuity_evidence,
                ensure_ascii=False,
            ),
            "final_label_assigned": False,
        })

    return registry


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, dict[str, int]] = {
        "confidence": {},
        "candidate_label": {},
    }

    for row in rows:
        confidence = str(row.get("confidence") or "")
        counters["confidence"][confidence] = (
            counters["confidence"].get(confidence, 0) + 1
        )

        labels = json.loads(str(row.get("candidate_labels") or "[]"))

        for label in labels:
            counters["candidate_label"][label] = (
                counters["candidate_label"].get(label, 0) + 1
            )

    summary: list[dict[str, Any]] = []

    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            summary.append({
                "summary_type": summary_type,
                "name": name,
                "count": count,
            })

    return summary


# ---------------------------------------------------------
# Output
# ---------------------------------------------------------


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")



def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            delimiter="\t",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, Path, Path]:
    predications = load_predications(book)
    connectors = load_connectors(book)
    continuity_rows = load_continuity(book)

    registry = build_registry(
        predications,
        connectors,
        continuity_rows,
    )

    summary = build_summary(registry)

    out_dir = mna_root() / "data" / "paso9-support"

    jsonl_out = out_dir / f"{book}-paso9-support.jsonl"
    tsv_out = out_dir / f"{book}-paso9-support.tsv"
    summary_out = out_dir / f"{book}-paso9-support-summary.tsv"

    write_jsonl(jsonl_out, registry)
    write_tsv(tsv_out, registry)
    write_tsv(summary_out, summary)

    return len(registry), tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_build_paso9_support_registry.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    count, tsv_out, summary_out = process_book(book)

    print(f"paso9_support_rows = {count}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
