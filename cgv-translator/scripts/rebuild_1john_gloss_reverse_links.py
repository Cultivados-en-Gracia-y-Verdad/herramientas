#!/usr/bin/env python3
"""Rebuild 1 John reverse-links with BLE-gloss matching (monotonic).

Auto-zip slides content words; this assigns Spanish bundles to TR tokens by
BLE `es` gloss when possible, keeping Spanish reading order.

Writes: translations/tr-spine/1john/1john-reverse-links.json
Then: python3 cgv-reader/scripts/compile-lbf-alignment-1juan.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERR = Path(__file__).resolve().parents[1]
PHRASES = HERR / "translations/tr-spine/1john/1john-phrases-tr.json"
SPINE = HERR / "translations/tr-spine/1john/1john-tr-spine.json"
OUT = HERR / "translations/tr-spine/1john/1john-reverse-links.json"
CGV_DATA = HERR.parent.parent / "cgv-data"
TOKENS = CGV_DATA / "interlinears/NT/1juan.tokens.jsonl"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+(?:'[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+)?")

FUNCTION = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "por", "para", "con", "sin",
    "que", "y", "e", "o", "u", "su", "sus", "lo", "les", "nos",
    "me", "te", "se", "le", "este", "esta", "estos", "estas",
    "ese", "esa", "esos", "esas", "si", "no", "ni", "ya", "mas",
    # Perfect auxiliaries that should ride with the next content participle/verb
    "he", "ha", "has", "han", "hemos", "habeis", "habéis",
}


def fold(value: str) -> str:
    value = value.lower().strip().replace("·", " ")
    value = "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", value)


def tokenize_spanish(spanish: str) -> list[dict]:
    return [
        {
            "surface": m.group(0),
            "charStart": m.start(),
            "charEnd": m.end(),
            "fold": fold(m.group(0)),
        }
        for m in WORD_RE.finditer(spanish)
    ]


def bundle_spanish(spanish: str) -> list[dict]:
    units = tokenize_spanish(spanish)
    if not units:
        return []
    bundles: list[dict] = []
    pending: list[dict] = []
    for u in units:
        if u["fold"] in FUNCTION:
            pending.append(u)
            continue
        group = pending + [u]
        pending = []
        bundles.append(
            {
                "surface": spanish[group[0]["charStart"] : group[-1]["charEnd"]],
                "charStart": group[0]["charStart"],
                "charEnd": group[-1]["charEnd"],
                "contentFold": u["fold"],
            }
        )
    if pending and bundles:
        last = bundles[-1]
        last["surface"] = spanish[last["charStart"] : pending[-1]["charEnd"]]
        last["charEnd"] = pending[-1]["charEnd"]
    elif pending:
        bundles.append(
            {
                "surface": spanish[pending[0]["charStart"] : pending[-1]["charEnd"]],
                "charStart": pending[0]["charStart"],
                "charEnd": pending[-1]["charEnd"],
                "contentFold": pending[-1]["fold"],
            }
        )
    return bundles


def is_function_greek(row: dict, gloss_fold: str) -> bool:
    rmac = (row.get("rmac") or row.get("robinson") or "").upper()
    greek = fold(row.get("greek") or "")
    if rmac.startswith("T-") or rmac.startswith("P-") or rmac.startswith("C-"):
        return True
    if greek in {"και", "δε", "γαρ", "ουν", "οτι", "εν", "εις", "εκ", "απο", "δια", "προς", "μετα", "υπο", "περι", "ως", "μη", "ου", "ουκ", "ουχ", "τε", "η", "ο", "το", "του", "της", "τω", "τη", "τον", "την", "οι", "αι", "τα", "των", "τοις", "ταις", "τους", "τας"}:
        return True
    if gloss_fold in FUNCTION or gloss_fold in {"el", "la", "y", "de", "en", "a", "que", "no", "si"}:
        return True
    return False


def gloss_parts(gloss: str) -> list[str]:
    """Folded content-ish parts of a BLE gloss (may be multi-word: 'hemos oído')."""
    parts = []
    for raw in re.split(r"[\s·/]+", gloss or ""):
        f = fold(raw)
        if f and f not in FUNCTION:
            parts.append(f)
    return parts


def gloss_score(gloss: str, bundle: dict) -> int:
    parts = gloss_parts(gloss)
    if not parts:
        return 0
    content = bundle["contentFold"]
    surface = fold(bundle["surface"])
    best = 0
    for part in parts:
        if part == content:
            best = max(best, 100)
        elif part in content or content in part:
            best = max(best, 80)
        elif part in surface:
            best = max(best, 60)
        else:
            n = min(5, len(part), len(content))
            if n >= 4 and part[:n] == content[:n]:
                best = max(best, 40)
    return best


def load_ble_gloss() -> dict[tuple[int, int, int], str]:
    out: dict[tuple[int, int, int], str] = {}
    if not TOKENS.exists():
        return out
    for line in TOKENS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        out[(int(row["ch"]), int(row["vs"]), int(row["tok"]))] = row.get("es") or ""
    return out


def parse_ref(reference: str) -> tuple[int, int]:
    m = re.search(r"(\d+):(\d+)\s*$", reference)
    if not m:
        raise ValueError(reference)
    return int(m.group(1)), int(m.group(2))


def link_phrase(phrase: dict, spine_by_id: dict[str, dict], ble: dict[tuple[int, int, int], str]) -> list[dict]:
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    if not rows or not spanish.strip():
        return []
    bundles = bundle_spanish(spanish)
    if not bundles:
        return []

    ch, vs = parse_ref(phrase["reference"])
    enriched = []
    for row in rows:
        sid = row["sourceTokenId"]
        spine = spine_by_id.get(sid, {})
        morph = spine.get("morphIndex")
        gloss = ble.get((ch, vs, morph), "") if morph else ""
        gf = fold(gloss)
        enriched.append(
            {
                "sourceTokenId": sid,
                "greek": row.get("greek") or spine.get("greek") or "",
                "gloss": gloss,
                "glossFold": gf,
                "function": is_function_greek(row, gf),
                "morphIndex": morph,
            }
        )

    n_b = len(bundles)
    assignment: list[int | None] = [None] * len(enriched)
    used: set[int] = set()
    cursor = 0

    # Pass 1: content Greek → best unused bundle at/after cursor
    for gi, tok in enumerate(enriched):
        if tok["function"]:
            continue
        best_bi = None
        best_score = 0
        for bi in range(cursor, n_b):
            if bi in used:
                continue
            score = gloss_score(tok["gloss"], bundles[bi])
            if score > best_score:
                best_score = score
                best_bi = bi
            if best_score >= 100:
                break
        if best_bi is None or best_score < 40:
            for bi in range(cursor, n_b):
                if bi not in used:
                    best_bi = bi
                    break
            if best_bi is None:
                best_bi = n_b - 1
        assignment[gi] = best_bi
        used.add(best_bi)
        cursor = max(cursor, best_bi)

    # Pass 2: function Greek → same bundle as next content, else previous, else nearest
    for gi, tok in enumerate(enriched):
        if assignment[gi] is not None:
            continue
        nxt = next((assignment[j] for j in range(gi + 1, len(enriched)) if assignment[j] is not None), None)
        prv = next((assignment[j] for j in range(gi - 1, -1, -1) if assignment[j] is not None), None)
        assignment[gi] = nxt if nxt is not None else prv if prv is not None else 0

    # Build units in Spanish bundle order
    ids_by_bundle: list[list[str]] = [[] for _ in range(n_b)]
    for gi, bi in enumerate(assignment):
        if bi is None:
            continue
        ids_by_bundle[bi].append(enriched[gi]["sourceTokenId"])

    units = []
    for bi, bundle in enumerate(bundles):
        ids = ids_by_bundle[bi]
        if not ids:
            continue
        units.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{len(units)}",
                "surface": bundle["surface"],
                "charStart": bundle["charStart"],
                "charEnd": bundle["charEnd"],
                "sourceTokenIds": ids,
                "method": "gloss-match",
            }
        )
    return units


def main() -> None:
    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
    if isinstance(phrases, dict):
        phrases = phrases.get("phrases") or phrases.get("entries") or []
    spine = json.loads(SPINE.read_text(encoding="utf-8"))
    spine_by_id = {}
    for verse in spine["verses"].values():
        for tok in verse["tokens"]:
            spine_by_id[tok["sourceTokenId"]] = tok
    ble = load_ble_gloss()

    out_links = []
    for p in sorted(phrases, key=lambda x: int(x["phraseIndex"])):
        units = link_phrase(p, spine_by_id, ble)
        out_links.append(
            {
                "phraseIndex": int(p["phraseIndex"]),
                "reference": p["reference"],
                "status": "gloss-seed",
                "units": units,
            }
        )

    doc = {
        "bookId": "1john",
        "textualBasis": "Scrivener 1894 TR",
        "schemaVersion": 1,
        "notes": {
            "seed": (
                "Spanish unit → TR sourceTokenIds. Gloss-matched from BLE es with "
                "monotonic Spanish order (2026-07-24). Hand-refine in translator UI."
            )
        },
        "stats": {
            "phrases": len(out_links),
            "hand": 0,
            "auto": 0,
            "gloss": len(out_links),
            "units": sum(len(link["units"]) for link in out_links),
        },
        "links": out_links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
