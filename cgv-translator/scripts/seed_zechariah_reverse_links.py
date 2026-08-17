#!/usr/bin/env python3
"""Seed Spanish→OSHB reverse-interlinear links for Zechariah.

Hand-only. Unwalked phrases get empty units (status=unwalked).
Never auto-zip. Never gloss DP.

Chapter 1 (phrases 0–20, Protestant 1:1–21): hand-mapped.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERR = Path("/Users/johnwry/Nextcloud/Documents/GitHub/herramientas")
PHRASES = HERR / "cgv-translator/translations/oshb-spine/zechariah/zechariah-phrases.json"
OUT = HERR / "cgv-translator/translations/oshb-spine/zechariah/zechariah-reverse-links.json"

# phraseIndex → list of (spanish_unit_surface, list of tokenRows 0-based)
# Surfaces are found in Spanish order (cursor advances).
HAND = {
    0: [
        ("En el mes", [0]),
        ("octavo", [1]),
        ("en el año", [2]),
        ("segundo", [3]),
        ("de Darío", [4]),
        ("vino", [5]),
        ("palabra", [6]),
        ("de Jehová", [7]),
        ("a", [8]),
        ("Zacarías", [9]),
        ("hijo de", [10]),
        ("Berequías", [11]),
        ("hijo de", [12]),
        ("Iddo", [13]),
        ("el profeta", [14]),
        ("diciendo", [15]),
    ],
    1: [
        ("Se airó", [0]),
        ("Jehová", [1]),
        ("contra", [2]),
        ("sus padres", [3]),
        ("con ira", [4]),
    ],
    2: [
        ("Y les dirás", [0, 1]),
        ("Así", [2]),
        ("dice", [3]),
        ("Jehová", [4]),
        ("de los ejércitos", [5]),
        ("Vuélvanse", [6]),
        ("a mí", [7]),
        ("declara", [8]),
        ("Jehová", [9]),
        ("de los ejércitos", [10]),
        ("y yo me volveré", [11]),
        ("a ustedes", [12]),
        ("dice", [13]),
        ("Jehová", [14]),
        ("de los ejércitos", [15]),
    ],
    3: [
        ("No", [0]),
        ("sean", [1]),
        ("como sus padres", [2]),
        ("a quienes", [3, 5]),
        ("los primeros profetas", [6, 7]),
        ("proclamaron", [4]),
        ("diciendo", [8]),
        ("Así", [9]),
        ("dice", [10]),
        ("Jehová", [11]),
        ("de los ejércitos", [12]),
        ("Vuélvanse", [13]),
        ("ahora", [14]),
        ("de sus malos caminos", [15, 16]),
        ("y de sus malas obras", [17, 18]),
        ("Y no", [19]),
        ("oyeron", [20]),
        ("ni", [21]),
        ("prestaron atención", [22]),
        ("a mí", [23]),
        ("declara", [24]),
        ("Jehová", [25]),
    ],
    4: [
        ("Sus padres", [0]),
        ("dónde", [1]),
        ("están", [2]),
        ("Y los profetas", [3]),
        ("para siempre", [4]),
        ("vivirán", [5]),
    ],
    5: [
        ("Pero", [0]),
        ("mis palabras", [1]),
        ("y mis estatutos", [2]),
        ("que", [3]),
        ("mandé", [4]),
        ("a mis siervos", [5, 6]),
        ("los profetas", [7]),
        ("no", [8]),
        ("alcanzaron", [9]),
        ("a sus padres", [10]),
        ("Y se volvieron", [11]),
        ("y dijeron", [12]),
        ("Como", [13]),
        ("Jehová", [15]),
        ("de los ejércitos", [16]),
        ("se propuso", [14]),
        ("hacer", [17]),
        ("con nosotros", [18]),
        ("conforme a nuestros caminos", [19]),
        ("y conforme a nuestras obras", [20]),
        ("así", [21]),
        ("hizo", [22]),
        ("con nosotros", [23]),
    ],
    6: [
        ("En el día", [0]),
        ("veinticuatro", [1, 2]),
        ("del mes", [5]),
        ("undécimo", [3, 4]),
        ("que es", [6]),
        ("el mes", [7]),
        ("de Sebat", [8]),
        ("en el año", [9]),
        ("segundo", [10]),
        ("de Darío", [11]),
        ("vino", [12]),
        ("palabra", [13]),
        ("de Jehová", [14]),
        ("a", [15]),
        ("Zacarías", [16]),
        ("hijo de", [17]),
        ("Berequías", [18]),
        ("hijo de", [19]),
        ("Iddo", [20]),
        ("el profeta", [21]),
        ("diciendo", [22]),
    ],
    7: [
        ("Vi", [0]),
        ("de noche", [1]),
        ("y he aquí", [2]),
        ("un hombre", [3]),
        ("cabalgando", [4]),
        ("sobre", [5]),
        ("un caballo", [6]),
        ("rojo", [7]),
        ("y él", [8]),
        ("estaba de pie", [9]),
        ("entre", [10]),
        ("los mirtos", [11]),
        ("que", [12]),
        ("había en la hondonada", [13]),
        ("y detrás de él", [14]),
        ("caballos", [15]),
        ("rojos", [16]),
        ("alazanes", [17]),
        ("y blancos", [18]),
    ],
    8: [
        ("Y dije", [0]),
        ("Qué", [1]),
        ("son estos", [2]),
        ("señor mío", [3]),
        ("Y me dijo", [4, 5]),
        ("el ángel", [6]),
        ("que hablaba", [7]),
        ("conmigo", [8]),
        ("Yo", [9]),
        ("te mostraré", [10]),
        ("qué", [11]),
        ("son", [12]),
        ("estos", [13]),
    ],
    9: [
        ("Y respondió", [0]),
        ("el hombre", [1]),
        ("que estaba de pie", [2]),
        ("entre", [3]),
        ("los mirtos", [4]),
        ("y dijo", [5]),
        ("Estos", [6]),
        ("son los que", [7]),
        ("Jehová", [9]),
        ("envió", [8]),
        ("a recorrer", [10]),
        ("la tierra", [11]),
    ],
    10: [
        ("Y respondieron", [0]),
        ("al ángel", [1, 2]),
        ("de Jehová", [3]),
        ("que estaba de pie", [4]),
        ("entre", [5]),
        ("los mirtos", [6]),
        ("y dijeron", [7]),
        ("Hemos recorrido", [8]),
        ("la tierra", [9]),
        ("y he aquí", [10]),
        ("toda", [11]),
        ("la tierra", [12]),
        ("está asentada", [13]),
        ("y quieta", [14]),
    ],
    11: [
        ("Y respondió", [0]),
        ("el ángel", [1]),
        ("de Jehová", [2]),
        ("y dijo", [3]),
        ("Jehová", [4]),
        ("de los ejércitos", [5]),
        ("hasta cuándo", [6, 7]),
        ("tú", [8]),
        ("no", [9]),
        ("tendrás compasión", [10]),
        ("de Jerusalén", [11, 12]),
        ("y", [13]),
        ("de las ciudades", [14]),
        ("de Judá", [15]),
        ("contra las cuales", [16]),
        ("te has indignado", [17]),
        ("estos", [18]),
        ("setenta", [19]),
        ("años", [20]),
    ],
    12: [
        ("Y respondió", [0]),
        ("Jehová", [1]),
        ("al ángel", [2, 3]),
        ("que hablaba", [4]),
        ("conmigo", [5]),
        ("palabras", [6]),
        ("buenas", [7]),
        ("palabras", [8]),
        ("de consuelo", [9]),
    ],
    13: [
        ("Y me dijo", [0, 1]),
        ("el ángel", [2]),
        ("que hablaba", [3]),
        ("conmigo", [4]),
        ("Proclama", [5]),
        ("diciendo", [6]),
        ("Así", [7]),
        ("dice", [8]),
        ("Jehová", [9]),
        ("de los ejércitos", [10]),
        ("Celé", [11]),
        ("por Jerusalén", [12]),
        ("y por Sión", [13]),
        ("con gran celo", [14, 15]),
    ],
    14: [
        ("Y con gran ira", [0, 1]),
        ("estoy yo", [2]),
        ("airado", [3]),
        ("contra", [4]),
        ("las naciones", [5]),
        ("que están tranquilas", [6]),
        ("las cuales", [7]),
        ("yo", [8]),
        ("airé", [9]),
        ("un poco", [10]),
        ("y ellas", [11]),
        ("ayudaron", [12]),
        ("para mal", [13]),
    ],
    15: [
        ("Por tanto", [0]),
        ("así", [1]),
        ("dice", [2]),
        ("Jehová", [3]),
        ("Me he vuelto", [4]),
        ("a Jerusalén", [5]),
        ("con compasiones", [6]),
        ("mi casa", [7]),
        ("será edificada", [8]),
        ("en ella", [9]),
        ("declara", [10]),
        ("Jehová", [11]),
        ("de los ejércitos", [12]),
        ("y el cordel", [13]),
        ("será tendido", [14]),
        ("sobre", [15]),
        ("Jerusalén", [16]),
    ],
    16: [
        ("Proclama", [1]),
        ("otra vez", [0]),
        ("diciendo", [2]),
        ("Así", [3]),
        ("dice", [4]),
        ("Jehová", [5]),
        ("de los ejércitos", [6]),
        ("Aún", [7]),
        ("rebosarán", [8]),
        ("mis ciudades", [9]),
        ("de bien", [10]),
        ("y aún consolará", [11, 13]),
        ("Jehová", [12]),
        ("a Sión", [14, 15]),
        ("y aún escogerá", [16, 17]),
        ("a Jerusalén", [18]),
    ],
    17: [
        ("Y alcé", [0]),
        ("mis ojos", [1, 2]),
        ("y vi", [3]),
        ("y he aquí", [4]),
        ("cuatro", [5]),
        ("cuernos", [6]),
    ],
    18: [
        ("Y dije", [0]),
        ("al ángel", [1, 2]),
        ("que hablaba", [3]),
        ("conmigo", [4]),
        ("Qué", [5]),
        ("son estos", [6]),
        ("Y me dijo", [7, 8]),
        ("Estos", [9]),
        ("son los cuernos", [10]),
        ("que", [11]),
        ("dispersaron", [12]),
        ("a Judá", [13, 14]),
        ("a Israel", [15, 16]),
        ("y a Jerusalén", [17]),
    ],
    19: [
        ("Y me mostró", [0]),
        ("Jehová", [1]),
        ("cuatro", [2]),
        ("artesanos", [3]),
    ],
    20: [
        ("Y dije", [0]),
        ("Qué", [1]),
        ("vienen", [3]),
        ("estos", [2]),
        ("a hacer", [4]),
        ("Y dijo", [5]),
        ("diciendo", [6]),
        ("Estos", [7]),
        ("son los cuernos", [8]),
        ("que", [9]),
        ("dispersaron", [10]),
        ("a Judá", [11, 12]),
        ("de modo que", [13]),
        ("nadie", [14, 15]),
        ("alzó", [16]),
        ("su cabeza", [17]),
        ("y vinieron", [18]),
        ("estos", [19]),
        ("para aterrarlos", [20, 21]),
        ("para derribar", [22]),
        ("los cuernos", [23, 24]),
        ("de las naciones", [25]),
        ("que alzan", [26]),
        ("cuerno", [27]),
        ("contra", [28]),
        ("la tierra", [29]),
        ("de Judá", [30]),
        ("para dispersarla", [31]),
    ],
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def find_span(spanish: str, surface: str, start: int = 0) -> tuple[int, int] | None:
    idx = spanish.find(surface, start)
    if idx >= 0:
        return idx, idx + len(surface)
    low = spanish.lower()
    target = surface.lower()
    idx = low.find(target, start)
    if idx >= 0:
        return idx, idx + len(surface)
    pattern = re.compile(re.escape(surface), re.IGNORECASE)
    m = pattern.search(spanish, start)
    if m:
        return m.start(), m.end()
    return None


def hand_link(phrase: dict, specs: list) -> list[dict]:
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    links = []
    cursor = 0
    for surface, row_idxs in specs:
        span = find_span(spanish, surface, cursor)
        if span is None:
            raise SystemExit(
                f"phrase {phrase['phraseIndex']}: surface {surface!r} not in {spanish!r} after {cursor}"
            )
        ids = []
        for ri in row_idxs:
            if ri < 0 or ri >= len(rows):
                raise SystemExit(f"phrase {phrase['phraseIndex']}: bad row idx {ri} (n={len(rows)})")
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
        cursor = span[1]
    return links


def main() -> None:
    doc_in = json.loads(PHRASES.read_text(encoding="utf-8"))
    phrases = doc_in["phrases"] if isinstance(doc_in, dict) else doc_in
    by_index = {int(p["phraseIndex"]): p for p in phrases}
    out_links = []
    hand_n = unwalked_n = 0
    uncovered = []
    for idx in sorted(by_index):
        p = by_index[idx]
        ref = p["reference"]
        if idx in HAND:
            units = hand_link(p, HAND[idx])
            status = "seeded-hand"
            hand_n += 1
            linked = {tid for u in units for tid in u["sourceTokenIds"]}
            rows = p.get("tokenRows") or []
            missing = [
                r["sourceTokenId"] + " " + (r.get("surface") or r.get("greek") or "")
                for r in rows
                if r["sourceTokenId"] not in linked
            ]
            if missing:
                uncovered.append((idx, ref, missing))
        else:
            units = []
            status = "unwalked"
            unwalked_n += 1
        out_links.append(
            {
                "phraseIndex": idx,
                "reference": ref,
                "status": status,
                "units": units,
            }
        )

    doc = {
        "bookId": "zechariah",
        "textualBasis": "OSHB/WLC",
        "schemaVersion": 1,
        "verseNumbering": "Protestant",
        "notes": (
            "Reverse interlinear: Spanish unit → OSHB sourceTokenIds. "
            "Chapter 1 (phrases 0–20, Protestant 1:1–21 including 1:18–21) is hand-seeded. "
            "Remaining phrases are unwalked. No auto-zip. No gloss DP."
        ),
        "stats": {"phrases": len(out_links), "hand": hand_n, "unwalked": unwalked_n},
        "links": out_links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)
    print("hand uncovered source tokens:")
    for idx, ref, missing in uncovered:
        print(f"  [{idx}] {ref}: {missing}")


if __name__ == "__main__":
    main()
