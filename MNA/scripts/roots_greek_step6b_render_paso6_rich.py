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
- shows readable connector information
- renders visible structure
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
}


def read_tsv(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def group_rows(rows, keys):
    grouped = defaultdict(list)

    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        grouped[key].append(row)

    return grouped


def build_lookup(rows, keys):
    lookup = {}

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

    if not verbs:
        lines.append("- ninguno")
        lines.append("")
        return lines

    for row in verbs:
        greek = row.get("GREEK", "")
        lemma = row.get("LEMMA", "")
        rmac = row.get("RMAC", "")

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

    if not connectors:
        lines.append("- ninguno")
        lines.append("")
        return lines

    for row in connectors:
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

    return lines


def render_book(grouped_db, grouped_spans, tree_lookup):
    lines = []

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

        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
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