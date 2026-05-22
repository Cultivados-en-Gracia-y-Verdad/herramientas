#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage1-frozen-finite-verbs-builder-v1"

TENSE = {"P":"present","I":"imperfect","F":"future","A":"aorist","R":"perfect","L":"pluperfect"}
VOICE = {"A":"active","M":"middle","P":"passive","E":"middle_or_passive","D":"middle_deponent","O":"passive_deponent","N":"middle_or_passive_deponent"}
MOOD = {"I":"indicative","S":"subjunctive","O":"optative","M":"imperative","N":"infinitive","P":"participle"}
PERSON = {"1":"first","2":"second","3":"third"}
NUMBER = {"S":"singular","P":"plural"}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def ref_parts(code: str) -> tuple[int, int]:
    d = "".join(c for c in code if c.isdigit())
    if len(d) < 4:
        raise ValueError(f"Bad MorphGNT reference: {code}")
    return int(d[-4:-2]), int(d[-2:])


def find_source(mna: Path, book: str) -> Path:
    base = mna / "SOURCES" / "MorphGNT"
    choices = [base / f"{book}-morphgnt.txt", base / f"{book}.txt", base / f"{book}.tsv"]
    for p in choices:
        if p.is_file():
            return p
    for p in sorted(base.rglob(f"*{book}*")):
        if p.is_file():
            return p
    raise FileNotFoundError(f"No MorphGNT source found for {book}")


def parse_line(raw: str):
    parts = raw.strip().split()
    if len(parts) < 5:
        return None
    if not parts[1].startswith("V-"):
        return None
    ref = parts[0]
    morph = parts[2]
    greek = parts[3]
    lemma = parts[4]
    if len(morph) < 4:
        return None
    person_code = morph[0]
    tense_code = morph[1]
    voice_code = morph[2]
    mood_code = morph[3]
    number_code = morph[5] if len(morph) > 5 else ""
    if mood_code in {"N", "P"}:
        return None
    if person_code not in PERSON:
        return None
    chapter, verse = ref_parts(ref)
    return {
        "chapter": chapter,
        "verse": verse,
        "greek_form": greek,
        "lemma": lemma,
        "morphology": f"V-{morph}",
        "is_finite": True,
        "tense": TENSE.get(tense_code, tense_code),
        "voice": VOICE.get(voice_code, voice_code),
        "mood": MOOD.get(mood_code, mood_code),
        "person": PERSON.get(person_code, person_code),
        "number": NUMBER.get(number_code, number_code),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    args = ap.parse_args()
    book = args.book.strip().lower()
    mna = root()
    src = find_source(mna, book)
    out = mna / "datasets" / "finite-verbs" / f"{book}.jsonl"
    rows = []
    token_index = 0
    with src.open("r", encoding="utf-8") as f:
        for raw in f:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            token_index += 1
            row = parse_line(raw)
            if row is None:
                continue
            rows.append({"record_type":"finite_verb", "book":book, "token_index":token_index, **row})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"record_type":"metadata","builder_version":VERSION,"book":book,"source":str(src.relative_to(mna)),"rows_written":len(rows)}, ensure_ascii=False, sort_keys=True)+"\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n")
    print("MNA Stage 1 — Frozen Finite Verbs Builder")
    print(f"BOOK: {book}")
    print(f"ROWS WRITTEN: {len(rows)}")
    print(f"OUTPUT: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
