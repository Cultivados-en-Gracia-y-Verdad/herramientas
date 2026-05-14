#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — finite predication candidate builder

Machine-readable ROOTS dataset stage.

Current scope:
- verse-based
- 1corintios MorphGNT mapping only
- finite predication candidates only
- no topology, Paso 5, Paso 6, or human-readable rendering

Usage from repository root:
    python3 MNA/scripts/roots_build_predications.py 1corintios 2 4

Default output:
    MNA/data/predications/<book>-<chapter>-<verse>.jsonl
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

SUBORDINATORS = {
    "ει", "εαν", "ινα", "οτι", "οταν", "οτε", "οπως", "ως",
    "ωστε", "επει", "επειδη", "καθως", "πριν",
}

BOUNDARY_CONNECTORS = {
    "αλλα", "δε", "και", "ουδε", "μηδε", "η", "γαρ", "ουν",
}

BOOK_CODES = {"1corintios": "07"}
CASE_CODE_INDEX = 0
NUMBER_CODE_INDEX = 1
GENDER_CODE_INDEX = 2


def normalize_greek(token: str) -> str:
    token = token.lower()
    token = token.replace("ʼ", "").replace("’", "").replace("'", "")
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"—]", "", token)
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token.strip()


def has_visible_boundary(token: str) -> bool:
    return any(mark in token for mark in [",", ";", "·", ":", "?", "!", "—", "·"])


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
            idx = idx.strip()
            if not idx.isdigit():
                raise ValueError(f"{path}:{lineno}: invalid token index {idx!r}")
            rows.append({"idx": idx.zfill(2), "token": text.strip()})
    return rows


def read_alignment(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows:
        return {}
    required = {"BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"}
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
    return {row["G_IDX"].zfill(2): row for row in rows}


def morph_ref_code(book: str, chapter: str, verse: str) -> str:
    if book not in BOOK_CODES:
        raise ValueError(f"No MorphGNT book code configured for {book!r}")
    return f"{BOOK_CODES[book]}{int(chapter):02d}{int(verse):02d}"


def read_morph_for_verse(path: Path, book: str, chapter: str, verse: str) -> dict[str, dict[str, str]]:
    wanted = morph_ref_code(book, chapter, verse)
    rows: dict[str, dict[str, str]] = {}
    counter = 0
    with path.open(encoding="utf-8") as f:
        for raw in f:
            parts = raw.strip().split()
            if len(parts) < 7 or parts[0] != wanted:
                continue
            counter += 1
            idx = f"{counter:02d}"
            pos, morph, greek, lemma = parts[1], parts[2], parts[3], parts[-1]
            rows[idx] = {
                "idx": idx,
                "ref_code": parts[0],
                "pos": pos,
                "morph": morph,
                "code": f"{pos} {morph}",
                "greek": greek,
                "lemma": lemma,
            }
    return rows


def morphgnt_pos_and_body(code: str) -> tuple[str, str]:
    parts = code.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", code


def compact_verb_code(code: str) -> str:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-" or len(body) < 4:
        return ""
    person = body[0]
    tvm = body[1:4]
    number = body[5] if len(body) > 5 else "-"
    if person not in {"1", "2", "3"}:
        return f"V-{tvm}"
    return f"V-{tvm}-{person}{number}"


def is_finite(code: str) -> bool:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-" or len(body) < 6:
        return False
    return (
        body[0] in {"1", "2", "3"}
        and len(body[1:4]) == 3
        and body[3] in {"I", "S", "M", "O", "D"}
        and body[5] in {"S", "P"}
    )


def person_number(code: str) -> tuple[str | None, str | None]:
    pos, body = morphgnt_pos_and_body(code)
    if pos != "V-" or len(body) < 6:
        return None, None
    person, number = body[0], body[5]
    if person in {"1", "2", "3"} and number in {"S", "P"}:
        return person, number
    return None, None


def parse_case_number_gender(code: str) -> tuple[str | None, str | None, str | None]:
    parts = code.split()
    if len(parts) != 2:
        return None, None, None
    body = parts[1].replace("-", "").strip()
    if len(body) < 3:
        return None, None, None
    return body[CASE_CODE_INDEX], body[NUMBER_CODE_INDEX], body[GENDER_CODE_INDEX]


def is_nominative_candidate(code: str) -> bool:
    pos, _body = morphgnt_pos_and_body(code)
    if pos not in {"N-", "A-", "RA", "RP", "RD", "RI", "RR", "D-", "T-"}:
        return False
    case, _number, _gender = parse_case_number_gender(code)
    return case == "N"


def nominative_agrees_with_finite(code: str, finite_person: str | None, finite_number: str | None) -> bool:
    if finite_person != "3":
        return False

    case, nominal_number, nominal_gender = parse_case_number_gender(code)
    if case != "N" or nominal_number is None:
        return False

    if nominal_number == finite_number:
        return True

    if nominal_number == "P" and nominal_gender == "N" and finite_number == "S":
        return True

    return False


def previous_finite_idx(finite_indexes: list[str], current_idx: str) -> str | None:
    current = int(current_idx)
    previous = [idx for idx in finite_indexes if int(idx) < current]
    return previous[-1] if previous else None


def finite_zone_start(finite_indexes: list[str], current_idx: str) -> int:
    previous = previous_finite_idx(finite_indexes, current_idx)
    return int(previous) + 1 if previous else 1


def boundary_between(tokens: list[dict[str, Any]], morph: dict[str, dict[str, str]], start_idx: str, end_idx: str) -> bool:
    start = int(start_idx)
    end = int(end_idx)
    if start >= end:
        return False

    for i in range(start + 1, end):
        idx = f"{i:02d}"
        token = tokens[i - 1]["token"]
        key = normalize_greek(token)
        row = morph.get(idx)
        pos = row["pos"] if row else ""

        if has_visible_boundary(token):
            return True
        if key in BOUNDARY_CONNECTORS:
            return True
        if pos == "C-" and key not in SUBORDINATORS:
            return True

    return False


def recover_subject(
    tokens: list[dict[str, Any]],
    morph: dict[str, dict[str, str]],
    verb_idx: str,
    finite_indexes: list[str],
) -> dict[str, Any]:
    verb_i = int(verb_idx)
    person, number = person_number(morph[verb_idx]["code"])
    window_start = max(finite_zone_start(finite_indexes, verb_idx), verb_i - 6, 1)
    explicit_candidates: list[dict[str, Any]] = []

    if person == "3":
        for i in range(window_start, verb_i):
            idx = f"{i:02d}"
            row = morph.get(idx)
            if not row or not is_nominative_candidate(row["code"]):
                continue
            if not nominative_agrees_with_finite(row["code"], person, number):
                continue
            if boundary_between(tokens, morph, idx, verb_idx):
                continue
            explicit_candidates.append({
                "token": idx,
                "form": row["greek"],
                "lemma": row["lemma"],
                "morph": row["code"],
            })

    if explicit_candidates:
        selected = explicit_candidates[-1]
        return {
            "subject_status": "candidate",
            "subject_source": "nearest_agreeing_nominative_no_visible_boundary",
            "subject_token": selected["token"],
            "subject_person": None,
            "subject_number": None,
            "subject_candidates": [selected],
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


def detect_subordination(tokens: list[dict[str, Any]], verb_idx: str, finite_indexes: list[str]) -> dict[str, Any]:
    verb_i = int(verb_idx)
    start = finite_zone_start(finite_indexes, verb_idx)
    markers: list[dict[str, str]] = []
    for i in range(start, verb_i):
        idx = f"{i:02d}"
        token = tokens[i - 1]["token"]
        key = normalize_greek(token)
        if key in SUBORDINATORS:
            markers.append({"token": idx, "form": token, "key": key})
    if markers:
        return {
            "subordination_status": "candidate",
            "subordination_source": "explicit_marker_after_previous_finite_before_current_finite",
            "subordination_markers": markers,
        }
    return {"subordination_status": "not_detected", "subordination_source": None, "subordination_markers": []}


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


def build_record(book: str, chapter: str, verse: str, n: int, token: dict[str, Any], morph_row: dict[str, str], subject: dict[str, Any], subordination: dict[str, Any], alignment: dict[str, str] | None) -> dict[str, Any]:
    finite_idx = token["idx"]
    independence_status = "unresolved" if subordination["subordination_status"] == "candidate" else "candidate"
    return {
        "predication_id": f"{book}-{chapter}-{verse}-P{n:02d}",
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
        "independence": {"independence_status": independence_status, "independence_source": "subordination_marker_scan_only"},
        "subordination": subordination,
        "certainty": {"finite_verb": "confirmed", "predication": "candidate", "independence": independence_status},
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
        raise ValueError(f"Token/morph count mismatch for {book} {chapter}:{verse}: tokens={len(tokens)} morph={len(morph)}")

    finite_indexes = [idx for idx, row in morph.items() if is_finite(row["code"])]
    records: list[dict[str, Any]] = []

    for token in tokens:
        idx = token["idx"]
        morph_row = morph.get(idx)
        if not morph_row:
            continue
        if normalize_greek(token["token"]) != normalize_greek(morph_row["greek"]):
            raise ValueError(f"Greek/morph mismatch at {book} {chapter}:{verse} token {idx}: {token['token']} != {morph_row['greek']}")
        if not is_finite(morph_row["code"]):
            continue
        subject = recover_subject(tokens, morph, idx, finite_indexes)
        subordination = detect_subordination(tokens, idx, finite_indexes)
        records.append(build_record(book, chapter, verse, len(records) + 1, token, morph_row, subject, subordination, alignment.get(idx)))
    return records


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    if len(sys.argv) not in {4, 5}:
        print("Usage:\n  python3 MNA/scripts/roots_build_predications.py 1corintios <chapter> <verse> [output.jsonl]", file=sys.stderr)
        sys.exit(2)
    book = sys.argv[1].lower()
    chapter = str(int(sys.argv[2]))
    verse = str(int(sys.argv[3]))
    records = build_verse(book, chapter, verse)
    output_path = Path(sys.argv[4]) if len(sys.argv) == 5 else mna_root() / "data" / "predications" / f"{book}-{chapter}-{verse}.jsonl"
    write_jsonl(records, output_path)
    print(f"WROTE {len(records)} predication candidate(s): {output_path}")


if __name__ == "__main__":
    main()
