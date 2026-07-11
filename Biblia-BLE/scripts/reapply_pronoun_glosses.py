#!/usr/bin/env python3
"""Re-apply ἐγώ / σύ morph glosses across NT token files (fixes lexicon 'yo'/'tú' bleed)."""

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

PRONOUN_TABLES: dict[str, dict[str, str]] = {}


def load_tables(rules_dir: Path) -> None:
    PRONOUN_TABLES["ἐγώ"] = json.loads((rules_dir / "grc_ego_by_morph.json").read_text(encoding="utf-8"))
    PRONOUN_TABLES["σύ"] = json.loads((rules_dir / "grc_su_by_morph.json").read_text(encoding="utf-8"))


def reapply_file(path: Path) -> tuple[int, int, int]:
    ego = su = 0
    changed = 0
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        lemma = str(row.get("lemma", ""))
        morph = str(row.get("morph", ""))
        if lemma in PRONOUN_TABLES:
            if lemma == "ἐγώ":
                ego += 1
            else:
                su += 1
            table = PRONOUN_TABLES[lemma]
            if morph in table:
                new_es = table[morph]
                if row.get("es") != new_es:
                    row["es"] = new_es
                    changed += 1
        rows.append(row)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return changed, ego, su


def main() -> int:
    parser = argparse.ArgumentParser(description="Reapply ἐγώ/σύ morph glosses in token JSONL.")
    parser.add_argument("book", nargs="?", help="book slug")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    args = parser.parse_args()

    load_tables(args.rules_dir)
    books = NT_BOOKS if args.all else ([args.book] if args.book else [])
    if not books:
        parser.error("provide book or --all")

    total_changed = 0
    for book in books:
        path = args.tokens_dir / f"{book}.tokens.jsonl"
        if not path.is_file():
            print(f"skip {path}", file=sys.stderr)
            continue
        changed, ego, su = reapply_file(path)
        total_changed += changed
        print(f"{book}: {changed} updated ({ego} ἐγώ, {su} σύ tokens)")

    print(f"total updated: {total_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
