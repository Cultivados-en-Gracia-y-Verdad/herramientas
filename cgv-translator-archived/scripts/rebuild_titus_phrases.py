#!/usr/bin/env python3
"""Rebuild Titus phrase map + phrases.json with clause-level spans.

Hand-segmented Titus 1–3 with preliminary LBF Spanish.
Any verse without an explicit segment list falls back to punctuation splits
seeded from BLE (should not happen once BOOK_SEGMENTS is complete).
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
# Plus Spanish for that span (preliminary LBF).
BOOK_SEGMENTS: dict[tuple[int, int], list[tuple[int, int, str]]] = {
    (1, 1): [
        (1, 3, "Pablo, siervo de Dios,"),
        (4, 7, "apóstol de Cristo Jesús,"),
        (8, 11, "según la fe de los elegidos de Dios"),
        (12, 14, "y el conocimiento de la verdad"),
        (15, 17, "de acuerdo con la piedad"),
    ],
    (1, 2): [
        (1, 4, "para la esperanza de la vida eterna,"),
        (5, 9, "la cual prometió el Dios que es sin mentira,"),
        (10, 12, "antes de los tiempos eternos,"),
    ],
    (1, 3): [
        (1, 9, "y a su propio tiempo manifestó su palabra por la predicación,"),
        (10, 18, "la cual me fue confiada según el mandato de Dios nuestro Salvador."),
    ],
    (1, 4): [
        (1, 7, "A Tito, hijo genuino según la fe común: gracia"),
        (8, 18, "misericordia y paz de Dios Padre y del Señor Jesús Cristo nuestro Salvador."),
    ],
    (1, 5): [
        (1, 6, "Por esta razón te dejé en Creta,"),
        (7, 10, "para que corrigieras lo que falta,"),
        (11, 19, "y pusieras ancianos en cada ciudad, como yo te ordené:"),
    ],
    (1, 6): [
        (1, 8, "si alguien es irreprochable, marido de una sola mujer, con hijos"),
        (9, 16, "fieles, que no estén bajo acusación de disolución o de ser insubordinados."),
    ],
    (1, 7): [
        (1, 9, "Porque es necesario que el obispo sea irreprochable como mayordomo de Dios,"),
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
        (1, 7, "Porque hay muchos e insubordinados, vanos habladores y"),
        (8, 13, "engañadores, sobre todo los de la circuncisión,"),
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
        (6, 10, "Por esta razón repréndelos"),
        (11, 16, "severamente, para que sean sanos en la fe,"),
    ],
    (1, 14): [
        (1, 10, "no prestando atención a mitos judíos y a mandamientos de hombres que se apartan de la verdad."),
    ],
    (1, 15): [
        (1, 3, "Todas las cosas son puras para los"),
        (4, 12, "puros; pero para los contaminados e incrédulos nada es puro, sino que"),
        (13, 20, "tanto su mente como su conciencia están contaminadas."),
    ],
    (1, 16): [
        (1, 3, "Profesan conocer a Dios,"),
        (4, 7, "pero con las obras lo niegan,"),
        (8, 17, "siendo abominables e inobedientes y reprobados para toda buena obra."),
    ],
    # --- Chapter 2 ---
    (2, 1): [
        (1, 8, "Pero tú habla lo que conviene a la sana doctrina."),
    ],
    (2, 2): [
        (1, 5, "Que los ancianos sean sobrios, dignos, prudentes,"),
        (6, 12, "sanos en la fe, en el amor, en la paciencia."),
    ],
    (2, 3): [
        (1, 5, "Las ancianas igualmente, en conducta reverentes,"),
        (6, 12, "no calumniadoras, ni esclavizadas a mucho vino, maestras del bien,"),
    ],
    (2, 4): [
        (1, 7, "para que instruyan a las jóvenes a ser amantes de sus maridos, amantes de sus hijos,"),
    ],
    (2, 5): [
        (1, 4, "prudentes, puras, trabajadoras del hogar, buenas,"),
        (5, 8, "sometidas a sus propios maridos,"),
        (9, 15, "para que la palabra de Dios no sea blasfemada."),
    ],
    (2, 6): [
        (1, 5, "Exhorta igualmente a los jóvenes a ser prudentes,"),
    ],
    (2, 7): [
        (1, 7, "mostrándote en todo como ejemplo de buenas obras;"),
        (8, 12, "en la enseñanza, integridad, dignidad,"),
    ],
    (2, 8): [
        (1, 3, "palabra sana, irreprensible,"),
        (4, 14, "para que el de la parte contraria se avergüence, no teniendo nada malo que decir de nosotros."),
    ],
    (2, 9): [
        (1, 10, "A los siervos, someterse a sus propios amos en todo, ser agradables, no contradiciendo,"),
    ],
    (2, 10): [
        (1, 2, "no apropiándose,"),
        (3, 7, "sino demostrando toda buena fidelidad,"),
        (8, 18, "para que en todo adornen la doctrina de Dios nuestro Salvador."),
    ],
    (2, 11): [
        (1, 9, "Porque se ha manifestado la gracia de Dios, salvadora para todos los hombres,"),
    ],
    (2, 12): [
        (1, 2, "disciplinándonos,"),
        (
            3,
            20,
            "para que, habiendo renunciado a la impiedad y a los deseos mundanos, vivamos prudentemente, justamente y piadosamente en el presente siglo,",
        ),
    ],
    (2, 13): [
        (
            1,
            16,
            "aguardando la esperanza bienaventurada y la manifestación de la gloria del gran Dios y Salvador nuestro, Jesús Cristo,",
        ),
    ],
    (2, 14): [
        (
            1,
            16,
            "quien se dio a sí mismo por nosotros para redimirnos de toda iniquidad y purificar para sí un pueblo propio,",
        ),
        (17, 19, "celoso de buenas obras."),
    ],
    (2, 15): [
        (1, 9, "Estas cosas habla, y exhorta, y reprende con toda autoridad."),
        (10, 12, "Que nadie te menosprecie."),
    ],
    # --- Chapter 3 ---
    (3, 1): [
        (1, 6, "Recuérdales que se sometan a los gobernantes y a las autoridades, que obedezcan,"),
        (7, 12, "estar listos para toda buena obra,"),
    ],
    (3, 2): [
        (1, 5, "a nadie blasfemar, ser no contenciosos, amables,"),
        (6, 11, "mostrando toda mansedumbre hacia todos los hombres."),
    ],
    (3, 3): [
        (1, 8, "Porque también nosotros éramos en otro tiempo necios, desobedientes, extraviados,"),
        (9, 13, "esclavizados a deseos y placeres diversos,"),
        (14, 21, "viviendo en malicia y envidia, odiosos, odiándonos unos a otros."),
    ],
    (3, 4): [
        (
            1,
            12,
            "Pero cuando se manifestó la bondad y el amor a los hombres de Dios nuestro Salvador,",
        ),
    ],
    (3, 5): [
        (
            1,
            23,
            "no por obras de justicia que nosotros hicimos, sino según su misericordia, nos salvó mediante el lavamiento de la regeneración y la renovación del Espíritu Santo,",
        ),
    ],
    (3, 6): [
        (1, 11, "el cual derramó sobre nosotros abundantemente por medio de Jesús Cristo nuestro Salvador,"),
    ],
    (3, 7): [
        (
            1,
            11,
            "para que, justificados por la gracia de aquel, llegáramos a ser herederos según la esperanza de la vida eterna.",
        ),
    ],
    (3, 8): [
        (1, 3, "Fiel es la palabra,"),
        (4, 9, "y acerca de estas cosas quiero que te afirmes firmemente,"),
        (10, 17, "para que los que han creído en Dios se dediquen a buenas obras."),
        (18, 24, "Estas cosas son buenas y provechosas para los hombres."),
    ],
    (3, 9): [
        (
            1,
            11,
            "Pero evita las necias controversias, genealogías, contiendas y peleas acerca de la ley,",
        ),
        (12, 16, "porque son inútiles y vanas."),
    ],
    (3, 10): [
        (1, 8, "Al hombre sectario, después de una y segunda amonestación, recházalo,"),
    ],
    (3, 11): [
        (1, 9, "sabiendo que tal está pervertido y peca, siendo autocondenado."),
    ],
    (3, 12): [
        (1, 7, "Cuando envíe a Artemas a ti, o a Tíquico,"),
        (8, 13, "apresúrate a venir a mí a Nicópolis,"),
        (14, 17, "porque allí he decidido pasar el invierno."),
    ],
    (3, 13): [
        (1, 7, "A Zenas el jurista y a Apolos, envíalos diligentemente,"),
        (8, 11, "para que nada les falte."),
    ],
    (3, 14): [
        (
            1,
            12,
            "Y aprendan también los nuestros a dedicarse a buenas obras para las necesidades urgentes,",
        ),
        (13, 16, "para que no sean infructuosos."),
    ],
    (3, 15): [
        (1, 6, "Te saludan todos los que están conmigo."),
        (7, 12, "Saluda a los que nos aman en la fe."),
        (13, 17, "La gracia sea con todos ustedes."),
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
        segs = BOOK_SEGMENTS.get((ch, vs))
        if segs:
            spans = [(a, b, es) for a, b, es in segs]
        else:
            spans = [(a, b, "") for a, b in split_on_punct(tokens)]

        for local_i, (a, b, es) in enumerate(spans):
            ids = [token_id(ch, vs, p) for p in range(a, b + 1)]
            greek = " ".join(tokens[p - 1]["surface"] for p in range(a, b + 1))
            spanish = es.strip()
            # Hand Spanish seeds the translator textarea as a preliminary draft.
            # Human review in CGV Translator promotes phrases to approved/saved.
            if spanish:
                status = "preliminary"
                suggestion_source = "lbf-preliminary"
            else:
                spanish = ble_seed_for_span(ble.get((ch, vs), ""), a, b, len(tokens))
                status = "draft"
                suggestion_source = "ble-seed"

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
                    "suggestionSource": suggestion_source,
                    "approval": {
                        "status": status,
                        "approvedAt": "",
                        "approvedBy": "lbf-rebuild" if status == "preliminary" else "",
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

    # Verse-structured docs (preliminary + approved Spanish)
    by_verse: dict[tuple[int, int], list[str]] = defaultdict(list)
    for p in phrases:
        if p["approval"]["status"] not in {"preliminary", "approved"}:
            continue
        if not (p.get("spanish") or "").strip():
            continue
        m = re.search(r"(\d+):(\d+)$", p["reference"])
        if not m:
            continue
        by_verse[(int(m.group(1)), int(m.group(2)))].append(p["spanish"])

    lines = ["# Tito", "", "> La Biblia Fiel — Tito (borrador preliminar).", ""]
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

    preliminary = sum(1 for p in phrases if p["approval"]["status"] == "preliminary")
    approved = sum(1 for p in phrases if p["approval"]["status"] == "approved")
    draft = len(phrases) - preliminary - approved
    print(f"phrases: {len(phrases)} (preliminary {preliminary}, approved {approved}, draft {draft})")
    print(f"wrote {OUT_MAP}")
    print(f"wrote {OUT_PHRASES}")
    print(f"wrote {OUT_DOC}")
    print(f"wrote {LBF_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
