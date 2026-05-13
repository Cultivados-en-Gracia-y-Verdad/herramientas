#!/usr/bin/env python3
"""ROOTS Greek Step 6B: readable Spanish PASO 6 renderer."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

RELATION_LABELS = {
    "coordination": "coordinación",
    "cause/ground": "explicación/apoyo",
    "content/cause": "contenido/explicación",
    "purpose/result": "propósito/resultado",
    "purpose": "propósito",
    "condition": "condición",
    "comparison/manner": "comparación/manera",
    "contrast": "contraste",
    "contrast/exception": "contraste/excepción",
    "result/inference": "resultado/inferencia",
    "inference": "inferencia",
    "temporal": "temporal",
    "temporal/condition": "temporal/condición",
    "alternative/comparison": "alternativa/comparación",
    "alternative": "alternativa",
    "negative coordination": "coordinación negativa",
    "negation": "negación",
}

KIND_LABELS = {
    "coordinating": "coordinante",
    "subordinating": "subordinante",
    "negation": "negación",
}


def read_tsv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def group_rows(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(k, "") for k in keys)].append(row)
    return grouped


def build_lookup(rows, keys):
    return {tuple(row.get(k, "") for k in keys): row for row in rows}


def safe_int(value, default=999999):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def previous_verse_ref(book, ch, vs):
    ch_i = safe_int(ch, 0)
    vs_i = safe_int(vs, 0)
    if vs_i > 1:
        return f"{book} {ch_i}:{vs_i - 1}"
    if ch_i > 1:
        return f"{book} {ch_i - 1}:versículo anterior"
    return "versículo anterior"


def clause_number(clause_id):
    return safe_int(str(clause_id).replace("C", ""), 999999)


def sort_by_gidx(rows):
    return sorted(rows, key=lambda r: safe_int(r.get("G_IDX", "999999")))


def label_relation(value):
    return RELATION_LABELS.get(value, value or "relación no clasificada todavía")


def label_kind(value):
    return KIND_LABELS.get(value, value or "tipo no clasificado todavía")


def connectors_for_verse(db_rows):
    rows = [r for r in sort_by_gidx(db_rows) if r.get("TYPE") == "connector"]
    tokens = sorted({r.get("GREEK", "").strip() for r in rows if r.get("GREEK", "").strip()}, key=len, reverse=True)
    return rows, tokens


def connector_lookup_by_id(db_rows):
    return {r.get("ID", ""): r for r in db_rows if r.get("TYPE") == "connector"}


def mark_connectors_inline(text, tokens):
    if not text:
        return text
    marked = f" {text} "
    for token in tokens:
        if f"({token})" in marked:
            continue
        for suffix in [" ", ",", ".", ";", ":", "·"]:
            marked = marked.replace(f" {token}{suffix}", f" ({token}){suffix}")
    return marked.strip()


def span_bounds(span):
    start = safe_int(span.get("START_G_IDX", span.get("FINITE_G_IDX", "")), -1)
    end = safe_int(span.get("END_G_IDX", span.get("FINITE_G_IDX", "")), -1)
    return start, end


def verb_clause_id(row, spans):
    gidx = safe_int(row.get("G_IDX", ""), -1)
    if gidx < 0:
        return ""
    for span in spans:
        start, end = span_bounds(span)
        if start <= gidx <= end:
            return span.get("CLAUSE_ID", "")
    return ""


def render_verbs(db_rows, spans):
    lines = ["### Verbos detectados", ""]
    verbs = [r for r in sort_by_gidx(db_rows) if r.get("TYPE") == "verb"]
    if not verbs:
        return lines + ["- ninguno", ""]
    for row in verbs:
        location = verb_clause_id(row, spans) or "sin cláusula finita"
        finite = row.get("FINITE", "") or "?"
        lines.append(f"- {row.get('GREEK','')} | {row.get('LEMMA','')} | {row.get('RMAC','')} | [{finite}] | {location}")
    lines.append("")
    return lines


def render_connectors(db_rows):
    lines = ["### Conectores detectados", ""]
    rows, _ = connectors_for_verse(db_rows)
    if not rows:
        return lines + ["- ninguno", ""]
    for row in rows:
        certainty = row.get("CERTAINTY", "")
        note = f" | certeza: {certainty}" if certainty else ""
        lines.append(f"- {row.get('ID','')}. {row.get('GREEK','')} | {label_kind(row.get('CONNECTOR_KIND',''))} | {label_relation(row.get('DEFAULT_RELATION',''))}{note}")
    lines.append("")
    return lines


def render_structure(spans, tree_lookup, db_rows):
    lines = ["### Vista estructural propuesta", ""]
    _, tokens = connectors_for_verse(db_rows)
    for row in spans:
        cid = row.get("CLAUSE_ID", "")
        key = (row.get("BOOK", ""), row.get("CH", ""), row.get("VS", ""), cid)
        depth = safe_int(tree_lookup.get(key, {}).get("TREE_DEPTH", "0"), 0)
        text = mark_connectors_inline(row.get("SPAN_TEXT", ""), tokens)
        lines.append(f"{'    ' * depth}{cid}. {text}")
    lines.append("")
    return lines


def render_cross_verse(book, ch, vs, db_rows, certainty_rows):
    lines = ["### Conexiones entre versículos", ""]
    cross_rows = [
        r for r in certainty_rows
        if r.get("LAYER") == "step5.5-cross-verse-candidates"
    ]

    if not cross_rows:
        return lines + ["- ninguna conexión entre versículos propuesta por la auditoría.", ""]

    connectors = connector_lookup_by_id(db_rows)
    prior_ref = previous_verse_ref(book, ch, vs)

    for row in cross_rows:
        item_id = row.get("ITEM_ID", "")
        connector = connectors.get(item_id, {})
        greek = connector.get("GREEK", item_id)
        relation = label_relation(row.get("ITEM_TYPE", ""))
        classification = row.get("CLASSIFICATION", "REVIEW")
        use = row.get("ALLOWED_DOWNSTREAM_USE", "review-only")
        reason = row.get("REASON", "")
        lines.append(
            f"- {item_id}. {greek} | posible conexión hacia {prior_ref} | {relation} | estado: {classification} | uso: {use}"
        )
        if reason:
            lines.append(f"  - motivo: {reason}")

    lines.append("- Estas conexiones son evidencia para auditoría; no son estructura final confirmada.")
    lines.append("")
    return lines


def render_observations(spans, tree_lookup):
    lines = ["### Observaciones estructurales", ""]
    if not spans:
        return lines + ["- No hay cláusulas finitas para mostrar en este versículo.", ""]
    for row in spans:
        cid = row.get("CLAUSE_ID", "")
        key = (row.get("BOOK", ""), row.get("CH", ""), row.get("VS", ""), cid)
        tree = tree_lookup.get(key, {})
        parent = tree.get("PARENT_CLAUSE", "")
        if parent:
            lines.append(f"- {cid} aparece visualmente bajo {parent} por una propuesta mecánica provisional.")
        elif tree.get("NODE_TYPE", "") == "root-parent":
            lines.append(f"- {cid} aparece como cláusula raíz con posible desarrollo subordinado debajo.")
        else:
            lines.append(f"- {cid} aparece como cláusula raíz o todavía no resuelta.")
    lines.append("- La indentación ayuda a ver la propuesta mecánica, pero no confirma jerarquía.")
    lines.append("- Los conectores entre paréntesis son conectores detectados en el texto griego; el paréntesis no confirma su función estructural.")
    lines.append("")
    return lines


def render_book(grouped_db, grouped_spans, grouped_certainty, tree_lookup):
    lines = []
    verse_keys = sorted(grouped_spans.keys(), key=lambda x: (x[0], safe_int(x[1]), safe_int(x[2])))
    for key in verse_keys:
        book, ch, vs = key
        db_rows = grouped_db.get(key, [])
        certainty_rows = grouped_certainty.get(key, [])
        spans = sorted(grouped_spans.get(key, []), key=lambda r: clause_number(r.get("CLAUSE_ID", "C999")))
        lines.extend([f"## {book} {ch}:{vs}", ""])
        lines.extend(render_verbs(db_rows, spans))
        lines.extend(render_connectors(db_rows))
        lines.extend(render_structure(spans, tree_lookup, db_rows))
        lines.extend(render_cross_verse(book, ch, vs, db_rows, certainty_rows))
        lines.extend(render_observations(spans, tree_lookup))
        lines.extend(["---", ""])
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 6B readable Spanish PASO 6 renderer")
    parser.add_argument("book")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/output")
    args = parser.parse_args()

    db_rows = read_tsv(Path(args.db_dir) / f"{args.book}-verbs-connectors.tsv")
    span_rows = read_tsv(Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv")
    tree_rows = read_tsv(Path(args.dataset_dir) / f"{args.book}-structure-tree.tsv")
    certainty_rows = read_tsv(Path(args.dataset_dir) / f"{args.book}-certainty-gate.tsv")

    grouped_db = group_rows(db_rows, ["BOOK", "CH", "VS"])
    grouped_spans = group_rows(span_rows, ["BOOK", "CH", "VS"])
    grouped_certainty = group_rows(certainty_rows, ["BOOK", "CH", "VS"])
    tree_lookup = build_lookup(tree_rows, ["BOOK", "CH", "VS", "CLAUSE_ID"])

    out_path = Path(args.out_dir) / f"{args.book}-paso6-rich.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_book(grouped_db, grouped_spans, grouped_certainty, tree_lookup), encoding="utf-8")
    print(f"Wrote {out_path}")
    print({"verses": len(grouped_spans), "clauses": len(span_rows)})


if __name__ == "__main__":
    main()
