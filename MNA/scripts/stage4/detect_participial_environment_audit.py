#!/usr/bin/env python3
"""
MNA Stage 4 — participial environment audit.

PURPOSE
- Read Stage 3 anchor skeleton rows.
- Read MorphGNT source tokens for local context.
- Surface finite predicate anchors near real MorphGNT participles.

IMPORTANT
This script is AUDIT ONLY.
It is NOT an approved Stage 4 eliminator.

All output rows are quarantined review environments only.
Participial proximity is NOT dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-participial-environment-audit-v3-correct-participle-detection"

BOOK_CODES = {
    "mateo": "01", "marcos": "02", "lucas": "03", "juan": "04",
    "hechos": "05", "romanos": "06", "1corintios": "07",
    "2corintios": "08", "galatas": "09", "efesios": "10",
    "filipenses": "11", "colosenses": "12", "1tesalonicenses": "13",
    "2tesalonicenses": "14", "1timoteo": "15", "2timoteo": "16",
    "tito": "17", "filemon": "18", "hebreos": "19",
    "santiago": "20", "1pedro": "21", "2pedro": "22",
    "1juan": "23", "2juan": "24", "3juan": "25",
    "judas": "26", "apocalipsis": "27",
}


@dataclass(frozen=True)
class SourceToken:
    source_line_number: int
    ref_code: str
    chapter: int
    verse: int
    token_index_in_verse: int
    pos: str
    parsing: str
    greek: str
    greek_clean: str
    lemma: str
    lemma_clean: str


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def clean_surface(value: str) -> str:
    return re.sub(
        r"^[^\w\u0370-\u03ff\u1f00-\u1fff]+|[^\w\u0370-\u03ff\u1f00-\u1fff]+$",
        "",
        value,
    )


def resolve_source(mna_root: Path, book: str, explicit_source: Optional[str]) -> Path:
    if explicit_source:
        path = Path(explicit_source)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Explicit source file not found: {path}")
        return path

    morph_dir = mna_root / "SOURCES" / "MorphGNT"
    for candidate in [
        morph_dir / f"{book}-morphgnt.txt",
        morph_dir / f"{book}.txt",
    ]:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError("No MorphGNT source file found.")


def parse_ref(ref_code: str, expected_book_code: str) -> Optional[tuple[int, int]]:
    digits = re.sub(r"\D", "", ref_code)
    if len(digits) < 6 or not digits.startswith(expected_book_code):
        return None
    return int(digits[-4:-2]), int(digits[-2:])


def load_source_tokens(path: Path, expected_book_code: str) -> dict[tuple[int, int], list[SourceToken]]:
    verse_counts: dict[tuple[int, int], int] = {}
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for source_line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue

            parts = stripped.split()
            if len(parts) < 5:
                continue

            parsed = parse_ref(parts[0], expected_book_code)
            if parsed is None:
                continue

            chapter, verse = parsed
            key = (chapter, verse)
            verse_counts[key] = verse_counts.get(key, 0) + 1

            greek = parts[3]
            lemma = parts[-1]

            tokens_by_ref.setdefault(key, []).append(
                SourceToken(
                    source_line_number=source_line_number,
                    ref_code=parts[0],
                    chapter=chapter,
                    verse=verse,
                    token_index_in_verse=verse_counts[key],
                    pos=parts[1],
                    parsing=parts[2],
                    greek=greek,
                    greek_clean=clean_surface(greek),
                    lemma=lemma,
                    lemma_clean=clean_surface(lemma),
                )
            )

    return tokens_by_ref


def load_anchor_skeleton(path: Path):
    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue

            obj = json.loads(stripped)

            if obj.get("record_type") == "metadata":
                metadata = obj
            elif obj.get("record_type") == "anchor_skeleton_row":
                rows.append(obj)

    return metadata, rows


def is_participle_token(token: SourceToken) -> bool:
    # Real MorphGNT participle detection.
    # Examples:
    # V-PPPNSM
    # V-PAPNSM
    # V-RPPASM
    #       ^
    # parsing[3] == P

    if not token.pos.startswith("V"):
        return False

    parsing = token.parsing.strip()

    if len(parsing) < 4:
        return False

    return parsing[3] == "P"


def nearest_participle_environment(row, tokens_by_ref, window):
    chapter = int(row["chapter"])
    verse = int(row["verse"])
    anchor_index = int(row["token_index_in_verse"])

    tokens = tokens_by_ref.get((chapter, verse), [])

    participles = [
        tok
        for tok in tokens
        if is_participle_token(tok)
        and tok.token_index_in_verse != anchor_index
        and abs(tok.token_index_in_verse - anchor_index) <= window
    ]

    if not participles:
        return None

    nearest = min(
        participles,
        key=lambda tok: abs(tok.token_index_in_verse - anchor_index),
    )

    if nearest.token_index_in_verse < anchor_index:
        status = "PARTICIPLE_BEFORE_FINITE_REVIEW_ONLY"
    else:
        status = "PARTICIPLE_AFTER_FINITE_REVIEW_ONLY"

    return nearest, status


def build_row(row, participle, status):
    return {
        "record_type": "participial_environment_audit_row",
        "audit_status": status,
        "approved_for_official_elimination": "NO",
        "official_stage4_classification_changed": "NO",
        "predicate_anchor_id": row["predicate_anchor_id"],
        "book": row["book"],
        "chapter": row["chapter"],
        "verse": row["verse"],
        "reference": row["reference"],
        "anchor_greek_surface": row["greek_surface"],
        "participle_greek_surface": participle.greek,
        "participle_parsing": participle.parsing,
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("book")
    parser.add_argument("--source")
    parser.add_argument("--window", type=int, default=6)
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()

        skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        morphgnt_path = resolve_source(root, book, args.source)
        output_path = root / "audits" / "stage4" / "participial-environment-audit" / f"{book}.jsonl"

        _, rows = load_anchor_skeleton(skeleton_path)

        tokens_by_ref = load_source_tokens(morphgnt_path, BOOK_CODES[book])

        audit_rows = []

        for row in rows:
            env = nearest_participle_environment(row, tokens_by_ref, args.window)
            if env is None:
                continue

            participle, status = env
            audit_rows.append(build_row(row, participle, status))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "record_type": "metadata",
            "stage": "Stage 4 — Participial Environment Audit",
            "version": VERSION,
            "book": book,
            "anchors_inspected": len(rows),
            "participial_environment_rows_found": len(audit_rows),
            "approved_for_official_elimination": "NO",
            "official_stage4_classification_changed": "NO",
        }

        with output_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")

            for row in audit_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        print("MNA Stage 4 — Participial Environment Audit")
        print(f"BOOK: {book}")
        print(f"ANCHOR SKELETON: {skeleton_path}")
        print(f"MORPHGNT SOURCE: {morphgnt_path}")
        print(f"OUTPUT: {output_path}")
        print(f"ANCHORS INSPECTED: {len(rows)}")
        print(f"PARTICIPIAL ENVIRONMENT ROWS FOUND: {len(audit_rows)}")
        print("APPROVED FOR OFFICIAL ELIMINATION: NO")
        print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
        print()
        print("VISIBLE OUTPUT PREVIEW:")

        for idx, row in enumerate(audit_rows[:args.preview_lines], start=1):
            print(
                f"{idx:>4}. "
                f"{row['predicate_anchor_id']} | "
                f"{row['reference']} | "
                f"anchor={row['anchor_greek_surface']} | "
                f"participle={row['participle_greek_surface']} | "
                f"{row['audit_status']}"
            )

        remaining = len(audit_rows) - min(len(audit_rows), args.preview_lines)
        if remaining:
            print(f"... {remaining} more participial environment audit rows written")

        return 0

    except Exception as exc:
        print("MNA Stage 4 participial environment audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
