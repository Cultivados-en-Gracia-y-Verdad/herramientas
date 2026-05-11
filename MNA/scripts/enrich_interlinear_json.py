#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path
from typing import Dict


MORPH_PATH = Path("data/morphgnt/filemon-morphgnt.txt")


def fail(message: str) -> None:
    print("FAIL\n")
    print(f"- {message}")
    sys.exit(1)


def load_json(path: Path) -> Dict:
    if not path.exists():
        fail(f"JSON not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_book(book: str) -> str:
    return book.lower().replace(" ", "")

def morphgnt_to_rmac(pos: str, morph: str) -> str:
    if pos == "V-":
        # Example MorphGNT:
        # 1PAI-S-- = first person, present, active, indicative, singular
        # -PMPNSM- = participle, present, middle/passive, nominative singular masculine

        person = morph[0]
        tense = morph[1]
        voice = morph[2]
        mood = morph[3]

        # Finite verbs usually have person in slot 0.
        if person in {"1", "2", "3"}:
            number = morph[5]

            return f"V-{tense}{voice}{mood}-{person}{number}"

        # Non-finite verb forms keep a simpler converted code for now.
        return f"V-{tense}{voice}{mood}"

    if pos == "N-":
        case = morph[4]
        number = morph[5]
        gender = morph[6]
        return f"N-{case}{number}{gender}"

    if pos == "A-":
        case = morph[4]
        number = morph[5]
        gender = morph[6]
        return f"A-{case}{number}{gender}"

    if pos == "RA":
        case = morph[4]
        number = morph[5]
        gender = morph[6]
        return f"T-{case}{number}{gender}"

    if pos == "C-":
        return "CONJ"

    if pos == "RP":
        case = morph[4]
        number = morph[5]
        gender = morph[6] if morph[7] != "-" else ""
        return f"P-{case}{number}{gender}"

    return pos + morph

def load_morph() -> Dict:
    if not MORPH_PATH.exists():
        fail(f"MorphGNT file not found: {MORPH_PATH}")

    morph = {}

    with MORPH_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = re.split(r"\s+", line)

            if len(parts) < 7:
                continue

            ref = parts[0]
            pos = parts[1]
            morph_code = parts[2]
            surface = parts[3]
            lemma = parts[6]

            morphgnt = pos + morph_code
            rmac = morphgnt_to_rmac(pos, morph_code)

            # Example: 180101 = book 18, chapter 01, verse 01
            if not re.match(r"^\d{6}$", ref):
                continue

            book = "filemon"
            chapter = int(ref[2:4])
            verse = int(ref[4:6])

            key = (book, chapter, verse)

            if key not in morph:
                morph[key] = []

            morph[key].append({
                "surface": surface,
                "lemma": lemma,
                "morphgnt": morphgnt,
                "rmac": rmac
            })

    return morph


def enrich(data: Dict, morph_data: Dict) -> Dict:
    book = normalize_book(data["book"])
    chapter = data["chapter"]
    verse = data["verse"]

    key = (book, chapter, verse)

    if key not in morph_data:
        fail(f"MorphGNT verse not found: {book} {chapter}:{verse}")

    verse_tokens = morph_data[key]

    for column in data["columns"]:
        greek_tokens = column.get("greek_tokens", [])

        if not greek_tokens:
            continue

        try:
            g_idx = int(greek_tokens[0]) - 1
        except:
            continue

        if g_idx < 0 or g_idx >= len(verse_tokens):
            continue

        token = verse_tokens[g_idx]

        column["lemma"] = token["lemma"]
        column["morphgnt"] = token["morphgnt"]
        column["rmac"] = token["rmac"]

    return data


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:")
        print(
            "  python3 scripts/enrich_interlinear_json.py "
            "data/interlinear/filemon/1/1.json"
        )
        sys.exit(2)

    json_path = Path(sys.argv[1])

    data = load_json(json_path)

    morph_data = load_morph()

    data = enrich(data, morph_data)

    save_json(json_path, data)

    print(f"PASS enriched:")
    print(json_path)


if __name__ == "__main__":
    main()