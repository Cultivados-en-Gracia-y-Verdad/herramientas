#!/usr/bin/env python3
"""
MNA Stage 4 — eliminated independent candidate renderer.

PURPOSE
- Read datasets/independent-clause-candidates/<book>.jsonl.
- Print rows marked NO.
- Optionally filter by dependency_candidate_sources.
- Show local Greek context for audit.

IMPORTANT
This script does NOT classify anything.
This script does NOT modify datasets.
This script does NOT create trunk, [S], [M], connectors, labels, units, or titles.

It is only a diagnostic/audit renderer to check false eliminations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-eliminated-independent-candidate-renderer-v1"

BOOK_CODES = {
    "mateo": "01",
    "marcos": "02",
    "lucas": "03",
    "juan": "04",
    "hechos": "05",
    "romanos": "06",
    "1corintios": "07",
    "2corintios": "08",
    "galatas": "09",
    "efesios": "10",
    "filipenses": "11",
    "colosenses": "12",
    "1tesalonicenses": "13",
    "2tesalonicenses": "14",
    "1timoteo": "15",
    "2timoteo": "16",
    "tito": "17",
    "filemon": "18",
    "hebreos": "19",
    "santiago": "20",
    "1pedro": "21",
    "2pedro": "22",
    "1juan": "23",
    "2juan": "24",
    "3juan": "25",
    "judas": "26",
    "apocalipsis": "27",
}

NO_STATUS = "NO"


@dataclass(frozen=True)
class SourceToken:
    chapter: int
    verse: int
    token_index_in_verse: int
    pos: str
    parsing: str
    greek: str
    lemma: str


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_morphgnt_dir(mna_root: Path) -> Path:
    return mna_root / "SOURCES" / "MorphGNT"


def candidate_sources(mna_root: Path, book: str) -> list[Path]:
    morph_dir = canonical_morphgnt_dir(mna_root)
    return [
        morph_dir / f"{book}.txt",
        morph_dir / f"{book}.md",
        morph_dir / f"{book}-morphgnt.txt",
        morph_dir / f"{book}-morphgnt.md",
        morph_dir / "morphgnt.txt",
        morph_dir / "MorphGNT.txt",
    ]


def resolve_source(mna_root: Path, book: str, explicit_source: Optional[str]) -> Optional[Path]:
    if explicit_source:
        path = Path(explicit_source)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Explicit source file not found: {path}")
        return path

    for path in candidate_sources(mna_root, book):
        if path.is_file():
            return path

    return None


def parse_ref(ref_code: str, expected_book_code: str) -> Optional[tuple[int, int]]:
    digits = re.sub(r"\D", "", ref_code)
    if len(digits) < 6:
        return None
    if not digits.startswith(expected_book_code):
        return None
    return int(digits[-4:-2]), int(digits[-2:])


def load_source_tokens(path: Path, expected_book_code: str) -> dict[tuple[int, int], list[SourceToken]]:
    verse_counts: dict[tuple[int, int], int] = {}
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split()
            if len(parts) < 5:
                continue

            ref_code = parts[0]
            parsed = parse_ref(ref_code, expected_book_code)
            if parsed is None:
                continue

            chapter, verse = parsed
            key = (chapter, verse)
            verse_counts[key] = verse_counts.get(key, 0) + 1

            token = SourceToken(
                chapter=chapter,
                verse=verse,
                token_index_in_verse=verse_counts[key],
                pos=parts[1],
                parsing=parts[2],
                greek=parts[3],
                lemma=parts[-1],
            )
            tokens_by_ref.setdefault(key, []).append(token)

    return tokens_by_ref


def load_candidate_dataset(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Independent-clause-candidate dataset not found: {path}")

    metadata = None
    rows = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            elif obj.get("record_type") == "independent_clause_candidate_row":
                rows.append(obj)
            else:
                raise ValueError(
                    f"Unexpected record_type at {path}:{line_number}: {obj.get('record_type')}"
                )

    if metadata is None:
        raise ValueError("Independent-clause-candidate dataset missing metadata row.")

    return metadata, rows


def token_index_from_anchor_id(predicate_anchor_id: str) -> Optional[int]:
    match = re.search(r"-pa-(\d+)-\d+$", predicate_anchor_id)
    if not match:
        return None
    return int(match.group(1))


def context_for_row(
    row: dict[str, object],
    tokens_by_ref: Optional[dict[tuple[int, int], list[SourceToken]]],
    before: int,
    after: int,
) -> str:
    if tokens_by_ref is None:
        return ""

    chapter = int(row["chapter"])
    verse = int(row["verse"])
    anchor_index = token_index_from_anchor_id(str(row["predicate_anchor_id"]))
    if anchor_index is None:
        return ""

    tokens = tokens_by_ref.get((chapter, verse), [])
    start = max(1, anchor_index - before)
    end = anchor_index + after

    parts = []
    for token in tokens:
        if start <= token.token_index_in_verse <= end:
            marker = "{ANCHOR}" if token.token_index_in_verse == anchor_index else ""
            parts.append(f"{token.token_index_in_verse}:{token.greek}{marker}")

    return " ".join(parts)


def row_matches_source(row: dict[str, object], source_filter: Optional[str]) -> bool:
    if not source_filter:
        return True
    sources = row.get("dependency_candidate_sources")
    if not isinstance(sources, list):
        return False
    return source_filter in sources


def render_rows(
    rows: list[dict[str, object]],
    tokens_by_ref: Optional[dict[tuple[int, int], list[SourceToken]]],
    start: int,
    limit: int,
    before: int,
    after: int,
) -> None:
    selected = rows[start - 1 : start - 1 + limit]

    for display_index, row in enumerate(selected, start=start):
        sources = ",".join(row.get("dependency_candidate_sources", []))
        print(
            f"{display_index:>4}. {row['predicate_anchor_id']} | "
            f"{row['reference']} | {row['greek_surface']} | "
            f"mood={row['mood']} | morph={row['morphology']} | sources={sources}"
        )

        context = context_for_row(row, tokens_by_ref, before, after)
        if context:
            print(f"     CONTEXT: {context}")

        print()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render eliminated Stage 4 independent-clause candidates for audit."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source-filter", help="Only show rows eliminated by this audit source")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--before", type=int, default=8)
    parser.add_argument("--after", type=int, default=8)
    parser.add_argument("--no-context", action="store_true")
    parser.add_argument("--source", help="Explicit MorphGNT source path")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        dataset_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"
        metadata, rows = load_candidate_dataset(dataset_path)

        eliminated = [
            row
            for row in rows
            if row.get("independent_clause_candidate") == NO_STATUS
            and row_matches_source(row, args.source_filter)
        ]

        tokens_by_ref = None
        if not args.no_context:
            expected_book_code = BOOK_CODES.get(book)
            if expected_book_code is None:
                raise ValueError(f"Unsupported book slug: {book}")
            source_path = resolve_source(root, book, args.source)
            if source_path is not None:
                tokens_by_ref = load_source_tokens(source_path, expected_book_code)

        print("MNA Stage 4 — Eliminated Independent Candidate Audit Render")
        print(f"BOOK: {book}")
        print(f"VERSION: {VERSION}")
        print(f"DATASET: {dataset_path}")
        print(f"TOTAL ROWS: {len(rows)}")
        print(f"ELIMINATED_MATCHING_ROWS: {len(eliminated)}")
        print(f"SOURCE_FILTER: {args.source_filter or '-'}")
        print(f"RENDER START: {args.start}")
        print(f"RENDER LIMIT: {args.limit}")
        print()

        render_rows(
            eliminated,
            tokens_by_ref,
            max(1, args.start),
            args.limit,
            args.before,
            args.after,
        )

        remaining = len(eliminated) - (max(1, args.start) - 1 + args.limit)
        if remaining > 0:
            print(f"... {remaining} more eliminated candidates not shown")

        return 0
    except Exception as exc:
        print("MNA Stage 4 eliminated independent candidate render FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
