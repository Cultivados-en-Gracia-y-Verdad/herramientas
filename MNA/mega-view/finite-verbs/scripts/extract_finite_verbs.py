#!/usr/bin/env python3
"""
Finite Verb Observatory for Ephesians using MorphGNT.

Targets:
  MNA/SOURCES/MorphGNT/70-Eph-morphgnt.txt

MorphGNT line format in this repo:
  100101 N- ----NSM- Παῦλος Παῦλος Παῦλος Παῦλος
  100101 V- -PAPDPM- οὖσιν οὖσιν οὖσι(ν) εἰμί

Columns:
  ref, part_of_speech, morph, surface, normalized, clean, lemma

Finite verb rule:
  POS must be V-
  morph mood slot must be one of:
    I = indicative
    S = subjunctive
    O = optative
    D = imperative

Excluded:
  P = participle
  N = infinitive
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from pathlib import Path


MOOD_MAP = {
    "I": "indicative",
    "S": "subjunctive",
    "O": "optative",
    "D": "imperative",
}

TENSE_MAP = {
    "P": "present",
    "I": "imperfect",
    "F": "future",
    "A": "aorist",
    "R": "perfect",
    "L": "pluperfect",
    "-": "",
}

VOICE_MAP = {
    "A": "active",
    "M": "middle",
    "P": "passive",
    "E": "middle/passive",
    "D": "middle deponent",
    "O": "passive deponent",
    "N": "middle/passive deponent",
    "-": "",
}

PERSON_MAP = {
    "1": "1st",
    "2": "2nd",
    "3": "3rd",
    "-": "",
}

NUMBER_MAP = {
    "S": "singular",
    "P": "plural",
    "-": "",
}

MATCH_MARKS = str.maketrans("", "", "⸀⸂⸃[]·,.;:!?“”\"")


def parse_ref(raw_ref: str):
    # Repo format appears to be:
    # 10 01 01 = Ephesians 1:1
    digits = "".join(ch for ch in raw_ref if ch.isdigit())
    if len(digits) >= 6:
        chapter = int(digits[-4:-2])
        verse = int(digits[-2:])
        return f"Eph {chapter}:{verse}", chapter, verse
    return raw_ref, 0, 0


def normalize_match_text(value: str) -> str:
    return value.translate(MATCH_MARKS)


def load_spanish_tokens(path: Path):
    by_form = defaultdict(deque)
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            token = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {error}") from error

        morph = str(token.get("morph", ""))
        if not morph.startswith("V-"):
            continue

        key = (
            int(token["ch"]),
            int(token["vs"]),
            normalize_match_text(str(token.get("surface", ""))),
            str(token.get("lemma", "")),
            morph[2:],
        )
        by_form[key].append(token)
    return by_form


def is_finite_verb(pos: str, morph: str) -> bool:
    if pos != "V-":
        return False
    if len(morph) < 4:
        return False

    # In this MorphGNT format:
    # finite:      3AAI-S--  person tense voice mood number ...
    # participle:  -PAPDPM-  - tense voice P case number gender
    # infinitive:  -PAN----  - tense voice N ...
    mood = morph[3]
    return mood in MOOD_MAP


def parse_verb_morph(morph: str):
    person_code = morph[0] if len(morph) > 0 else ""
    tense_code = morph[1] if len(morph) > 1 else ""
    voice_code = morph[2] if len(morph) > 2 else ""
    mood_code = morph[3] if len(morph) > 3 else ""
    number_code = morph[5] if len(morph) > 5 else ""

    return {
        "person": PERSON_MAP.get(person_code, person_code),
        "tense": TENSE_MAP.get(tense_code, tense_code),
        "voice": VOICE_MAP.get(voice_code, voice_code),
        "mood": MOOD_MAP.get(mood_code, mood_code),
        "number": NUMBER_MAP.get(number_code, number_code),
        "person_code": person_code,
        "tense_code": tense_code,
        "voice_code": voice_code,
        "mood_code": mood_code,
        "number_code": number_code,
    }


def extract(path: Path, tokens_path: Path):
    finite_verbs = []
    order = 0
    spanish_tokens = load_spanish_tokens(tokens_path)

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 7:
            continue

        raw_ref = parts[0]
        pos = parts[1]
        morph = parts[2]
        surface = parts[3]
        normalized = parts[4]
        clean = parts[5]
        lemma = parts[6]

        if not is_finite_verb(pos, morph):
            continue

        ref, chapter, verse = parse_ref(raw_ref)
        match_key = (
            chapter,
            verse,
            normalize_match_text(surface),
            lemma,
            morph,
        )
        if not spanish_tokens[match_key]:
            raise SystemExit(
                f"No Spanish token match for {ref} {surface} {lemma} {morph}"
            )
        spanish = str(spanish_tokens[match_key].popleft().get("es", "")).replace("·", " ")
        order += 1

        finite_verbs.append({
            "order": order,
            "line": line_no,
            "raw_ref": raw_ref,
            "ref": ref,
            "chapter": chapter,
            "verse": verse,
            "surface": surface,
            "normalized": normalized,
            "clean": clean,
            "lemma": lemma,
            "es": spanish,
            "pos": pos,
            "morph": morph,
            **parse_verb_morph(morph),
            "raw": line,
        })

    return finite_verbs


def write_outputs(finite_verbs, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "finite_verbs.json").write_text(
        json.dumps(finite_verbs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "finite_verbs_data.js").write_text(
        "window.FINITE_VERBS = "
        + json.dumps(finite_verbs, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )

    assertions_path = out_dir / "assertions.json"
    existing_assertions = {}
    if assertions_path.exists():
        try:
            existing_rows = json.loads(assertions_path.read_text(encoding="utf-8"))
            existing_assertions = {
                int(row["order"]): row
                for row in existing_rows
                if isinstance(row, dict) and "order" in row
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            existing_assertions = {}

    assertions = []
    for verb in finite_verbs:
        existing = existing_assertions.get(verb["order"], {})
        assertions.append({
            "order": verb["order"],
            "ref": verb["ref"],
            "subject": str(existing.get("subject", "")),
            "verb_form": verb["surface"],
            "verb_lemma": verb["lemma"],
            "object": str(existing.get("object", "")),
            "notes": str(existing.get("notes", "")),
            "confidence": str(existing.get("confidence", "")),
        })

    assertions_path.write_text(
        json.dumps(assertions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "assertions_data.js").write_text(
        "window.ASSERTIONS = "
        + json.dumps(assertions, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )

    fields = [
        "order", "ref", "chapter", "verse", "surface", "es", "normalized", "lemma",
        "morph", "person", "tense", "voice", "mood", "number",
    ]

    with (out_dir / "finite_verbs.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in finite_verbs:
            writer.writerow({k: row.get(k, "") for k in fields})

    by_chapter = Counter(v["chapter"] for v in finite_verbs)
    by_mood = Counter(v["mood"] for v in finite_verbs)
    by_tense = Counter(v["tense"] for v in finite_verbs)
    by_voice = Counter(v["voice"] for v in finite_verbs)
    by_person = Counter(v["person"] for v in finite_verbs)
    by_lemma = Counter(v["lemma"] for v in finite_verbs)

    by_chapter_mood = defaultdict(Counter)
    for v in finite_verbs:
        by_chapter_mood[v["chapter"]][v["mood"]] += 1

    summary = {
        "total_finite_verbs": len(finite_verbs),
        "by_chapter": dict(sorted(by_chapter.items())),
        "by_mood": dict(by_mood),
        "by_tense": dict(by_tense),
        "by_voice": dict(by_voice),
        "by_person": dict(by_person),
        "by_chapter_mood": {
            str(ch): dict(counts)
            for ch, counts in sorted(by_chapter_mood.items())
        },
        "top_lemmas": by_lemma.most_common(30),
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    moods = ["indicative", "subjunctive", "optative", "imperative"]

    md = []
    md.append("# Ephesians Finite Verb Observatory\n")
    md.append("Finite verbs only. Participles and infinitives excluded.\n")
    md.append(f"Total finite verbs: **{len(finite_verbs)}**\n")

    md.append("## Finite Verbs by Chapter\n")
    md.append("| chapter | count |")
    md.append("| --- | ---: |")
    for ch, count in sorted(by_chapter.items()):
        md.append(f"| {ch} | {count} |")

    md.append("\n## Mood by Chapter\n")
    md.append("| chapter | " + " | ".join(moods) + " |")
    md.append("| --- | " + " | ".join(["---:"] * len(moods)) + " |")
    for ch in sorted(by_chapter.keys()):
        counts = by_chapter_mood[ch]
        md.append("| " + str(ch) + " | " + " | ".join(str(counts.get(m, 0)) for m in moods) + " |")

    md.append("\n## Ordered Finite Verb Path\n")
    md.append("| # | ref | form | español | lemma | morph | person | tense | voice | mood | number |")
    md.append("| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for v in finite_verbs:
        md.append(
            f"| {v['order']} | {v['ref']} | {v['surface']} | {v['es']} | {v['lemma']} | {v['morph']} | "
            f"{v['person']} | {v['tense']} | {v['voice']} | {v['mood']} | {v['number']} |"
        )

    (out_dir / "finite_verbs.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--morphgnt",
        default="MNA/SOURCES/MorphGNT/70-Eph-morphgnt.txt",
        help="Path to MorphGNT Ephesians file.",
    )
    parser.add_argument(
        "--out",
        default="MNA/mega-view/finite-verbs/output",
        help="Output directory.",
    )
    parser.add_argument(
        "--tokens",
        default="MNA/datasets/interlinear/NT/efesios.tokens.jsonl",
        help="Path to Ephesians interlinear tokens containing Spanish glosses.",
    )
    args = parser.parse_args()

    morph_path = Path(args.morphgnt)
    if not morph_path.exists():
        raise SystemExit(f"Missing MorphGNT file: {morph_path}")
    tokens_path = Path(args.tokens)
    if not tokens_path.exists():
        raise SystemExit(f"Missing interlinear tokens file: {tokens_path}")

    finite_verbs = extract(morph_path, tokens_path)
    write_outputs(finite_verbs, Path(args.out))

    print(f"Extracted {len(finite_verbs)} finite verbs.")
    print(f"Wrote outputs to: {args.out}")


if __name__ == "__main__":
    main()
