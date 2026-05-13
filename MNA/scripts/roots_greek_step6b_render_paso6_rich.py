#!/usr/bin/env python3

"""
ROOTS Greek Step 6B
Readable Spanish PASO 6 renderer.

Purpose:
- Human-readable structural evidence
- Greek-driven
- Epistemologically constrained
- No fake hierarchy promotion

This renderer:
- shows finite/non-finite verbs clearly
<<<<<<< HEAD
- shows readable connector information
- renders visible structure
=======
- shows connector information from the Greek DB
- marks connectors inline in the structural view as (connector)
- renders visible structure clearly
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
- explains unresolved structure simply

This renderer does NOT:
- create PASO 7 reductions
- confirm hierarchy
- interpret theology
- promote provisional topology
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


<<<<<<< HEAD
FINITE_MOODS = {"I", "S", "M", "O"}

CONNECTOR_RELATIONS = {
    "ἵνα": "propósito/resultado",
    "γάρ": "explicación/apoyo",
    "δέ": "transición/coordinación",
    "καί": "coordinación",
    "ἀλλά": "contraste",
    "οὖν": "conclusión",
    "ὅτι": "contenido/explicación",
    "μή": "negación",
    "μὴ": "negación",
=======
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
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
}


def read_tsv(path):
    if not path.exists():
        return []
<<<<<<< HEAD

=======
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def group_rows(rows, keys):
    grouped = defaultdict(list)
<<<<<<< HEAD

    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        grouped[key].append(row)

=======
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        grouped[key].append(row)
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
    return grouped


def build_lookup(rows, keys):
    lookup = {}
<<<<<<< HEAD

    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        lookup[key] = row

    return lookup


def is_finite(rmac):
    if not rmac.startswith("V-"):
        return False

    parts = rmac.split("-")

    if len(parts) < 2:
        return False

    morph = parts[1]

    if len(morph) < 3:
        return False

    mood = morph[2]

    has_person_number = bool(re.search(r"[123][SP]", rmac))

    return mood in FINITE_MOODS and has_person_number


def finite_label(rmac):
    return "F" if is_finite(rmac) else "NF"


def verb_role(greek, clause_id, parent):
    if clause_id == "C1":
        return "verbo principal"

    if parent:
        return f"subordinado bajo {parent}"

    return "cláusula independiente/provisional"


def render_verbs(rows, tree_lookup):
    lines = []

    lines.append("### Verbos detectados")
    lines.append("")

    verbs = [r for r in rows if r.get("TYPE") == "verb"]
=======
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        lookup[key] = row
    return lookup


def safe_int(value, default=999999):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def clause_number(clause_id):
    return safe_int(str(clause_id).replace("C", ""), 999999)


def relation_label(value):
    if not value:
        return "relación no clasificada todavía"
    return RELATION_LABELS.get(value, value)


def kind_label(value):
    if not value:
        return "tipo no clasificado todavía"
    return KIND_LABELS.get(value, value)


def sort_by_gidx(rows):
    return sorted(rows, key=lambda r: safe_int(r.get("G_IDX", "999999")))


def connector_tokens(db_rows):
    tokens = []
    for row in db_rows:
        if row.get("TYPE") != "connector":
            continue
        greek = row.get("GREEK", "").strip()
        if greek:
            tokens.append(greek)
    return sorted(set(tokens), key=len, reverse=True)


def mark_connectors_inline(text, connectors):
    if not text:
        return text

    marked = text
    for connector in connectors:
        escaped = re.escape(connector)
        pattern = rf"(?<!\()(?<![\wͅ]){escaped}(?!\))(?![\wͅ])"
        marked = re.sub(pattern, f"({connector})", marked)
    return marked


def verb_clause_id(row, spans):
    gidx = safe_int(row.get("G_IDX", ""), -1)
    if gidx < 0:
        return ""

    for span in spans:
        start = safe_int(span.get("START_G_IDX", span.get("FINITE_G_IDX", "")), -1)
        end = safe_int(span.get("END_G_IDX", span.get("FINITE_G_IDX", "")), -1)
        if start <= gidx <= end:
            return span.get("CLAUSE_ID", "")

    return ""


def render_verbs(db_rows, spans):
    lines = ["### Verbos detectados", ""]
    verbs = [r for r in sort_by_gidx(db_rows) if r.get("TYPE") == "verb"]
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1

    if not verbs:
        lines.append("- ninguno")
        lines.append("")
        return lines

    for row in verbs:
        greek = row.get("GREEK", "")
        lemma = row.get("LEMMA", "")
        rmac = row.get("RMAC", "")
<<<<<<< HEAD

        clause_id = row.get("CLAUSE_ID", "")

        tree = tree_lookup.get(
            (
                row.get("BOOK", ""),
                row.get("CH", ""),
                row.get("VS", ""),
                clause_id,
            ),
            {},
        )

        parent = tree.get("PARENT_CLAUSE", "")

        role = verb_role(greek, clause_id, parent)

        lines.append(
            f"- {greek} | {lemma} | {rmac} | [{finite_label(rmac)}] | {role}"
        )

    lines.append("")

    return lines


def render_connectors(rows):
    lines = []

    lines.append("### Conectores detectados")
    lines.append("")

    connectors = [r for r in rows if r.get("TYPE") == "connector"]
=======
        finite = row.get("FINITE", "") or "?"
        cid = verb_clause_id(row, spans)
        location = cid if cid else "sin cláusula finita"
        lines.append(f"- {greek} | {lemma} | {rmac} | [{finite}] | {location}")

    lines.append("")
    return lines


def render_connectors(db_rows):
    lines = ["### Conectores detectados", ""]
    connectors = [r for r in sort_by_gidx(db_rows) if r.get("TYPE") == "connector"]
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1

    if not connectors:
        lines.append("- ninguno")
        lines.append("")
        return lines

    for row in connectors:
<<<<<<< HEAD
        greek = row.get("GREEK", "")

        relation = CONNECTOR_RELATIONS.get(
            greek,
            "relación no clasificada todavía"
        )

        lines.append(
            f"- {greek} | {relation}"
        )

    lines.append("")

    return lines


def inject_visible_connectors(text, connector_rows):
    """
    Inserts visible connector markers into the clause text.

    Example:
        ἵνα -> (ἵνα)
        ὅτι -> (ὅτι)

    Connectors remain visible lexical evidence,
    not confirmed structural authority.
    """

    if not text:
        return text

    connectors = []

    for row in connector_rows:
        greek = row.get("GREEK", "").strip()

        if not greek:
            continue

        connectors.append(greek)

    # longest first prevents partial overlaps
    connectors = sorted(set(connectors), key=len, reverse=True)

    for connector in connectors:
        pattern = rf"(?<!\()\\b{re.escape(connector)}\\b"

        text = re.sub(
            pattern,
            f"({connector})",
            text,
            count=1,
        )

    return text


def render_structure(spans, tree_lookup, db_rows):
    lines = []

    lines.append("### Vista estructural")
    lines.append("")

    connector_rows = [
        r for r in db_rows
        if r.get("TYPE") == "connector"
    ]

    for row in spans:
        clause_id = row.get("CLAUSE_ID", "")

        tree = tree_lookup.get(
            (
                row.get("BOOK", ""),
                row.get("CH", ""),
                row.get("VS", ""),
                clause_id,
            ),
            {},
        )

        depth = int(tree.get("TREE_DEPTH", "0") or "0")

        indent = "    " * depth

        text = row.get("SPAN_TEXT", "")

        text = inject_visible_connectors(
            text,
            connector_rows,
        )

        lines.append(f"{indent}{clause_id}. {text}")

    lines.append("")

    return lines


def render_notes(spans, tree_lookup):
    lines = []

    lines.append("### Observaciones estructurales")
    lines.append("")

    notes = []

    for row in spans:
        clause_id = row.get("CLAUSE_ID", "")

        tree = tree_lookup.get(
            (
                row.get("BOOK", ""),
                row.get("CH", ""),
                row.get("VS", ""),
                clause_id,
            ),
            {},
        )

        parent = tree.get("PARENT_CLAUSE", "")

        if parent:
            notes.append(
                f"- {clause_id} aparece actualmente subordinada bajo {parent}."
            )

        else:
            notes.append(
                f"- {clause_id} actualmente no posee relación estructural confirmada."
            )

    notes.append(
        "- La indentación representa una propuesta estructural mecánica provisional."
    )

    notes.append(
        "- La topología visible NO constituye jerarquía confirmada."
    )

    lines.extend(notes)
    lines.append("")

=======
        cid = row.get("ID", "")
        greek = row.get("GREEK", "")
        kind = kind_label(row.get("CONNECTOR_KIND", ""))
        relation = relation_label(row.get("DEFAULT_RELATION", ""))
        certainty = row.get("CERTAINTY", "")
        certainty_note = f" | certeza: {certainty}" if certainty else ""
        lines.append(f"- {cid}. {greek} | {kind} | {relation}{certainty_note}")

    lines.append("")
    return lines


def render_structure(spans, tree_lookup, db_rows):
    lines = ["### Vista estructural", ""]
    connectors = connector_tokens(db_rows)

    for row in spans:
        clause_id = row.get("CLAUSE_ID", "")
        key = (row.get("BOOK", ""), row.get("CH", ""), row.get("VS", ""), clause_id)
        tree = tree_lookup.get(key, {})
        depth = safe_int(tree.get("TREE_DEPTH", "0"), 0)
        indent = "    " * depth
        text = mark_connectors_inline(row.get("SPAN_TEXT", ""), connectors)
        lines.append(f"{indent}{clause_id}. {text}")

    lines.append("")
    return lines


def render_observations(spans, tree_lookup):
    lines = ["### Observaciones estructurales", ""]

    if not spans:
        lines.append("- No hay cláusulas finitas para mostrar en este versículo.")
        lines.append("")
        return lines

    for row in spans:
        clause_id = row.get("CLAUSE_ID", "")
        key = (row.get("BOOK", ""), row.get("CH", ""), row.get("VS", ""), clause_id)
        tree = tree_lookup.get(key, {})
        parent = tree.get("PARENT_CLAUSE", "")
        node_type = tree.get("NODE_TYPE", "root-or-unresolved")

        if parent:
            lines.append(f"- {clause_id} aparece visualmente bajo {parent} por una propuesta mecánica provisional.")
        elif node_type == "root-parent":
            lines.append(f"- {clause_id} aparece como cláusula raíz con posible desarrollo subordinado debajo.")
        else:
            lines.append(f"- {clause_id} aparece como cláusula raíz o todavía no resuelta.")

    lines.append("- La indentación ayuda a ver la propuesta mecánica, pero no confirma jerarquía.")
    lines.append("- Los conectores entre paréntesis son conectores detectados en el texto griego; el paréntesis no confirma su función estructural.")
    lines.append("")
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
    return lines


def render_book(grouped_db, grouped_spans, tree_lookup):
    lines = []
<<<<<<< HEAD

    verse_keys = sorted(
        grouped_spans.keys(),
        key=lambda x: (x[0], int(x[1]), int(x[2]))
    )

    for key in verse_keys:
        book, ch, vs = key

        lines.append(f"## {book} {ch}:{vs}")
        lines.append("")

        db_rows = grouped_db.get(key, [])

        spans = sorted(
            grouped_spans[key],
            key=lambda r: int(
                r.get("CLAUSE_ID", "C999").replace("C", "")
            )
        )

        lines.extend(render_verbs(db_rows, tree_lookup))
        lines.extend(render_connectors(db_rows))
        lines.extend(
    render_structure(
        spans,
        tree_lookup,
        db_rows,
    )
)
        lines.extend(render_notes(spans, tree_lookup))

=======
    verse_keys = sorted(grouped_spans.keys(), key=lambda x: (x[0], safe_int(x[1]), safe_int(x[2])))

    for key in verse_keys:
        book, ch, vs = key
        db_rows = grouped_db.get(key, [])
        spans = sorted(grouped_spans.get(key, []), key=lambda r: clause_number(r.get("CLAUSE_ID", "C999")))

        lines.append(f"## {book} {ch}:{vs}")
        lines.append("")
        lines.extend(render_verbs(db_rows, spans))
        lines.extend(render_connectors(db_rows))
        lines.extend(render_structure(spans, tree_lookup, db_rows))
        lines.extend(render_observations(spans, tree_lookup))
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
<<<<<<< HEAD
    parser = argparse.ArgumentParser()

    parser.add_argument("book")

    parser.add_argument(
        "--db-dir",
        default="MNA/roots-greek/db"
    )

    parser.add_argument(
        "--dataset-dir",
        default="MNA/roots-greek/dataset"
    )

    parser.add_argument(
        "--out-dir",
        default="MNA/roots-greek/output"
    )

    args = parser.parse_args()

    db_rows = read_tsv(
        Path(args.db_dir)
        / f"{args.book}-verbs-connectors.tsv"
    )

    span_rows = read_tsv(
        Path(args.dataset_dir)
        / f"{args.book}-clause-spans.tsv"
    )

    tree_rows = read_tsv(
        Path(args.dataset_dir)
        / f"{args.book}-structure-tree.tsv"
    )

    grouped_db = group_rows(
        db_rows,
        ["BOOK", "CH", "VS"]
    )

    grouped_spans = group_rows(
        span_rows,
        ["BOOK", "CH", "VS"]
    )

    tree_lookup = build_lookup(
        tree_rows,
        ["BOOK", "CH", "VS", "CLAUSE_ID"]
    )

    rendered = render_book(
        grouped_db,
        grouped_spans,
        tree_lookup,
    )

    out_path = (
        Path(args.out_dir)
        / f"{args.book}-paso6-rich.md"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(rendered, encoding="utf-8")

    print(f"Wrote {out_path}")

    print({
        "verses": len(grouped_spans),
        "clauses": len(span_rows),
    })


if __name__ == "__main__":
    main()
=======
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 6B readable Spanish PASO 6 renderer")
    parser.add_argument("book")
    parser.add_argument("--db-dir", default="MNA/roots-greek/db")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/output")
    args = parser.parse_args()

    db_rows = read_tsv(Path(args.db_dir) / f"{args.book}-verbs-connectors.tsv")
    span_rows = read_tsv(Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv")
    tree_rows = read_tsv(Path(args.dataset_dir) / f"{args.book}-structure-tree.tsv")

    grouped_db = group_rows(db_rows, ["BOOK", "CH", "VS"])
    grouped_spans = group_rows(span_rows, ["BOOK", "CH", "VS"])
    tree_lookup = build_lookup(tree_rows, ["BOOK", "CH", "VS", "CLAUSE_ID"])

    rendered = render_book(grouped_db, grouped_spans, tree_lookup)

    out_path = Path(args.out_dir) / f"{args.book}-paso6-rich.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")

    print(f"Wrote {out_path}")
    print({"verses": len(grouped_spans), "clauses": len(span_rows)})


if __name__ == "__main__":
    main()
>>>>>>> b90dcdd9316e395da529d4d8ff6dba447c1289c1
