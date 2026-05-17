#!/usr/bin/env python3
"""
MNA Stage 4 — Local Clause Span Audit

PURPOSE
- Estimate local clause spans around predicate anchors conservatively.
- Use MorphGNT as the full Greek token stream.
- Use anchor-skeleton only to recover predicate anchor coordinates.
- Use predicate-completeness as the authoritative predicate-anchor list.

IMPORTANT
This script does NOT:
- prove independent clauses,
- create the trunk,
- create [S],
- create [M],
- create labels,
- create sections.

This is an audit-only reconstruction layer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-local-clause-span-audit-v4-morphgnt-token-stream"

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

FINITE_MOOD_CODES = {"I", "S", "O", "M"}


@dataclass(frozen=True)
class Token:
    chapter: int
    verse: int
    token_index_in_verse: int
    pos: str
    parsing: str
    greek: str
    lemma: str


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
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
            else:
                rows.append(obj)
    return metadata, rows


def parse_ref(ref_code: str, expected_book_code: str) -> Optional[tuple[int, int]]:
    digits = re.sub(r"\D", "", ref_code)
    if len(digits) < 6 or not digits.startswith(expected_book_code):
        return None
    return int(digits[-4:-2]), int(digits[-2:])


def resolve_morphgnt_source(root: Path, book: str, explicit_source: Optional[str]) -> Path:
    if explicit_source:
        path = Path(explicit_source)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Explicit MorphGNT source not found: {path}")
        return path

    morph_dir = root / "SOURCES" / "MorphGNT"
    candidates = [
        morph_dir / f"{book}-morphgnt.txt",
        morph_dir / f"{book}.txt",
        morph_dir / f"{book}.md",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("No MorphGNT source file found. Tried: " + ", ".join(str(p) for p in candidates))


def load_morphgnt_tokens(path: Path, expected_book_code: str) -> dict[tuple[int, int], list[Token]]:
    verse_counts: dict[tuple[int, int], int] = {}
    by_verse: dict[tuple[int, int], list[Token]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
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
            by_verse.setdefault(key, []).append(
                Token(
                    chapter=chapter,
                    verse=verse,
                    token_index_in_verse=verse_counts[key],
                    pos=parts[1],
                    parsing=parts[2],
                    greek=parts[3],
                    lemma=parts[-1],
                )
            )
    return by_verse


def is_finite_token(token: Token) -> bool:
    if not token.pos.startswith("V"):
        return False
    parsing = token.parsing.strip()
    if len(parsing) < 4:
        return False
    return parsing[3] in FINITE_MOOD_CODES


def build_anchor_coord_lookup(anchor_rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("predicate_anchor_id")): row for row in anchor_rows}


def estimate_span(anchor_token_index: int, verse_tokens: list[Token]) -> tuple[int, int]:
    anchor_pos = None
    for idx, token in enumerate(verse_tokens):
        if token.token_index_in_verse == anchor_token_index:
            anchor_pos = idx
            break
    if anchor_pos is None:
        raise ValueError(f"Anchor token index {anchor_token_index} not found in verse token stream")

    left = anchor_pos
    right = anchor_pos

    idx = anchor_pos - 1
    while idx >= 0:
        if is_finite_token(verse_tokens[idx]):
            break
        left = idx
        idx -= 1

    idx = anchor_pos + 1
    while idx < len(verse_tokens):
        if is_finite_token(verse_tokens[idx]):
            break
        right = idx
        idx += 1

    return left, right


def span_text(tokens: list[Token], left: int, right: int) -> str:
    return " ".join(token.greek for token in tokens[left:right + 1])


def build_row(predicate_row: dict, anchor_row: dict, tokens: list[Token], left: int, right: int) -> dict:
    return {
        "record_type": "local_clause_span_audit_row",
        "predicate_anchor_id": predicate_row.get("predicate_anchor_id"),
        "book": predicate_row.get("book"),
        "chapter": predicate_row.get("chapter"),
        "verse": predicate_row.get("verse"),
        "reference": predicate_row.get("reference"),
        "anchor_order": predicate_row.get("anchor_order"),
        "anchor_token_index_in_verse": anchor_row.get("token_index_in_verse"),
        "anchor_greek_surface": predicate_row.get("greek_surface"),
        "estimated_clause_span": span_text(tokens, left, right),
        "span_left_token_index": tokens[left].token_index_in_verse,
        "span_right_token_index": tokens[right].token_index_in_verse,
        "span_left_greek": tokens[left].greek,
        "span_right_greek": tokens[right].greek,
        "span_method": "morphgnt_full_token_stream_v4_stop_at_neighbor_finite",
        "official_stage4_classification_changed": "NO",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit local clause spans using MorphGNT token stream.")
    parser.add_argument("book")
    parser.add_argument("--source", help="Explicit MorphGNT source path")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        predicate_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
        skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        morphgnt_path = resolve_morphgnt_source(root, book, args.source)
        output_path = root / "audits" / "stage4" / "local-clause-span-audit" / f"{book}.jsonl"

        _predicate_metadata, predicate_rows = load_jsonl(predicate_path)
        _skeleton_metadata, skeleton_rows = load_jsonl(skeleton_path)
        anchor_lookup = build_anchor_coord_lookup(skeleton_rows)
        tokens_by_verse = load_morphgnt_tokens(morphgnt_path, BOOK_CODES[book])

        audit_rows = []
        missing_anchor_coordinates = 0
        missing_verse_tokens = 0

        for predicate_row in predicate_rows:
            anchor_id = str(predicate_row.get("predicate_anchor_id"))
            anchor_row = anchor_lookup.get(anchor_id)
            if not anchor_row:
                missing_anchor_coordinates += 1
                continue

            key = (int(predicate_row.get("chapter")), int(predicate_row.get("verse")))
            tokens = tokens_by_verse.get(key, [])
            if not tokens:
                missing_verse_tokens += 1
                continue

            anchor_token_index = int(anchor_row.get("token_index_in_verse"))
            left, right = estimate_span(anchor_token_index, tokens)
            audit_rows.append(build_row(predicate_row, anchor_row, tokens, left, right))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "record_type": "metadata",
            "stage": "Stage 4 — Local Clause Span Audit",
            "version": VERSION,
            "book": book,
            "predicate_dataset": str(predicate_path.relative_to(root)),
            "anchor_skeleton_dataset": str(skeleton_path.relative_to(root)),
            "morphgnt_source": str(morphgnt_path.relative_to(root)),
            "rows_inspected": len(predicate_rows),
            "rows_written": len(audit_rows),
            "missing_anchor_coordinates": missing_anchor_coordinates,
            "missing_verse_tokens": missing_verse_tokens,
            "span_method": "morphgnt_full_token_stream_v4_stop_at_neighbor_finite",
            "official_stage4_classification_changed": "NO",
        }

        with output_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
            for row in audit_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        print("MNA Stage 4 — Local Clause Span Audit")
        print(f"BOOK: {book}")
        print(f"PREDICATE DATASET: {predicate_path}")
        print(f"ANCHOR SKELETON: {skeleton_path}")
        print(f"MORPHGNT SOURCE: {morphgnt_path}")
        print(f"OUTPUT: {output_path}")
        print(f"ROWS INSPECTED: {len(predicate_rows)}")
        print(f"ROWS WRITTEN: {len(audit_rows)}")
        print(f"MISSING ANCHOR COORDINATES: {missing_anchor_coordinates}")
        print(f"MISSING VERSE TOKENS: {missing_verse_tokens}")
        print("SPAN METHOD: morphgnt_full_token_stream_v4_stop_at_neighbor_finite")
        print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
        print()
        print("VISIBLE OUTPUT PREVIEW:")
        for idx, row in enumerate(audit_rows[: args.preview_lines], start=1):
            print(
                f"{idx:>4}. {row['predicate_anchor_id']} | {row['reference']} | "
                f"anchor={row['anchor_greek_surface']} | span={row['estimated_clause_span']}"
            )

        return 0
    except Exception as exc:
        print("MNA Stage 4 local clause span audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
