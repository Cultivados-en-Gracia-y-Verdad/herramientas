#!/usr/bin/env python3

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REQUIRED_COLUMNS = [
    "BOOK",
    "CH",
    "VS",
    "G_IDX",
    "GREEK",
    "NBLA_IDX",
    "NBLA_TEXT",
    "ALIGNMENT",
]

BOOK_ALIASES = {
    "1cor": "1corintios",
    "1corintios": "1corintios",
    "filemon": "filemon",
    "romanos": "romanos",
}


def fail(message: str) -> None:
    print("FAIL\n")
    print(f"- {message}")
    sys.exit(1)


def clean_nbla(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def normalize_book(book: str) -> str:
    return book.lower().replace(" ", "")


def canonical_book(book: str) -> str:
    normalized = normalize_book(book)
    return BOOK_ALIASES.get(normalized, normalized)


def morph_path_candidates(book: str) -> List[Path]:
    normalized = normalize_book(book)
    canonical = canonical_book(book)

    names = []

    for name in [normalized, canonical]:
        if name and name not in names:
            names.append(name)

    return [
        Path(f"data/morphgnt/{name}-morphgnt.txt")
        for name in names
    ]


def find_morph_path(book: str) -> Path:
    candidates = morph_path_candidates(book)

    for path in candidates:
        if path.exists():
            return path

    fail(
        "MorphGNT file not found. Tried: "
        + ", ".join(str(path) for path in candidates)
    )


def morphgnt_to_rmac(pos: str, morph: str) -> str:
    if pos == "V-":
        if len(morph) < 6:
            return pos + morph

        person = morph[0]
        tense = morph[1]
        voice = morph[2]
        mood = morph[3]

        if person in {"1", "2", "3"}:
            number = morph[5]
            return f"V-{tense}{voice}{mood}-{person}{number}"

        return f"V-{tense}{voice}{mood}"

    if pos in {"N-", "A-", "RA"}:
        if len(morph) < 7:
            return pos + morph

        case = morph[4]
        number = morph[5]
        gender = morph[6]

        if pos == "N-":
            return f"N-{case}{number}{gender}"

        if pos == "A-":
            return f"A-{case}{number}{gender}"

        return f"T-{case}{number}{gender}"

    if pos == "C-":
        return "CONJ"

    if pos == "RP":
        if len(morph) < 7:
            return pos + morph

        case = morph[4]
        number = morph[5]
        gender = morph[6] if len(morph) > 7 and morph[6] != "-" else ""
        return f"P-{case}{number}{gender}"

    return pos + morph


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        fail(f"file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        if not reader.fieldnames:
            fail("TSV has no header row")

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            fail("missing required column(s): " + ", ".join(missing))

        rows = list(reader)

    if not rows:
        fail("TSV has no data rows")

    return rows


def first_nbla_index(value: str) -> int:
    value = value.strip()

    if not value or value == "-":
        return 999999

    first = value.split(",")[0].strip()

    if "-" in first:
        first = first.split("-")[0]

    return int(first)


def load_morph(book: str) -> Dict[Tuple[int, int], List[Dict[str, str]]]:
    morph_path = find_morph_path(book)
    morph: Dict[Tuple[int, int], List[Dict[str, str]]] = {}

    with morph_path.open("r", encoding="utf-8") as f:
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

            if not re.match(r"^\d{6}$", ref):
                continue

            chapter = int(ref[2:4])
            verse = int(ref[4:6])
            key = (chapter, verse)

            morphgnt = pos + morph_code
            rmac = morphgnt_to_rmac(pos, morph_code)

            morph.setdefault(key, []).append({
                "surface": surface,
                "lemma": lemma,
                "morphgnt": morphgnt,
                "rmac": rmac,
            })

    return morph


def build_columns(rows: List[Dict[str, str]], verse_morph: List[Dict[str, str]]) -> List[Dict]:
    rows = sorted(
        rows,
        key=lambda r: first_nbla_index(r["NBLA_IDX"])
    )

    columns = []

    for i, row in enumerate(rows, start=1):
        g_idx = row["G_IDX"].strip()
        greek = row["GREEK"].strip()

        greek_tokens = [] if g_idx in {"", "-"} else [g_idx]

        lemma = ""
        morphgnt = ""
        rmac = ""

        if greek_tokens:
            try:
                morph_idx = int(greek_tokens[0]) - 1
            except ValueError:
                morph_idx = -1

            if 0 <= morph_idx < len(verse_morph):
                token = verse_morph[morph_idx]
                lemma = token["lemma"]
                morphgnt = token["morphgnt"]
                rmac = token["rmac"]

        columns.append({
            "column": i,
            "nbla_idx": row["NBLA_IDX"].strip(),
            "nbla": clean_nbla(row["NBLA_TEXT"]),
            "greek": "" if greek == "-" else greek,
            "greek_tokens": greek_tokens,
            "translit": "",
            "lemma": lemma,
            "rmac": rmac,
            "strongs": "",
            "alignment": row["ALIGNMENT"].strip(),
            "morphgnt": morphgnt,
        })

    return columns


def build_json(rows: List[Dict[str, str]], morph_data: Dict[Tuple[int, int], List[Dict[str, str]]]) -> Dict:
    first = rows[0]

    book = first["BOOK"].strip()
    chapter = int(first["CH"])
    verse = int(first["VS"])
    key = (chapter, verse)

    if key not in morph_data:
        fail(f"MorphGNT verse not found: {book} {chapter}:{verse}")

    return {
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "reference": f"{book.title()} {chapter}:{verse}",
        "columns": build_columns(rows, morph_data[key])
    }


def output_path(data: Dict) -> Path:
    return Path(
        f"data/interlinear/{data['book']}/{data['chapter']}/{data['verse']}.json"
    )


def write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python3 scripts/build_interlinear_json.py data/alignments/filemon/filemon-1-1.tsv")
        sys.exit(2)

    rows = read_tsv(Path(sys.argv[1]))
    book = rows[0]["BOOK"].strip()
    morph_data = load_morph(book)
    data = build_json(rows, morph_data)
    out = output_path(data)

    write_json(out, data)

    print("PASS JSON written:")
    print(out)


if __name__ == "__main__":
    main()
