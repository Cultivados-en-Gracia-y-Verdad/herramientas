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
- raw Greek clause stream

This is the canonical ROOTS structural reset layer.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

FINITE_ENDINGS = {"I", "S", "M", "D"}

CONNECTOR_GLOSSES = {
    "δέ": "coordination",
    "καί": "coordination",
    "ἀλλά": "contrast",
    "γάρ": "cause",
    "οὖν": "inference",
    "ἵνα": "purpose",
    "ὅτι": "content/cause",
    "ἐάν": "condition",
    "εἰ": "condition",
    "ὡς": "comparison/manner",
    "μή": "negation",
    "οὐ": "negation",
}

CONNECTORS = set(CONNECTOR_GLOSSES)


def is_verb(rmac: str) -> bool:
    return bool(rmac) and rmac.startswith("V-")


def is_finite(rmac: str) -> bool:
    if not is_verb(rmac):
        return False
    parts = rmac.split("-")
    if len(parts) < 2 or len(parts[1]) < 3:
        return False
    return parts[1][-1] in FINITE_ENDINGS


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


def iter_columns(data: Dict) -> Iterable[Dict]:
    cols = data.get("columns", [])

    def gidx(col: Dict) -> int:
        gt = col.get("greek_tokens") or []
        if not gt:
            return 999999
        try:
            return int(gt[0])
        except Exception:
            return 999999

    for col in sorted(cols, key=gidx):
        yield col


def finite_label(rmac: str) -> str:
    return "[F]" if is_finite(rmac) else "[NF]"


def build_clause_stream(columns: List[Dict]) -> List[List[Dict]]:
    """
    Temporary Greek-only clause stream.

    Current heuristic:
    - start new clause at finite verb after another finite verb
    - start new clause after strong connector introducing dependency

    This is intentionally simple during the reset phase.
    """

    clauses: List[List[Dict]] = []
    current: List[Dict] = []
    finite_seen = False

    for col in columns:
        greek = str(col.get("greek", "") or "")
        rmac = str(col.get("rmac", "") or "")

        start_new = False

        if current:
            if greek in {"ἵνα", "ὅτι", "ἐάν", "εἰ"}:
                start_new = True
            elif finite_seen and is_finite(rmac):
                start_new = True

        if start_new:
            clauses.append(current)
            current = []
            finite_seen = False

        current.append(col)

        if is_finite(rmac):
            finite_seen = True

    if current:
        clauses.append(current)

    return clauses


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

        lines.append(
            f"- {greek} | {lemma} | {rmac} | {finite_label(rmac)}"
        )

    if not verb_found:
        lines.append("- none")

    lines.append("")
    lines.append("### Conectores detectados")
    lines.append("")

    connector_count = 0

    for col in columns:
        greek = str(col.get("greek", "") or "")

        if greek not in CONNECTORS:
            continue

        connector_count += 1

        relation = CONNECTOR_GLOSSES.get(greek, "unknown")

        lines.append(
            f"- cn{connector_count}. {greek} | relación: {relation} | alcance: clause-level"
        )

    if connector_count == 0:
        lines.append("- none")

    lines.append("")
    lines.append("### Cláusulas")
    lines.append("")

    clauses = build_clause_stream(columns)

    for idx, clause in enumerate(clauses, start=1):
        parts: List[str] = []

        for col in clause:
            greek = str(col.get("greek", "") or "")
            rmac = str(col.get("rmac", "") or "")

            if is_finite(rmac):
                parts.append(f"=={greek}==")
            else:
                parts.append(greek)

        clause_text = " ".join(parts).strip()

        lines.append(f"C{idx}. {clause_text}")

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
