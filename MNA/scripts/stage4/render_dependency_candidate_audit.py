#!/usr/bin/env python3
"""
MNA Stage 4 — dependency candidate audit renderer.

PURPOSE
- Read audit candidates from detect_absolute_dependency_candidates.py.
- Read MorphGNT source tokens.
- Print visible local Greek context for manual review.

IMPORTANT
This script does NOT classify anything.
This script does NOT modify datasets.
This script does NOT create trunk, [S], [M], labels, units, or titles.

It only renders candidate evidence so decisions can be audited one case at a time.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-dependency-candidate-audit-renderer-v1"

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


def resolve_source(mna_root: Path, book: str, explicit_source: Optional[str]) -> Path:
    if explicit_source:
        path = Path(explicit_source)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Explicit source file not found: {path}")
        return path

    tried = candidate_sources(mna_root, book)
    for path in tried:
        if path.is_file():
            return path

    raise FileNotFoundError(
        "No MorphGNT source file found. Tried:\n" + "\n".join(str(p) for p in tried)
    )


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


def load_candidates(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Candidate audit dataset not found: {path}")

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
            elif obj.get("record_type") == "absolute_dependency_candidate":
                rows.append(obj)
            else:
                raise ValueError(f"Unexpected record_type at {path}:{line_number}: {obj.get('record_type')}")

    if metadata is None:
        raise ValueError("Candidate audit dataset missing metadata row.")

    return metadata, rows


def context_tokens(
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]],
    chapter: int,
    verse: int,
    anchor_index: int,
    before: int,
    after: int,
) -> list[SourceToken]:
    tokens = tokens_by_ref.get((chapter, verse), [])
    start = max(1, anchor_index - before)
    end = anchor_index + after
    return [tok for tok in tokens if start <= tok.token_index_in_verse <= end]


def render_candidate(
    number: int,
    candidate: dict[str, object],
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]],
    before: int,
    after: int,
) -> str:
    chapter = int(candidate["chapter"])
    verse = int(candidate["verse"])
    anchor_index = int(candidate["anchor_token_index_in_verse"])
    trigger_index = int(candidate["trigger_token_index_in_verse"])

    tokens = context_tokens(tokens_by_ref, chapter, verse, anchor_index, before, after)

    greek_parts = []
    morph_parts = []

    for tok in tokens:
        greek = tok.greek
        label = ""
        if tok.token_index_in_verse == trigger_index:
            label = "{TRIGGER}"
        if tok.token_index_in_verse == anchor_index:
            label = "{ANCHOR}"
        greek_parts.append(f"{tok.token_index_in_verse}:{greek}{label}")
        morph_parts.append(f"{tok.token_index_in_verse}:{tok.pos} {tok.parsing} {tok.lemma}")

    lines = [
        f"{number:>4}. {candidate['predicate_anchor_id']} | {candidate['reference']}",
        f"     RULE: {candidate['rule_id']}",
        f"     STATUS: {candidate['candidate_status']}",
        f"     TRIGGER: {candidate['trigger_greek_surface']} @ token {trigger_index}",
        f"     ANCHOR: {candidate['anchor_greek_surface']} @ token {anchor_index}",
        f"     GREEK CONTEXT: {' '.join(greek_parts)}",
        f"     MORPH CONTEXT: {' | '.join(morph_parts)}",
        "",
    ]

    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render Stage 4 dependency candidates for manual audit."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source path")
    parser.add_argument("--input", help="Explicit candidate audit JSONL path")
    parser.add_argument("--before", type=int, default=8, help="Context tokens before anchor")
    parser.add_argument("--after", type=int, default=8, help="Context tokens after anchor")
    parser.add_argument("--limit", type=int, default=25, help="Number of candidates to render")
    parser.add_argument("--start", type=int, default=1, help="1-based candidate index to begin rendering")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        expected_book_code = BOOK_CODES.get(book)
        if expected_book_code is None:
            raise ValueError(f"Unsupported book slug: {book}")

        morphgnt_path = resolve_source(root, book, args.source)
        candidate_path = Path(args.input) if args.input else root / "audits" / "stage4" / "absolute-dependency-candidates" / f"{book}.jsonl"
        if not candidate_path.is_absolute():
            candidate_path = (Path.cwd() / candidate_path).resolve()

        metadata, candidates = load_candidates(candidate_path)
        tokens_by_ref = load_source_tokens(morphgnt_path, expected_book_code)

        print("MNA Stage 4 — Dependency Candidate Manual Audit Render")
        print(f"BOOK: {book}")
        print(f"CANDIDATE DATASET: {candidate_path}")
        print(f"MORPHGNT SOURCE: {morphgnt_path}")
        print(f"TOTAL CANDIDATES: {len(candidates)}")
        print(f"RENDER START: {args.start}")
        print(f"RENDER LIMIT: {args.limit}")
        print()

        start_index = max(1, args.start)
        selected = candidates[start_index - 1 : start_index - 1 + args.limit]

        for offset, candidate in enumerate(selected, start=start_index):
            print(render_candidate(offset, candidate, tokens_by_ref, args.before, args.after))

        return 0
    except Exception as exc:
        print("MNA Stage 4 dependency candidate audit render FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
