#!/usr/bin/env python3
"""
MNA Stage 4 — infinitive-governed environment audit.

PURPOSE
- Inspect narrow infinitive-governed environments.
- Surface possible patterns for later detector design.

IMPORTANT
This script is NOT an approved dependency detector.
It is deliberately audit-only because first-pass output showed that predicates
near governed infinitives may still be independent matrix clauses.

It does NOT change:
- Stage 1,
- Stage 2,
- Stage 3,
- predicate-completeness classifications,
- independent-clause-candidate classifications,
- trunk,
- [S],
- [M].

It writes environment evidence only.
No rows from this script should be merged into official Stage 4 elimination.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VERSION = "stage4-infinitive-governed-environment-audit-v2-quarantined"

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

GOVERNING_LEMMAS = {"δύναμαι", "θέλω", "μέλλω", "δεῖ", "ἄρχομαι"}


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
    tried = [
        morph_dir / f"{book}.txt",
        morph_dir / f"{book}.md",
        morph_dir / f"{book}-morphgnt.txt",
        morph_dir / f"{book}-morphgnt.md",
        morph_dir / "morphgnt.txt",
        morph_dir / "MorphGNT.txt",
    ]
    for path in tried:
        if path.is_file():
            return path
    raise FileNotFoundError("No MorphGNT source file found. Tried:\n" + "\n".join(str(p) for p in tried))


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
                raise ValueError(f"Unexpected record_type at {path}:{line_number}: {obj.get('record_type')}")

    if metadata is None:
        raise ValueError("Anchor skeleton dataset missing metadata row.")
    return metadata, rows


def is_verb(token: SourceToken) -> bool:
    return token.pos.startswith("V")


def is_finite_source_token(token: SourceToken) -> bool:
    if not is_verb(token):
        return False
    combined = f"{token.pos}{token.parsing}"
    return bool(re.search(r"[ISODM]-?[123][SP]|[123][A-Z][A-Z][ISODM]-[SP]", combined))


def is_infinitive_source_token(token: SourceToken) -> bool:
    if not is_verb(token):
        return False
    combined = f"{token.pos}{token.parsing}"
    return "N" in combined and not is_finite_source_token(token)


def is_governing_predicate(token: SourceToken) -> bool:
    return is_finite_source_token(token) and token.lemma_clean in GOVERNING_LEMMAS


def find_environment_near_anchor(
    row: dict[str, object],
    tokens_by_ref: dict[tuple[int, int], list[SourceToken]],
    window: int,
) -> Optional[tuple[SourceToken, SourceToken, str]]:
    chapter = int(row["chapter"])
    verse = int(row["verse"])
    anchor_index = int(row["token_index_in_verse"])
    tokens = tokens_by_ref.get((chapter, verse), [])

    local = [
        tok for tok in tokens
        if anchor_index - window <= tok.token_index_in_verse <= anchor_index + window
    ]

    governors = [tok for tok in local if is_governing_predicate(tok)]
    infinitives = [tok for tok in local if is_infinitive_source_token(tok)]
    if not governors or not infinitives:
        return None

    nearest_governor = min(governors, key=lambda tok: abs(tok.token_index_in_verse - anchor_index))
    nearest_infinitive = min(infinitives, key=lambda tok: abs(tok.token_index_in_verse - anchor_index))

    if nearest_governor.token_index_in_verse < nearest_infinitive.token_index_in_verse < anchor_index:
        risk = "UNSAFE_AFTER_INFINITIVE_NOT_APPROVED_FOR_ELIMINATION"
    elif nearest_governor.token_index_in_verse < anchor_index < nearest_infinitive.token_index_in_verse:
        risk = "BETWEEN_GOVERNOR_AND_INFINITIVE_REVIEW_ONLY"
    else:
        risk = "INF_GOV_ENVIRONMENT_REVIEW_ONLY"

    return nearest_governor, nearest_infinitive, risk


def build_audit_record(row: dict[str, object], governor: SourceToken, infinitive: SourceToken, risk: str) -> dict[str, object]:
    return {
        "record_type": "infinitive_governed_environment_audit_row",
        "audit_status": risk,
        "approved_for_official_elimination": "NO",
        "candidate_status": "NOT_A_DEPENDENCY_CANDIDATE",
        "rule_family": "PC-INF-GOV-AUDIT",
        "rule_id": "PC-INF-GOV-AUDIT-001",
        "reason": "Infinitive-governed environment detected near finite predicate; proximity alone is not sufficient to prove finite predicate dependency.",
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
        "governor_token_index_in_verse": governor.token_index_in_verse,
        "governor_greek_surface": governor.greek,
        "governor_lemma": governor.lemma,
        "infinitive_token_index_in_verse": infinitive.token_index_in_verse,
        "infinitive_greek_surface": infinitive.greek,
        "infinitive_lemma": infinitive.lemma,
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
        "connector_relationship_claim": "NONE",
        "label_claim": "NONE",
        "unit_claim": "NONE",
        "title_claim": "NONE",
    }


def detect_audit_rows(
    book: str,
    skeleton_path: Path,
    morphgnt_path: Path,
    output_path: Path,
    mna_root: Path,
    window: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    skeleton_metadata, rows = load_anchor_skeleton(skeleton_path)
    if str(skeleton_metadata.get("book")) != book:
        raise ValueError(f"Requested book '{book}' but anchor skeleton dataset is '{skeleton_metadata.get('book')}'.")

    expected_book_code = BOOK_CODES.get(book)
    if expected_book_code is None:
        raise ValueError(f"Unsupported book slug: {book}")

    tokens_by_ref = load_source_tokens(morphgnt_path, expected_book_code)
    audit_rows = []

    for row in rows:
        env = find_environment_near_anchor(row, tokens_by_ref, window)
        if env is None:
            continue
        governor, infinitive, risk = env
        audit_rows.append(build_audit_record(row, governor, infinitive, risk))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "record_type": "metadata",
        "stage": "Stage 4 — Infinitive Governed Environment Audit",
        "producer_script": "scripts/stage4/detect_infinitive_governed_dependency_candidates.py",
        "producer_command": f"python3 scripts/stage4/detect_infinitive_governed_dependency_candidates.py {book}",
        "version": VERSION,
        "book": book,
        "anchor_skeleton_dataset": str(skeleton_path.relative_to(mna_root)),
        "morphgnt_source": str(morphgnt_path.relative_to(mna_root)),
        "window_tokens_around_anchor": window,
        "governing_lemmas": sorted(GOVERNING_LEMMAS),
        "anchors_inspected": len(rows),
        "environment_audit_rows_found": len(audit_rows),
        "approved_for_official_elimination": "NO",
        "official_stage4_classification_changed": "NO",
        "trunk_claim": "NONE",
        "subject_marker_claim": "NONE",
        "movement_marker_claim": "NONE",
    }

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
        for audit_row in audit_rows:
            handle.write(json.dumps(audit_row, ensure_ascii=False, sort_keys=True) + "\n")

    return metadata, audit_rows


def print_visible_output(
    book: str,
    skeleton_path: Path,
    morphgnt_path: Path,
    output_path: Path,
    metadata: dict[str, object],
    audit_rows: list[dict[str, object]],
    preview_lines: int,
) -> None:
    print("MNA Stage 4 — Infinitive Governed Environment Audit")
    print(f"BOOK: {book}")
    print(f"ANCHOR SKELETON: {skeleton_path}")
    print(f"MORPHGNT SOURCE: {morphgnt_path}")
    print(f"OUTPUT: {output_path}")
    print(f"ANCHORS INSPECTED: {metadata['anchors_inspected']}")
    print(f"ENVIRONMENT AUDIT ROWS FOUND: {metadata['environment_audit_rows_found']}")
    print("APPROVED FOR OFFICIAL ELIMINATION: NO")
    print("OFFICIAL STAGE 4 CLASSIFICATION CHANGED: NO")
    print()
    print("VISIBLE OUTPUT PREVIEW:")

    for idx, row in enumerate(audit_rows[:preview_lines], start=1):
        print(
            f"{idx:>4}. {row['predicate_anchor_id']} | "
            f"{row['reference']} | "
            f"governor={row['governor_greek_surface']} | "
            f"infinitive={row['infinitive_greek_surface']} | "
            f"anchor={row['anchor_greek_surface']} | "
            f"{row['audit_status']}"
        )

    remaining = len(audit_rows) - min(len(audit_rows), preview_lines)
    if remaining:
        print(f"... {remaining} more infinitive-governed environment audit rows written")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Stage 4 infinitive-governed environments.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--source", help="Explicit MorphGNT source path")
    parser.add_argument("--window", type=int, default=12, help="Number of same-verse tokens around anchor to inspect")
    parser.add_argument("--preview-lines", type=int, default=40)
    args = parser.parse_args(argv)

    book = args.book.strip().lower()

    try:
        root = mna_root_from_script()
        skeleton_path = root / "datasets" / "anchor-skeleton" / f"{book}.jsonl"
        morphgnt_path = resolve_source(root, book, args.source)
        output_path = root / "audits" / "stage4" / "infinitive-governed-environment-audit" / f"{book}.jsonl"

        metadata, audit_rows = detect_audit_rows(
            book,
            skeleton_path,
            morphgnt_path,
            output_path,
            root,
            args.window,
        )

        print_visible_output(book, skeleton_path, morphgnt_path, output_path, metadata, audit_rows, args.preview_lines)
        return 0
    except Exception as exc:
        print("MNA Stage 4 infinitive-governed environment audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
