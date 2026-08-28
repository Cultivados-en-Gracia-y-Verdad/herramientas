#!/usr/bin/env python3
"""Rebuild Philemon phrase map + phrases.json with preliminary LBF Spanish."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERR = ROOT.parent
MORPH = HERR / "MNA" / "SOURCES" / "MorphGNT" / "78-Phm-morphgnt.txt"
BLE = HERR / "Biblia-BLE" / "output" / "filemon.ble.md"
OUT_MAP = ROOT / "translations" / "phrase-maps" / "philemon.json"
OUT_PHRASES = ROOT / "translations" / "philemon-phrases.json"
OUT_DOC = ROOT / "translations" / "filemon.md"
LBF_OUT = HERR / "Biblia-LBF" / "translation" / "nt" / "filemon.md"
STRONGS = HERR / "MNA" / "datasets" / "rules" / "grc_lemma_strongs.json"

BOOK_CODE = 57
BOOK_LABEL = "Philemon"
DOC_TITLE = "Filemón"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# (chapter, verse) -> list of (start, end, spanish)
BOOK_SEGMENTS: dict[tuple[int, int], list[tuple[int, int, str]]] = {
    (1, 1): [
        (1, 4, "Pablo, prisionero de Cristo Jesús,"),
        (5, 8, "y Timoteo el hermano,"),
        (9, 14, "a Filemón, el amado y colaborador nuestro,"),
    ],
    (1, 2): [
        (1, 4, "y a Apia la hermana,"),
        (5, 9, "y a Arquipo nuestro compañero de milicia,"),
        (10, 15, "y a la iglesia en tu casa:"),
    ],
    (1, 3): [
        (1, 12, "Gracia a ustedes y paz de Dios nuestro Padre y del Señor Jesús Cristo."),
    ],
    (1, 4): [
        (1, 5, "Doy gracias a mi Dios siempre,"),
        (6, 12, "haciendo mención de ti en mis oraciones,"),
    ],
    (1, 5): [
        (
            1,
            18,
            "oyendo de tu amor y de la fe que tienes hacia el Señor Jesús y hacia todos los santos,",
        ),
    ],
    (1, 6): [
        (
            1,
            17,
            "para que la comunión de tu fe sea eficaz en el conocimiento de todo lo bueno que hay en nosotros hacia Cristo.",
        ),
    ],
    (1, 7): [
        (1, 10, "Porque tuve mucho gozo y consolación por tu amor,"),
        (11, 19, "porque las entrañas de los santos han hallado reposo por medio de ti, hermano."),
    ],
    (1, 8): [
        (1, 10, "Por lo cual, teniendo mucha franqueza en Cristo para mandarte lo que conviene,"),
    ],
    (1, 9): [
        (1, 5, "por amor más bien te exhorto,"),
        (6, 16, "siendo tal como Pablo, anciano, y ahora también prisionero de Cristo Jesús;"),
    ],
    (1, 10): [
        (1, 12, "te exhorto acerca de mi hijo, a quien engendré en las cadenas, Onésimo,"),
    ],
    (1, 11): [
        (1, 10, "el que en otro tiempo te fue inútil, pero ahora a ti y a mí útil,"),
    ],
    (1, 12): [
        (1, 9, "a quien te envié de vuelta, a él mismo, esto es, mis propias entrañas;"),
    ],
    (1, 13): [
        (1, 6, "a quien yo quería retener junto a mí,"),
        (7, 16, "para que en lugar tuyo me sirviera en las cadenas del evangelio;"),
    ],
    (1, 14): [
        (1, 8, "pero sin tu parecer no quise hacer nada,"),
        (9, 20, "para que tu bien no sea como por necesidad, sino por voluntad."),
    ],
    (1, 15): [
        (1, 7, "Porque quizás por esto se apartó por un tiempo,"),
        (8, 11, "para que lo recibas para siempre,"),
    ],
    (1, 16): [
        (1, 8, "ya no como siervo, sino más que siervo, hermano amado,"),
        (9, 20, "especialmente para mí, pero cuánto más para ti, tanto en la carne como en el Señor."),
    ],
    (1, 17): [
        (1, 9, "Si, pues, me tienes por compañero, recíbelo como a mí."),
    ],
    (1, 18): [
        (1, 10, "Pero si en algo te hizo injusticia o te debe, esto cárgamelo a mí."),
    ],
    (1, 19): [
        (1, 8, "Yo, Pablo, lo escribí de mi mano, yo lo pagaré;"),
        (9, 17, "para no decirte que aun tú mismo te me debes."),
    ],
    (1, 20): [
        (1, 7, "Sí, hermano, que yo reciba de ti este provecho en el Señor;"),
        (8, 13, "da reposo a mis entrañas en Cristo."),
    ],
    (1, 21): [
        (1, 6, "Confiado en tu obediencia te escribí,"),
        (7, 13, "sabiendo que harás aun más de lo que digo."),
    ],
    (1, 22): [
        (1, 6, "Y al mismo tiempo, prepárame también hospedaje;"),
        (
            7,
            15,
            "porque espero que por medio de las oraciones de ustedes me sea concedido a ustedes.",
        ),
    ],
    (1, 23): [
        (1, 9, "Te saluda Epafras, mi compañero de prisión en Cristo Jesús,"),
    ],
    (1, 24): [
        (1, 7, "Marcos, Aristarco, Demas, Lucas, mis colaboradores."),
    ],
    (1, 25): [
        (1, 10, "La gracia del Señor Jesús Cristo sea con el espíritu de ustedes."),
    ],
}


def token_id(ch: int, vs: int, pos: int) -> str:
    return f"n{BOOK_CODE}{ch:03d}{vs:03d}{pos:03d}"


def parse_morph(path: Path) -> dict[tuple[int, int], list[dict]]:
    verses: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        vid = parts[0]
        ch, vs = int(vid[2:4]), int(vid[4:6])
        verses[(ch, vs)].append(
            {
                "pos": parts[1],
                "parsing": parts[2],
                "surface_punct": parts[3],
                "surface": parts[4],
                "norm": parts[5],
                "lemma": parts[6],
            }
        )
    return verses


def load_strongs() -> dict[str, str]:
    if not STRONGS.is_file():
        return {}
    return {k: str(v).upper() for k, v in json.loads(STRONGS.read_text(encoding="utf-8")).items()}


def fold(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def strongs_for(lemma: str, index: dict[str, str]) -> str:
    if lemma in index:
        return index[lemma]
    f = fold(lemma)
    for k, v in index.items():
        if fold(k) == f:
            return v
    return ""


def load_ble() -> dict[tuple[int, int], str]:
    out: dict[tuple[int, int], str] = {}
    if not BLE.is_file():
        return out
    for line in BLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^Filemon\s+(\d+):(\d+)\s+(.+)$", line)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()
    return out


def ble_seed_for_span(ble: str, start: int, end: int, n_tokens: int) -> str:
    if not ble:
        return ""
    words = ble.split()
    if not words or n_tokens <= 0:
        return ble
    a = max(0, int((start - 1) / n_tokens * len(words)))
    b = min(len(words), int(end / n_tokens * len(words)))
    if b <= a:
        b = min(len(words), a + 1)
    return " ".join(words[a:b]).replace("•", " ").strip()


def main() -> int:
    verses = parse_morph(MORPH)
    strongs_index = load_strongs()
    ble = load_ble()

    phrase_map: list[dict] = []
    phrases: list[dict] = []
    phrase_index = 0
    missing = []

    for (ch, vs) in sorted(verses.keys()):
        tokens = verses[(ch, vs)]
        segs = BOOK_SEGMENTS.get((ch, vs))
        if not segs:
            missing.append(f"{ch}:{vs}")
            continue
        for local_i, (a, b, es) in enumerate(segs):
            ids = [token_id(ch, vs, p) for p in range(a, b + 1)]
            greek = " ".join(tokens[p - 1]["surface"] for p in range(a, b + 1))
            spanish = es.strip()
            token_rows = []
            for p in range(a, b + 1):
                tok = tokens[p - 1]
                token_rows.append(
                    {
                        "sourceTokenId": token_id(ch, vs, p),
                        "greek": tok["surface"],
                        "lemma": tok["lemma"],
                        "strongs": strongs_for(tok["lemma"], strongs_index),
                        "rmac": f"{tok['pos']}{tok['parsing'].strip('-')}",
                        "morphology": "",
                        "ble": "",
                        "rv1909": "",
                    }
                )

            phrase_map.append(
                {
                    "reference": f"{BOOK_LABEL} {ch}:{vs}",
                    "phraseIndex": phrase_index,
                    "localIndex": local_i,
                    "start": a,
                    "end": b,
                    "sourceTokenIds": ids,
                    "greek": greek,
                }
            )
            phrases.append(
                {
                    "reference": f"{BOOK_LABEL} {ch}:{vs}",
                    "phraseIndex": phrase_index,
                    "greek": greek,
                    "spanish": spanish,
                    "sourceTokenIds": ids,
                    "tokenRows": token_rows,
                    "rv1909Text": "",
                    "bleText": ble_seed_for_span(ble.get((ch, vs), ""), a, b, len(tokens)),
                    "suggestionSource": "lbf-preliminary",
                    "approval": {
                        "status": "preliminary",
                        "approvedAt": "",
                        "approvedBy": "lbf-rebuild",
                    },
                    "gates": None,
                    "aiProposal": None,
                }
            )
            phrase_index += 1

    if missing:
        raise SystemExit(f"Missing segments for: {', '.join(missing)}")

    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAP.write_text(
        json.dumps({"book": "philemon", "version": 1, "phrases": phrase_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_PHRASES.write_text(json.dumps(phrases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    by_verse: dict[tuple[int, int], list[str]] = defaultdict(list)
    for p in phrases:
        m = re.search(r"(\d+):(\d+)$", p["reference"])
        if not m:
            continue
        by_verse[(int(m.group(1)), int(m.group(2)))].append(p["spanish"])

    lines = [f"# {DOC_TITLE}", "", f"> La Biblia Fiel — {DOC_TITLE} (borrador preliminar).", ""]
    cur_ch = None
    for (ch, vs) in sorted(by_verse.keys()):
        if ch != cur_ch:
            cur_ch = ch
            lines += [f"## Capítulo {ch}", ""]
        lines += [f"### {ch}:{vs}", "", " ".join(by_verse[(ch, vs)]).strip(), ""]
    doc = "\n".join(lines).rstrip() + "\n"
    OUT_DOC.write_text(doc, encoding="utf-8")
    LBF_OUT.parent.mkdir(parents=True, exist_ok=True)
    LBF_OUT.write_text(doc, encoding="utf-8")

    print(f"phrases: {len(phrases)} (preliminary {len(phrases)})")
    print(f"wrote {OUT_MAP}")
    print(f"wrote {OUT_PHRASES}")
    print(f"wrote {OUT_DOC}")
    print(f"wrote {LBF_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
