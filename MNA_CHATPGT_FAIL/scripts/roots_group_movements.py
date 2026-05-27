#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — mechanical movement grouping

This script follows the ROOTS pipeline:

independent clause stream
→ [S] subject continuity
→ [M] movement shifts
→ mechanical movement groups

This is NOT final labels, patterns, or units.

Purpose:
- group adjacent movement records into contiguous mechanical runs
- preserve every movement reason
- expose stable grammatical regimes before labeling

Allowed input:
- MNA/data/movements/<book>-movements.jsonl

Outputs:
- MNA/data/movement-groups/<book>-movement-groups.jsonl
- MNA/data/movement-groups/<book>-movement-groups.tsv

Strict prohibitions:
- no Scripture text reading
- no semantic labels
- no theological interpretation
- no topology reconstruction
- no H0/H1/H2 assignment
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BREAK_STATUSES = {"strong"}


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


def parse_reasons(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


def signature(row: dict[str, Any]) -> str:
    reasons = parse_reasons(row.get("movement_reasons"))
    if not reasons:
        return row.get("movement_status") or "none"
    return "+".join(sorted(reasons))


def starts_new_group(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    if previous is None:
        return True

    if current.get("movement_status") in BREAK_STATUSES:
        return True

    if previous.get("chapter") != current.get("chapter"):
        return True

    if signature(previous) != signature(current):
        return True

    return False


def summarize_group(group_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counter = Counter(row.get("movement_status") or "none" for row in rows)
    reason_counter: Counter[str] = Counter()

    for row in rows:
        reason_counter.update(parse_reasons(row.get("movement_reasons")))

    first = rows[0]
    last = rows[-1]

    return {
        "movement_group_id": f"MG{group_id:04d}",
        "group_index": group_id,
        "book": first.get("book"),
        "start_stream_index": first.get("stream_index"),
        "end_stream_index": last.get("stream_index"),
        "start_reference": f"{first.get('chapter')}:{first.get('verse')}",
        "end_reference": f"{last.get('chapter')}:{last.get('verse')}",
        "start_predication_id": first.get("predication_id"),
        "end_predication_id": last.get("predication_id"),
        "record_count": len(rows),
        "dominant_movement_status": status_counter.most_common(1)[0][0],
        "movement_status_counts": json.dumps(dict(sorted(status_counter.items())), ensure_ascii=False, sort_keys=True),
        "movement_reason_counts": json.dumps(dict(sorted(reason_counter.items())), ensure_ascii=False, sort_keys=True),
        "group_signature": signature(first),
        "first_finite_verb": first.get("finite_verb"),
        "last_finite_verb": last.get("finite_verb"),
    }


def build_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None

    for row in rows:
        if starts_new_group(previous, row):
            if current_group:
                groups.append(current_group)
            current_group = [row]
        else:
            current_group.append(row)

        previous = row

    if current_group:
        groups.append(current_group)

    return [summarize_group(i, group) for i, group in enumerate(groups, start=1)]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "movement_group_id",
        "group_index",
        "book",
        "start_stream_index",
        "end_stream_index",
        "start_reference",
        "end_reference",
        "start_predication_id",
        "end_predication_id",
        "record_count",
        "dominant_movement_status",
        "movement_status_counts",
        "movement_reason_counts",
        "group_signature",
        "first_finite_verb",
        "last_finite_verb",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_book(book: str) -> tuple[Path, Path, int]:
    in_path = mna_root() / "data" / "movements" / f"{book}-movements.jsonl"
    rows = read_jsonl(in_path)
    groups = build_groups(rows)

    out_dir = mna_root() / "data" / "movement-groups"
    jsonl_out = out_dir / f"{book}-movement-groups.jsonl"
    tsv_out = out_dir / f"{book}-movement-groups.tsv"

    write_jsonl(jsonl_out, groups)
    write_tsv(tsv_out, groups)

    return jsonl_out, tsv_out, len(groups)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_group_movements.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    jsonl_out, tsv_out, count = process_book(book)

    print(f"WROTE {count} movement group record(s): {jsonl_out}")
    print(f"WROTE {count} movement group record(s): {tsv_out}")


if __name__ == "__main__":
    main()
