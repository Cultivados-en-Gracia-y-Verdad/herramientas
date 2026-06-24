#!/usr/bin/env python3
"""Fill ὅταν / μέν placeholder glosses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_DIR = ROOT / "MNA" / "datasets" / "interlinear" / "NT"

NT_BOOKS = [
    "mateo", "marcos", "lucas", "juan", "hechos", "romanos",
    "1corintios", "2corintios", "galatas", "efesios", "filipenses", "colosenses",
    "1tesalonicenses", "2tesalonicenses", "1timoteo", "2timoteo", "tito", "filemon",
    "hebreos", "santiago", "1pedro", "2pedro", "1juan", "2juan", "3juan", "judas",
    "apocalipsis",
]

PARTICLE_GLOSS = {
    "ὅταν": "cuando",
    "μέν": "en·verdad",
}


def reapply_file(path: Path) -> int:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    changed = 0
    for row in rows:
        lemma = str(row.get("lemma", ""))
        if lemma not in PARTICLE_GLOSS:
            continue
        new_es = PARTICLE_GLOSS[lemma]
        if row.get("es") != new_es and str(row.get("es", "")).startswith("__FILL_"):
            row["es"] = new_es
            changed += 1
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    args = parser.parse_args()

    books = NT_BOOKS if args.all else ([args.book] if args.book else [])
    if not books:
        parser.error("provide book or --all")

    total = 0
    for book in books:
        path = args.tokens_dir / f"{book}.tokens.jsonl"
        if not path.is_file():
            continue
        n = reapply_file(path)
        total += n
        if n:
            print(f"{book}: {n} particles updated")
    print(f"total updated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
