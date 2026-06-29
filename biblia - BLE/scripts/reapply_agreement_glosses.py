#!/usr/bin/env python3
"""πᾶς inflection (todo/toda/…) and articles matched to Spanish noun gender."""

from __future__ import annotations

import argparse
import json
import re
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

PAS_TABLE: dict[str, str] = {}
ARTICLE_TABLE: dict[str, str] = {}
SPANISH_GENDER: dict[str, str] = {}


def load_rules(rules_dir: Path) -> None:
    global PAS_TABLE, ARTICLE_TABLE, SPANISH_GENDER
    PAS_TABLE = json.loads((rules_dir / "grc_pas_by_morph.json").read_text(encoding="utf-8"))
    ARTICLE_TABLE = json.loads((rules_dir / "grc_article_by_morph.json").read_text(encoding="utf-8"))
    raw = json.loads((rules_dir / "grc_spanish_noun_gender.json").read_text(encoding="utf-8"))
    SPANISH_GENDER = {k: v for k, v in raw.items() if not k.startswith("_")}


def pas_from_morph(morph: str) -> str | None:
    if morph in PAS_TABLE:
        return PAS_TABLE[morph]
    if len(morph) < 9 or morph[0] not in ("A", "V"):
        return None
    number = morph[7]
    gender = morph[8]
    if number == "S":
        return "toda" if gender == "F" else "todo"
    return "todas" if gender == "F" else "todos"


def clean_gloss_word(gloss: str) -> str:
    word = gloss.replace("·", " ").strip().split()[0] if gloss else ""
    return re.sub(r"[.,;:!?»«]+$", "", word).lower()


def guess_gender_from_gloss(gloss: str) -> str | None:
    word = clean_gloss_word(gloss)
    if not word:
        return None
    if word.endswith(("ción", "sión", "dad", "tad", "ez", "umbre", "ión")):
        return "f"
    if word.endswith("a") and not word.endswith("ma"):
        return "f"
    if word.endswith("o"):
        return "m"
    return None


def gender_from_greek_morph(morph: str) -> str | None:
    if len(morph) <= 8:
        return None
    g = morph[8]
    if g == "F":
        return "f"
    if g in ("M", "N"):
        return "m"
    return None


def is_participle_morph(morph: str) -> bool:
    return morph.startswith("V") and len(morph) > 5 and morph[5] == "P"


def spanish_gender_for_token(row: dict) -> str | None:
    lemma = str(row.get("lemma", ""))
    gloss = str(row.get("es", ""))
    if gloss in ("", "?"):
        return None
    if lemma in SPANISH_GENDER:
        return SPANISH_GENDER[lemma]
    morph = str(row.get("morph", ""))
    if is_participle_morph(morph):
        return gender_from_greek_morph(morph)
    if morph.startswith("A"):
        return gender_from_greek_morph(morph) or guess_gender_from_gloss(gloss)
    if morph.startswith("N"):
        return guess_gender_from_gloss(gloss)
    return None


def next_head_gender(rows: list[dict], index: int) -> str | None:
    """Gender for article agreement: noun lexical gender, or Greek gender for participle/adj."""
    deferred_adj: str | None = None
    for j in range(index + 1, min(index + 6, len(rows))):
        row = rows[j]
        morph = str(row.get("morph", ""))
        if morph.startswith("RA"):
            continue
        if is_participle_morph(morph):
            return gender_from_greek_morph(morph)
        if morph.startswith("N"):
            return spanish_gender_for_token(row)
        if morph.startswith("A"):
            deferred_adj = gender_from_greek_morph(morph) or spanish_gender_for_token(row)
            continue
    return deferred_adj


def morph_with_gender(morph: str, gender: str) -> str:
    letter = {"m": "M", "f": "F", "n": "N"}.get(gender, "M")
    if len(morph) >= 9:
        return morph[:8] + letter + morph[9:]
    return morph


def article_for_spanish_noun(article_morph: str, noun_gender: str) -> str | None:
    return ARTICLE_TABLE.get(morph_with_gender(article_morph, noun_gender))


def next_noun_gender(rows: list[dict], index: int) -> str | None:
    return next_head_gender(rows, index)


def reapply_file(path: Path) -> tuple[int, int]:
    pas_changed = art_changed = 0
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    for i, row in enumerate(rows):
        lemma = str(row.get("lemma", ""))
        morph = str(row.get("morph", ""))

        if lemma == "πᾶς":
            new_es = pas_from_morph(morph)
            if new_es and row.get("es") != new_es:
                row["es"] = new_es
                pas_changed += 1

        if lemma == "ὁ" and morph in ARTICLE_TABLE:
            noun_gender = next_noun_gender(rows, i)
            if noun_gender:
                new_es = article_for_spanish_noun(morph, noun_gender)
                if new_es and row.get("es") != new_es:
                    row["es"] = new_es
                    art_changed += 1

    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return pas_changed, art_changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    args = parser.parse_args()

    load_rules(args.rules_dir)
    books = NT_BOOKS if args.all else ([args.book] if args.book else [])
    if not books:
        parser.error("provide book or --all")

    tp = ta = 0
    for book in books:
        path = args.tokens_dir / f"{book}.tokens.jsonl"
        if not path.is_file():
            continue
        pas_c, art_c = reapply_file(path)
        tp += pas_c
        ta += art_c
        if pas_c or art_c:
            print(f"{book}: πᾶς {pas_c}, articles {art_c}")

    print(f"total: πᾶς {tp}, articles {ta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
