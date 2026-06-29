#!/usr/bin/env python3
"""Find lemmas whose Greek morphology varies in gender but Spanish gloss does not."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from tokens_to_ble import NT_BOOKS, TOKENS_DIR, load_tokens

# MorphGNT: position 7 = number (S/P), 8 = gender (M/F/N)
GENDER = {"M": "masc", "F": "fem", "N": "neut"}
NUMBER = {"S": "sg", "P": "pl"}


def nominal_gender_number(morph: str, pos: str) -> tuple[str, str] | None:
    """Return (gender, number) for nouns, adjectives, and participles."""
    if not morph or len(morph) < 9:
        return None
    if pos in ("N", "A"):
        pass
    elif pos == "V" and len(morph) > 5 and morph[5] == "P":
        pass  # participle
    else:
        return None
    gender = GENDER.get(morph[8])
    number = NUMBER.get(morph[7])
    if not gender or not number:
        return None
    return gender, number


def pos_from_morph(morph: str) -> str:
    return morph[0] if morph else ""


def audit_book(path: Path) -> dict[str, dict]:
    """Lemma -> {genders, glosses, count, examples}."""
    tokens = load_tokens(path)
    by_lemma: dict[str, dict] = defaultdict(
        lambda: {
            "genders": set(),
            "numbers": set(),
            "glosses": set(),
            "count": 0,
            "examples": [],
        }
    )

    for token in tokens:
        morph = str(token.get("morph", ""))
        pos = pos_from_morph(morph)
        gn = nominal_gender_number(morph, pos)
        if not gn:
            continue

        lemma = str(token.get("lemma", ""))
        es = str(token.get("es", ""))
        if not lemma or es in ("", "?"):
            continue

        entry = by_lemma[lemma]
        gender, number = gn
        entry["genders"].add(gender)
        entry["numbers"].add(number)
        entry["glosses"].add(es)
        entry["count"] += 1
        if len(entry["examples"]) < 3:
            entry["examples"].append(
                f"{token.get('book')} {token['ch']}:{token['vs']} "
                f"{token.get('surface')} ({morph}) → {es}"
            )

    return by_lemma


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit Spanish glosses that ignore Greek gender morphology."
    )
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--book", help="single book slug")
    parser.add_argument("--min-count", type=int, default=2, help="min token hits per lemma")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    books = [args.book] if args.book else NT_BOOKS
    merged: dict[str, dict] = defaultdict(
        lambda: {
            "genders": set(),
            "numbers": set(),
            "glosses": set(),
            "count": 0,
            "examples": [],
        }
    )

    for book in books:
        path = args.tokens_dir / f"{book}.tokens.jsonl"
        if not path.is_file():
            print(f"skip missing {path}", file=sys.stderr)
            continue
        for lemma, data in audit_book(path).items():
            m = merged[lemma]
            m["genders"] |= data["genders"]
            m["numbers"] |= data["numbers"]
            m["glosses"] |= data["glosses"]
            m["count"] += data["count"]
            for ex in data["examples"]:
                if len(m["examples"]) < 3:
                    m["examples"].append(ex)

    flagged = []
    for lemma, data in sorted(merged.items(), key=lambda item: -item[1]["count"]):
        if data["count"] < args.min_count:
            continue
        if "masc" in data["genders"] and "fem" in data["genders"] and len(data["glosses"]) == 1:
            flagged.append(
                {
                    "lemma": lemma,
                    "gloss": next(iter(data["glosses"])),
                    "genders": sorted(data["genders"]),
                    "numbers": sorted(data["numbers"]),
                    "count": data["count"],
                    "examples": data["examples"],
                }
            )

    if args.json:
        print(json.dumps(flagged, ensure_ascii=False, indent=2))
    else:
        print(f"lemmas with masc+fem morphology but one Spanish gloss: {len(flagged)}\n")
        for row in flagged[:40]:
            print(f"{row['lemma']} → {row['gloss']}  ({row['count']} tokens, g={row['genders']})")
            for ex in row["examples"]:
                print(f"    {ex}")
        if len(flagged) > 40:
            print(f"... and {len(flagged) - 40} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
