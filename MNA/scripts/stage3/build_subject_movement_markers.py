#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "stage3-subject-movement-marking-builder-v1"


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
    if str(current.get("explicit_connector_before") or ""):
        changes.append("connector_before")
    return "[M]" if changes else ""


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

    finite_by_location = {(r["chapter"], r["verse"], r["token_index"]): r for r in finite_rows}
    for a in anchors:
        f = finite_by_location.get((a["chapter"], a["verse"], a["token_index"]))
        if f:
            for key in ["tense", "voice", "mood", "person", "number"]:
                a[key] = f.get(key, "")

    rows = []
    previous = None
    for idx, anchor in enumerate(anchors, start=1):
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
            "tense": anchor.get("tense", ""),
            "voice": anchor.get("voice", ""),
            "mood": anchor.get("mood", ""),
            "person": anchor.get("person", ""),
            "number": anchor.get("number", ""),
            "explicit_connector_before": anchor.get("explicit_connector_before", ""),
            "explicit_subject_before": anchor.get("explicit_subject_before", ""),
            "subject_signal": subject_signal(anchor),
            "s_marker": s_marker(anchor, previous),
            "m_marker": m_marker(anchor, previous),
        })
        previous = anchor

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
