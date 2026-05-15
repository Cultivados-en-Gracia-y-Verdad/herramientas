#!/usr/bin/env python3
"""
MNA Stage 1 — finite verb extraction from MorphGNT.

This script does exactly one thing:
- read MorphGNT-style source lines,
- mechanically extract finite Greek verbs,
- write a deterministic JSONL dataset,
- print visible whole-book output.

It does NOT infer predicates, clauses, subjects, trunk, continuity, movement,
or any downstream structure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

VERSION = "stage1-finite-verbs-v1"

# MorphGNT / SBLGNT numeric NT book codes.
# These are source-reference codes only; they are not interpretation.
BOOK_CODES = {
    "mateo": "40",
    "marcos": "41",
    "lucas": "42",
    "juan": "43",
    "hechos": "44",
    "romanos": "45",
    "1corintios": "46",
    "2corintios": "47",
    "galatas": "48",
    "efesios": "49",
    "filipenses": "50",
    "colosenses": "51",
    "1tesalonicenses": "52",
    "2tesalonicenses": "53",
    "1timoteo": "54",
    "2timoteo": "55",
    "tito": "56",
    "filemon": "57",
    "hebreos": "58",
    "santiago": "59",
    "1pedro": "60",
    "2pedro": "61",
    "1juan": "62",
    "2juan": "63",
    "3juan": "64",
    "judas": "65",
    "apocalipsis": "66",
}

FINITE_MOODS = {
    "I": "indicative",
    "S": "subjunctive",
    "O": "optative",
    "M": "imperative",
}

PERSON_LABELS = {"1": "first", "2": "second", "3": "third"}
NUMBER_LABELS = {"S": "singular", "P": "plural"}


@dataclass(frozen=True)
class MorphLine:
    source_line_number: int
    raw: str
    ref_code: str
    chapter: int
    verse: int
    pos: str
    parsing: str
    greek: str
    lemma: str
    token_index_in_verse: int


def repo_root_from_script() -> Path:
    # MNA/scripts/build_finite_verbs.py -> MNA
    return Path(__file__).resolve().parents[1]


def candidate_sources(mna_root: Path, book: str) -> list[Path]:
    return [
        mna_root / "sources" / "morphgnt" / f"{book}.txt",
        mna_root / "sources" / "MorphGNT" / f"{book}.txt",
        mna_root / "data" / "morphgnt" / f"{book}.txt",
        mna_root / "data" / "MorphGNT" / f"{book}.txt",
        mna_root / "data" / "morphgnt.txt",
        mna_root / "data" / "MorphGNT.txt",
        mna_root / "MNA_CHATPGT_FAIL" / "data" / "morphgnt" / f"{book}.txt",
        mna_root / "MNA_CHATPGT_FAIL" / "data" / "MorphGNT" / f"{book}.txt",
        mna_root / "MNA_CHATPGT_FAIL" / "data" / "morphgnt.txt",
        mna_root / "MNA_CHATPGT_FAIL" / "data" / "MorphGNT.txt",
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

    lines = ["No MorphGNT source file found.", "Tried:"]
    lines.extend(f"- {p}" for p in tried)
    raise FileNotFoundError("\n".join(lines))


def parse_ref(ref_code: str, expected_book_code: str) -> Optional[tuple[int, int]]:
    digits = re.sub(r"\D", "", ref_code)
    if len(digits) < 6:
        return None
    if not digits.startswith(expected_book_code):
        return None
    chapter = int(digits[-4:-2])
    verse = int(digits[-2:])
    return chapter, verse


def parse_morph_line(line: str, line_number: int, expected_book_code: str, verse_counts: dict[tuple[int, int], int]) -> Optional[MorphLine]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    parts = stripped.split()
    if len(parts) < 5:
        return None

    ref_code = parts[0]
    parsed_ref = parse_ref(ref_code, expected_book_code)
    if parsed_ref is None:
        return None

    chapter, verse = parsed_ref
    pos = parts[1]
    parsing = parts[2]
    greek = parts[3]
    lemma = parts[-1]

    key = (chapter, verse)
    verse_counts[key] = verse_counts.get(key, 0) + 1

    return MorphLine(
        source_line_number=line_number,
        raw=stripped,
        ref_code=ref_code,
        chapter=chapter,
        verse=verse,
        pos=pos,
        parsing=parsing,
        greek=greek,
        lemma=lemma,
        token_index_in_verse=verse_counts[key],
    )


def finite_features(pos: str, parsing: str) -> Optional[dict[str, str]]:
    """Return mechanical finite-verb features, or None.

    Supported source shapes:
    - RMAC-like combined: V-PAI-3S
    - MorphGNT common: pos=V-, parsing=3PAI-S--
    - MorphGNT alternate: pos=V-, parsing=PAI-3S--
    """
    if not pos.startswith("V"):
        return None

    combined = f"{pos}{parsing}"

    patterns = [
        # V-PAI-3S / V-AAI-3P etc.
        (re.compile(r"^V-([A-Z])([A-Z])([ISOMNP])-([123])([SP])"), "rm_label"),
        # V-3PAI-S-- / V-1AAI-P-- etc.
        (re.compile(r"^V-([123])([A-Z])([A-Z])([ISOMNP])-([SP])"), "morphgnt_person_first"),
        # V-PAI-3S-- / V-AAI-3P-- etc.
        (re.compile(r"^V-([A-Z])([A-Z])([ISOMNP])-?([123])([SP])"), "morphgnt_person_after_mood"),
    ]

    for regex, shape in patterns:
        match = regex.search(combined)
        if not match:
            continue

        groups = match.groups()
        if shape == "morphgnt_person_first":
            person, tense, voice, mood, number = groups
        else:
            tense, voice, mood, person, number = groups

        if mood not in FINITE_MOODS:
            return None

        return {
            "shape": shape,
            "tense_code": tense,
            "voice_code": voice,
            "mood_code": mood,
            "mood": FINITE_MOODS[mood],
            "person_code": person,
            "person": PERSON_LABELS.get(person, person),
            "number_code": number,
            "number": NUMBER_LABELS.get(number, number),
        }

    return None


def iter_morph_lines(source: Path, book_code: str) -> Iterable[MorphLine]:
    verse_counts: dict[tuple[int, int], int] = {}
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            parsed = parse_morph_line(line, line_number, book_code, verse_counts)
            if parsed is not None:
                yield parsed


def build_dataset(book: str, source: Path, output_path: Path, mna_root: Path) -> tuple[int, int, int]:
    if book not in BOOK_CODES:
        known = ", ".join(sorted(BOOK_CODES))
        raise ValueError(f"Unknown book '{book}'. Known books: {known}")

    book_code = BOOK_CODES[book]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_book_tokens = 0
    total_verb_tokens = 0
    finite_count = 0

    records: list[dict[str, object]] = []

    for morph in iter_morph_lines(source, book_code):
        total_book_tokens += 1
        if morph.pos.startswith("V"):
            total_verb_tokens += 1

        features = finite_features(morph.pos, morph.parsing)
        if features is None:
            continue

        finite_count += 1
        records.append(
            {
                "record_type": "finite_verb",
                "book": book,
                "chapter": morph.chapter,
                "verse": morph.verse,
                "reference": f"{book} {morph.chapter}:{morph.verse}",
                "ref_code": morph.ref_code,
                "token_index_in_verse": morph.token_index_in_verse,
                "source_line_number": morph.source_line_number,
                "greek": morph.greek,
                "lemma": morph.lemma,
                "pos": morph.pos,
                "parsing": morph.parsing,
                "morph_code": f"{morph.pos}{morph.parsing}",
                "finite_detection": features,
            }
        )

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 1 — Finite Verbs",
        "source": str(source.relative_to(mna_root) if source.is_relative_to(mna_root) else source),
        "producer_script": "scripts/build_finite_verbs.py",
        "producer_command": f"python3 scripts/build_finite_verbs.py {book}",
        "generated_at": "DETERMINISTIC-NOT-RUNTIME-STAMPED",
        "version": VERSION,
        "book": book,
        "book_code": book_code,
        "total_book_tokens_seen": total_book_tokens,
        "total_verb_tokens_seen": total_verb_tokens,
        "finite_verbs_extracted": finite_count,
        "rule": "A token is extracted only when MorphGNT POS is verbal and morphology marks mood as indicative, subjunctive, optative, or imperative with person/number.",
        "downstream_claims": "NONE: predicates, clauses, subjects, trunk, continuity, and movement are not produced here.",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    return total_book_tokens, total_verb_tokens, finite_count


def print_visible_output(book: str, source: Path, output_path: Path, total_tokens: int, verb_tokens: int, finite_count: int, preview_lines: int) -> None:
    print("MNA Stage 1 — Finite Verbs")
    print(f"BOOK: {book}")
    print(f"SOURCE: {source}")
    print(f"OUTPUT: {output_path}")
    print(f"TOKENS SEEN: {total_tokens}")
    print(f"VERB TOKENS SEEN: {verb_tokens}")
    print(f"FINITE VERBS EXTRACTED: {finite_count}")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    shown = 0
    with output_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            obj = json.loads(raw)
            if obj.get("record_type") != "finite_verb":
                continue
            shown += 1
            det = obj["finite_detection"]
            print(
                f"{shown:>4}. {obj['reference']} | {obj['greek']} | lemma={obj['lemma']} | "
                f"morph={obj['morph_code']} | {det['person_code']}{det['number_code']} {det['mood']}"
            )
            if shown >= preview_lines:
                break

    if finite_count == 0:
        print("NO FINITE VERBS EXTRACTED — this is a failed Stage 1 output unless the source/book is wrong.")
    elif finite_count > shown:
        print(f"... {finite_count - shown} more finite verbs written to dataset")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build MNA Stage 1 finite verbs dataset from MorphGNT.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios, romanos, filemon")
    parser.add_argument("--source", help="Explicit MorphGNT source file path")
    parser.add_argument("--output", help="Explicit output JSONL path")
    parser.add_argument("--preview-lines", type=int, default=40, help="Number of finite-verb rows to print")
    args = parser.parse_args(argv)

    book = args.book.strip().lower()
    mna_root = repo_root_from_script()

    try:
        source = resolve_source(mna_root, book, args.source)
        output_path = Path(args.output) if args.output else mna_root / "datasets" / "finite-verbs" / f"{book}.jsonl"
        if not output_path.is_absolute():
            output_path = (Path.cwd() / output_path).resolve()

        total_tokens, verb_tokens, finite_count = build_dataset(book, source, output_path, mna_root)
        print_visible_output(book, source, output_path, total_tokens, verb_tokens, finite_count, args.preview_lines)
        return 0 if finite_count > 0 else 2
    except Exception as exc:
        print("MNA Stage 1 — Finite Verbs FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
