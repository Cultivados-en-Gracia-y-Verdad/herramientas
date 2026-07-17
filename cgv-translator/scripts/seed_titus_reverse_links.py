#!/usr/bin/env python3
"""Seed Spanish→TR reverse-interlinear links for Titus.

Writes: translations/tr-spine/titus/titus-reverse-links.json

Phrases 0–11: hand-mapped (high confidence).
Remaining phrases: sequential auto-seed for UI scaffolding (status=auto).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERR = Path("/Users/johnwry/Nextcloud/Documents/GitHub/herramientas")
PHRASES = HERR / "cgv-translator/translations/tr-spine/titus/titus-phrases-tr.json"
OUT = HERR / "cgv-translator/translations/tr-spine/titus/titus-reverse-links.json"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+(?:'[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+)?")

# phraseIndex → list of (spanish_unit_surface, list of trIndex within phrase tokenRows 0-based)
# Surfaces must match a contiguous span in the phrase Spanish (first occurrence).
HAND = {
    0: [
        ("Pablo", [0]),
        ("siervo", [1]),
        ("de Dios", [2]),
    ],
    1: [
        ("apóstol", [0]),
        ("de Cristo", [3]),
        ("Jesús", [2]),
        # δὲ (1): discourse particle, untranslated in this Spanish (not "y", not "de")
    ],
    # Spanish units keep natural articles/flow (la fe, not bare fe).
    # Spanish-only articles attach to the noun; they do not invent a Greek token.
    2: [
        ("según", [0]),
        ("la fe", [1]),
        ("de los elegidos", [2]),
        ("de Dios", [3]),
    ],
    3: [
        ("y", [0]),
        ("el conocimiento", [1]),
        ("de la verdad", [2]),
    ],
    4: [
        ("de acuerdo con", [1]),  # κατ’
        ("la piedad", [0, 2]),  # τῆς εὐσέβειαν (article + noun)
    ],
    5: [
        ("para", [0]),
        ("la esperanza", [1]),
        ("de la vida", [2]),
        ("eterna", [3]),
    ],
    6: [
        ("la cual", [0]),
        ("prometió", [1]),
        ("el Dios", [2, 4]),  # ο … Θεὸς
        ("sin mentira", [3]),
    ],
    7: [
        ("antes", [0]),
        ("de los tiempos", [1]),
        ("eternos", [2]),
    ],
    8: [
        ("y", [1]),
        ("manifestó", [0]),
        ("propio", [3]),
        ("tiempo", [2]),
        ("Su palabra", [5, 6]),  # λόγον αὐτοῦ
        ("la predicación", [8]),
        # τὸν (4), ἐν (7)
    ],
    9: [
        ("la cual", [0]),
        ("me", [2]),
        ("fue confiada", [1]),
        ("según", [3]),
        ("el mandato", [4]),
        ("Salvador", [6]),
        ("nuestro", [7]),
        ("Dios", [8]),
        # τοῦ (5)
    ],
    10: [
        ("Tito", [0]),
        ("hijo", [2]),
        ("genuino", [1]),
        ("según", [3]),
        ("la fe", [5]),
        ("común", [4]),
        ("gracia", [6]),
    ],
    11: [
        ("misericordia y paz", [0, 1]),  # ἔλεος εἰρήνη
        ("de Dios", [2, 3]),  # ἀπὸ Θεοῦ
        ("Padre", [4]),
        ("y", [5]),  # καὶ
        ("del Señor", [6]),  # Κυρίου
        ("Jesús", [7]),
        ("Cristo", [8]),  # Χριστοῦ
        ("nuestro Salvador", [9, 10, 11]),  # τοῦ σωτῆρος ἡμῶν
    ],
    # Titus 1:5 — Por esta razón te dejé en Creta
    12: [
        ("Por esta razón", [0, 1]),  # Τούτου χάριν
        ("te", [3]),  # σε
        ("dejé", [2]),  # κατέλιπόν (TR; not ἀπέλιπόν)
        ("en", [4]),
        ("Creta", [5]),
    ],
    13: [
        ("para que", [0]),  # ἵνα
        ("corrigieras", [3]),  # ἐπιδιορθώσῃ
        ("lo que falta", [1, 2]),  # τὰ λείποντα
    ],
    14: [
        ("y", [0]),  # καὶ
        ("pusieras", [1]),  # καταστήσῃς
        ("ancianos", [4]),  # πρεσβυτέρους
        ("en cada ciudad", [2, 3]),  # κατὰ πόλιν
        ("como", [5]),  # ὡς
        ("yo", [6]),
        ("te", [7]),
        ("ordené", [8]),
    ],
    # Titus 1:6 — si alguien es irreprochable… (phraseIndex 15 = UI phrase 1 of verse)
    15: [
        ("si", [0]),  # εἴ
        ("alguien", [1]),  # τίς
        ("es", [2]),  # ἐστιν
        ("irreprochable", [3]),  # ἀνέγκλητος
        ("marido de una sola mujer", [4, 5, 6]),  # μιᾶς γυναικὸς ἀνήρ
        ("con hijos", [7]),  # τέκνα (ἔχων in next phrase)
    ],
    # Titus 1:6 — fieles… (phraseIndex 16 = UI phrase 2 of verse)
    16: [
        ("fieles", [0, 1]),  # ἔχων πιστά (having faithful children)
        ("que no estén bajo acusación", [2, 3, 4]),  # μὴ ἐν κατηγορίᾳ
        ("de disolución", [5]),  # ἀσωτίας (gen.)
        ("o de ser insubordinados", [6, 7]),  # ἢ ἀνυπότακτα
    ],
    # Titus 1:7 — Porque es necesario… (phraseIndex 17 = UI phrase 1 of verse)
    17: [
        ("Porque", [1]),  # γάρ
        ("es necesario", [0]),  # δεῖ
        ("que el obispo sea irreprochable", [2, 3, 4, 5]),  # τὸν ἐπίσκοπον ἀνέγκλητον εἶναι
        ("como", [6]),  # ὡς
        ("mayordomo de Dios", [7, 8]),  # Θεοῦ οἰκονόμον
    ],
    # Titus 1:8 — sino hospitalario… (phraseIndex 19 = UI phrase 1 of verse)
    19: [
        ("sino", [0]),  # ἀλλὰ
        ("hospitalario", [1]),  # φιλόξενον
        ("amante de lo bueno", [2]),  # φιλάγαθον
        ("prudente", [3]),  # σώφρονα
        ("justo", [4]),  # δίκαιον
        ("santo", [5]),  # ὅσιον
        ("dueño de sí", [6]),  # ἐγκρατῆ
    ],

    # Titus 1:9 — auto-zip was shifted; keep πιστοῦ λόγου as one NP
    20: [
        ("reteniendo", [0]),  # ἀντεχόμενον
        ("la palabra fiel", [5, 6]),  # πιστοῦ λόγου
        ("conforme a", [2]),  # κατὰ
        ("la enseñanza", [3, 4]),  # τὴν διδαχὴν
        # τοῦ (1) unlinked
    ],
    # Titus 1:9 — phrase 2 (phraseIndex 21)
    21: [
        ("para que", [0]),  # ἵνα
        ("sea poderoso", [1, 2]),  # δυνατὸς … ᾖ (TR surface η)
        ("tanto para exhortar", [3, 4]),  # καὶ παρακαλεῖν
        ("con la sana doctrina", [5, 6, 7, 8, 9]),  # ἐν τῇ διδασκαλίᾳ τῇ ὑγιαινούσῃ
        ("como para reprender", [10, 13]),  # καὶ … ἐλέγχειν
        ("a los que contradicen", [11, 12]),  # τοὺς ἀντιλέγοντας
    ],
    # Titus 1:10 — UI phrase 1 (phraseIndex 22)
    22: [
        ("Porque", [1]),  # γάρ
        ("hay", [0]),  # εἰσίν
        ("muchos e insubordinados", [2, 3, 4]),  # πολλοὶ καὶ ἀνυπότακτοι
        ("vanos habladores y", [5, 6]),  # ματαιολόγοι καὶ
    ],
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def find_span(spanish: str, surface: str) -> tuple[int, int] | None:
    """Find surface in spanish; prefer word-boundary-ish match, case-insensitive."""
    # Exact first
    idx = spanish.find(surface)
    if idx >= 0:
        return idx, idx + len(surface)
    # Case-insensitive
    low = spanish.lower()
    target = surface.lower()
    idx = low.find(target)
    if idx >= 0:
        return idx, idx + len(surface)
    # Folded
    # Build map from folded positions carefully — fall back to regex word search
    pattern = re.compile(re.escape(surface), re.IGNORECASE)
    m = pattern.search(spanish)
    if m:
        return m.start(), m.end()
    return None


def tokenize_spanish(spanish: str) -> list[dict]:
    units = []
    for i, m in enumerate(WORD_RE.finditer(spanish)):
        units.append(
            {
                "surface": m.group(0),
                "charStart": m.start(),
                "charEnd": m.end(),
                "fold": fold(m.group(0)),
            }
        )
    return units


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


def auto_link(phrase: dict) -> list[dict]:
    """Sequential content-word zip; attach nearby function words to next Greek token."""
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    if not rows or not spanish.strip():
        return []

    es_units = tokenize_spanish(spanish)
    # Greek content: skip bare articles often? Keep all TR tokens for coverage.
    g_idxs = list(range(len(rows)))
    content_es = [u for u in es_units if u["fold"] not in FUNCTION]
    if not content_es:
        content_es = es_units

    links = []
    # Map content ES → Greek by index proportion
    for i, u in enumerate(content_es):
        if not g_idxs:
            break
        gi = min(int(round(i * (len(g_idxs) - 1) / max(len(content_es) - 1, 1))), len(g_idxs) - 1)
        # Prefer unused: walk forward
        used = {tuple(x["sourceTokenIds"]) for x in links}
        chosen = None
        for offset in range(len(g_idxs)):
            cand = g_idxs[(gi + offset) % len(g_idxs)]
            tid = rows[cand]["sourceTokenId"]
            if (tid,) not in used:
                chosen = cand
                break
        if chosen is None:
            continue
        tid = rows[chosen]["sourceTokenId"]
        links.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{len(links)}",
                "surface": u["surface"],
                "charStart": u["charStart"],
                "charEnd": u["charEnd"],
                "sourceTokenIds": [tid],
                "method": "auto-zip",
            }
        )
    return links


def hand_link(phrase: dict, specs: list) -> list[dict]:
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    links = []
    for surface, row_idxs in specs:
        span = find_span(spanish, surface)
        if span is None:
            raise SystemExit(
                f"phrase {phrase['phraseIndex']}: surface {surface!r} not in {spanish!r}"
            )
        ids = []
        for ri in row_idxs:
            if ri < 0 or ri >= len(rows):
                raise SystemExit(f"phrase {phrase['phraseIndex']}: bad row idx {ri}")
            ids.append(rows[ri]["sourceTokenId"])
        links.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{len(links)}",
                "surface": spanish[span[0] : span[1]],
                "charStart": span[0],
                "charEnd": span[1],
                "sourceTokenIds": ids,
                "method": "hand",
            }
        )
    return links


def main() -> None:
    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
    by_index = {int(p["phraseIndex"]): p for p in phrases}
    out_links = []
    hand_n = auto_n = 0
    for idx in sorted(by_index):
        p = by_index[idx]
        if idx in HAND:
            units = hand_link(p, HAND[idx])
            status = "seeded-hand"
            hand_n += 1
        else:
            units = auto_link(p)
            status = "seeded-auto"
            auto_n += 1
        out_links.append(
            {
                "phraseIndex": idx,
                "reference": p["reference"],
                "status": status,
                "units": units,
            }
        )

    doc = {
        "bookId": "titus",
        "textualBasis": "Scrivener 1894 TR",
        "schemaVersion": 1,
        "notes": (
            "Reverse interlinear: Spanish unit → TR sourceTokenIds. "
            "Phrases 0–11 are hand-seeded; others are auto zip for scaffolding."
        ),
        "stats": {"phrases": len(out_links), "hand": hand_n, "auto": auto_n},
        "links": out_links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)
    # show phrase 0
    print("sample 0:", json.dumps(out_links[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
