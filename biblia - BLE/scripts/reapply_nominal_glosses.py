#!/usr/bin/env python3
"""Re-inflect noun/adjective glosses from lemma lexicon + Greek morph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "MNA" / "scripts"))

from grc_inflect_es import inflect_from_lemma, is_nominal_morph, load_spanish_gender  # noqa: E402

TOKENS_DIR = ROOT / "MNA" / "datasets" / "interlinear" / "NT"
RULES_DIR = ROOT / "MNA" / "datasets" / "rules"

NT_BOOKS = [
    "mateo", "marcos", "lucas", "juan", "hechos", "romanos",
    "1corintios", "2corintios", "galatas", "efesios", "filipenses", "colosenses",
    "1tesalonicenses", "2tesalonicenses", "1timoteo", "2timoteo", "tito", "filemon",
    "hebreos", "santiago", "1pedro", "2pedro", "1juan", "2juan", "3juan", "judas",
    "apocalipsis",
]

LEMMA_LEXICON: dict[str, str] = {}
LEMMA_DEFAULTS: dict[str, str] = {}


def load_lexica(rules_dir: Path) -> None:
    global LEMMA_LEXICON, LEMMA_DEFAULTS
    LEMMA_LEXICON = json.loads((rules_dir / "grc_lemma_lexicon.json").read_text(encoding="utf-8"))
    LEMMA_DEFAULTS = json.loads((rules_dir / "grc_lemma_defaults.json").read_text(encoding="utf-8"))


def base_gloss(lemma: str) -> str | None:
    gloss = LEMMA_LEXICON.get(lemma) or LEMMA_DEFAULTS.get(lemma)
    if not gloss or gloss in ("?",) or gloss.startswith("__FILL_"):
        return None
    return gloss


def reapply_file(path: Path) -> int:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    changed = 0
    for row in rows:
        lemma = str(row.get("lemma", ""))
        morph = str(row.get("morph", ""))
        if not is_nominal_morph(morph):
            continue
        base = base_gloss(lemma)
        if not base:
            continue
        new_es = inflect_from_lemma(lemma, base, morph)
        if new_es and row.get("es") != new_es:
            row["es"] = new_es
            changed += 1
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Reapply Spanish gender/number on N/A glosses.")
    parser.add_argument("book", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    args = parser.parse_args()

    load_lexica(args.rules_dir)
    load_spanish_gender(args.rules_dir)
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
            print(f"{book}: {n} nominal glosses updated")

    print(f"total updated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
