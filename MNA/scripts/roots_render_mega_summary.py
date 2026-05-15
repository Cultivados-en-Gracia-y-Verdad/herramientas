#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

WINDOW_SIZE = 25

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


def load_all(book: str) -> dict[str, Any]:
    data: dict[str, Any] = {"paths": {}}
    for name, templates in DATASETS.items():
        path = find_existing(book, templates)
        data["paths"][name] = path
        data[name] = read_jsonl(path) if path else []
    return data


def key_for(row: dict[str, Any]) -> str:
    return str(row.get("predication_id") or row.get("stream_index") or row.get("id") or "")


def idx_for(row: dict[str, Any]) -> int:
    return int(row.get("stream_index") or row.get("predication_index") or 0)


def ref_for(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"


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
    out = {}
    for row in rows:
        key = key_for(row)
        if key:
            out[key] = row
    return out


def connector_by_target(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("target_predication_id") or key_for(row))
        if key:
            out[key].append(row)
    return out


def chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i:i + size] for i in range(0, len(rows), size)]


def surface_connector(row: dict[str, Any]) -> str:
    return str(row.get("connector_surface_original") or row.get("connector_surface") or row.get("surface") or "")


def profile_region(
    region_no: int,
    rows: list[dict[str, Any]],
    paso9: dict[str, dict[str, Any]],
    field: dict[str, dict[str, Any]],
    action: dict[str, dict[str, Any]],
    conns: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    labels: Counter[str] = Counter()
    states: Counter[str] = Counter()
    subjects: Counter[str] = Counter()
    connector_classes: Counter[str] = Counter()
    connector_surfaces: Counter[str] = Counter()
    verbs: list[str] = []
    anchors: list[str] = []

    for row in rows:
        key = key_for(row)
        p9 = paso9.get(key, {})
        fld = field.get(key, {})
        act = action.get(key, {})
        labels.update(parse_list(p9.get("candidate_labels")))
        state = str(fld.get("field_state") or "unresolved")
        states[state] += 1
        subj = first_text(row, SUBJECT_FIELDS) or str(act.get("subject_support") or "unresolved")
        subjects[subj] += 1
        verb = first_text(row, VERB_FIELDS) or str(act.get("verb_support") or "")
        if verb:
            verbs.append(verb)
        for conn in conns.get(key, []):
            if conn.get("connector_class"):
                connector_classes[str(conn.get("connector_class"))] += 1
            surf = surface_connector(conn)
            if surf:
                connector_surfaces[surf] += 1

    # anchors: first, strongest label/state transition points, last
    selected = []
    if rows:
        selected.append(rows[0])
        mid_ranked = sorted(
            rows[1:-1],
            key=lambda r: (
                len(parse_list(paso9.get(key_for(r), {}).get("candidate_labels"))),
                len(conns.get(key_for(r), [])),
                idx_for(r),
            ),
            reverse=True,
        )
        for r in mid_ranked[:4]:
            selected.append(r)
        if len(rows) > 1:
            selected.append(rows[-1])

    seen = set()
    for r in sorted(selected, key=idx_for):
        key = key_for(r)
        if key in seen:
            continue
        seen.add(key)
        act = action.get(key, {})
        verb = first_text(r, VERB_FIELDS) or str(act.get("verb_support") or "") or "—"
        subj = first_text(r, SUBJECT_FIELDS) or str(act.get("subject_support") or "") or "—"
        lab = "/".join(parse_list(paso9.get(key, {}).get("candidate_labels"))) or "—"
        st = str(field.get(key, {}).get("field_state") or "—")
        anchors.append(f"{ref_for(r)} {key} | {subj} → {verb} | labels={lab} | state={st}")

    return {
        "region_no": region_no,
        "start_ref": ref_for(rows[0]),
        "end_ref": ref_for(rows[-1]),
        "count": len(rows),
        "dominant_labels": labels.most_common(5),
        "states": states,
        "subjects": subjects.most_common(5),
        "connector_classes": connector_classes.most_common(5),
        "connector_surfaces": connector_surfaces.most_common(8),
        "anchors": anchors,
    }


def fmt_counter(items: list[tuple[str, int]]) -> str:
    if not items:
        return "—"
    return ", ".join(f"{name}={count}" for name, count in items)


def render_book(book: str) -> str:
    data = load_all(book)
    stream = sorted(data["stream"], key=idx_for)
    if not stream:
        tried = "\n".join(str(mna_root() / t.format(book=book)) for t in DATASETS["stream"])
        raise FileNotFoundError(f"No stream dataset found for {book}. Tried:\n{tried}")

    paso9 = index_by_key(data["paso9_support"])
    field = index_by_key(data["continuity_field"])
    action = index_by_key(data["paso13_action_support"])
    conns = connector_by_target(data["connector_registry"])

    profiles = [
        profile_region(i, chunk, paso9, field, action, conns)
        for i, chunk in enumerate(chunks(stream, WINDOW_SIZE), start=1)
    ]

    global_labels: Counter[str] = Counter()
    global_states: Counter[str] = Counter()
    global_connectors: Counter[str] = Counter()
    for p in profiles:
        global_labels.update(dict(p["dominant_labels"]))
        global_states.update(p["states"])
        global_connectors.update(dict(p["connector_classes"]))

    lines: list[str] = []
    lines.append(f"# MEGA STRUCTURE SUMMARY — {book.upper()}")
    lines.append("")
    lines.append("<!-- Resumen mecánico desde datasets existentes. No interpreta, no calibra, no suaviza. -->")
    lines.append("")
    lines.append("## 1. Archivos usados")
    lines.append("")
    for name, path in data["paths"].items():
        lines.append(f"- {name}: {path if path else 'NO ENCONTRADO'}")
    lines.append("")
    lines.append("## 2. Totales del libro")
    lines.append("")
    lines.append(f"- predicaciones: {len(stream)}")
    lines.append(f"- registros paso9: {len(data['paso9_support'])}")
    lines.append(f"- registros continuidad: {len(data['continuity_field'])}")
    lines.append(f"- registros paso13: {len(data['paso13_action_support'])}")
    lines.append(f"- conectores registrados: {len(data['connector_registry'])}")
    lines.append("")
    lines.append("## 3. Distribución global observable")
    lines.append("")
    lines.append(f"- etiquetas dominantes: {fmt_counter(global_labels.most_common(10))}")
    lines.append(f"- estados de continuidad: {fmt_counter(global_states.most_common(10))}")
    lines.append(f"- clases de conectores: {fmt_counter(global_connectors.most_common(10))}")
    lines.append("")
    lines.append("## 4. Mega regiones mecánicas")
    lines.append("")
    lines.append(f"Cada región agrupa {WINDOW_SIZE} predicaciones consecutivas, sin imponer tema ni título interpretativo.")
    lines.append("")

    for p in profiles:
        lines.append(f"### Región {p['region_no']} — {p['start_ref']}–{p['end_ref']}")
        lines.append("")
        lines.append(f"- predicaciones: {p['count']}")
        lines.append(f"- etiquetas: {fmt_counter(p['dominant_labels'])}")
        lines.append(f"- continuidad: {fmt_counter(p['states'].most_common())}")
        lines.append(f"- sujetos: {fmt_counter(p['subjects'])}")
        lines.append(f"- conectores: {fmt_counter(p['connector_classes'])}")
        lines.append(f"- superficies conectoras: {fmt_counter(p['connector_surfaces'])}")
        lines.append("")
        lines.append("#### Evidencia ancla")
        lines.append("")
        lines.append("```text")
        for anchor in p["anchors"]:
            lines.append(anchor)
        lines.append("```")
        lines.append("")

    lines.append("## 5. Lectura permitida")
    lines.append("")
    lines.append("Este archivo no asigna estructura final. Solo muestra regiones consecutivas respaldadas por conteos y anclas de predicación existentes.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_mega_summary.py <book>", file=sys.stderr)
        sys.exit(2)
    book = sys.argv[1].lower()
    out_dir = mna_root() / "output" / "roots-render"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-mega-summary.md"
    out_path.write_text(render_book(book), encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
