#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage3-subject-movement-marking-builder-v3-morphgnt-connectors-rmac"

TENSE_RMAC = {"P":"P", "I":"I", "F":"F", "A":"A", "R":"X", "L":"Y"}
VOICE_RMAC = {"A":"A", "M":"M", "P":"P", "E":"E", "D":"M", "O":"P", "N":"E"}
MOOD_RMAC = {"I":"I", "S":"S", "O":"O", "M":"M", "N":"N", "P":"P"}
NUMBER_RMAC = {"S":"S", "P":"P"}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row.get("chapter") or 0), int(row.get("verse") or 0), int(row.get("token_index") or 0))


def find_morphgnt_file(mna: Path, book: str) -> Path:
    base = mna / "SOURCES" / "MorphGNT"
    choices = [base / f"{book}-morphgnt.txt", base / f"{book}.txt", base / f"{book}.tsv"]
    for p in choices:
        if p.is_file():
            return p
    for p in sorted(base.rglob(f"*{book}*")):
        if p.is_file():
            return p
    raise FileNotFoundError(f"No MorphGNT source found for {book}")


def parse_ref(code: str) -> tuple[int, int]:
    digits = "".join(c for c in code if c.isdigit())
    if len(digits) < 4:
        raise ValueError(f"Bad MorphGNT reference: {code}")
    return int(digits[-4:-2]), int(digits[-2:])


def load_morphgnt_tokens(mna: Path, book: str) -> list[dict[str, Any]]:
    source = find_morphgnt_file(mna, book)
    tokens: list[dict[str, Any]] = []
    token_index = 0
    with source.open("r", encoding="utf-8") as f:
        for raw in f:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            token_index += 1
            parts = raw.strip().split()
            if len(parts) < 5:
                continue
            chapter, verse = parse_ref(parts[0])
            tokens.append({
                "token_index": token_index,
                "chapter": chapter,
                "verse": verse,
                "pos": parts[1],
                "morph": parts[2],
                "greek": parts[3],
                "lemma": parts[4],
            })
    return tokens


def morphgnt_to_rmac(morphology: str) -> str:
    code = morphology[2:] if morphology.startswith("V-") else morphology
    if len(code) < 4:
        return morphology
    person = code[0]
    tense = TENSE_RMAC.get(code[1], code[1])
    voice = VOICE_RMAC.get(code[2], code[2])
    mood = MOOD_RMAC.get(code[3], code[3])
    number = NUMBER_RMAC.get(code[5], code[5]) if len(code) > 5 else ""
    if person in {"1", "2", "3"} and number:
        return f"V-{tense}{voice}{mood}-{person}{number}"
    return f"V-{tense}{voice}{mood}"


def subject_signal(anchor: dict[str, Any]) -> str:
    explicit = str(anchor.get("explicit_subject_before") or "").strip()
    if explicit:
        return f"LEX:{explicit}"
    return f"MORPH:{anchor.get('person','')}:{anchor.get('number','')}"


def s_marker(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return ""
    return "[S]" if subject_signal(current) != subject_signal(previous) else ""


def m_marker(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return ""
    changes = []
    for field in ["tense", "voice", "mood"]:
        if str(current.get(field) or "") != str(previous.get(field) or ""):
            changes.append(field)
    if current.get("connector_before_anchor"):
        changes.append("connector_before")
    return "[M]" if changes else ""


def connector_tokens_between(tokens_by_index: dict[int, dict[str, Any]], start_idx: int, end_idx: int, chapter: int, verse: int) -> list[dict[str, Any]]:
    connectors = []
    for idx in range(start_idx, end_idx):
        t = tokens_by_index.get(idx)
        if not t:
            continue
        if int(t["chapter"]) != int(chapter) or int(t["verse"]) != int(verse):
            continue
        if str(t.get("pos") or "").startswith("C-"):
            connectors.append({
                "form": t.get("greek", ""),
                "lemma": t.get("lemma", ""),
                "token_index": t.get("token_index"),
                "distance_to_anchor": end_idx - int(t.get("token_index")),
            })
    return connectors


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Stage 3 subject and movement markers.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    anchors_path = mna / "datasets" / "predicate-anchors" / f"{book}.jsonl"
    finite_path = mna / "datasets" / "finite-verbs" / f"{book}.jsonl"
    out_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"

    anchors = sorted(load_jsonl(anchors_path), key=sort_key)
    finite_rows = sorted(load_jsonl(finite_path), key=sort_key)
    morph_tokens = load_morphgnt_tokens(mna, book)
    tokens_by_index = {int(t["token_index"]): t for t in morph_tokens}
    verse_start = {}
    for t in morph_tokens:
        key = (int(t["chapter"]), int(t["verse"]))
        verse_start.setdefault(key, int(t["token_index"]))

    finite_by_location = {(r["chapter"], r["verse"], r["token_index"]): r for r in finite_rows}
    for a in anchors:
        f = finite_by_location.get((a["chapter"], a["verse"], a["token_index"]))
        if f:
            for key in ["tense", "voice", "mood", "person", "number"]:
                a[key] = f.get(key, "")
            a["rmac"] = morphgnt_to_rmac(f.get("morphology", a.get("morphology", "")))

    rows = []
    previous = None
    previous_token_index = None
    for idx, anchor in enumerate(anchors, start=1):
        anchor_token_index = int(anchor["token_index"])
        v_start = verse_start.get((int(anchor["chapter"]), int(anchor["verse"])), anchor_token_index)
        start_idx = max(v_start, (previous_token_index + 1) if previous_token_index else v_start)
        connectors = connector_tokens_between(tokens_by_index, start_idx, anchor_token_index, int(anchor["chapter"]), int(anchor["verse"]))
        connector_forms = [c["form"] for c in connectors]
        connector_lemmas = [c["lemma"] for c in connectors]
        connector_indexes = [c["token_index"] for c in connectors]
        connector_distances = [c["distance_to_anchor"] for c in connectors]
        anchor["connector_before_anchor"] = bool(connectors)

        rows.append({
            "record_type": "subject_movement_marking",
            "book": book,
            "order": idx,
            "anchor_id": anchor["anchor_id"],
            "chapter": anchor["chapter"],
            "verse": anchor["verse"],
            "token_index": anchor["token_index"],
            "greek_form": anchor["greek_form"],
            "lemma": anchor["lemma"],
            "morphology": anchor["morphology"],
            "rmac": anchor.get("rmac", ""),
            "tense": anchor.get("tense", ""),
            "voice": anchor.get("voice", ""),
            "mood": anchor.get("mood", ""),
            "person": anchor.get("person", ""),
            "number": anchor.get("number", ""),
            "explicit_subject_before": anchor.get("explicit_subject_before", ""),
            "subject_signal": subject_signal(anchor),
            "connector_form": " ".join(connector_forms),
            "connector_lemma": " ".join(connector_lemmas),
            "connector_token_index": connector_indexes,
            "connector_distance_to_anchor": connector_distances,
            "connector_before_anchor": bool(connectors),
            "connector_count_before_anchor": len(connectors),
            "connectors_before_anchor": connectors,
            "s_marker": s_marker(anchor, previous),
            "m_marker": m_marker(anchor, previous),
        })
        previous = anchor
        previous_token_index = anchor_token_index

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "record_type": "metadata",
            "builder_version": VERSION,
            "book": book,
            "rows_written": len(rows),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    print("MNA Stage 3 — Subject and Movement Marking")
    print(f"BOOK: {book}")
    print(f"ROWS WRITTEN: {len(rows)}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
