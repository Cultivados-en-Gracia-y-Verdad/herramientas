#!/usr/bin/env python3
"""Rebuild Titus phrase map + phrases.json with clause-level spans.

Hand-segmented Titus 1 (including 1:12–1:16). Chapters 2–3 split on
Greek punctuation. Seeds Spanish from prior approved phrases / BLE glosses.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERR = ROOT.parent
MORPH = HERR / "MNA" / "SOURCES" / "MorphGNT" / "77-Tit-morphgnt.txt"
BLE = HERR / "Biblia-BLE" / "output" / "tito.ble.md"
OLD_PHRASES = ROOT / "translations" / "titus-phrases.json"
OUT_MAP = ROOT / "translations" / "phrase-maps" / "titus.json"
OUT_PHRASES = ROOT / "translations" / "titus-phrases.json"
OUT_DOC = ROOT / "translations" / "titus.md"
LBF_OUT = HERR / "Biblia-LBF" / "translation" / "nt" / "titus.md"
STRONGS = HERR / "MNA" / "datasets" / "rules" / "grc_lemma_strongs.json"

BOOK_CODE = 56
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# (chapter, verse) -> list of (start, end) inclusive 1-based token positions
# Plus optional spanish override for that span.
CH1_SEGMENTS: dict[tuple[int, int], list[tuple[int, int, str]]] = {
    (1, 1): [
        (1, 3, "Pablo, siervo de Dios,"),
        (4, 7, "apóstol de Cristo Jesús,"),
        (8, 11, "según la fe de los elegidos de Dios"),
        (12, 14, "y el conocimiento de la verdad"),
        (15, 17, "de acuerdo con la piedad"),
    ],
    (1, 2): [
        (1, 4, "para la esperanza de la vida eterna,"),
        (5, 9, "la cual prometió el Dios que no miente,"),
        (10, 12, "antes de los tiempos eternos,"),
    ],
    (1, 3): [
        (1, 9, "y a su propio tiempo manifestó su palabra por la predicación,"),
        (10, 18, "la cual me fue confiada según el mandato de Dios nuestro Salvador."),
    ],
    (1, 4): [
        (1, 7, "A Tito, hijo genuino según la fe común:"),
        (8, 18, "gracia y paz de Dios Padre y de Cristo Jesús nuestro Salvador."),
    ],
    (1, 5): [
        (1, 6, "Por esta razón te dejé en Creta,"),
        (7, 12, "para que corrigieras lo que falta"),
        (13, 19, "y pusieras ancianos en cada ciudad, como yo te ordené:"),
    ],
    (1, 6): [
        (1, 8, "si alguien es irreprochable, marido de una sola mujer,"),
        (9, 16, "teniendo hijos fieles, que no estén bajo acusación de disolución o de ser insubordinados."),
    ],
    (1, 7): [
        (1, 9, "Porque es necesario que el obispo sea irreprochable como administrador de Dios,"),
        (10, 19, "no soberbio, no iracundo, no bebedor, no violento, no codicioso de ganancia deshonesta,"),
    ],
    (1, 8): [
        (1, 7, "sino hospitalario, amante de lo bueno, prudente, justo, santo, dueño de sí;"),
    ],
    (1, 9): [
        (1, 7, "reteniendo la palabra fiel conforme a la enseñanza,"),
        (8, 21, "para que sea poderoso tanto para exhortar con la sana doctrina como para reprender a los que contradicen."),
    ],
    (1, 10): [
        (1, 7, "Porque hay muchos insubordinados, vanos habladores y engañadores,"),
        (8, 13, "sobre todo los de la circuncisión,"),
    ],
    (1, 11): [
        (1, 3, "a quienes es necesario tapar la boca,"),
        (4, 7, "que trastornan casas enteras"),
        (8, 14, "enseñando lo que no conviene por causa de ganancia vergonzosa."),
    ],
    (1, 12): [
        (1, 7, "Dijo uno de ellos, su propio profeta:"),
        (8, 14, "«Los cretenses son siempre mentirosos, malas bestias, vientres ociosos»."),
    ],
    (1, 13): [
        (1, 5, "Este testimonio es verdadero."),
        (6, 10, "Por esta razón repréndelos severamente,"),
        (11, 16, "para que sean sanos en la fe,"),
    ],
    (1, 14): [
        (1, 10, "no prestando atención a mitos judíos y a mandamientos de hombres que se apartan de la verdad."),
    ],
    (1, 15): [
        (1, 3, "Todas las cosas son puras para los puros;"),
        (4, 12, "pero para los contaminados e incrédulos nada es puro,"),
        (13, 20, "sino que tanto su mente como su conciencia están contaminadas."),
    ],
    (1, 16): [
        (1, 3, "Profesan conocer a Dios,"),
        (4, 7, "pero con las obras lo niegan,"),
        (8, 17, "siendo abominables e inobedientes y reprobados para toda buena obra."),
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
        m = re.match(r"^Tito\s+(\d+):(\d+)\s+(.+)$", line)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()
    return out


def split_on_punct(tokens: list[dict]) -> list[tuple[int, int]]:
    """Return 1-based inclusive spans split after punctuation tokens."""
    spans: list[tuple[int, int]] = []
    start = 1
    for i, tok in enumerate(tokens, start=1):
        punct = bool(re.search(r"[,.;·:!?]$", tok["surface_punct"]))
        if punct or i == len(tokens):
            spans.append((start, i))
            start = i + 1
    if start <= len(tokens):
        spans.append((start, len(tokens)))
    # merge tiny trailing fragments into previous
    merged: list[tuple[int, int]] = []
    for a, b in spans:
        if merged and (b - a + 1) <= 2 and (merged[-1][1] - merged[-1][0] + 1) < 12:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged or [(1, len(tokens))]


def ble_seed_for_span(ble: str, start: int, end: int, n_tokens: int) -> str:
    if not ble:
        return ""
    words = ble.split()
    if not words or n_tokens <= 0:
        return ble
    # proportional slice
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

    for (ch, vs) in sorted(verses.keys()):
        tokens = verses[(ch, vs)]
        segs = CH1_SEGMENTS.get((ch, vs))
        if segs:
            spans = [(a, b, es) for a, b, es in segs]
        else:
            spans = [(a, b, "") for a, b in split_on_punct(tokens)]

        for local_i, (a, b, es) in enumerate(spans):
            ids = [token_id(ch, vs, p) for p in range(a, b + 1)]
            greek = " ".join(tokens[p - 1]["surface"] for p in range(a, b + 1))
            spanish = es.strip()
            status = "approved" if spanish else "draft"
            if not spanish:
                spanish = ble_seed_for_span(ble.get((ch, vs), ""), a, b, len(tokens))
                status = "draft"

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
                    "reference": f"Titus {ch}:{vs}",
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
                    "reference": f"Titus {ch}:{vs}",
                    "phraseIndex": phrase_index,
                    "greek": greek,
                    "spanish": spanish,
                    "sourceTokenIds": ids,
                    "tokenRows": token_rows,
                    "rv1909Text": "",
                    "bleText": ble_seed_for_span(ble.get((ch, vs), ""), a, b, len(tokens)),
                    "suggestionSource": "lbf-approved" if status == "approved" else "ble-seed",
                    "approval": {
                        "status": status,
                        "approvedAt": NOW if status == "approved" else "",
                        "approvedBy": "lbf-rebuild" if status == "approved" else "",
                    },
                    "gates": None,
                    "aiProposal": None,
                }
            )
            phrase_index += 1

    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAP.write_text(
        json.dumps({"book": "titus", "version": 1, "phrases": phrase_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_PHRASES.write_text(json.dumps(phrases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Verse-structured docs
    by_verse: dict[tuple[int, int], list[str]] = defaultdict(list)
    for p in phrases:
        if p["approval"]["status"] != "approved":
            continue
        m = re.search(r"(\d+):(\d+)$", p["reference"])
        if not m:
            continue
        by_verse[(int(m.group(1)), int(m.group(2)))].append(p["spanish"])

    lines = ["# Tito", "", "> La Biblia Fiel — Tito (borrador de trabajo).", ""]
    cur_ch = None
    for (ch, vs) in sorted(by_verse.keys()):
        if ch != cur_ch:
            cur_ch = ch
            lines += [f"## Capítulo {ch}", ""]
        text = " ".join(by_verse[(ch, vs)]).strip()
        lines += [f"### {ch}:{vs}", "", text, ""]
    doc = "\n".join(lines).rstrip() + "\n"
    OUT_DOC.write_text(doc, encoding="utf-8")
    LBF_OUT.parent.mkdir(parents=True, exist_ok=True)
    LBF_OUT.write_text(doc, encoding="utf-8")

    approved = sum(1 for p in phrases if p["approval"]["status"] == "approved")
    print(f"phrases: {len(phrases)} (approved {approved}, draft {len(phrases) - approved})")
    print(f"wrote {OUT_MAP}")
    print(f"wrote {OUT_PHRASES}")
    print(f"wrote {OUT_DOC}")
    print(f"wrote {LBF_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
