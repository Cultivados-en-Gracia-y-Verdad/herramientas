#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — calibrated movement substrate

Purpose:
- reduce artificial volatility in macro movement detection
- preserve raw continuity-field data unchanged
- produce a calibrated comparison layer for diagnostics

This layer DOES NOT:
- overwrite raw movement data
- assign H-levels
- assign themes
- interpret theology/rhetoric
- render final views

It only calibrates movement window classification using conservative smoothing,
pressure normalization, and dominance constraints.
"""

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RAW_WINDOW_SIZE = 12
SMOOTHING_RADIUS = 1

# Conservative thresholds after diagnostics showed high volatility.
STABLE_MIN_RATIO = 0.67
UNSTABLE_MIN_RATIO = 0.42
TRANSITIONING_MIN_RATIO = 0.42
RECOVERY_MIN_RATIO = 0.34
LABEL_DOMINANCE_CAP = 0.70


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
        key=lambda row: int(row.get("stream_index") or row.get("predication_index") or 0),
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
    path = mna_root() / "data" / "continuity-field" / f"{book}-continuity-field.jsonl"
    rows = ordered(read_jsonl(path))
    if not rows:
        raise FileNotFoundError(f"No continuity field found for: {book}")
    return rows



def load_paso9(book: str) -> dict[str, dict[str, Any]]:
    path = mna_root() / "data" / "paso9-support" / f"{book}-paso9-support.jsonl"
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



def make_windows(rows: list[dict[str, Any]], size: int = RAW_WINDOW_SIZE) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for row in rows:
        current.append(row)
        if len(current) >= size:
            windows.append(current)
            current = []
    if current:
        windows.append(current)
    return windows



def raw_band(state_counter: Counter[str]) -> str:
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



def calibrated_band(
    state_counter: Counter[str],
    pressure_delta: float,
    label_dominance_ratio: float,
) -> tuple[str, str]:
    total = sum(state_counter.values()) or 1
    stable_ratio = (state_counter.get("stable", 0) + state_counter.get("extended", 0)) / total
    unstable_ratio = state_counter.get("unstable", 0) / total
    transitioning_ratio = state_counter.get("transitioning", 0) / total
    recovering_ratio = state_counter.get("recovering", 0) / total

    # Label dominance guard: if the dominant label is too strong, avoid overpromoting
    # transition-like bands unless pressure is also strongly positive.
    label_guard = label_dominance_ratio >= LABEL_DOMINANCE_CAP

    if stable_ratio >= STABLE_MIN_RATIO and pressure_delta <= 10:
        return "extended_stable_field", "stable_ratio_threshold"

    if unstable_ratio >= UNSTABLE_MIN_RATIO and pressure_delta >= 18:
        if label_guard and pressure_delta < 30:
            return "mixed_continuity", "label_dominance_guard"
        return "transition_cluster", "unstable_ratio_pressure"

    if transitioning_ratio >= TRANSITIONING_MIN_RATIO and pressure_delta >= 12:
        if label_guard and pressure_delta < 24:
            return "mixed_continuity", "label_dominance_guard"
        return "movement_accumulation", "transitioning_ratio_pressure"

    if recovering_ratio >= RECOVERY_MIN_RATIO and pressure_delta <= 12:
        return "recovery_field", "recovery_ratio_threshold"

    return "mixed_continuity", "default_mixed"


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

    label_total = sum(label_counter.values())
    top_label_count = label_counter.most_common(1)[0][1] if label_counter else 0
    label_dominance_ratio = round(top_label_count / label_total, 4) if label_total else 0.0

    pressure_delta = transition_total - persistence_total
    raw = raw_band(state_counter)
    calibrated, reason = calibrated_band(state_counter, pressure_delta, label_dominance_ratio)

    first = rows[0]
    last = rows[-1]

    return {
        "calibrated_window_id": f"CMW{window_index:05d}",
        "book": book,
        "window_index": window_index,
        "start_ref": chapter_verse(first),
        "end_ref": chapter_verse(last),
        "start_stream_index": first.get("stream_index"),
        "end_stream_index": last.get("stream_index"),
        "predication_count": len(rows),
        "raw_band": raw,
        "calibrated_band": calibrated,
        "calibration_reason": reason,
        "band_changed": raw != calibrated,
        "dominant_field": dominant(state_counter),
        "dominant_tendency": dominant(label_counter),
        "state_counts": json.dumps(dict(state_counter), ensure_ascii=False, sort_keys=True),
        "label_counts": json.dumps(dict(label_counter), ensure_ascii=False, sort_keys=True),
        "label_dominance_ratio": label_dominance_ratio,
        "persistence_total": persistence_total,
        "transition_total": transition_total,
        "extension_total": extension_total,
        "weakening_total": weakening_total,
        "pressure_delta": pressure_delta,
    }


# ---------------------------------------------------------
# Smoothing and diagnostics
# ---------------------------------------------------------


def smooth_bands(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    smoothed: list[dict[str, Any]] = []

    for idx, row in enumerate(windows):
        left = max(0, idx - SMOOTHING_RADIUS)
        right = min(len(windows), idx + SMOOTHING_RADIUS + 1)
        neighborhood = windows[left:right]
        counter = Counter(str(item.get("calibrated_band") or "") for item in neighborhood)
        smoothed_band = dominant(counter)

        new_row = dict(row)
        new_row["smoothed_band"] = smoothed_band
        new_row["smoothing_changed"] = smoothed_band != row.get("calibrated_band")
        new_row["smoothing_neighborhood"] = json.dumps(
            [item.get("calibrated_window_id") for item in neighborhood],
            ensure_ascii=False,
        )
        smoothed.append(new_row)

    return smoothed



def build_calibration_summary(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []

    counters = {
        "raw_band": Counter(str(row.get("raw_band") or "") for row in windows),
        "calibrated_band": Counter(str(row.get("calibrated_band") or "") for row in windows),
        "smoothed_band": Counter(str(row.get("smoothed_band") or "") for row in windows),
        "calibration_reason": Counter(str(row.get("calibration_reason") or "") for row in windows),
        "band_changed": Counter(str(row.get("band_changed") or "") for row in windows),
        "smoothing_changed": Counter(str(row.get("smoothing_changed") or "") for row in windows),
    }

    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            summary.append({
                "summary_type": summary_type,
                "name": name,
                "count": count,
            })

    if windows:
        raw_switches = count_switches([str(row.get("raw_band") or "") for row in windows])
        cal_switches = count_switches([str(row.get("calibrated_band") or "") for row in windows])
        smooth_switches = count_switches([str(row.get("smoothed_band") or "") for row in windows])

        summary.extend([
            {"summary_type": "switch_count", "name": "raw_band", "count": raw_switches},
            {"summary_type": "switch_count", "name": "calibrated_band", "count": cal_switches},
            {"summary_type": "switch_count", "name": "smoothed_band", "count": smooth_switches},
        ])

    return summary



def count_switches(values: list[str]) -> int:
    switches = 0
    prev = None
    for value in values:
        if prev is not None and value != prev:
            switches += 1
        prev = value
    return switches


# ---------------------------------------------------------
# Main processing
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, Path, Path]:
    field_rows = load_field(book)
    paso9 = load_paso9(book)

    raw_windows = make_windows(field_rows)
    profiled = [
        profile_window(book, idx, rows, paso9)
        for idx, rows in enumerate(raw_windows, start=1)
    ]
    calibrated = smooth_bands(profiled)
    summary = build_calibration_summary(calibrated)

    out_dir = mna_root() / "data" / "calibrated-movement"
    jsonl_out = out_dir / f"{book}-calibrated-movement.jsonl"
    tsv_out = out_dir / f"{book}-calibrated-movement.tsv"
    summary_out = out_dir / f"{book}-calibrated-movement-summary.tsv"

    write_jsonl(jsonl_out, calibrated)
    write_tsv(tsv_out, calibrated)
    write_tsv(summary_out, summary)

    return len(calibrated), tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_build_calibrated_movement.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    count, tsv_out, summary_out = process_book(book)

    print(f"calibrated_movement_windows = {count}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
