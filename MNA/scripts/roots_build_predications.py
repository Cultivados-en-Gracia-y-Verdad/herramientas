#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — finite predication candidate builder

This is the first machine-readable ROOTS dataset stage.

Scope for this stage:
- verse-based, not book-based
- built from existing MNA repository files
- no generic input.tsv interface
- no topology
- no Paso 5 / Paso 6 reconstruction
- no human-readable rendering

Usage from MNA directory:
    python3 scripts/roots_build_predications.py 1corintios 1 10

Usage from repository root:
    python3 MNA/scripts/roots_build_predications.py 1corintios 1 10

Default output:
    MNA/data/predications/1corintios-1-10.jsonl
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


SUBORDINATORS = {
    "ει",
    "εαν",
    "ινα",
    "οτι",
    "οταν",
    "οτε",
    "οπως",
    "ως",
    "ωστε",
    "επει",
    "επειδη",
    "καθως",
    "πριν",
}

CASE_CODE_INDEX = 0
NUMBER_CODE_INDEX = 1
GENDER_CODE_INDEX = 2


def normalize_greek(token: str) -> str:
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"'—]", "", token).lower()
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token.strip()


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_tokens(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue

            if "\t" in line:
                idx, text = line.split("\t", 1)
            else:
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    raise ValueError(f"{path}:{lineno}: expected IDX<TAB>TOKEN")
                idx, text = parts

            if not idx.strip().isdigit():
                raise ValueError(f"{path}:{lineno}: invalid token index {idx!r}")

            rows.append({"idx": idx.strip().zfill(2), "token": text.strip()})

    return rows


def read_alignment(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    required = {"BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"}
    if not rows:
        return {}

    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")

    return {row["G_IDX"].zfill(2): row for row in rows}


def morph_ref_code(book: str, chapter: str, verse: str) -> str:
    book_codes = {"1corintios": "07"}

    if book not in book_codes:
        raise ValueError(
            f"No MorphGNT book code configured for {book!r}. "
            "This first predication pass is intentionally limited."
        )

    return f"{book_codes[book]}{int(chapter):02d}{int(verse):02d}"


def read_morph_for_verse(path: Path, book: str, chapter: str, verse: str) -> dict[str, dict[str, str]]:
    wanted = morph_ref_code(book, chapter, verse)
    rows: dict[str, dict[str, str]] = {}
    counter = 0

    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            ref_code = parts[0]
            if ref_code != wanted:
                continue

            counter += 1
            idx = f"{counter:02d}"
            pos = parts[1]
            morph = parts[2]
            greek = parts[3]
            lemma = parts[-1]
            code = f"{pos} {morph}"

            rows[idx] = {
                "idx": idx,
                "ref_code": ref_code,
                "pos": pos,
                "morph": morph,
                "code": code,
                "greek": greek,
                "lemma": lemma,
            }

    return rows


def morphgnt_pos_and_body(code: str) -> tuple[str, str]:
    parts = code.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    if code.startswith("V-"):
        return "V-", code[2:]
    return "", code


def compact_verb_code(code: str) -> str:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-":
        return ""

    body = body.strip()
    if len(body) < 4:
        return ""

    person = body[0]
    tvm = body[1:4]
    number = body[5] if len(body) > 5 else "-"

    if person not in {"1", "2", "3"}:
        return f"V-{tvm}"

    return f"V-{tvm}-{person}{number}"


def is_finite(code: str) -> bool:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-":
        return False

    if len(body) < 6:
        return False

    person = body[0]
    tvm = body[1:4]
    mood = body[3]
    number = body[5]

    return (
        person in {"1", "2", "3"}
        and len(tvm) == 3
        and mood in {"I", "S", "M", "O", "D"}
        and number in {"S", "P"}
    )


def person_number(code: str) -> tuple[str | None, str | None]:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-" or len(body) < 6:
        return None, None

    person = body[0]
    number = body[5]

    if person not in {"1", "2", "3"} or number not in {"S", "P"}:
        return None, None

    return person, number


def parse_case_number_gender(code: str) -> tuple[str | None, str | None, str | None]:
    parts = code.split()
    body = parts[1] if len(parts) == 2 else code.strip().split("-")[-1]
    body = body.replace("-", "").strip()

    if len(body) < 3:
        return None, None, None

    return body[CASE_CODE_INDEX], body[NUMBER_CODE_INDEX], body[GENDER_CODE_INDEX]


def is_nominative_candidate(code: str) -> bool:
    if not code:
        return False

    pos, _body = morphgnt_pos_and_body(code)
    if pos not in {"N-", "A-", "RA", "RP", "RD", "RI", "RR", "D-", "T-"}:
        return False

    case, _number, _gender = parse_case_number_gender(code)
    return case == "N"


def recover_subject(tokens: list[dict[str, Any]], morph: dict[str, dict[str, str]], verb_idx: str) -> dict[str, Any]:
    verb_i = int(verb_idx)
    verb_morph = morph[verb_idx]
    person, number = person_number(verb_morph["code"])

    window_start = max(1, verb_i - 6)
    explicit_candidates: list[dict[str, Any]] = []

    for i in range(window_start, verb_i):
        idx = f"{i:02d}"
        m = morph.get(idx)
        if not m:
            continue

        if is_nominative_candidate(m["code"]):
            explicit_candidates.append({
                "token": idx,
                "form": m["greek"],
                "lemma": m["lemma"],
                "morph": m["code"],
            })

    if explicit_candidates:
        selected = explicit_candidates[-1]
        return {
            "subject_status": "candidate",
            "subject_source": "explicit_nominative_before_verb",
            "subject_token": selected["token"],
            "subject_person": None,
            "subject_number": None,
            "subject_candidates": explicit_candidates,
        }

    if person and number:
        return {
            "subject_status": "confirmed",
            "subject_source": "finite_verb_morphology",
            "subject_token": None,
            "subject_person": person,
            "subject_number": number,
            "subject_candidates": [],
        }

    return {
        "subject_status": "unresolved",
        "subject_source": None,
        "subject_token": None,
        "subject_person": None,
        "subject_number": None,
        "subject_candidates": [],
    }


def detect_subordination(tokens: list[dict[str, Any]], verb_idx: str) -> dict[str, Any]:
    verb_i = int(verb_idx)
    start = max(1, verb_i - 4)

    markers = []
    for i in range(start, verb_i):
        idx = f"{i:02d}"
        token = tokens[i - 1]["token"]
        key = normalize_greek(token)
        if key in SUBORDINATORS:
            markers.append({"token": idx, "form": token, "key": key})

    if markers:
        return {
            "subordination_status": "candidate",
            "subordination_source": "explicit_marker_before_finite_verb",
            "subordination_markers": markers,
        }

    return {
        "subordination_status": "not_detected",
        "subordination_source": None,
        "subordination_markers": [],
    }


def find_alignment_path(root: Path, book: str, chapter: str, verse: str) -> Path:
    data = root / "data"
    filename = f"{book}-{chapter}-{verse}.tsv"

    candidates = [
        data / "alignments" / filename,
        data / "alignments" / book / filename,
        data / "alignments" / book / chapter / filename,
        data / "alignments" / book / chapter / f"{verse}.tsv",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = sorted((data / "alignments").glob(f"**/{filename}"))
    if matches:
        return matches[0]

    raise FileNotFoundError("Could not find alignment TSV. Tried:\n" + "\n".join(str(c) for c in candidates))


def build_record(book: str, chapter: str, verse: str, predication_number: int, token: dict[str, Any], morph_row: dict[str, str], subject: dict[str, Any], subordination: dict[str, Any], alignment: dict[str, str] | None) -> dict[str, Any]:
    finite_idx = token["idx"]
    independence_status = "unresolved" if subordination["subordination_status"] == "candidate" else "candidate"

    return {
        "predication_id": f"{book}-{chapter}-{verse}-P{predication_number:02d}",
        "book": book,
        "chapter": int(chapter),
        "verse": int(verse),
        "g_idx": finite_idx,
        "finite_verb": token["token"],
        "finite_lemma": morph_row["lemma"],
        "finite_morphgnt": morph_row["code"],
        "finite_compact": compact_verb_code(morph_row["code"]),
        "nbla_idx": alignment.get("NBLA_IDX") if alignment else None,
        "nbla_text": alignment.get("NBLA_TEXT") if alignment else None,
        "subject": subject,
        "predicate": {
            "predicate_status": "candidate",
            "predicate_source": "finite_verb_anchor_only",
            "predicate_g_start": finite_idx,
            "predicate_g_end": finite_idx,
        },
        "independence": {
            "independence_status": independence_status,
            "independence_source": "subordination_marker_scan_only",
        },
        "subordination": subordination,
        "certainty": {
            "finite_verb": "confirmed",
            "predication": "candidate",
            "independence": independence_status,
        },
    }


def build_verse(book: str, chapter: str, verse: str) -> list[dict[str, Any]]:
    root = mna_root()

    greek_path = root / "data" / "g-tokens" / book / f"{book}-{chapter}-{verse}.txt"
    morph_path = root / "data" / "MorphGNT" / f"{book}-morphgnt.txt"
    alignment_path = find_alignment_path(root, book, chapter, verse)

    if not greek_path.exists():
        raise FileNotFoundError(greek_path)

    if not morph_path.exists():
        raise FileNotFoundError(morph_path)

    tokens = read_tokens(greek_path)
    morph = read_morph_for_verse(morph_path, book, chapter, verse)
    alignment = read_alignment(alignment_path)

    if len(tokens) != len(morph):
        raise ValueError(
            f"Token/morph count mismatch for {book} {chapter}:{verse}: "
            f"tokens={len(tokens)} morph={len(morph)}"
        )

    records: list[dict[str, Any]] = []

    for token in tokens:
        idx = token["idx"]
        morph_row = morph.get(idx)

        if not morph_row:
            continue

        if normalize_greek(token["token"]) != normalize_greek(morph_row["greek"]):
            raise ValueError(
                f"Greek/morph mismatch at {book} {chapter}:{verse} token {idx}: "
                f"{token['token']} != {morph_row['greek']}"
            )

        if not is_finite(morph_row["code"]):
            continue

        subject = recover_subject(tokens, morph, idx)
        subordination = detect_subordination(tokens, idx)

        records.append(build_record(
            book=book,
            chapter=chapter,
            verse=verse,
            predication_number=len(records) + 1,
            token=token,
            morph_row=morph_row,
            subject=subject,
            subordination=subordination,
            alignment=alignment.get(idx),
        ))

    return records


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    if len(sys.argv) not in {4, 5}:
        print(
            "Usage:\n"
            "  python3 scripts/roots_build_predications.py 1corintios <chapter> <verse> [output.jsonl]\n"
            "\nExample:\n"
            "  python3 scripts/roots_build_predications.py 1corintios 1 10",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()
    chapter = str(int(sys.argv[2]))
    verse = str(int(sys.argv[3]))

    records = build_verse(book, chapter, verse)

    if len(sys.argv) == 5:
        output_path = Path(sys.argv[4])
    else:
        output_path = mna_root() / "data" / "predications" / f"{book}-{chapter}-{verse}.jsonl"

    write_jsonl(records, output_path)

    print(f"WROTE {len(records)} predication candidate(s): {output_path}")


if __name__ == "__main__":
    main()
