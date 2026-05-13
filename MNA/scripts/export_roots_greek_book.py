#!/usr/bin/env python3

"""
Greek-only ROOTS exporter.

This exporter intentionally ignores ALL Spanish alignment fields.
It uses only:
- Greek token order
- Greek surface forms
- lemma
- RMAC

Current output:
- detected verbs
- finite/non-finite status
- connector list
- Greek clause stream

This is the canonical ROOTS structural reset layer.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

FINITE_ENDINGS = {"I", "S", "M", "D"}

# Clause-level connectors only. Simple negators are not listed as connectors here;
# they remain inside the clause they negate.
CONNECTOR_GLOSSES = {
    "δέ": "coordination",
    "δὲ": "coordination",
    "καί": "coordination",
    "καὶ": "coordination",
    "ἀλλά": "contrast",
    "ἀλλὰ": "contrast",
    "ἀλλʼ": "contrast",
    "γάρ": "cause",
    "γὰρ": "cause",
    "οὖν": "inference",
    "ἄρα": "inference",
    "ὥστε": "result/inference",
    "διό": "inference",
    "διόπερ": "inference",
    "τοίνυν": "inference",
    "ἵνα": "purpose",
    "ὅπως": "purpose",
    "ὅτι": "content/cause",
    "ἐάν": "condition",
    "ἐὰν": "condition",
    "εἰ": "condition",
    "εἴπερ": "condition",
    "ὅταν": "temporal/condition",
    "ἐπειδή": "cause/ground",
    "ἐπειδὴ": "cause/ground",
    "καθώς": "comparison/manner",
    "καθὼς": "comparison/manner",
    "ὡς": "comparison/manner",
    "ὥσπερ": "comparison/manner",
}

SUBORDINATING_CONNECTORS = {
    "ἵνα", "ὅπως", "ὅτι", "ἐάν", "ἐὰν", "εἰ", "εἴπερ", "ὅταν",
    "ἐπειδή", "ἐπειδὴ", "καθώς", "καθὼς", "ὡς", "ὥσπερ", "ὥστε",
}

COORDINATING_CONNECTORS = {
    "δέ", "δὲ", "καί", "καὶ", "ἀλλά", "ἀλλὰ", "ἀλλʼ", "οὖν", "ἄρα", "διό", "διόπερ", "τοίνυν", "γάρ", "γὰρ",
}

PRE_FINITE_CARRY = {
    "δέ", "δὲ", "καί", "καὶ", "ἀλλά", "ἀλλὰ", "ἀλλʼ", "ἢ", "μή", "μὴ",
    "οὐ", "οὐκ", "οὐχ", "οὔτε", "μηδέ", "μηδὲ", "οὐδέ", "οὐδὲ",
}

CONNECTORS = set(CONNECTOR_GLOSSES)


def clean_surface(text: str) -> str:
    text = str(text or "").strip()
    return text.strip(".,;:·—⸁⸃[]();?·")


def is_verb(rmac: str) -> bool:
    return bool(rmac) and rmac.startswith("V-")


def is_finite(rmac: str) -> bool:
    if not is_verb(rmac):
        return False
    parts = rmac.split("-")
    if len(parts) < 2 or len(parts[1]) < 3:
        return False
    return parts[1][-1] in FINITE_ENDINGS


def is_connector(col: Dict) -> bool:
    return clean_surface(col.get("greek", "")) in CONNECTORS


def connector_relation(col: Dict) -> str:
    return CONNECTOR_GLOSSES.get(clean_surface(col.get("greek", "")), "unknown")


def read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def verse_sort_key(path: Path) -> Tuple[int, int]:
    try:
        chapter = int(path.parent.name)
    except ValueError:
        chapter = 999999
    try:
        verse = int(path.stem)
    except ValueError:
        verse = 999999
    return chapter, verse


def greek_index(col: Dict) -> int:
    gt = col.get("greek_tokens") or []
    if not gt:
        return 999999
    try:
        return int(gt[0])
    except Exception:
        return 999999


def iter_columns(data: Dict) -> Iterable[Dict]:
    for col in sorted(data.get("columns", []), key=greek_index):
        if str(col.get("greek", "") or "").strip():
            yield col


def finite_label(rmac: str) -> str:
    return "[F]" if is_finite(rmac) else "[NF]"


def clause_has_finite(clause: List[Dict]) -> bool:
    return any(is_finite(str(col.get("rmac", "") or "")) for col in clause)


def clean_token(col: Dict) -> str:
    return clean_surface(col.get("greek", ""))


def starts_subordinate_clause(col: Dict) -> bool:
    return clean_token(col) in SUBORDINATING_CONNECTORS


def carry_trailing_prefinite_tokens(current: List[Dict]) -> List[Dict]:
    carried: List[Dict] = []

    while current and clean_token(current[-1]) in PRE_FINITE_CARRY:
        carried.insert(0, current.pop())

    return carried


def build_clause_stream(columns: List[Dict]) -> List[List[Dict]]:
    """
    Greek-only clause stream v2.

    Rules:
    1. A subordinate connector starts a new clause when a finite clause is already open.
    2. A second finite verb starts a new clause.
    3. When a second finite verb starts a new clause, trailing pre-finite particles
       such as καὶ, δὲ, μὴ, οὐκ are carried forward into the new clause.
    4. Non-finite-only verses remain one visible unit for now.
    """

    clauses: List[List[Dict]] = []
    current: List[Dict] = []

    for col in columns:
        rmac = str(col.get("rmac", "") or "")
        start_new = False
        carry: List[Dict] = []

        if current:
            if starts_subordinate_clause(col) and clause_has_finite(current):
                start_new = True
            elif is_finite(rmac) and clause_has_finite(current):
                start_new = True
                carry = carry_trailing_prefinite_tokens(current)

        if start_new:
            if current:
                clauses.append(current)
            current = carry[:]

        current.append(col)

    if current:
        clauses.append(current)

    return clauses


def render_clause(clause: List[Dict]) -> str:
    parts: List[str] = []

    for col in clause:
        greek = str(col.get("greek", "") or "")
        rmac = str(col.get("rmac", "") or "")

        if is_finite(rmac):
            parts.append(f"=={greek}==")
        else:
            parts.append(greek)

    return " ".join(parts).strip()


def render_verse(data: Dict) -> str:
    book = data["book"]
    chapter = data["chapter"]
    verse = data["verse"]

    lines: List[str] = []

    lines.append(f"### {book} {chapter}:{verse}")
    lines.append("")

    columns = list(iter_columns(data))

    lines.append("### Verbos detectados")
    lines.append("")

    verb_found = False

    for col in columns:
        rmac = str(col.get("rmac", "") or "")

        if not is_verb(rmac):
            continue

        verb_found = True

        greek = col.get("greek", "")
        lemma = col.get("lemma", "")

        lines.append(f"- {greek} | {lemma} | {rmac} | {finite_label(rmac)}")

    if not verb_found:
        lines.append("- none")

    lines.append("")
    lines.append("### Conectores detectados")
    lines.append("")

    connector_count = 0

    for col in columns:
        if not is_connector(col):
            continue

        connector_count += 1
        greek = col.get("greek", "")
        relation = connector_relation(col)

        lines.append(f"- cn{connector_count}. {greek} | relación: {relation} | alcance: clause-level")

    if connector_count == 0:
        lines.append("- none")

    lines.append("")
    lines.append("### Cláusulas")
    lines.append("")

    clauses = build_clause_stream(columns)

    for idx, clause in enumerate(clauses, start=1):
        lines.append(f"C{idx}. {render_clause(clause)}")

    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def export_book(book: str, interlinear_dir: Path, output_dir: Path) -> None:
    book_dir = interlinear_dir / book

    outputs: List[str] = []

    for json_path in sorted(book_dir.glob("*/*.json"), key=verse_sort_key):
        data = read_json(json_path)
        outputs.append(render_verse(data))

    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"{book}.md"

    with out_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(outputs))

    print(f"Wrote Greek ROOTS export: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Greek-only ROOTS structure.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--interlinear-dir", default="MNA/data/interlinear")
    parser.add_argument("--output-dir", default="MNA/roots-greek/outputs")
    args = parser.parse_args()

    export_book(
        book=args.book,
        interlinear_dir=Path(args.interlinear_dir),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
