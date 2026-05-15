#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SEED_SIZE = 12
MIN_REGION_SIZE = 18
MAX_REGION_SIZE = 55

DATASETS = {
    "stream": [
        "data/predications/{book}-predications.jsonl",
        "data/independent-stream/{book}-independent-stream.jsonl",
    ],
    "connector_registry": [
        "data/connectors/{book}-connector-registry.jsonl",
        "data/connector-registry/{book}-connector-registry.jsonl",
    ],
    "paso9_support": ["data/paso9-support/{book}-paso9-support.jsonl"],
    "continuity_field": ["data/continuity-field/{book}-continuity-field.jsonl"],
    "paso13_action_support": ["data/paso13-action-support/{book}-paso13-action-support.jsonl"],
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


def surface_connector(row: dict[str, Any]) -> str:
    return str(row.get("connector_surface_original") or row.get("connector_surface") or row.get("surface") or "")


def row_signature(row: dict[str, Any], paso9, field, conns) -> dict[str, str]:
    key = key_for(row)
    labels = parse_list(paso9.get(key, {}).get("candidate_labels"))
    dominant_label = labels[0] if labels else "NONE"
    state = str(field.get(key, {}).get("field_state") or "unresolved")
    connector_classes = [str(c.get("connector_class")) for c in conns.get(key, []) if c.get("connector_class")]
    conn = connector_classes[0] if connector_classes else "NONE"
    subj = first_text(row, SUBJECT_FIELDS)
    return {"label": dominant_label, "state": state, "conn": conn, "subject": subj or "unresolved"}


def seed_profiles(stream, paso9, field, conns) -> list[dict[str, Any]]:
    seeds = []
    for i in range(0, len(stream), SEED_SIZE):
        rows = stream[i:i + SEED_SIZE]
        if not rows:
            continue
        labels = Counter()
        states = Counter()
        concls = Counter()
        subjects = Counter()
        for row in rows:
            sig = row_signature(row, paso9, field, conns)
            labels[sig["label"]] += 1
            states[sig["state"]] += 1
            concls[sig["conn"]] += 1
            subjects[sig["subject"]] += 1
        seeds.append({
            "rows": rows,
            "start": i,
            "end": i + len(rows),
            "label": labels.most_common(1)[0][0],
            "state": states.most_common(1)[0][0],
            "connector": concls.most_common(1)[0][0],
            "subject": subjects.most_common(1)[0][0],
            "labels": labels,
            "states": states,
            "connectors": concls,
            "subjects": subjects,
        })
    return seeds


def similarity(a: dict[str, Any], b: dict[str, Any]) -> int:
    score = 0
    if a["label"] == b["label"]:
        score += 3
    if a["state"] == b["state"]:
        score += 2
    if a["connector"] != "NONE" and a["connector"] == b["connector"]:
        score += 2
    if a["subject"] != "unresolved" and a["subject"] == b["subject"]:
        score += 1
    return score


def build_regions_from_seeds(seeds: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    regions: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_len = 0
    prev = None

    for seed in seeds:
        if not current:
            current = [seed]
            current_len = len(seed["rows"])
            prev = seed
            continue

        sim = similarity(prev, seed) if prev else 0
        force_split = current_len >= MAX_REGION_SIZE
        allow_split = current_len >= MIN_REGION_SIZE
        split = force_split or (allow_split and sim <= 2)

        if split:
            regions.append(current)
            current = [seed]
            current_len = len(seed["rows"])
        else:
            current.append(seed)
            current_len += len(seed["rows"])
        prev = seed

    if current:
        regions.append(current)
    return [[row for seed in region for row in seed["rows"]] for region in regions]


def profile_region(region_no: int, rows, paso9, field, action, conns) -> dict[str, Any]:
    labels: Counter[str] = Counter()
    states: Counter[str] = Counter()
    subjects: Counter[str] = Counter()
    connector_classes: Counter[str] = Counter()
    connector_surfaces: Counter[str] = Counter()
    anchor_candidates = []

    for row in rows:
        key = key_for(row)
        p9 = paso9.get(key, {})
        fld = field.get(key, {})
        act = action.get(key, {})
        row_labels = parse_list(p9.get("candidate_labels"))
        labels.update(row_labels)
        states[str(fld.get("field_state") or "unresolved")] += 1
        subj = first_text(row, SUBJECT_FIELDS) or str(act.get("subject_support") or "unresolved")
        subjects[subj] += 1
        conn_rows = conns.get(key, [])
        for conn in conn_rows:
            if conn.get("connector_class"):
                connector_classes[str(conn.get("connector_class"))] += 1
            surf = surface_connector(conn)
            if surf:
                connector_surfaces[surf] += 1
        anchor_candidates.append((len(row_labels) + len(conn_rows), row))

    selected = [rows[0]]
    for _, r in sorted(anchor_candidates[1:-1], key=lambda item: (item[0], idx_for(item[1])), reverse=True)[:5]:
        selected.append(r)
    if len(rows) > 1:
        selected.append(rows[-1])

    anchors = []
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

    dominant_label, label_count = labels.most_common(1)[0] if labels else ("—", 0)
    dominant_state, state_count = states.most_common(1)[0] if states else ("—", 0)
    label_ratio = round(label_count / max(sum(labels.values()), 1), 3)
    state_ratio = round(state_count / max(sum(states.values()), 1), 3)

    return {
        "region_no": region_no,
        "start_ref": ref_for(rows[0]),
        "end_ref": ref_for(rows[-1]),
        "count": len(rows),
        "dominant_label": dominant_label,
        "dominant_state": dominant_state,
        "label_ratio": label_ratio,
        "state_ratio": state_ratio,
        "dominant_labels": labels.most_common(6),
        "states": states,
        "subjects": subjects.most_common(6),
        "connector_classes": connector_classes.most_common(6),
        "connector_surfaces": connector_surfaces.most_common(8),
        "anchors": anchors,
    }


def fmt_counter(items) -> str:
    if not items:
        return "—"
    return ", ".join(f"{name}={count}" for name, count in items)


def transition_reason(prev: dict[str, Any] | None, cur: dict[str, Any]) -> list[str]:
    if prev is None:
        return ["inicio del flujo observado"]
    reasons = []
    if prev["dominant_label"] != cur["dominant_label"]:
        reasons.append(f"etiqueta dominante cambia: {prev['dominant_label']} → {cur['dominant_label']}")
    if prev["dominant_state"] != cur["dominant_state"]:
        reasons.append(f"continuidad cambia: {prev['dominant_state']} → {cur['dominant_state']}")
    prev_conn = prev["connector_classes"][0][0] if prev["connector_classes"] else "—"
    cur_conn = cur["connector_classes"][0][0] if cur["connector_classes"] else "—"
    if prev_conn != cur_conn:
        reasons.append(f"conector dominante cambia: {prev_conn} → {cur_conn}")
    if not reasons:
        reasons.append("región continuada por tamaño máximo del campo mecánico")
    return reasons


def readable_field(p: dict[str, Any]) -> str:
    parts = []
    parts.append(f"campo {p['dominant_label']} dominante")
    parts.append(f"continuidad {p['dominant_state']}")
    if p["connector_classes"]:
        parts.append(f"conector dominante {p['connector_classes'][0][0]}")
    return "; ".join(parts)


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

    seeds = seed_profiles(stream, paso9, field, conns)
    regions = build_regions_from_seeds(seeds)
    profiles = [profile_region(i, rows, paso9, field, action, conns) for i, rows in enumerate(regions, start=1)]

    global_labels = Counter()
    global_states = Counter()
    global_connectors = Counter()
    for p in profiles:
        global_labels.update(dict(p["dominant_labels"]))
        global_states.update(p["states"])
        global_connectors.update(dict(p["connector_classes"]))

    lines: list[str] = []
    lines.append(f"# MACRO STRUCTURE — {book.upper()}")
    lines.append("")
    lines.append("<!-- Render mecánico desde datasets existentes. No interpreta, no calibra, no suaviza. -->")
    lines.append("")
    lines.append("## 1. Archivos usados")
    lines.append("")
    for name, path in data["paths"].items():
        lines.append(f"- {name}: {path if path else 'NO ENCONTRADO'}")
    lines.append("")
    lines.append("## 2. Totales observables")
    lines.append("")
    lines.append(f"- predicaciones: {len(stream)}")
    lines.append(f"- macro regiones detectadas: {len(profiles)}")
    lines.append(f"- registros paso9: {len(data['paso9_support'])}")
    lines.append(f"- registros continuidad: {len(data['continuity_field'])}")
    lines.append(f"- registros paso13: {len(data['paso13_action_support'])}")
    lines.append(f"- conectores registrados: {len(data['connector_registry'])}")
    lines.append("")
    lines.append("## 3. Flujo macro observable")
    lines.append("")
    for p in profiles:
        lines.append(f"- {p['start_ref']}–{p['end_ref']}: {readable_field(p)}")
    lines.append("")
    lines.append("## 4. Macro regiones evidenciadas")
    lines.append("")

    prev = None
    for p in profiles:
        lines.append(f"### Región {p['region_no']} — {p['start_ref']}–{p['end_ref']}")
        lines.append("")
        lines.append(f"**Campo observable:** {readable_field(p)}.")
        lines.append("")
        lines.append("#### Evidencia de persistencia")
        lines.append("")
        lines.append(f"- predicaciones: {p['count']}")
        lines.append(f"- etiquetas: {fmt_counter(p['dominant_labels'])}")
        lines.append(f"- continuidad: {fmt_counter(p['states'].most_common())}")
        lines.append(f"- sujetos: {fmt_counter(p['subjects'])}")
        lines.append(f"- conectores: {fmt_counter(p['connector_classes'])}")
        lines.append(f"- superficies conectoras: {fmt_counter(p['connector_surfaces'])}")
        lines.append(f"- fuerza interna: etiqueta={p['label_ratio']} continuidad={p['state_ratio']}")
        lines.append("")
        lines.append("#### Gatillo de transición")
        lines.append("")
        for reason in transition_reason(prev, p):
            lines.append(f"- {reason}")
        lines.append("")
        lines.append("#### Evidencia ancla")
        lines.append("")
        lines.append("```text")
        for anchor in p["anchors"]:
            lines.append(anchor)
        lines.append("```")
        lines.append("")
        prev = p

    lines.append("## 5. Límite de lectura")
    lines.append("")
    lines.append("Este archivo comprime persistencia estructural observada. No asigna títulos temáticos finales ni interpreta contenido.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_mega_summary.py <book>", file=sys.stderr)
        sys.exit(2)
    book = sys.argv[1].lower()
    out_dir = mna_root() / "output" / "roots-render"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-macro-structure.md"
    out_path.write_text(render_book(book), encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
