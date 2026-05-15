#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

DATASETS = {
    "stream": [
        "data/predications/{book}-predications.jsonl",
        "data/independent-stream/{book}-independent-stream.jsonl",
    ],
    "connector_registry": [
        "data/connectors/{book}-connector-registry.jsonl",
        "data/connector-registry/{book}-connector-registry.jsonl",
    ],
    "paso9_support": [
        "data/paso9-support/{book}-paso9-support.jsonl",
    ],
    "continuity_field": [
        "data/continuity-field/{book}-continuity-field.jsonl",
    ],
    "paso13_action_support": [
        "data/paso13-action-support/{book}-paso13-action-support.jsonl",
    ],
}

GREEK_FIELDS = ["greek", "greek_text", "clause_greek", "text_greek", "finite_clause_greek", "raw_greek"]
NBLA_FIELDS = ["nbla", "spanish", "text_nbla", "clause_nbla", "visible_clause", "rendered_clause", "clause_text"]
VERB_FIELDS = ["verb", "finite_verb", "main_verb", "verb_surface", "greek_verb"]
SUBJECT_FIELDS = ["subject", "subject_label", "subject_refined", "implicit_subject", "subject_person_number"]


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
            except Exception as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON") from exc
    return rows


def find_existing(book: str, templates: list[str]) -> Path | None:
    for template in templates:
        path = mna_root() / template.format(book=book)
        if path.exists():
            return path
    return None


def key_for(row: dict[str, Any]) -> str:
    return str(row.get("predication_id") or row.get("stream_index") or row.get("id") or "")


def first_text(row: dict[str, Any] | None, fields: list[str]) -> str:
    if not row:
        return ""
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def parse_list(value: Any) -> list[str]:
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


def index_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = key_for(row)
        if key:
            out[key] = row
    return out


def load_all(book: str) -> dict[str, Any]:
    loaded: dict[str, Any] = {"paths": {}}
    for name, templates in DATASETS.items():
        path = find_existing(book, templates)
        if path is None:
            loaded[name] = []
            loaded["paths"][name] = None
        else:
            loaded[name] = read_jsonl(path)
            loaded["paths"][name] = path
    return loaded


def connector_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("target_predication_id") or key_for(row))
        if key:
            out[key].append(row)
    return out


def ref(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"


def format_connectors(rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in rows:
        surface = row.get("connector_surface_original") or row.get("connector_surface") or row.get("surface") or ""
        cls = row.get("connector_class") or ""
        dep = row.get("dependency_type") or ""
        direction = row.get("direction") or ""
        if surface or cls or dep or direction:
            out.append(f"{surface} | clase={cls or '—'} | dependencia={dep or '—'} | dirección={direction or '—'}")
    return out


def render_block(
    row: dict[str, Any],
    connectors: list[dict[str, Any]],
    paso9: dict[str, Any] | None,
    field: dict[str, Any] | None,
    action: dict[str, Any] | None,
) -> str:
    greek = first_text(row, GREEK_FIELDS)
    nbla = first_text(row, NBLA_FIELDS)
    subject = first_text(row, SUBJECT_FIELDS) or first_text(action, ["subject_support"])
    verb = first_text(row, VERB_FIELDS) or first_text(action, ["verb_support"])
    labels = parse_list(paso9.get("candidate_labels") if paso9 else None)
    action_text = first_text(action, ["minimal_action_support", "action", "trunk_action"])
    field_state = field.get("field_state") if field else ""

    lines: list[str] = []
    lines.append(f"# {ref(row)} — {key_for(row)}")
    lines.append("")
    lines.append("## PASO 1 — COPIAR TEXTO")
    lines.append("")
    lines.append(nbla or "—")
    lines.append("")
    lines.append("## PASO 2 — VERBOS FINITOS")
    lines.append("")
    lines.append(f"- {verb or '—'}")
    lines.append("")
    lines.append("## PASO 3 — CLÁUSULAS")
    lines.append("")
    if greek:
        lines.append(f"- GRIEGO: {greek}")
    lines.append(f"- NBLA: {nbla or '—'}")
    lines.append("")
    lines.append("## PASO 4 — CONECTORES")
    lines.append("")
    connector_lines = format_connectors(connectors)
    if connector_lines:
        for item in connector_lines:
            lines.append(f"- {item}")
    else:
        lines.append("- ninguno")
    lines.append("")
    lines.append("## PASO 5 — CONECTOR + B → BUSCAR A")
    lines.append("")
    lines.append("- ver registro de conectores locales; no se inventa relación ausente")
    lines.append("")
    lines.append("## PASO 6 — MOSTRAR LA ESTRUCTURA")
    lines.append("")
    lines.append("```text")
    lines.append(nbla or "")
    lines.append("```")
    lines.append("")
    lines.append("## PASO 7 — REDUCCIÓN")
    lines.append("")
    lines.append(nbla or "—")
    lines.append("")
    lines.append("## PASO 8 — TRONCO")
    lines.append("")
    lines.append(nbla or "—")
    lines.append("")
    lines.append("## PASO 9 — ETIQUETAS")
    lines.append("")
    if labels:
        for label in labels:
            lines.append(f"- {label}")
    else:
        lines.append("- ninguna")
    lines.append("")
    lines.append("## PASO 10–12 — CONTINUIDAD OBSERVADA")
    lines.append("")
    lines.append(f"- estado: {field_state or '—'}")
    lines.append(f"- sujeto: {subject or '—'}")
    lines.append("")
    lines.append("## PASO 13 — ACCIÓN DEL TRONCO")
    lines.append("")
    lines.append(action_text or "—")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_book(book: str) -> str:
    data = load_all(book)
    stream = sorted(data["stream"], key=lambda r: int(r.get("stream_index") or 0))
    if not stream:
        tried = "\n".join(str(mna_root() / t.format(book=book)) for t in DATASETS["stream"])
        raise FileNotFoundError(f"No stream dataset found for {book}. Tried:\n{tried}")

    conns = connector_index(data["connector_registry"])
    paso9 = index_by_key(data["paso9_support"])
    field = index_by_key(data["continuity_field"])
    action = index_by_key(data["paso13_action_support"])

    lines: list[str] = [f"# ROOTS RENDER — {book.upper()}", ""]
    lines.append("<!-- Render directo desde datasets existentes. No calibra, no suaviza, no inventa estructura. -->")
    lines.append("")
    for row in stream:
        key = key_for(row)
        lines.append(render_block(row, conns.get(key, []), paso9.get(key), field.get(key), action.get(key)))
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_full.py <book>", file=sys.stderr)
        sys.exit(2)
    book = sys.argv[1].lower()
    out_dir = mna_root() / "output" / "roots-render"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-roots-render.md"
    out_path.write_text(render_book(book), encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
