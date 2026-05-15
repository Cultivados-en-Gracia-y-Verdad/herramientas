#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — movement diagnostics builder

Purpose:
- verify movement behavior before further interpretation or rendering
- expose instability, label dependence, window artifacts, and pressure inflation
- remain objective, factual, and non-interpretive

This layer DOES NOT:
- assign H-levels
- assign themes
- correct the data
- render final views
- interpret theology or rhetoric

It only reports diagnostic facts about the movement substrate.
"""

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW_SIZES = [8, 10, 12, 14, 16]
DEFAULT_WINDOW_SIZE = 12


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



def make_windows(rows: list[dict[str, Any]], size: int, offset: int = 0) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    usable = rows[offset:] if offset else rows

    for row in usable:
        current.append(row)
        if len(current) >= size:
            windows.append(current)
            current = []

    if current:
        windows.append(current)

    return windows



def profile_window(rows: list[dict[str, Any]], paso9: dict[str, dict[str, Any]]) -> dict[str, Any]:
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

    return {
        "start_ref": chapter_verse(rows[0]),
        "end_ref": chapter_verse(rows[-1]),
        "start_stream_index": rows[0].get("stream_index"),
        "end_stream_index": rows[-1].get("stream_index"),
        "predication_count": len(rows),
        "movement_band": movement_band(state_counter),
        "dominant_field": dominant(state_counter),
        "dominant_tendency": dominant(label_counter),
        "state_counts": dict(state_counter),
        "label_counts": dict(label_counter),
        "persistence_total": persistence_total,
        "transition_total": transition_total,
        "extension_total": extension_total,
        "weakening_total": weakening_total,
        "pressure_delta": pressure_delta,
        "label_dominance_ratio": label_dominance_ratio,
    }


# ---------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------


def field_volatility(rows: list[dict[str, Any]]) -> dict[str, Any]:
    switches = 0
    prev = None
    states: Counter[str] = Counter()

    for row in rows:
        state = str(row.get("field_state") or "")
        states[state] += 1
        if prev is not None and state != prev:
            switches += 1
        prev = state

    possible = max(len(rows) - 1, 1)
    return {
        "diagnostic_type": "field_volatility",
        "name": "field_state_switch_rate",
        "value": round(switches / possible, 4),
        "count": switches,
        "total": possible,
        "details": json.dumps(dict(states), ensure_ascii=False, sort_keys=True),
    }



def pressure_inflation(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deltas = [int(row.get("pressure_delta") or 0) for row in windows]
    if not deltas:
        return []

    mean = statistics.mean(deltas)
    stdev = statistics.pstdev(deltas)
    threshold = mean + stdev

    findings: list[dict[str, Any]] = []
    for idx, row in enumerate(windows, start=1):
        delta = int(row.get("pressure_delta") or 0)
        if delta >= threshold and delta > 0:
            findings.append({
                "diagnostic_type": "pressure_inflation",
                "name": f"window_{idx}",
                "value": delta,
                "count": delta,
                "total": 0,
                "details": json.dumps({
                    "start_ref": row.get("start_ref"),
                    "end_ref": row.get("end_ref"),
                    "threshold": round(threshold, 4),
                    "transition_total": row.get("transition_total"),
                    "persistence_total": row.get("persistence_total"),
                    "movement_band": row.get("movement_band"),
                }, ensure_ascii=False, sort_keys=True),
            })
    return findings



def label_dependence(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for idx, row in enumerate(windows, start=1):
        ratio = float(row.get("label_dominance_ratio") or 0.0)
        if ratio >= 0.70:
            findings.append({
                "diagnostic_type": "label_dependence",
                "name": f"window_{idx}",
                "value": ratio,
                "count": 0,
                "total": 0,
                "details": json.dumps({
                    "start_ref": row.get("start_ref"),
                    "end_ref": row.get("end_ref"),
                    "dominant_tendency": row.get("dominant_tendency"),
                    "label_counts": row.get("label_counts"),
                    "movement_band": row.get("movement_band"),
                }, ensure_ascii=False, sort_keys=True),
            })

    return findings



def flat_region_detection(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for idx, row in enumerate(windows, start=1):
        transition = int(row.get("transition_total") or 0)
        persistence = int(row.get("persistence_total") or 0)
        weakening = int(row.get("weakening_total") or 0)

        if transition <= 8 and weakening <= 4 and persistence >= 25:
            findings.append({
                "diagnostic_type": "flat_region_detection",
                "name": f"window_{idx}",
                "value": persistence,
                "count": transition,
                "total": weakening,
                "details": json.dumps({
                    "start_ref": row.get("start_ref"),
                    "end_ref": row.get("end_ref"),
                    "movement_band": row.get("movement_band"),
                    "dominant_field": row.get("dominant_field"),
                    "dominant_tendency": row.get("dominant_tendency"),
                }, ensure_ascii=False, sort_keys=True),
            })

    return findings



def oscillation_detection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unstable_like = {"unstable", "transitioning"}
    stable_like = {"stable", "extended", "recovering"}
    flips = 0
    prev_group = None

    for row in rows:
        state = str(row.get("field_state") or "")
        if state in unstable_like:
            group = "unstable_like"
        elif state in stable_like:
            group = "stable_like"
        else:
            group = "other"

        if prev_group is not None and group != prev_group:
            flips += 1
        prev_group = group

    possible = max(len(rows) - 1, 1)
    return {
        "diagnostic_type": "oscillation_detection",
        "name": "stable_unstable_flip_rate",
        "value": round(flips / possible, 4),
        "count": flips,
        "total": possible,
        "details": json.dumps({
            "stable_like": sorted(stable_like),
            "unstable_like": sorted(unstable_like),
        }, ensure_ascii=False, sort_keys=True),
    }



def window_sensitivity(rows: list[dict[str, Any]], paso9: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    size_counters: dict[int, Counter[str]] = {}
    for size in WINDOW_SIZES:
        profiles = [profile_window(w, paso9) for w in make_windows(rows, size)]
        size_counters[size] = Counter(str(p.get("movement_band") or "") for p in profiles)

    all_bands = sorted({band for counter in size_counters.values() for band in counter})

    for band in all_bands:
        counts = [size_counters[size].get(band, 0) for size in WINDOW_SIZES]
        spread = max(counts) - min(counts)
        avg = statistics.mean(counts)
        relative_spread = round(spread / avg, 4) if avg else 0.0

        findings.append({
            "diagnostic_type": "window_sensitivity",
            "name": band,
            "value": relative_spread,
            "count": spread,
            "total": int(avg),
            "details": json.dumps({
                "window_sizes": WINDOW_SIZES,
                "counts": counts,
            }, ensure_ascii=False, sort_keys=True),
        })

    return findings



def overlap_stability(rows: list[dict[str, Any]], paso9: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    base_profiles = [profile_window(w, paso9) for w in make_windows(rows, DEFAULT_WINDOW_SIZE, offset=0)]
    shifted_profiles = [profile_window(w, paso9) for w in make_windows(rows, DEFAULT_WINDOW_SIZE, offset=DEFAULT_WINDOW_SIZE // 2)]

    base_counter = Counter(str(p.get("movement_band") or "") for p in base_profiles)
    shifted_counter = Counter(str(p.get("movement_band") or "") for p in shifted_profiles)

    bands = sorted(set(base_counter) | set(shifted_counter))
    findings: list[dict[str, Any]] = []

    for band in bands:
        base_count = base_counter.get(band, 0)
        shifted_count = shifted_counter.get(band, 0)
        diff = abs(base_count - shifted_count)
        denom = max(base_count, shifted_count, 1)
        findings.append({
            "diagnostic_type": "overlap_stability",
            "name": band,
            "value": round(diff / denom, 4),
            "count": diff,
            "total": denom,
            "details": json.dumps({
                "base_count": base_count,
                "shifted_count": shifted_count,
                "window_size": DEFAULT_WINDOW_SIZE,
                "offset": DEFAULT_WINDOW_SIZE // 2,
            }, ensure_ascii=False, sort_keys=True),
        })

    return findings


# ---------------------------------------------------------
# Build diagnostics
# ---------------------------------------------------------


def build_default_windows(rows: list[dict[str, Any]], paso9: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [profile_window(w, paso9) for w in make_windows(rows, DEFAULT_WINDOW_SIZE)]



def build_diagnostics(book: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_field(book)
    paso9 = load_paso9(book)
    windows = build_default_windows(rows, paso9)

    diagnostics: list[dict[str, Any]] = []
    diagnostics.append(field_volatility(rows))
    diagnostics.append(oscillation_detection(rows))
    diagnostics.extend(pressure_inflation(windows))
    diagnostics.extend(label_dependence(windows))
    diagnostics.extend(flat_region_detection(windows))
    diagnostics.extend(window_sensitivity(rows, paso9))
    diagnostics.extend(overlap_stability(rows, paso9))

    summary_counter: Counter[str] = Counter(str(row.get("diagnostic_type") or "") for row in diagnostics)
    summary = [
        {"summary_type": "diagnostic_count", "name": name, "count": count}
        for name, count in sorted(summary_counter.items())
    ]

    return diagnostics, summary


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, Path, Path]:
    diagnostics, summary = build_diagnostics(book)

    out_dir = mna_root() / "data" / "movement-diagnostics"
    jsonl_out = out_dir / f"{book}-movement-diagnostics.jsonl"
    tsv_out = out_dir / f"{book}-movement-diagnostics.tsv"
    summary_out = out_dir / f"{book}-movement-diagnostics-summary.tsv"

    write_jsonl(jsonl_out, diagnostics)
    write_tsv(tsv_out, diagnostics)
    write_tsv(summary_out, summary)

    return len(diagnostics), tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_build_movement_diagnostics.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    count, tsv_out, summary_out = process_book(book)

    print(f"movement_diagnostics = {count}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
