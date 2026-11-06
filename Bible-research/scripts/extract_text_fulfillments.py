#!/usr/bin/env python3
"""Collect verses where the text itself says a word was fulfilled.

No event names. No map onto a later passage. The row is the verse that makes
the claim, plus the words it uses and any name it gives.

Hebrew: the clause has a completion verb (מלא / קום) and דבר, and also יהוה
or נביא / נביאה.

Greek: the clause has πληρόω or ἐκπληρόω, and also γραφή or προφήτης /
προφῆτις / προφητεία.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prophecy" / "text_fulfillments.jsonl"
SUMMARY = ROOT / "prophecy" / "text_fulfillments_summary.json"

HE_DONE = {"מלא", "קום"}
HE_WORD = {"דבר"}
HE_WHO = {"יהוה", "אדני", "נביא", "נביאה"}
EL_DONE = {"πληρόω", "ἐκπληρόω"}
EL_WHAT = {"γραφή", "προφήτης", "προφῆτις", "προφητεία"}


def cons(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def hebrew_hit(row: dict) -> bool:
    lems = {cons(x) for x in (row.get("lemmas") or [])}
    verb = cons(row.get("verb_lemma") or "")
    return (verb in HE_DONE or bool(lems & HE_DONE)) and bool(lems & HE_WORD) and bool(lems & HE_WHO)


def greek_hit(row: dict) -> bool:
    lems = set(row.get("lemmas") or [])
    verb = row.get("verb_lemma") or ""
    return (verb in EL_DONE or bool(lems & EL_DONE)) and bool(lems & EL_WHAT)


def pack(row: dict, lang: str, markers: list[str]) -> dict:
    return {
        "id": row["id"],
        "corpus": lang,
        "ref": row.get("ref"),
        "ref_protestant": row.get("ref_protestant"),
        "book": row.get("book"),
        "markers": markers,
        "own_gloss": row.get("own_gloss"),
        "own_text": row.get("own_text"),
        "verb_lemma": row.get("verb_lemma"),
        "verb_english": row.get("verb_english"),
        "subject_lemmas": row.get("subject_lemmas"),
    }


def markers_he(row: dict) -> list[str]:
    lems = {cons(x) for x in (row.get("lemmas") or [])}
    out = []
    if lems & {"מלא"}:
        out.append("מלא")
    if lems & {"קום"}:
        out.append("קום")
    if lems & {"דבר"}:
        out.append("דבר")
    if lems & {"יהוה"}:
        out.append("יהוה")
    if lems & {"נביא", "נביאה"}:
        out.append("נביא")
    return out


def markers_el(row: dict) -> list[str]:
    lems = set(row.get("lemmas") or [])
    out = []
    for w in sorted(EL_DONE | EL_WHAT):
        if w in lems or row.get("verb_lemma") == w:
            out.append(w)
    return out


def main() -> int:
    rows = []
    for r in load_jsonl(ROOT / "clauses" / "hebrew.jsonl"):
        if hebrew_hit(r):
            rows.append(pack(r, "hebrew", markers_he(r)))
    for r in load_jsonl(ROOT / "clauses" / "greek.jsonl"):
        if greek_hit(r):
            rows.append(pack(r, "greek", markers_el(r)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for rec in rows:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    by_book: dict[str, int] = {}
    for rec in rows:
        b = rec.get("book") or "?"
        by_book[b] = by_book.get(b, 0) + 1
    summary = {
        "method": "Only clauses whose own lemmas include fulfillment language plus word/prophet/scripture.",
        "count": len(rows),
        "hebrew": sum(1 for r in rows if r["corpus"] == "hebrew"),
        "greek": sum(1 for r in rows if r["corpus"] == "greek"),
        "by_book": dict(sorted(by_book.items(), key=lambda kv: (-kv[1], kv[0]))),
        "does_not": [
            "name an event (birth, exile, return)",
            "point at a different verse as the prophecy that was fulfilled",
            "judge whether the claim is true or false",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(rows), "hebrew": summary["hebrew"], "greek": summary["greek"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
