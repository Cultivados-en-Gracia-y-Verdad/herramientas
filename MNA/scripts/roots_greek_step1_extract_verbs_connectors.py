#!/usr/bin/env python3

"""
ROOTS Greek Step 1
Extract objective Greek facts only:
- verbs, marked [F] or [NF]
- all connector words

No Spanish.
No clause ownership.
No connector function in context.
No interpretation.

Output:
  MNA/roots-greek/db/{book}-verbs-connectors.tsv
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

FINITE_ENDINGS = {"I", "S", "M", "D"}

CONNECTOR_GLOSSES = {
    "δέ": "coordination", "δὲ": "coordination",
    "καί": "coordination", "καὶ": "coordination", "τε": "coordination",
    "οὐδέ": "negative coordination", "οὐδὲ": "negative coordination",
    "μηδέ": "negative coordination", "μηδὲ": "negative coordination",
    "οὔτε": "negative coordination", "μήτε": "negative coordination",
    "ἀλλά": "contrast", "ἀλλὰ": "contrast", "ἀλλʼ": "contrast",
    "πλήν": "contrast/exception", "πλὴν": "contrast/exception",
    "γάρ": "cause/ground", "γὰρ": "cause/ground",
    "οὖν": "inference", "ἄρα": "inference", "ὥστε": "result/inference",
    "διό": "inference", "διὸ": "inference", "διόπερ": "inference", "τοίνυν": "inference",
    "ἵνα": "purpose/result", "ὅπως": "purpose", "ὅτι": "content/cause",
    "ἐάν": "condition", "ἐὰν": "condition", "εἰ": "condition", "εἴ": "condition", "εἴπερ": "condition",
    "ἐπεί": "cause/temporal", "ἐπεὶ": "cause/temporal",
    "ἐπειδή": "cause/ground", "ἐπειδὴ": "cause/ground",
    "ὅταν": "temporal/condition", "ἕως": "temporal",
    "καθώς": "comparison/manner", "καθὼς": "comparison/manner", "καθάπερ": "comparison/manner",
    "ὡς": "comparison/manner", "ὥσπερ": "comparison/manner",
    "ἤ": "alternative/comparison", "ἢ": "alternative/comparison", "εἴτε": "alternative",
    "μή": "negation", "μὴ": "negation", "οὐ": "negation", "οὐκ": "negation", "οὐχ": "negation",
}

SUBORDINATING_CONNECTORS = {
    "ἵνα", "ὅπως", "ὅτι", "ἐάν", "ἐὰν", "εἰ", "εἴ", "εἴπερ", "ὅταν",
    "ἐπεί", "ἐπεὶ", "ἐπειδή", "ἐπειδὴ", "ἕως", "καθώς", "καθὼς", "καθάπερ",
    "ὡς", "ὥσπερ", "ὥστε",
}

COORDINATING_CONNECTORS = {
    "δέ", "δὲ", "καί", "καὶ", "τε", "ἀλλά", "ἀλλὰ", "ἀλλʼ", "πλήν", "πλὴν",
    "οὖν", "ἄρα", "διό", "διὸ", "διόπερ", "τοίνυν", "γάρ", "γὰρ", "ἤ", "ἢ", "εἴτε",
    "οὐδέ", "οὐδὲ", "μηδέ", "μηδὲ", "οὔτε", "μήτε",
}

HEADER = [
    "BOOK", "CH", "VS", "G_IDX", "TYPE", "ID", "GREEK", "LEMMA", "RMAC",
    "FINITE", "CONNECTOR_KIND", "DEFAULT_RELATION", "CERTAINTY",
]


def clean_surface(text: str) -> str:
    return str(text or "").strip().strip(".,;:·—⸁⸃[]();?·")


def is_verb(rmac: str) -> bool:
    return bool(rmac) and rmac.startswith("V-")


def is_finite(rmac: str) -> bool:
    if not is_verb(rmac):
        return False
    parts = rmac.split("-")
    return len(parts) >= 2 and len(parts[1]) >= 3 and parts[1][-1] in FINITE_ENDINGS


def connector_kind(surface: str) -> str:
    if surface in SUBORDINATING_CONNECTORS:
        return "subordinating"
    if surface in COORDINATING_CONNECTORS:
        return "coordinating"
    if surface in {"μή", "μὴ", "οὐ", "οὐκ", "οὐχ"}:
        return "negation"
    return "connector-word"


def greek_index(col: Dict) -> int:
    gt = col.get("greek_tokens") or []
    if not gt:
        return 999999
    try:
        return int(gt[0])
    except Exception:
        return 999999


def read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def verse_sort_key(path: Path) -> Tuple[int, int]:
    try:
        return int(path.parent.name), int(path.stem)
    except Exception:
        return 999999, 999999


def iter_columns(data: Dict) -> Iterable[Dict]:
    for col in sorted(data.get("columns", []), key=greek_index):
        if str(col.get("greek", "") or "").strip():
            yield col


def extract_book(book: str, interlinear_dir: Path) -> List[List[str]]:
    rows: List[List[str]] = []

    book_dir = interlinear_dir / book
    for json_path in sorted(book_dir.glob("*/*.json"), key=verse_sort_key):
        data = read_json(json_path)
        ch = str(data["chapter"])
        vs = str(data["verse"])
        verb_count = 0
        connector_count = 0

        for col in iter_columns(data):
            g_idx = f"{greek_index(col):02d}"
            greek = str(col.get("greek", "") or "")
            surface = clean_surface(greek)
            lemma = str(col.get("lemma", "") or "")
            rmac = str(col.get("rmac", "") or "")

            if is_verb(rmac):
                verb_count += 1
                rows.append([
                    book, ch, vs, g_idx, "verb", f"v{verb_count}", greek, lemma, rmac,
                    "F" if is_finite(rmac) else "NF", "", "", "certain",
                ])

            if surface in CONNECTOR_GLOSSES:
                connector_count += 1
                rows.append([
                    book, ch, vs, g_idx, "connector", f"cn{connector_count}", greek, lemma, rmac,
                    "", connector_kind(surface), CONNECTOR_GLOSSES[surface], "certain",
                ])

    return rows


def write_tsv(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 1: extract verbs and connector words.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--interlinear-dir", default="MNA/data/interlinear")
    parser.add_argument("--out-dir", default="MNA/roots-greek/db")
    args = parser.parse_args()

    rows = extract_book(args.book, Path(args.interlinear_dir))
    out_path = Path(args.out_dir) / f"{args.book}-verbs-connectors.tsv"
    write_tsv(out_path, rows)

    verbs = sum(1 for row in rows if row[4] == "verb")
    connectors = sum(1 for row in rows if row[4] == "connector")
    print(f"Wrote {out_path}")
    print({"verbs": verbs, "connectors": connectors, "rows": len(rows)})


if __name__ == "__main__":
    main()
