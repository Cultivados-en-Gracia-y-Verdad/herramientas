#!/usr/bin/env python3

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


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


def fail(message: str) -> None:
    print("FAIL\n")
    print(f"- {message}")
    sys.exit(1)


def clean_nbla(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


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


def build_columns(rows: List[Dict[str, str]]) -> List[Dict]:
    rows = sorted(
        rows,
        key=lambda r: first_nbla_index(r["NBLA_IDX"])
    )

    columns = []

    for i, row in enumerate(rows, start=1):
        g_idx = row["G_IDX"].strip()
        greek = row["GREEK"].strip()

        greek_tokens = [] if g_idx in {"", "-"} else [g_idx]

        columns.append({
            "column": i,

            "nbla_idx": row["NBLA_IDX"].strip(),

            "nbla": clean_nbla(row["NBLA_TEXT"]),

            "greek": "" if greek == "-" else greek,

            "greek_tokens": greek_tokens,

            "translit": "",

            "lemma": "",

            "rmac": "",

            "strongs": "",

            "alignment": row["ALIGNMENT"].strip()
        })

    return columns


def build_json(rows: List[Dict[str, str]]) -> Dict:
    first = rows[0]

    book = first["BOOK"].strip()
    chapter = int(first["CH"])
    verse = int(first["VS"])

    return {
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "reference": f"{book.title()} {chapter}:{verse}",
        "columns": build_columns(rows)
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
    data = build_json(rows)
    out = output_path(data)

    write_json(out, data)

    print("PASS JSON written:")
    print(out)


if __name__ == "__main__":
    main()