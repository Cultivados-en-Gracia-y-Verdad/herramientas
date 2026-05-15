#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — movement persistence substrate

Purpose:
- track movement tendencies that persist across macro windows
- identify sustained fields, repeated pressure, recovery, and weakening behavior
- provide a non-rendering substrate for later macro movement perception

This layer DOES NOT:
- render final human output
- assign H-levels
- assign themes
- interpret theology
- create sermon structure
- alter upstream data

It only analyzes persistence patterns from:
- continuity field
- Paso 9 support tendencies
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW_SIZE = 12


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]



def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

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
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------
# Load
# ---------------------------------------------------------


def load_field(book: str) -> list[dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "continuity-field"
        / f"{book}-continuity-field.jsonl"
    )

    rows = ordered(read_jsonl(path))

    if not rows:
        raise FileNotFoundError(f"No continuity field found for: {book}")

    return rows



def load_paso9(book: str) -> dict[str, dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "paso9-support"
        / f"{book}-paso9-support.jsonl"
    )

    out: dict[str, dict[str, Any]] = {}

    for row in ordered(read_jsonl(path)):
        key = str(row.get("predication_id") or row.get("stream_index") or "")
        if key:
            out[key] = row

    return out


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def parse_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]

    if not value:
        return []

    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
    except Exception:
        return []

    return []



def chapter_verse(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"



def dominant(counter: Counter[str]) -> str:
    if not counter:
        return "—"
    return counter.most_common(1)[0][0]



def movement_band(state_counter: Counter[str]) -> str:
    stable = state_counter.get("stable", 0) + state_counter.get("extended", 0)
    unstable = state_counter.get("unstable", 0)
    transitioning = state_counter.get("transitioning", 0)
    recovering = state_counter.get("recovering", 0)

    if unstable >= 4:
        return "transition_cluster"

    if transitioning >= 4:
        return "movement_accumulation"

    if stable >= 8:
        return "extended_stable_field"

    if recovering >= 4:
        return "recovery_field"

    return "mixed_continuity"



def make_windows(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for row in rows:
        current.append(row)
        if len(current) >= WINDOW_SIZE:
            windows.append(current)
            current = []

    if current:
        windows.append(current)

    return windows


# ---------------------------------------------------------
# Window profiles
# ---------------------------------------------------------


def profile_window(
    book: str,
    window_index: int,
    rows: list[dict[str, Any]],
    paso9: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    state_counter: Counter[str] = Counter()
    label_counter: Counter[str] = Counter()

    transition_total = 0
    persistence_total = 0
    extension_total = 0
    weakening_total = 0

    for row in rows:
        state = str(row.get("field_state") or "")
        state_counter[state] += 1

        transition_total += int(row.get("transition_score") or 0)
        persistence_total += int(row.get("persistence_score") or 0)
        extension_total += int(row.get("extension_score") or 0)
        weakening_total += int(row.get("weakening_score") or 0)

        key = str(row.get("predication_id") or row.get("stream_index") or "")
        p9 = paso9.get(key)
        if p9:
            for label in parse_json_list(p9.get("candidate_labels")):
                label_counter[label] += 1

    first = rows[0]
    last = rows[-1]

    return {
        "movement_window_id": f"MW{window_index:05d}",
        "book": book,
        "window_index": window_index,
        "start_ref": chapter_verse(first),
        "end_ref": chapter_verse(last),
        "start_stream_index": first.get("stream_index"),
        "end_stream_index": last.get("stream_index"),
        "predication_count": len(rows),
        "movement_band": movement_band(state_counter),
        "dominant_field": dominant(state_counter),
        "dominant_tendency": dominant(label_counter),
        "state_counts": json.dumps(dict(state_counter), ensure_ascii=False, sort_keys=True),
        "label_counts": json.dumps(dict(label_counter), ensure_ascii=False, sort_keys=True),
        "persistence_total": persistence_total,
        "transition_total": transition_total,
        "extension_total": extension_total,
        "weakening_total": weakening_total,
    }


# ---------------------------------------------------------
# Persistence runs
# ---------------------------------------------------------


def classify_run_kind(windows: list[dict[str, Any]]) -> str:
    bands = [str(row.get("movement_band") or "") for row in windows]
    fields = [str(row.get("dominant_field") or "") for row in windows]
    tendencies = [str(row.get("dominant_tendency") or "") for row in windows]

    if len(set(bands)) == 1:
        return f"band_persistence:{bands[0]}"

    if len(set(fields)) == 1:
        return f"field_persistence:{fields[0]}"

    if len(set(tendencies)) == 1:
        return f"tendency_persistence:{tendencies[0]}"

    return "mixed_persistence"



def continuation_score(prev: dict[str, Any], current: dict[str, Any]) -> int:
    score = 0

    if prev.get("movement_band") == current.get("movement_band"):
        score += 3

    if prev.get("dominant_field") == current.get("dominant_field"):
        score += 2

    if prev.get("dominant_tendency") == current.get("dominant_tendency"):
        score += 2

    # similar pressure balance
    prev_pressure = int(prev.get("transition_total") or 0) - int(prev.get("persistence_total") or 0)
    cur_pressure = int(current.get("transition_total") or 0) - int(current.get("persistence_total") or 0)

    if abs(prev_pressure - cur_pressure) <= 12:
        score += 1

    return score



def build_runs(book: str, windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not windows:
        return []

    runs: list[list[dict[str, Any]]] = []
    current_run: list[dict[str, Any]] = [windows[0]]

    for prev, current in zip(windows, windows[1:]):
        if continuation_score(prev, current) >= 4:
            current_run.append(current)
        else:
            runs.append(current_run)
            current_run = [current]

    if current_run:
        runs.append(current_run)

    out: list[dict[str, Any]] = []

    for idx, run in enumerate(runs, start=1):
        out.append({
            "movement_persistence_id": f"MP{idx:05d}",
            "book": book,
            "run_index": idx,
            "start_ref": run[0].get("start_ref"),
            "end_ref": run[-1].get("end_ref"),
            "start_window_index": run[0].get("window_index"),
            "end_window_index": run[-1].get("window_index"),
            "window_count": len(run),
            "persistence_kind": classify_run_kind(run),
            "dominant_band": dominant(Counter(str(row.get("movement_band") or "") for row in run)),
            "dominant_field": dominant(Counter(str(row.get("dominant_field") or "") for row in run)),
            "dominant_tendency": dominant(Counter(str(row.get("dominant_tendency") or "") for row in run)),
            "persistence_total": sum(int(row.get("persistence_total") or 0) for row in run),
            "transition_total": sum(int(row.get("transition_total") or 0) for row in run),
            "extension_total": sum(int(row.get("extension_total") or 0) for row in run),
            "weakening_total": sum(int(row.get("weakening_total") or 0) for row in run),
            "window_ids": json.dumps([row.get("movement_window_id") for row in run], ensure_ascii=False),
        })

    return out


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(windows: list[dict[str, Any]], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, Counter[str]] = {
        "movement_band": Counter(str(row.get("movement_band") or "") for row in windows),
        "dominant_field": Counter(str(row.get("dominant_field") or "") for row in windows),
        "dominant_tendency": Counter(str(row.get("dominant_tendency") or "") for row in windows),
        "persistence_kind": Counter(str(row.get("persistence_kind") or "") for row in runs),
    }

    out: list[dict[str, Any]] = []
    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            out.append({
                "summary_type": summary_type,
                "name": name,
                "count": count,
            })

    return out


# ---------------------------------------------------------
# Main processing
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, int, Path, Path, Path]:
    field_rows = load_field(book)
    paso9 = load_paso9(book)

    raw_windows = make_windows(field_rows)
    windows = [
        profile_window(book, idx, rows, paso9)
        for idx, rows in enumerate(raw_windows, start=1)
    ]

    runs = build_runs(book, windows)
    summary = build_summary(windows, runs)

    out_dir = mna_root() / "data" / "movement-persistence"

    windows_jsonl = out_dir / f"{book}-movement-windows.jsonl"
    windows_tsv = out_dir / f"{book}-movement-windows.tsv"
    runs_jsonl = out_dir / f"{book}-movement-persistence.jsonl"
    runs_tsv = out_dir / f"{book}-movement-persistence.tsv"
    summary_tsv = out_dir / f"{book}-movement-persistence-summary.tsv"

    write_jsonl(windows_jsonl, windows)
    write_tsv(windows_tsv, windows)
    write_jsonl(runs_jsonl, runs)
    write_tsv(runs_tsv, runs)
    write_tsv(summary_tsv, summary)

    return len(windows), len(runs), windows_tsv, runs_tsv, summary_tsv



def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_build_movement_persistence.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()

    window_count, run_count, windows_tsv, runs_tsv, summary_tsv = process_book(book)

    print(f"movement_windows = {window_count}")
    print(f"movement_persistence_runs = {run_count}")
    print(f"wrote: {windows_tsv}")
    print(f"wrote: {runs_tsv}")
    print(f"wrote: {summary_tsv}")


if __name__ == "__main__":
    main()
