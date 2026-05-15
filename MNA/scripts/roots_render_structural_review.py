#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — structural review renderer

Purpose:
- render the existing ROOTS substrate with a clearer visual grammar
- remain downstream-only
- make predication flow, connectors, Paso 9 support, continuity field, and Paso 13 support easier to audit

This renderer DOES NOT:
- assign labels
- assign sections
- generate H-level headings
- infer structure
- interpret the text
- alter substrate data

It is a readability layer only.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


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
            or row.get("id")
            or 0
        ),
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        rows = read_jsonl(path)
        if rows:
            return ordered(rows)

    raise FileNotFoundError("No predication source found")


def load_index(book: str, folder: str, suffix: str) -> dict[str, dict[str, Any]]:
    path = mna_root() / "data" / folder / f"{book}-{suffix}.jsonl"
    rows = ordered(read_jsonl(path))

    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = predication_key(row)
        if key:
            index[key] = row
    return index


def load_connectors_by_target(book: str) -> dict[str, list[dict[str, Any]]]:
    path = mna_root() / "data" / "connectors" / f"{book}-connector-registry.jsonl"
    rows = ordered(read_jsonl(path))

    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("target_predication_id") or "")
        if key:
            index[key].append(row)
    return index


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


GREEK_FIELDS = [
    "greek",
    "greek_text",
    "clause_greek",
    "text_greek",
    "finite_clause_greek",
    "raw_greek",
]

NBLA_FIELDS = [
    "nbla",
    "spanish",
    "text_nbla",
    "clause_nbla",
    "visible_clause",
    "rendered_clause",
    "clause_text",
]

VERB_FIELDS = [
    "verb",
    "finite_verb",
    "main_verb",
    "verb_surface",
    "greek_verb",
]

SUBJECT_FIELDS = [
    "subject",
    "subject_label",
    "subject_refined",
    "implicit_subject",
    "subject_person_number",
]


def first_text(row: dict[str, Any] | None, fields: list[str]) -> str:
    if not row:
        return ""
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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


def predication_key(row: dict[str, Any]) -> str:
    return str(row.get("predication_id") or row.get("stream_index") or row.get("id") or "")


def ref_tuple(row: dict[str, Any]) -> tuple[int, int]:
    return (int(row.get("chapter") or 0), int(row.get("verse") or 0))


def render_list(values: list[str]) -> str:
    if not values:
        return "—"
    return " · ".join(values)


def field_badge(field_state: str) -> str:
    if field_state == "stable":
        return "STABLE"
    if field_state == "extended":
        return "EXTENDED"
    if field_state == "recovering":
        return "RECOVERING"
    if field_state == "transitioning":
        return "TRANSITIONING"
    if field_state == "weakening":
        return "WEAKENING"
    if field_state == "unstable":
        return "UNSTABLE"
    return "UNKNOWN"


def compact_action(action: dict[str, Any] | None) -> str:
    if not action:
        return "—"
    return str(action.get("minimal_action_support") or "—")


def connector_line(connectors: list[dict[str, Any]]) -> str:
    if not connectors:
        return "CONNECTOR  —"

    parts: list[str] = []
    for row in connectors:
        surface = row.get("connector_surface_original") or row.get("connector_surface") or ""
        cls = row.get("connector_class") or ""
        dep = row.get("dependency_type") or ""
        direction = row.get("direction") or ""
        parts.append(f"{surface} [{cls}/{dep}/{direction}]")

    return "CONNECTOR  " + " | ".join(parts)


def support_line(paso9: dict[str, Any] | None) -> str:
    if not paso9:
        return "P9 SUPPORT —"
    labels = parse_json_list(paso9.get("candidate_labels"))
    confidence = str(paso9.get("confidence") or "—")
    return f"P9 SUPPORT {render_list(labels)} ({confidence})"


def continuity_line(field: dict[str, Any] | None) -> str:
    if not field:
        return "FIELD      —"

    state = field_badge(str(field.get("field_state") or ""))
    return (
        f"FIELD      {state} "
        f"p={field.get('persistence_score')} "
        f"t={field.get('transition_score')} "
        f"e={field.get('extension_score')} "
        f"w={field.get('weakening_score')}"
    )


def evidence_line(paso9: dict[str, Any] | None, field: dict[str, Any] | None) -> str:
    evidence: list[str] = []

    if paso9:
        evidence.extend(parse_json_list(paso9.get("evidence_sources")))

    if field:
        evidence.extend(parse_json_list(field.get("evidence")))

    # Keep this readable; full JSON remains in data files.
    evidence = evidence[:8]
    return "EVIDENCE   " + render_list(evidence)


def render_predication_block(
    predication: dict[str, Any],
    paso9: dict[str, Any] | None,
    field: dict[str, Any] | None,
    action: dict[str, Any] | None,
    connectors: list[dict[str, Any]],
) -> str:
    key = predication_key(predication)
    subject = first_text(predication, SUBJECT_FIELDS) or str(action.get("subject_support") if action else "") or "—"
    verb = first_text(predication, VERB_FIELDS) or str(action.get("verb_support") if action else "") or "—"
    greek = first_text(predication, GREEK_FIELDS)
    nbla = first_text(predication, NBLA_FIELDS)

    lines: list[str] = []
    lines.append(f"┌─ {key}")
    lines.append(f"│  S/V       {subject}  →  =={verb}==")

    if greek:
        lines.append(f"│  GREEK     {greek}")
    if nbla:
        lines.append(f"│  NBLA      {nbla}")

    lines.append(f"│  {connector_line(connectors)}")
    lines.append(f"│  {support_line(paso9)}")
    lines.append(f"│  {continuity_line(field)}")
    lines.append(f"│  ACTION    {compact_action(action)}")
    lines.append(f"│  {evidence_line(paso9, field)}")
    lines.append("└")
    return "\n".join(lines)


# ---------------------------------------------------------
# Render book
# ---------------------------------------------------------


def render_book(book: str) -> str:
    predications = load_predications(book)
    paso9 = load_index(book, "paso9-support", "paso9-support")
    field = load_index(book, "continuity-field", "continuity-field")
    action = load_index(book, "paso13-action-support", "paso13-action-support")
    connectors = load_connectors_by_target(book)

    lines: list[str] = []
    lines.append(f"# ROOTS Structural Review — {book}")
    lines.append("")
    lines.append("Lectura visual de auditoría. No contiene etiquetas finales, secciones finales, H-levels ni interpretación.")
    lines.append("")
    lines.append("Leyenda: p=persistencia · t=transición · e=extensión · w=debilitamiento")
    lines.append("")

    current_chapter: int | None = None
    current_verse: int | None = None

    for predication in predications:
        chapter, verse = ref_tuple(predication)

        if chapter != current_chapter:
            current_chapter = chapter
            current_verse = None
            lines.append(f"## Capítulo {chapter}")
            lines.append("")

        if verse != current_verse:
            current_verse = verse
            lines.append(f"### {book} {chapter}:{verse}")
            lines.append("")

        key = predication_key(predication)
        lines.append("```text")
        lines.append(
            render_predication_block(
                predication,
                paso9.get(key),
                field.get(key),
                action.get(key),
                connectors.get(key, []),
            )
        )
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> Path:
    out_dir = mna_root() / "data" / "human-review"
    out_path = out_dir / f"{book}-structural-review.md"
    write_text(out_path, render_book(book))
    return out_path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_structural_review.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    out_path = process_book(book)
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
