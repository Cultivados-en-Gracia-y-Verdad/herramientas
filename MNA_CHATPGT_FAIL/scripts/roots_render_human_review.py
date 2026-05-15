#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — human review renderer

Purpose:
- render the existing ROOTS substrate into a readable audit document
- help review the data without changing any upstream logic
- keep presentation downstream from analysis

This renderer DOES NOT:
- assign labels
- assign sections
- generate H-level headings
- interpret the text
- alter substrate data

It only displays existing evidence from:
- predications
- Paso 9 support
- continuity field (Pasos 10–12 substrate)
- Paso 13 action support
- connector registry
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
# Load substrate layers
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
        key = str(row.get("predication_id") or row.get("stream_index") or "")
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
# Extraction helpers
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


def first_text(row: dict[str, Any], fields: list[str]) -> str:
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



def ref_key(row: dict[str, Any]) -> tuple[int, int]:
    return (int(row.get("chapter") or 0), int(row.get("verse") or 0))



def display_ref(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"



def format_list(values: list[str]) -> str:
    if not values:
        return "—"
    return ", ".join(values)


# ---------------------------------------------------------
# Rendering
# ---------------------------------------------------------


def render_predication(
    predication: dict[str, Any],
    paso9: dict[str, Any] | None,
    field: dict[str, Any] | None,
    action: dict[str, Any] | None,
    connectors: list[dict[str, Any]],
) -> list[str]:
    key = predication_key(predication)

    greek = first_text(predication, GREEK_FIELDS)
    nbla = first_text(predication, NBLA_FIELDS)
    verb = first_text(predication, VERB_FIELDS)
    subject = first_text(predication, SUBJECT_FIELDS)

    if action:
        verb = verb or str(action.get("verb_support") or "")
        subject = subject or str(action.get("subject_support") or "")

    lines: list[str] = []
    lines.append(f"#### {key}")

    if greek:
        lines.append(f"- GRIEGO: {greek}")
    if nbla:
        lines.append(f"- NBLA: {nbla}")

    lines.append(f"- Sujeto: {subject or '—'}")
    lines.append(f"- Verbo: {verb or '—'}")

    if connectors:
        connector_bits = []
        for connector in connectors:
            surface = connector.get("connector_surface_original") or connector.get("connector_surface") or ""
            cls = connector.get("connector_class") or ""
            dep = connector.get("dependency_type") or ""
            direction = connector.get("direction") or ""
            connector_bits.append(f"{surface} [{cls}; {dep}; {direction}]")
        lines.append(f"- Conectores locales: {format_list(connector_bits)}")
    else:
        lines.append("- Conectores locales: —")

    if paso9:
        labels = parse_json_list(paso9.get("candidate_labels"))
        evidence = parse_json_list(paso9.get("evidence_sources"))
        lines.append(f"- Paso 9 soporte: {format_list(labels)}")
        lines.append(f"- Paso 9 confianza: {paso9.get('confidence') or '—'}")
        lines.append(f"- Evidencia Paso 9: {format_list(evidence)}")
    else:
        lines.append("- Paso 9 soporte: —")

    if field:
        lines.append(
            "- Campo continuidad 10–12: "
            f"{field.get('field_state') or '—'} "
            f"(persistencia={field.get('persistence_score')}, "
            f"transición={field.get('transition_score')}, "
            f"extensión={field.get('extension_score')}, "
            f"debilitamiento={field.get('weakening_score')})"
        )
    else:
        lines.append("- Campo continuidad 10–12: —")

    if action:
        lines.append(f"- Paso 13 soporte mínimo: {action.get('minimal_action_support') or '—'}")
        lines.append(f"- Paso 13 confianza: {action.get('confidence') or '—'}")
    else:
        lines.append("- Paso 13 soporte mínimo: —")

    lines.append("")
    return lines



def render_book(book: str) -> str:
    predications = load_predications(book)

    paso9 = load_index(book, "paso9-support", "paso9-support")
    field = load_index(book, "continuity-field", "continuity-field")
    action = load_index(book, "paso13-action-support", "paso13-action-support")
    connectors = load_connectors_by_target(book)

    lines: list[str] = []
    lines.append(f"# ROOTS Human Review — {book}")
    lines.append("")
    lines.append("Este archivo es para auditoría humana. No contiene etiquetas finales, secciones finales, H-levels ni interpretación.")
    lines.append("")

    current_chapter: int | None = None
    current_verse: int | None = None

    for predication in predications:
        chapter, verse = ref_key(predication)

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
        lines.extend(
            render_predication(
                predication,
                paso9.get(key),
                field.get(key),
                action.get(key),
                connectors.get(key, []),
            )
        )

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> Path:
    out_dir = mna_root() / "data" / "human-review"
    out_path = out_dir / f"{book}-human-review.md"
    write_text(out_path, render_book(book))
    return out_path



def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_human_review.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    out_path = process_book(book)
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
