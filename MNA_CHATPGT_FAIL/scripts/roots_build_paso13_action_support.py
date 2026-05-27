#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — Paso 13 action support

Purpose:
- produce a cautious support layer for Paso 13
- identify minimal action evidence from the existing predication stream
- avoid final interpretation, headings, themes, or polished summaries

This layer DOES NOT:
- write final Paso 13 sentences
- generate H-level headings
- infer themes
- interpret theology/semantics
- override earlier ROOTS layers

This layer ONLY prepares auditable minimal-action support.
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------
# IO
# ---------------------------------------------------------


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]



def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON") from exc

    return rows



def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: int(
            row.get("stream_index")
            or row.get("predication_index")
            or row.get("id")
            or 0
        ),
    )



def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")



def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------
# Load layers
# ---------------------------------------------------------


def load_predications(book: str) -> list[dict[str, Any]]:
    root = mna_root()
    candidates = [
        root / "data" / "predications" / f"{book}-predications.jsonl",
        root / "data" / "independent-stream" / f"{book}-independent-stream.jsonl",
    ]

    for path in candidates:
        if path.exists():
            return ordered(read_jsonl(path))

    raise FileNotFoundError("No predication source found")



def load_layer(book: str, folder: str, suffix: str) -> dict[str, dict[str, Any]]:
    path = mna_root() / "data" / folder / f"{book}-{suffix}.jsonl"

    if not path.exists():
        return {}

    out: dict[str, dict[str, Any]] = {}

    for row in ordered(read_jsonl(path)):
        key = str(row.get("predication_id") or row.get("stream_index") or "")
        if key:
            out[key] = row

    return out


# ---------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------


TEXT_FIELDS = [
    "nbla",
    "spanish",
    "text_nbla",
    "clause_nbla",
    "clause_text",
    "visible_clause",
    "rendered_clause",
]

GREEK_FIELDS = [
    "greek",
    "greek_text",
    "clause_greek",
    "text_greek",
    "finite_clause_greek",
    "raw_greek",
]

VERB_FIELDS = [
    "verb",
    "finite_verb",
    "main_verb",
    "verb_surface",
    "greek_verb",
]

SUBJECT_FIELDS = [
    "subject",
    "subject_label",
    "subject_refined",
    "implicit_subject",
    "subject_person_number",
]


def first_text(row: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""



def extract_verb(row: dict[str, Any]) -> str:
    direct = first_text(row, VERB_FIELDS)
    if direct:
        return direct

    # Conservative fallback: inspect common nested verb dictionaries.
    for key in ["finite", "finite_predicate", "predicate", "morph"]:
        value = row.get(key)
        if isinstance(value, dict):
            direct = first_text(value, VERB_FIELDS + ["surface", "text", "word"])
            if direct:
                return direct

    return ""



def extract_subject(row: dict[str, Any]) -> str:
    direct = first_text(row, SUBJECT_FIELDS)
    if direct:
        return direct

    person = row.get("person") or row.get("subject_person")
    number = row.get("number") or row.get("subject_number")

    if person or number:
        return f"implicit-{person or '?'}{number or '?'}"

    return "unknown"



def extract_scope(row: dict[str, Any]) -> str:
    nbla = first_text(row, TEXT_FIELDS)
    if nbla:
        return nbla
    greek = first_text(row, GREEK_FIELDS)
    if greek:
        return greek
    return ""



def compact_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


# ---------------------------------------------------------
# Action support
# ---------------------------------------------------------


def predication_key(row: dict[str, Any]) -> str:
    return str(row.get("predication_id") or row.get("stream_index") or row.get("id") or "")



def assess_action_confidence(verb: str, scope: str, field_row: dict[str, Any] | None) -> str:
    # Still only low/moderate; never high in this support layer.
    if not verb:
        return "low"

    if not scope:
        return "low"

    if field_row and str(field_row.get("field_state") or "") in {"stable", "extended"}:
        return "moderate"

    return "low"



def build_minimal_action(subject: str, verb: str, scope: str) -> str:
    if not verb:
        return ""

    subject_part = subject if subject and subject != "unknown" else "sujeto no resuelto"
    scope_part = compact_space(scope)

    if scope_part:
        return f"{subject_part} — {verb} — {scope_part}"

    return f"{subject_part} — {verb}"



def build_action_support(book: str) -> list[dict[str, Any]]:
    predications = load_predications(book)
    paso9 = load_layer(book, "paso9-support", "paso9-support")
    field = load_layer(book, "continuity-field", "continuity-field")

    rows: list[dict[str, Any]] = []

    for idx, predication in enumerate(predications, start=1):
        key = predication_key(predication)
        paso9_row = paso9.get(key)
        field_row = field.get(key)

        subject = extract_subject(predication)
        verb = extract_verb(predication)
        scope = extract_scope(predication)

        candidate_labels: list[str] = []
        if paso9_row:
            try:
                candidate_labels = json.loads(str(paso9_row.get("candidate_labels") or "[]"))
            except Exception:
                candidate_labels = []

        field_state = str(field_row.get("field_state") or "") if field_row else ""
        confidence = assess_action_confidence(verb, scope, field_row)

        evidence = [
            f"verb:{verb or 'missing'}",
            f"subject:{subject}",
            f"field:{field_state or 'missing'}",
            f"paso9:{','.join(candidate_labels) if candidate_labels else 'missing'}",
        ]

        rows.append({
            "paso13_action_support_id": f"P13{idx:05d}",
            "book": predication.get("book"),
            "chapter": predication.get("chapter"),
            "verse": predication.get("verse"),
            "reference": f"{predication.get('chapter')}:{predication.get('verse')}",
            "stream_index": predication.get("stream_index"),
            "predication_id": predication.get("predication_id"),
            "subject_support": subject,
            "verb_support": verb,
            "scope_support": compact_space(scope),
            "paso9_candidate_labels": json.dumps(candidate_labels, ensure_ascii=False),
            "continuity_field_state": field_state,
            "minimal_action_support": build_minimal_action(subject, verb, scope),
            "confidence": confidence,
            "evidence": json.dumps(evidence, ensure_ascii=False),
            "final_action_statement_assigned": False,
        })

    return rows


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, dict[str, int]] = {
        "confidence": {},
        "continuity_field_state": {},
        "has_verb_support": {},
    }

    for row in rows:
        confidence = str(row.get("confidence") or "")
        field_state = str(row.get("continuity_field_state") or "")
        has_verb = "yes" if str(row.get("verb_support") or "") else "no"

        counters["confidence"][confidence] = counters["confidence"].get(confidence, 0) + 1
        counters["continuity_field_state"][field_state] = counters["continuity_field_state"].get(field_state, 0) + 1
        counters["has_verb_support"][has_verb] = counters["has_verb_support"].get(has_verb, 0) + 1

    summary: list[dict[str, Any]] = []
    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            summary.append({"summary_type": summary_type, "name": name, "count": count})

    return summary


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def process_book(book: str) -> tuple[int, Path, Path]:
    rows = build_action_support(book)
    summary = build_summary(rows)

    out_dir = mna_root() / "data" / "paso13-action-support"

    jsonl_out = out_dir / f"{book}-paso13-action-support.jsonl"
    tsv_out = out_dir / f"{book}-paso13-action-support.tsv"
    summary_out = out_dir / f"{book}-paso13-action-support-summary.tsv"

    write_jsonl(jsonl_out, rows)
    write_tsv(tsv_out, rows)
    write_tsv(summary_out, summary)

    return len(rows), tsv_out, summary_out



def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 MNA/scripts/roots_build_paso13_action_support.py <book>",
            file=sys.stderr,
        )
        sys.exit(2)

    book = sys.argv[1].lower()

    count, tsv_out, summary_out = process_book(book)

    print(f"paso13_action_support_rows = {count}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")


if __name__ == "__main__":
    main()
