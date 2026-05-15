#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — dependency view renderer

Purpose:
- render a compact visual dependency view from existing ROOTS substrate
- show connector attachment and local dependency evidence between predications
- remain downstream-only and audit-oriented

This renderer DOES NOT:
- create new dependencies
- assign final labels
- assign sections or H-levels
- interpret semantic/theological meaning
- alter any substrate data

It only displays existing connector/dependency signals where present.
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


def available_predication_books() -> list[str]:
    root = mna_root()
    books: set[str] = set()

    for folder, suffix in [
        ("predications", "-predications.jsonl"),
        ("independent-stream", "-independent-stream.jsonl"),
    ]:
        path = root / "data" / folder
        if not path.exists():
            continue
        for item in path.glob(f"*{suffix}"):
            books.add(item.name.removesuffix(suffix))

    return sorted(books)


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

    available = available_predication_books()
    available_text = ", ".join(available) if available else "none found"
    tried = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"No predication source found for book: {book}\n"
        f"Tried:\n{tried}\n"
        f"Available books: {available_text}"
    )


def load_index(book: str, folder: str, suffix: str) -> dict[str, dict[str, Any]]:
    path = mna_root() / "data" / folder / f"{book}-{suffix}.jsonl"
    rows = ordered(read_jsonl(path))

    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = predication_key(row)
        if key:
            index[key] = row
    return index


def load_connectors(book: str) -> list[dict[str, Any]]:
    path = mna_root() / "data" / "connectors" / f"{book}-connector-registry.jsonl"
    return ordered(read_jsonl(path))


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


def predication_key(row: dict[str, Any]) -> str:
    return str(row.get("predication_id") or row.get("stream_index") or row.get("id") or "")


def ref_tuple(row: dict[str, Any]) -> tuple[int, int]:
    return (int(row.get("chapter") or 0), int(row.get("verse") or 0))


def short_id(key: str) -> str:
    # Keep exact uniqueness but reduce visual width when possible.
    if "-" in key:
        return key.split("-")[-1]
    return key


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


def format_predication_label(row: dict[str, Any], action: dict[str, Any] | None) -> str:
    key = predication_key(row)
    subject = first_text(row, SUBJECT_FIELDS)
    verb = first_text(row, VERB_FIELDS)

    if action:
        subject = subject or str(action.get("subject_support") or "")
        verb = verb or str(action.get("verb_support") or "")

    subject = subject or "?"
    verb = verb or "?"

    return f"{short_id(key)} [{subject} → {verb}]"


def connector_surface(row: dict[str, Any]) -> str:
    return str(
        row.get("connector_surface_original")
        or row.get("connector_surface")
        or "?"
    )


def connector_relation(row: dict[str, Any]) -> str:
    cls = row.get("connector_class") or "unknown"
    dep = row.get("dependency_type") or "unknown"
    direction = row.get("direction") or "unknown"
    return f"{cls}/{dep}/{direction}"


def inferred_source_key(
    connector: dict[str, Any],
    target_key: str,
    ordered_keys: list[str],
) -> str:
    # Only a display fallback for missing explicit source IDs.
    # It is marked as inferred in the output and must not be treated as final data.
    source = str(
        connector.get("source_predication_id")
        or connector.get("parent_predication_id")
        or connector.get("head_predication_id")
        or connector.get("a_predication_id")
        or ""
    )
    if source:
        return source

    direction = str(connector.get("direction") or "")
    try:
        idx = ordered_keys.index(target_key)
    except ValueError:
        return ""

    if direction == "backward_local" and idx > 0:
        return ordered_keys[idx - 1]

    return ""


# ---------------------------------------------------------
# Rendering
# ---------------------------------------------------------


def group_rows_by_verse(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[ref_tuple(row)].append(row)
    return dict(grouped)


def connectors_by_target(connectors: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in connectors:
        key = str(row.get("target_predication_id") or "")
        if key:
            grouped[key].append(row)
    return dict(grouped)


def render_verse_dependency(
    book: str,
    chapter: int,
    verse: int,
    predications: list[dict[str, Any]],
    target_connectors: dict[str, list[dict[str, Any]]],
    paso9: dict[str, dict[str, Any]],
    field: dict[str, dict[str, Any]],
    action: dict[str, dict[str, Any]],
) -> list[str]:
    keys = [predication_key(row) for row in predications]

    lines: list[str] = []
    lines.append(f"### {book} {chapter}:{verse}")
    lines.append("")
    lines.append("```text")

    # First list the predications in order.
    lines.append("PREDICATIONS")
    for row in predications:
        key = predication_key(row)
        p9 = paso9.get(key)
        cf = field.get(key)
        act = action.get(key)

        labels = parse_json_list(p9.get("candidate_labels") if p9 else None)
        label_text = ",".join(labels) if labels else "—"
        state = str(cf.get("field_state") or "—") if cf else "—"
        lines.append(f"  {format_predication_label(row, act)}  | P9={label_text} | FIELD={state}")

    lines.append("")
    lines.append("DEPENDENCIES")

    dependency_count = 0
    for row in predications:
        target_key = predication_key(row)
        conns = target_connectors.get(target_key, [])

        for connector in conns:
            dependency_count += 1
            source_key = inferred_source_key(connector, target_key, keys)
            source_label = short_id(source_key) if source_key else "?"
            target_label = short_id(target_key)
            source_note = "" if connector.get("source_predication_id") else " [source inferred/display-only]"

            lines.append(
                f"  {source_label} ── {connector_surface(connector)} "
                f"[{connector_relation(connector)}] ──▶ {target_label}{source_note}"
            )

    if dependency_count == 0:
        lines.append("  — no connector dependency rows for this verse")

    lines.append("```")
    lines.append("")
    return lines


def render_book(book: str) -> str:
    predications = load_predications(book)
    connectors = load_connectors(book)
    target_connectors = connectors_by_target(connectors)
    paso9 = load_index(book, "paso9-support", "paso9-support")
    field = load_index(book, "continuity-field", "continuity-field")
    action = load_index(book, "paso13-action-support", "paso13-action-support")

    grouped = group_rows_by_verse(predications)

    lines: list[str] = []
    lines.append(f"# ROOTS Dependency View — {book}")
    lines.append("")
    lines.append("Vista gráfica compacta de dependencias locales. No crea dependencias nuevas ni asigna etiquetas finales.")
    lines.append("Las flechas con [source inferred/display-only] son inferencias visuales mínimas cuando el registro no trae source_predication_id explícito.")
    lines.append("")

    current_chapter: int | None = None

    for chapter, verse in sorted(grouped):
        if chapter != current_chapter:
            current_chapter = chapter
            lines.append(f"## Capítulo {chapter}")
            lines.append("")

        lines.extend(
            render_verse_dependency(
                book,
                chapter,
                verse,
                grouped[(chapter, verse)],
                target_connectors,
                paso9,
                field,
                action,
            )
        )

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> Path:
    out_dir = mna_root() / "data" / "human-review"
    out_path = out_dir / f"{book}-dependency-view.md"
    write_text(out_path, render_book(book))
    return out_path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_dependency_view.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()

    try:
        out_path = process_book(book)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
