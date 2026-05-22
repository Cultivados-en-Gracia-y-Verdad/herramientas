#!/usr/bin/env python3
"""
MNA Stage 4 — relative dependency candidate detector.

PURPOSE
- Read Stage 3 anchor skeleton rows.
- Read MorphGNT source tokens for local context.
- Detect finite predicate anchors that appear in visible relative environments.

IMPORTANT
This script is an AUDIT detector, not the official classifier.

It does NOT change:
- Stage 1,
- Stage 2,
- Stage 3,
- predicate-completeness classifications,
- trunk,
- [S],
- [M].

It writes candidate evidence only.

CURRENT DETECTION FAMILY
PC-DEP-CAND-REL-001:
- a MorphGNT relative token POS=RR appears in a local pre-anchor window,
- the finite predicate anchor follows that relative token in the same verse,
- no intervening finite predicate appears between the RR token and the anchor,
- the result is recorded as a dependency candidate for manual audit.

This is strict and intentionally conservative.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-relative-dependency-candidates-v2"

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
    source_line_number: int
    ref_code: str
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
        for source_line_number, raw in enumerate(handle, start=1):
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
                source_line_number=source_line_number,
                ref_code=ref_code,
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


def load_anchor_skeleton(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Anchor skeleton dataset not found: {path}")

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
            elif obj.get("record_type") == "anchor_skeleton_row":
                rows.append(obj)
            else:
                raise ValueError(
                    f"Unexpected record_type at {path}:{line_number}: {obj.get('record_type')}"
                )

    if metadata is None:
        raise ValueError("Anchor skeleton dataset missing metadata row.")

    return metadata, rows


def is_finite_source_token(token: SourceToken) -> bool:
    if not token.pos.startswith("V"):
        return False
    combined = f"{token.pos}{token.parsing}"
    return bool(re.search(r"[ISODM]-?[123][SP]|[123][A-Z][A-Z][ISODM]-[SP]", combined))


def is_relative_token(token: SourceToken) -> bool:
    return token.pos == "RR"


def find_local_relative_trigger(
    row: dict[str, object],
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]],
    window: int,
) -> Optional[SourceToken]:
    chapter = int(row["chapter"])
    verse = int(row["verse"])
    anchor_index = int(row["token_index_in_verse"])
    tokens = tokens_by_ref.get((chapter, verse), [])

    previous_tokens = [tok for tok in tokens if tok.token_index_in_verse < anchor_index]
    local_tokens = previous_tokens[-window:]

    for candidate in reversed(local_tokens):
        if not is_relative_token(candidate):
            continue

        intervening = [
            tok
            for tok in tokens
            if candidate.token_index_in_verse < tok.token_index_in_verse < anchor_index
        ]
        if any(is_finite_source_token(tok) for tok in intervening):
            continue

        return candidate

    return None


def build_candidate_record(row: dict[str, object], relative: SourceToken) -> dict[str, object]:
    return {
        "record_type": "relative_dependency_candidate",
        "candidate_status": "DEPENDENCY_CANDIDATE_FOR_MANUAL_AUDIT",
        "rule_family": "PC-DEP-CAND-REL",
        "rule_id": "PC-DEP-CAND-REL-001",
        "reason": "Finite predicate anchor follows a local MorphGNT relative token POS=RR with no intervening finite predicate in the same verse.",
        "official_stage4_classification_changed": "NO",
        "book": row["book"],
        "chapter": row["chapter"],
        "verse": row["verse"],
        "reference": row["reference"],
        "predicate_anchor_id": row["predicate_anchor_id"],
        "anchor_order": row["anchor_order"],
        "anchor_token_index_in_verse": row["token_index_in_verse"],
        "anchor_greek_surface": row["greek_surface"],
        "anchor_lemma": row["lemma"],
        "anchor_morphology": row["morphology"],
        "anchor_mood": row["mood"],
        "relative_token_index_in_verse": relative.token_index_in_verse,
        "relative_greek_surface": relative.greek,
        "relative_lemma": relative.lemma,
        "relative_pos": relative.pos,
        "relative_parsing": relative.parsing,
    }


def detect_candidates(
    book: str,
    skeleton_path: Path,
    morphgnt_path: Path,
    output_path: Path,
    mna_root: Path,
    window: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    skeleton_metadata, rows = load_anchor_skeleton(skeleton_path)

    if str(skeleton_metadata.get("book")) != book:
        raise ValueError(
            f"Requested book '{book}' but anchor skeleton dataset is '{skeleton_metadata.get('book')}'."
        )

    expected_book_code = BOOK_CODES.get(book)
    if expected_book_code is None:
        raise ValueError(f"Unsupported book slug: {book}")

    tokens_by_ref = load_source_tokens(morphgnt_path, expected_book_code)
    candidates = []

    for row in rows:
        relative = find_local_relative_trigger(row, tokens_by_ref, window)
        if relative is not None:
            candidates.append(build_candidate_record(row, relative))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Relative Dependency Candidate Audit",
        "producer_script": "scripts/stage4/detect_relative_dependency_candidates.py",
        "producer_command": f"python3 scripts/stage4/detect_relative_dependency_candidates.py {book}",
        "version": VERSION,
        "book": book,
        "anchor_skeleton_dataset": str(skeleton_path.relative_to(mna_root)),
        "morphgnt_source": str(morphgnt_path.relative_to(mna_root)),
        "window_tokens_before_anchor": window,
        "relative_detection_rule": "MorphGNT POS=RR only",
        "anchors_inspected": len(rows),
        "dependency_candidates_found": len(candidates),
        "official_stage4_classification_changed": "NO",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for candidate in candidates:
            handle.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n")

    return metadata, candidates


def print_visible_output(
    book: str,
    skeleton_path: Path,
    morphgnt_path: Path,
    output_path: Path,
    metadata: dict[str, object],
    candidates: list[dict[str, object]],
    preview_lines: int,
) -> None:
    print("MNA Stage 4 — Relative Dependency Candidate Detector")
    print(f"BOOK: {book}")
    print(f"ANCHOR SKELETON: {skeleton_path}")
    print(f"MORPHGNT SOURCE: {morphgnt_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ANCHORS INSPECTED: {metadata['anchors_inspected']}")
    print(f"RELATIVE DEPENDENCY CANDIDATES FOUND: {metadata['dependency_candidates_found']}")
    print("RELATIVE DETECTION RULE: MorphGNT POS=RR only")
    print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, candidate in enumerate(candidates[:preview_lines], start=1):
        print(
            f"{idx:>4}. {candidate['predicate_anchor_id']} | "
            f"{candidate['reference']} | "
            f"relative={candidate['relative_greek_surface']} | "
            f"anchor={candidate['anchor_greek_surface']} | "
            f"{candidate['candidate_status']}"
        )

    remaining = len(candidates) - min(len(candidates), preview_lines)
    if remaining:
        print(f"... {remaining} more relative dependency candidates written")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect Stage 4 relative dependency candidates for manual audit."
    )
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source path")
    parser.add_argument("--window", type=int, default=10, help="Number of previous same-verse tokens to inspect")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        morphgnt_path = resolve_source(root, book, args.source)
        output_path = root / "audits" / "stage4" / "relative-dependency-candidates" / f"{book}.jsonl"

        metadata, candidates = detect_candidates(
            book,
            skeleton_path,
            morphgnt_path,
            output_path,
            root,
            args.window,
        )

        print_visible_output(
            book,
            skeleton_path,
            morphgnt_path,
            output_path,
            metadata,
            candidates,
            args.preview_lines,
        )

        return 0
    except Exception as exc:
        print("MNA Stage 4 relative dependency candidate detection FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
