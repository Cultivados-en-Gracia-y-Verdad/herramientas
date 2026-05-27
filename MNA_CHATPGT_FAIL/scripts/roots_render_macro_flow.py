#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — macro flow renderer

Purpose:
- render macro continuity movement visibility
- surface continuity persistence bands and transition clusters
- remain downstream-only and non-interpretive

This renderer DOES NOT:
- generate theology
- generate sermon structure
- assign H-levels
- interpret themes
- alter substrate data

It only renders movement visibility from:
- continuity field
- Paso 9 support tendencies
- dependency density
- predication continuity
- minimal textual anchors
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

WINDOW_SIZE = 12
MAX_ANCHORS = 6


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



def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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



def load_action_support(book: str) -> dict[str, dict[str, Any]]:
    path = (
        mna_root()
        / "data"
        / "paso13-action-support"
        / f"{book}-paso13-action-support.jsonl"
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
        return "TRANSITION CLUSTER"

    if transitioning >= 4:
        return "MOVEMENT ACCUMULATION"

    if stable >= 8:
        return "EXTENDED STABLE FIELD"

    if recovering >= 4:
        return "RECOVERY FIELD"

    return "MIXED CONTINUITY"



def chapter_verse(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"



def compact_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()



def anchor_text(
    row: dict[str, Any],
    action_support: dict[str, dict[str, Any]],
    paso9: dict[str, dict[str, Any]],
) -> str:
    key = str(row.get("predication_id") or row.get("stream_index") or "")
    action = action_support.get(key, {})
    p9 = paso9.get(key, {})

    verb = str(action.get("verb_support") or "").strip()
    subject = str(action.get("subject_support") or "").strip()
    scope = compact_space(str(action.get("scope_support") or ""))
    labels = parse_json_list(p9.get("candidate_labels"))
    state = str(row.get("field_state") or "")

    label_text = "/".join(labels[:2]) if labels else "—"

    if not verb:
        verb = "?"

    if subject and subject != "unknown":
        head = f"{subject} → =={verb}=="
    else:
        head = f"=={verb}=="

    if scope:
        # Keep anchors short; full text remains in detailed renderers.
        if len(scope) > 72:
            scope = scope[:69].rstrip() + "..."
        return f"{chapter_verse(row)}  {head:<34} [{state}; {label_text}]  {scope}"

    return f"{chapter_verse(row)}  {head:<34} [{state}; {label_text}]"



def choose_anchor_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) <= MAX_ANCHORS:
        return rows

    chosen: list[dict[str, Any]] = []

    # Always include start/end for movement perception.
    chosen.append(rows[0])

    # Include the strongest transition/weakening pressure points.
    ranked = sorted(
        rows[1:-1],
        key=lambda row: (
            int(row.get("transition_score") or 0)
            + int(row.get("weakening_score") or 0),
            int(row.get("stream_index") or 0),
        ),
        reverse=True,
    )

    for row in ranked:
        if row not in chosen:
            chosen.append(row)
        if len(chosen) >= MAX_ANCHORS - 1:
            break

    chosen.append(rows[-1])

    return sorted(chosen, key=lambda row: int(row.get("stream_index") or 0))


# ---------------------------------------------------------
# Rendering
# ---------------------------------------------------------


def render_window(
    rows: list[dict[str, Any]],
    paso9: dict[str, dict[str, Any]],
    action_support: dict[str, dict[str, Any]],
) -> list[str]:
    first = rows[0]
    last = rows[-1]

    start_ref = chapter_verse(first)
    end_ref = chapter_verse(last)

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

    band = movement_band(state_counter)

    lines: list[str] = []
    lines.append(f"### {start_ref} → {end_ref}")
    lines.append("")
    lines.append("```text")
    lines.append(f"FLOW BAND         {band}")
    lines.append("")
    lines.append("TEXTUAL ANCHORS")

    for row in choose_anchor_rows(rows):
        lines.append(f"  {anchor_text(row, action_support, paso9)}")

    lines.append("")
    lines.append("FIELD DISTRIBUTION")

    for name, count in sorted(state_counter.items()):
        lines.append(f"  {name:<16} {count}")

    lines.append("")
    lines.append("MOVEMENT PRESSURE")
    lines.append(f"  persistence      {persistence_total}")
    lines.append(f"  transition       {transition_total}")
    lines.append(f"  extension        {extension_total}")
    lines.append(f"  weakening        {weakening_total}")

    lines.append("")
    lines.append("PASO 9 TENDENCIES")

    for name, count in sorted(label_counter.items()):
        lines.append(f"  {name:<16} {count}")

    lines.append("")
    lines.append(f"DOMINANT FIELD     {dominant(state_counter)}")
    lines.append(f"DOMINANT TENDENCY  {dominant(label_counter)}")
    lines.append("```")
    lines.append("")

    return lines



def render_book(book: str) -> str:
    field_rows = load_field(book)
    paso9 = load_paso9(book)
    action_support = load_action_support(book)

    lines: list[str] = []
    lines.append(f"# ROOTS Macro Flow — {book}")
    lines.append("")
    lines.append("Vista macro de continuidad y acumulación de movimiento.")
    lines.append("No contiene temas, teología, H-levels ni interpretación.")
    lines.append("")

    windows: list[list[dict[str, Any]]] = []

    current: list[dict[str, Any]] = []

    for row in field_rows:
        current.append(row)

        if len(current) >= WINDOW_SIZE:
            windows.append(current)
            current = []

    if current:
        windows.append(current)

    current_chapter: int | None = None

    for rows in windows:
        chapter = int(rows[0].get("chapter") or 0)

        if chapter != current_chapter:
            current_chapter = chapter
            lines.append(f"## Capítulo {chapter}")
            lines.append("")

        lines.extend(render_window(rows, paso9, action_support))

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> Path:
    out_dir = mna_root() / "data" / "human-review"
    out_path = out_dir / f"{book}-macro-flow.md"

    write_text(out_path, render_book(book))

    return out_path



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_render_macro_flow.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    out_path = process_book(book)

    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
