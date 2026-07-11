#!/usr/bin/env python3
"""Re-apply τις (indefinite pronoun) morph glosses; μή/οὐ context → nadie."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_DIR = ROOT / "MNA" / "datasets" / "interlinear" / "NT"
RULES_DIR = ROOT / "MNA" / "datasets" / "rules"

NT_BOOKS = [
    "mateo", "marcos", "lucas", "juan", "hechos", "romanos",
    "1corintios", "2corintios", "galatas", "efesios", "filipenses", "colosenses",
    "1tesalonicenses", "2tesalonicenses", "1timoteo", "2timoteo", "tito", "filemon",
    "hebreos", "santiago", "1pedro", "2pedro", "1juan", "2juan", "3juan", "judas",
    "apocalipsis",
]

NEG_LEMMAS = frozenset({"μή", "οὐ", "οὐκ", "οὐχ", "οὐδέ", "οὐδείς", "μηδείς"})

TIS_TABLE: dict[str, str] = {}
NADIE_TABLE: dict[str, str] = {}


def load_tables(rules_dir: Path) -> None:
    global TIS_TABLE, NADIE_TABLE
    TIS_TABLE = json.loads((rules_dir / "grc_tis_indef_by_morph.json").read_text(encoding="utf-8"))
    NADIE_TABLE = json.loads((rules_dir / "grc_tis_indef_nadie_by_morph.json").read_text(encoding="utf-8"))


def is_negated(rows: list[dict], index: int) -> bool:
    for j in range(index - 1, max(index - 5, -1), -1):
        prev = rows[j]
        lemma = str(prev.get("lemma", ""))
        if lemma in NEG_LEMMAS:
            return True
        morph = str(prev.get("morph", ""))
        if morph.startswith(("C", "D", "X", "P")):
            continue
        break
    return False


def gloss_for_tis(rows: list[dict], index: int, morph: str) -> str | None:
    table = NADIE_TABLE if is_negated(rows, index) else TIS_TABLE
    return table.get(morph)


def reapply_file(path: Path) -> int:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    changed = 0
    for i, row in enumerate(rows):
        if str(row.get("lemma", "")) != "τις":
            continue
        morph = str(row.get("morph", ""))
        new_es = gloss_for_tis(rows, i, morph)
        if new_es and row.get("es") != new_es:
            row["es"] = new_es
            changed += 1
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Reapply τις indefinite pronoun glosses.")
    parser.add_argument("book", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    args = parser.parse_args()

    load_tables(args.rules_dir)
    books = NT_BOOKS if args.all else ([args.book] if args.book else [])
    if not books:
        parser.error("provide book or --all")

    total = 0
    for book in books:
        path = args.tokens_dir / f"{book}.tokens.jsonl"
        if not path.is_file():
            print(f"skip {path}", file=sys.stderr)
            continue
        n = reapply_file(path)
        total += n
        if n:
            print(f"{book}: {n} τις updated")

    print(f"total updated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
