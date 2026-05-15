#!/usr/bin/env python3
import csv
import sys
from pathlib import Path


REQUIRED_COLUMNS = [
    "BOOK",
    "CH",
    "VS",
    "COL",
    "NBLA_IDX",
    "NBLA_TEXT",
    "GREEK_IDX",
    "GREEK_TEXT",
    "LEMMA",
    "RMAC",
    "STRONGS",
    "ALIGNMENT",
]


OPTIONAL_EMPTY_COLUMNS = {
    "STRONGS",
}

from typing import Optional, List, Dict, Tuple


def fail(message: str) -> None:
    print("FAIL")
    print()
    print(f"- {message}")
    sys.exit(1)


def parse_int(value: str, field: str, line_no: int) -> int:
    value = value.strip()
    if not value.isdigit():
        fail(f"line {line_no}: {field} must be a positive integer, got '{value}'")
    return int(value)


def split_indices(value: str) -> list[str]:
    value = value.strip()

    if value in {"", "-"}:
        return []

    parts: list[str] = []

    for chunk in value.split(","):
        chunk = chunk.strip()

        if "-" in chunk:
            start_raw, end_raw = chunk.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)

            if end < start:
                fail(f"invalid index range '{chunk}'")

            width = max(len(start_raw), len(end_raw))

            for i in range(start, end + 1):
                parts.append(str(i).zfill(width))
        else:
            parts.append(chunk)

    return parts


from typing import Optional

def validate_required_columns(fieldnames: Optional[list[str]]) -> None:
    if not fieldnames:
        fail("TSV has no header row")

    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]

    if missing:
        fail(f"missing required column(s): {', '.join(missing)}")


from typing import List, Dict

def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        fail(f"file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        validate_required_columns(reader.fieldnames)
        return list(reader)


from typing import Tuple

def validate_rows(rows: List[Dict[str, str]]) -> Tuple[str, str, str]:
    if not rows:
        fail("TSV has no data rows")

    first = rows[0]

    book = first["BOOK"].strip()
    chapter = first["CH"].strip()
    verse = first["VS"].strip()

    if not book:
        fail("BOOK is empty on first row")

    previous_col = 0
    seen_cols: set[int] = set()
    seen_greek_indices: set[str] = set()

    for i, row in enumerate(rows, start=2):
        line_no = i

        for col in REQUIRED_COLUMNS:
            value = row.get(col, "").strip()

            if col not in OPTIONAL_EMPTY_COLUMNS and value == "":
                fail(f"line {line_no}: {col} is empty")

        if row["BOOK"].strip() != book:
            fail(f"line {line_no}: BOOK changes from '{book}' to '{row['BOOK'].strip()}'")

        if row["CH"].strip() != chapter:
            fail(f"line {line_no}: CH changes from '{chapter}' to '{row['CH'].strip()}'")

        if row["VS"].strip() != verse:
            fail(f"line {line_no}: VS changes from '{verse}' to '{row['VS'].strip()}'")

        col_num = parse_int(row["COL"], "COL", line_no)

        if col_num in seen_cols:
            fail(f"line {line_no}: duplicate COL {col_num}")

        if col_num != previous_col + 1:
            fail(f"line {line_no}: COL must be sequential; expected {previous_col + 1}, got {col_num}")

        previous_col = col_num
        seen_cols.add(col_num)

        nbla_indices = split_indices(row["NBLA_IDX"])
        greek_indices = split_indices(row["GREEK_IDX"])

        if not nbla_indices:
            fail(f"line {line_no}: NBLA_IDX is empty or '-'")

        if not row["NBLA_TEXT"].strip():
            fail(f"line {line_no}: NBLA_TEXT is empty")

        if not greek_indices and row["GREEK_TEXT"].strip() not in {"", "-"}:
            fail(f"line {line_no}: GREEK_TEXT exists but GREEK_IDX is empty")

        if greek_indices and row["GREEK_TEXT"].strip() in {"", "-"}:
            fail(f"line {line_no}: GREEK_IDX exists but GREEK_TEXT is empty")

        if greek_indices and not row["LEMMA"].strip():
            fail(f"line {line_no}: Greek column requires LEMMA")

        if greek_indices and not row["RMAC"].strip():
            fail(f"line {line_no}: Greek column requires RMAC")

        for g_idx in greek_indices:
            if g_idx in seen_greek_indices:
                fail(f"line {line_no}: Greek index {g_idx} reused")

            seen_greek_indices.add(g_idx)

    return book, chapter, verse


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python3 scripts/validate_interlinear_tsv.py data/alignments/filemon/1/1.tsv")
        sys.exit(2)

    path = Path(sys.argv[1])
    rows = read_rows(path)
    book, chapter, verse = validate_rows(rows)

    print(f"PASS {book} {chapter}:{verse}")


if __name__ == "__main__":
    main()