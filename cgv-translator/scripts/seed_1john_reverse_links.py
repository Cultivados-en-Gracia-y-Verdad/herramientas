#!/usr/bin/env python3
"""Seed Spanish→TR reverse-interlinear links for 1 John.

Writes: translations/tr-spine/1john/1john-reverse-links.json

All phrases start as auto-seed (function words attached to the next content
word) so Observer Structure can compile. Hand-refine in the translator UI
and re-run compile-lbf-alignment-judas.py in cgv-reader.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERR = Path("/Users/johnwry/Nextcloud/Documents/GitHub/herramientas")
PHRASES = HERR / "cgv-translator/translations/tr-spine/1john/1john-phrases-tr.json"
OUT = HERR / "cgv-translator/translations/tr-spine/1john/1john-reverse-links.json"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+(?:'[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+)?")

FUNCTION = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "de",
    "del",
    "al",
    "a",
    "en",
    "por",
    "para",
    "con",
    "sin",
    "que",
    "y",
    "e",
    "o",
    "u",
    "su",
    "sus",
    "lo",
}


def fold(value: str) -> str:
    value = value.lower().strip()
    value = "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w]", "", value)


def tokenize_spanish(spanish: str) -> list[dict]:
    units = []
    for m in WORD_RE.finditer(spanish):
        units.append(
            {
                "surface": m.group(0),
                "charStart": m.start(),
                "charEnd": m.end(),
                "fold": fold(m.group(0)),
            }
        )
    return units


def auto_link(phrase: dict) -> list[dict]:
    """Zip Spanish content units (with leading function words) onto TR tokens."""
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    if not rows or not spanish.strip():
        return []

    es_units = tokenize_spanish(spanish)
    if not es_units:
        return []

    # Bundle leading function words onto the next content word.
    bundles: list[dict] = []
    pending: list[dict] = []
    for u in es_units:
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
            }
        )
    if pending and bundles:
        # Trailing function words attach to the last bundle.
        last = bundles[-1]
        last["surface"] = spanish[last["charStart"] : pending[-1]["charEnd"]]
        last["charEnd"] = pending[-1]["charEnd"]
    elif pending:
        bundles.append(
            {
                "surface": spanish[pending[0]["charStart"] : pending[-1]["charEnd"]],
                "charStart": pending[0]["charStart"],
                "charEnd": pending[-1]["charEnd"],
            }
        )

    # Assign every TR token to a Spanish bundle (Structure needs Morph coverage).
    # When Greek is denser than Spanish, several tokens share one surface.
    n_b = len(bundles)
    n_g = len(rows)
    assigned: list[list[str]] = [[] for _ in range(n_b)]
    for gi in range(n_g):
        bi = min(int(gi * n_b / n_g), n_b - 1) if n_b else 0
        assigned[bi].append(rows[gi]["sourceTokenId"])

    links = []
    for i, bundle in enumerate(bundles):
        ids = assigned[i]
        if not ids:
            continue
        links.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{len(links)}",
                "surface": bundle["surface"],
                "charStart": bundle["charStart"],
                "charEnd": bundle["charEnd"],
                "sourceTokenIds": ids,
                "method": "auto-zip",
            }
        )
    return links


def main() -> None:
    raw = json.loads(PHRASES.read_text(encoding="utf-8"))
    phrases = raw.get("phrases") if isinstance(raw, dict) else raw
    by_index = {int(p["phraseIndex"]): p for p in phrases}
    out_links = []
    for idx in sorted(by_index):
        p = by_index[idx]
        units = auto_link(p)
        out_links.append(
            {
                "phraseIndex": idx,
                "reference": p["reference"],
                "status": "seeded-auto",
                "units": units,
            }
        )

    doc = {
        "bookId": "1john",
        "textualBasis": "Scrivener 1894 TR",
        "schemaVersion": 1,
        "notes": (
            "Reverse interlinear: Spanish unit → TR sourceTokenIds. "
            "All phrases auto-seeded (articles/prepositions attached to content words). "
            "Hand-refine in translator UI; Greek particles may stay unlinked."
        ),
        "stats": {
            "phrases": len(out_links),
            "hand": 0,
            "auto": len(out_links),
            "units": sum(len(link["units"]) for link in out_links),
        },
        "links": out_links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)
    print("sample 0:", json.dumps(out_links[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
