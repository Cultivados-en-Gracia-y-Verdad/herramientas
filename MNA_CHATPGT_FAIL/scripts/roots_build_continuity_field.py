#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — unified continuity field engine

Internal substrate for:
- Paso 10 (continuous persistence)
- Paso 11 (extension persistence)
- Paso 12 (unit stabilization)

This layer DOES NOT:
- assign sections
- assign H-levels
- determine themes
- interpret semantics/theology
- generate macro structure

This layer ONLY tracks continuity persistence behavior.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

WINDOW = 3


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


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
                raise ValueError(f"{path}:{lineno}: invalid JSON") from exc

    return rows



def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: int(
            row.get("stream_index")
            or row.get("predication_index")
            or 0
        ),
    )


# ---------------------------------------------------------
# Load layers
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

    raise FileNotFoundError("No predication source found")



def load_continuity(book: str) -> dict[str, dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "subject-continuity-audit"
        / f"{book}-subject-continuity-audit.jsonl"
    )

    if not path.exists():
        return {}

    rows = ordered(read_jsonl(path))

    out: dict[str, dict[str, Any]] = {}

    for row in rows:
        key = str(
            row.get("predication_id")
            or row.get("stream_index")
            or ""
        )

        if key:
            out[key] = row

    return out



def load_recovery(book: str) -> dict[str, dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "continuity-recovery"
        / f"{book}-continuity-recovery.jsonl"
    )

    if not path.exists():
        return {}

    rows = ordered(read_jsonl(path))

    out: dict[str, dict[str, Any]] = {}

    for row in rows:
        key = str(row.get("stream_index") or "")

        if key:
            out[key] = row

    return out



def load_paso9(book: str) -> dict[str, dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "paso9-support"
        / f"{book}-paso9-support.jsonl"
    )

    if not path.exists():
        return {}

    rows = ordered(read_jsonl(path))

    out: dict[str, dict[str, Any]] = {}

    for row in rows:
        key = str(
            row.get("predication_id")
            or row.get("stream_index")
            or ""
        )

        if key:
            out[key] = row

    return out


# ---------------------------------------------------------
# Scoring
# ---------------------------------------------------------


def continuity_scores(
    continuity_row: dict[str, Any] | None,
    recovery_row: dict[str, Any] | None,
    paso9_row: dict[str, Any] | None,
) -> tuple[int, int, int, int, list[str]]:
    persistence = 0
    transition = 0
    extension = 0
    weakening = 0

    evidence: list[str] = []

    # continuity audit
    if continuity_row:
        status = str(continuity_row.get("continuity_status") or "")
        audit = str(continuity_row.get("continuity_audit_status") or "")

        evidence.append(f"continuity:{status}")
        evidence.append(f"audit:{audit}")

        if status == "same":
            persistence += 2
            extension += 1

        elif status == "shift":
            transition += 2
            weakening += 1

        if audit == "demonstrable_shift":
            transition += 2
            weakening += 1

    # recovery layer
    if recovery_row:
        profile = str(recovery_row.get("recovery_profile") or "")

        evidence.append(f"recovery:{profile}")

        if profile == "stabilized":
            persistence += 2
            extension += 1

        elif profile == "continued_instability":
            transition += 2
            weakening += 2

        elif profile == "unstable":
            weakening += 2

    # paso9 support tendencies
    if paso9_row:
        confidence = str(paso9_row.get("confidence") or "")

        evidence.append(f"paso9:{confidence}")

        try:
            labels = json.loads(
                str(paso9_row.get("candidate_labels") or "[]")
            )
        except Exception:
            labels = []

        if "EXPONE" in labels:
            persistence += 1
            extension += 1

        if "RESULTADO" in labels:
            transition += 1

        if "CONDICIÓN" in labels:
            extension += 1

    return (
        persistence,
        transition,
        extension,
        weakening,
        evidence,
    )



def determine_field_state(
    persistence: int,
    transition: int,
    extension: int,
    weakening: int,
) -> str:
    if transition >= 4 and weakening >= 3:
        return "unstable"

    if transition >= 3:
        return "transitioning"

    if weakening >= 3:
        return "weakening"

    if persistence >= 4 and extension >= 2:
        return "extended"

    if persistence >= 3:
        return "stable"

    return "recovering"


# ---------------------------------------------------------
# Build field
# ---------------------------------------------------------


def predication_key(row: dict[str, Any]) -> str:
    return str(
        row.get("predication_id")
        or row.get("stream_index")
        or ""
    )



def build_field(book: str) -> list[dict[str, Any]]:
    predications = load_predications(book)
    continuity = load_continuity(book)
    recovery = load_recovery(book)
    paso9 = load_paso9(book)

    rows: list[dict[str, Any]] = []

    for idx, predication in enumerate(predications, start=1):
        key = predication_key(predication)
        stream_key = str(predication.get("stream_index") or "")

        continuity_row = continuity.get(key)
        recovery_row = recovery.get(stream_key)
        paso9_row = paso9.get(key)

        (
            persistence,
            transition,
            extension,
            weakening,
            evidence,
        ) = continuity_scores(
            continuity_row,
            recovery_row,
            paso9_row,
        )

        field_state = determine_field_state(
            persistence,
            transition,
            extension,
            weakening,
        )

        rows.append({
            "continuity_field_id": f"CF{idx:05d}",
            "book": predication.get("book"),
            "chapter": predication.get("chapter"),
            "verse": predication.get("verse"),
            "reference": f"{predication.get('chapter')}:{predication.get('verse')}",
            "stream_index": predication.get("stream_index"),
            "predication_id": predication.get("predication_id"),
            "persistence_score": persistence,
            "transition_score": transition,
            "extension_score": extension,
            "weakening_score": weakening,
            "field_state": field_state,
            "evidence": json.dumps(evidence, ensure_ascii=False),
        })

    return rows


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}

    for row in rows:
        state = str(row.get("field_state") or "")
        counts[state] = counts.get(state, 0) + 1

    out: list[dict[str, Any]] = []

    for name, count in sorted(counts.items()):
        out.append({
            "summary_type": "field_state",
            "name": name,
            "count": count,
        })

    return out


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
    rows = build_field(book)
    summary = build_summary(rows)

    out_dir = mna_root() / "data" / "continuity-field"

    jsonl_out = out_dir / f"{book}-continuity-field.jsonl"
    tsv_out = out_dir / f"{book}-continuity-field.tsv"
    summary_out = out_dir / f"{book}-continuity-field-summary.tsv"

    write_jsonl(jsonl_out, rows)
    write_tsv(tsv_out, rows)
    write_tsv(summary_out, summary)

    return len(rows), tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_build_continuity_field.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    count, tsv_out, summary_out = process_book(book)

    print(f"continuity_field_rows = {count}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
