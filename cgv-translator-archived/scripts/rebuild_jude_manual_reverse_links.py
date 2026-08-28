#!/usr/bin/env python3
"""Rebuild Jude reverse-links with manual Spanish→TR mappings (full book).

Auto-zip had slid Greek onto Spanish reading order for nearly every phrase.
1:3 was hand-fixed earlier; this script realigns the rest to the same bar.

Writes: translations/tr-spine/jude/jude-reverse-links.json
Then re-run in cgv-reader: python3 scripts/compile-lbf-alignment-judas.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERR = Path(__file__).resolve().parents[1] / "translations" / "tr-spine" / "jude"
PHRASES = HERR / "jude-phrases-tr.json"
OUT = HERR / "jude-reverse-links.json"

# phraseIndex → list of (spanish surface, sourceTokenIds)
# Surfaces must appear in phrase.spanish in order (whitespace-flexible via search).
MAPPINGS: dict[int, list[tuple[str, list[str]]]] = {
    # 1:1
    0: [
        ("Judas", ["n65001001001"]),
        ("siervo", ["n65001001004"]),
        ("de Jesús", ["n65001001002"]),
        ("Cristo", ["n65001001003"]),
        ("y hermano", ["n65001001005", "n65001001006"]),
        ("de Jacobo", ["n65001001007"]),
    ],
    1: [
        ("a los llamados", ["n65001001008", "n65001001017"]),
        ("amados", ["n65001001012"]),
        ("en Dios", ["n65001001009", "n65001001010"]),
        ("Padre", ["n65001001011"]),
        ("y guardados", ["n65001001013", "n65001001016"]),
        ("para Jesús", ["n65001001014"]),
        ("Cristo", ["n65001001015"]),
    ],
    # 1:2
    2: [
        ("Misericordia", ["n65001002001"]),
        ("paz", ["n65001002003", "n65001002004"]),
        ("y amor", ["n65001002005", "n65001002006"]),
        ("les sean multiplicados", ["n65001002002", "n65001002007"]),
    ],
    # 1:3 (keep prior manual)
    3: [
        ("Amados", ["n65001003001"]),
        ("poniéndome", ["n65001003004"]),
        ("toda", ["n65001003002"]),
        ("diligencia", ["n65001003003"]),
        ("en escribirles", ["n65001003005", "n65001003006"]),
        ("acerca", ["n65001003007"]),
        ("de nuestra", ["n65001003008"]),
        ("común", ["n65001003009"]),
        ("salvación", ["n65001003010"]),
    ],
    4: [
        ("me vi", ["n65001003012"]),
        ("en la necesidad", ["n65001003011"]),
        ("de escribirles", ["n65001003013", "n65001003014"]),
        ("exhortándolos", ["n65001003015"]),
        ("a contender", ["n65001003016"]),
        ("por la fe", ["n65001003017", "n65001003022"]),
        ("que una vez", ["n65001003018"]),
        ("fue entregada", ["n65001003019"]),
        ("a los santos", ["n65001003020", "n65001003021"]),
    ],
    # 1:4
    5: [
        ("Porque", ["n65001004002"]),
        ("se han infiltrado", ["n65001004001"]),
        ("algunos", ["n65001004003"]),
        ("hombres", ["n65001004004"]),
        ("los cuales", ["n65001004005"]),
        ("desde antiguo", ["n65001004006"]),
        ("estaban marcados", ["n65001004007"]),
        ("para esta condenación", ["n65001004008", "n65001004009", "n65001004010", "n65001004011"]),
    ],
    6: [
        ("impíos", ["n65001004012"]),
        ("que convierten", ["n65001004018"]),
        ("en lascivia", ["n65001004019", "n65001004020"]),
        ("la gracia", ["n65001004013", "n65001004017"]),
        ("de nuestro Dios", ["n65001004014", "n65001004015", "n65001004016"]),
    ],
    7: [
        ("y niegan", ["n65001004021", "n65001004031"]),
        ("a nuestro", ["n65001004022", "n65001004028"]),
        ("único", ["n65001004023"]),
        ("Dueño", ["n65001004024"]),
        ("y Señor", ["n65001004026", "n65001004027"]),
        ("Jesús", ["n65001004029"]),
        ("Cristo", ["n65001004030"]),
    ],
    # 1:5
    8: [
        ("Quiero", ["n65001005004"]),
        ("pues", ["n65001005002"]),
        ("recordarles", ["n65001005001", "n65001005003"]),
        ("aunque ustedes", ["n65001005006"]),
        ("ya lo saben", ["n65001005005"]),
        ("todo", ["n65001005008"]),
        ("de una vez", ["n65001005007"]),
    ],
    9: [
        ("que Jesús", ["n65001005009", "n65001005010"]),
        ("habiendo salvado", ["n65001005016"]),
        ("al pueblo", ["n65001005012"]),
        ("de la tierra", ["n65001005013", "n65001005014"]),
        ("de Egipto", ["n65001005015"]),
        ("después", ["n65001005017", "n65001005018"]),
        ("destruyó", ["n65001005022"]),
        ("a los que no creyeron", ["n65001005019", "n65001005020", "n65001005021"]),
    ],
    # 1:6
    10: [
        ("y a los ángeles", ["n65001006001", "n65001006002"]),
        ("que no guardaron", ["n65001006003", "n65001006004", "n65001006005"]),
        ("su propio dominio", ["n65001006006", "n65001006007", "n65001006008"]),
        ("sino", ["n65001006009"]),
        ("que abandonaron", ["n65001006010"]),
        ("su propia morada", ["n65001006011", "n65001006012", "n65001006013"]),
    ],
    11: [
        ("los ha guardado", ["n65001006022"]),
        ("bajo tinieblas", ["n65001006020", "n65001006021"]),
        ("en cadenas", ["n65001006018"]),
        ("eternas", ["n65001006019"]),
        ("para el juicio", ["n65001006014", "n65001006015"]),
        ("del gran día", ["n65001006016", "n65001006017"]),
    ],
    # 1:7
    12: [
        ("como", ["n65001007001"]),
        ("Sodoma", ["n65001007002"]),
        ("y Gomorra", ["n65001007003", "n65001007004"]),
        ("y las ciudades", ["n65001007005", "n65001007006", "n65001007009"]),
        ("de alrededor", ["n65001007007", "n65001007008"]),
    ],
    13: [
        ("las cuales", ["n65001007010"]),
        ("de la misma manera", ["n65001007011", "n65001007013"]),
        ("que aquellos", ["n65001007012"]),
        ("se entregaron a la fornicación", ["n65001007014"]),
        ("y fueron", ["n65001007015", "n65001007016"]),
        ("tras", ["n65001007017"]),
        ("carne", ["n65001007018"]),
        ("extraña", ["n65001007019"]),
    ],
    14: [
        ("están puestas", ["n65001007020"]),
        ("como ejemplo", ["n65001007021"]),
        ("sufriendo", ["n65001007025"]),
        ("el castigo", ["n65001007024"]),
        ("de fuego", ["n65001007022"]),
        ("eterno", ["n65001007023"]),
    ],
    # 1:8
    15: [
        ("De la misma manera", ["n65001008001", "n65001008002"]),
        ("también", ["n65001008003"]),
        ("estos", ["n65001008004"]),
        ("soñando", ["n65001008005"]),
        ("mancillan", ["n65001008007", "n65001008008"]),
        ("la carne", ["n65001008006"]),
    ],
    16: [
        ("rechazan", ["n65001008010", "n65001008011"]),
        ("la autoridad", ["n65001008009"]),
        ("y blasfeman", ["n65001008013", "n65001008014"]),
        ("de las glorias", ["n65001008012"]),
    ],
    # 1:9
    17: [
        ("Pero", ["n65001009001", "n65001009002"]),
        ("cuando", ["n65001009006"]),
        ("Miguel", ["n65001009003"]),
        ("el arcángel", ["n65001009004", "n65001009005"]),
        ("disputando", ["n65001009009"]),
        ("con el diablo", ["n65001009007", "n65001009008"]),
        ("discutía", ["n65001009010"]),
        ("acerca", ["n65001009011"]),
        ("del cuerpo", ["n65001009012", "n65001009014"]),
        ("de Moisés", ["n65001009013"]),
    ],
    18: [
        ("no se atrevió", ["n65001009015", "n65001009016"]),
        ("a pronunciar", ["n65001009018"]),
        ("juicio", ["n65001009017"]),
        ("de blasfemia", ["n65001009019"]),
        ("sino", ["n65001009020"]),
        ("que dijo", ["n65001009021"]),
    ],
    19: [
        ("El Señor", ["n65001009024"]),
        ("te", ["n65001009023"]),
        ("reprenda", ["n65001009022"]),
    ],
    # 1:10
    20: [
        ("Pero", ["n65001010002"]),
        ("estos", ["n65001010001"]),
        ("blasfeman", ["n65001010007"]),
        ("de lo que no conocen", ["n65001010003", "n65001010004", "n65001010005", "n65001010006"]),
    ],
    21: [
        ("y en lo que por naturaleza", ["n65001010008", "n65001010009", "n65001010010"]),
        ("como", ["n65001010011"]),
        ("animales", ["n65001010014"]),
        ("irracionales", ["n65001010012", "n65001010013"]),
        ("sí entienden", ["n65001010015"]),
        ("en eso", ["n65001010016", "n65001010017"]),
        ("se corrompen", ["n65001010018"]),
    ],
    # 1:11
    22: [
        ("Ay", ["n65001011001"]),
        ("de ellos", ["n65001011002"]),
        ("porque", ["n65001011003"]),
        ("han seguido", ["n65001011008"]),
        ("el camino", ["n65001011004", "n65001011005"]),
        ("de Caín", ["n65001011006", "n65001011007"]),
    ],
    23: [
        ("y por la paga", ["n65001011009", "n65001011014"]),
        ("se han lanzado", ["n65001011015"]),
        ("al error", ["n65001011010", "n65001011011"]),
        ("de Balaam", ["n65001011012", "n65001011013"]),
    ],
    24: [
        ("y en la rebelión", ["n65001011016", "n65001011017", "n65001011018"]),
        ("de Coré", ["n65001011019", "n65001011020"]),
        ("perecieron", ["n65001011021"]),
    ],
    # 1:12
    25: [
        ("Estos", ["n65001012001"]),
        ("son", ["n65001012002"]),
        ("escollos", ["n65001012007"]),
        ("en sus ágapes", ["n65001012003", "n65001012004", "n65001012005", "n65001012006"]),
        ("banqueteando", ["n65001012008"]),
        ("con ustedes", ["n65001012009"]),  # TR-only ὑμῖν
        ("sin temor", ["n65001012010"]),
        ("apacentándose", ["n65001012012"]),
        ("a sí mismos", ["n65001012011"]),
    ],
    26: [
        ("nubes", ["n65001012013"]),
        ("sin agua", ["n65001012014"]),
        ("llevadas", ["n65001012017"]),
        ("por los vientos", ["n65001012015", "n65001012016"]),
    ],
    27: [
        ("árboles", ["n65001012018"]),
        ("de otoño", ["n65001012019"]),
        ("sin fruto", ["n65001012020"]),
        ("dos veces", ["n65001012021"]),
        ("muertos", ["n65001012022"]),
        ("desarraigados", ["n65001012023"]),
    ],
    # 1:13
    28: [
        ("olas", ["n65001013001"]),
        ("bravías", ["n65001013002"]),
        ("del mar", ["n65001013003"]),
        ("que espuman", ["n65001013004"]),
        ("sus propias", ["n65001013005", "n65001013006"]),
        ("vergüenzas", ["n65001013007"]),
    ],
    29: [
        ("estrellas", ["n65001013008"]),
        ("errantes", ["n65001013009"]),
        ("para las cuales", ["n65001013010"]),
        ("la oscuridad", ["n65001013011", "n65001013012"]),
        ("de las tinieblas", ["n65001013013", "n65001013014"]),
        ("está reservada", ["n65001013018"]),
        ("para siempre", ["n65001013015", "n65001013017"]),
    ],
    # 1:14
    30: [
        ("De estos", ["n65001014002", "n65001014004"]),
        ("también", ["n65001014003"]),
        ("profetizó", ["n65001014001"]),
        ("Enoc", ["n65001014008"]),
        ("el séptimo", ["n65001014005"]),
        ("desde", ["n65001014006"]),
        ("Adán", ["n65001014007"]),
        ("diciendo", ["n65001014009"]),
    ],
    31: [
        ("He aquí", ["n65001014010"]),
        ("el Señor", ["n65001014012"]),
        ("vino", ["n65001014011"]),
        ("con sus santas miríadas", ["n65001014013", "n65001014014", "n65001014015", "n65001014016"]),
    ],
    # 1:15
    32: [
        ("para hacer", ["n65001015001"]),
        ("juicio", ["n65001015002"]),
        ("contra todos", ["n65001015003", "n65001015004"]),
        ("y convencer", ["n65001015005", "n65001015006"]),
        ("a todos", ["n65001015007"]),
        ("los impíos", ["n65001015008", "n65001015009"]),
    ],
    33: [
        ("acerca", ["n65001015011"]),
        ("de todas", ["n65001015012"]),
        ("las obras", ["n65001015013", "n65001015014"]),
        ("de impiedad", ["n65001015015", "n65001015016"]),
        ("que hicieron", ["n65001015017", "n65001015018"]),
    ],
    34: [
        ("y acerca", ["n65001015019", "n65001015020"]),
        ("de todas", ["n65001015021"]),
        ("las cosas", ["n65001015022"]),
        ("duras", ["n65001015023"]),
        ("que los pecadores", ["n65001015024", "n65001015028"]),
        ("impíos", ["n65001015029"]),
        ("hablaron", ["n65001015025"]),
        ("contra él", ["n65001015026", "n65001015027"]),
    ],
    # 1:16
    35: [
        ("Estos", ["n65001016001"]),
        ("son", ["n65001016002"]),
        ("murmuradores", ["n65001016003"]),
        ("quejumbrosos", ["n65001016004"]),
        ("que andan", ["n65001016009"]),
        ("según", ["n65001016005"]),
        ("sus deseos", ["n65001016006", "n65001016007", "n65001016008"]),
    ],
    36: [
        ("y su boca", ["n65001016010", "n65001016011", "n65001016012", "n65001016013"]),
        ("habla", ["n65001016014"]),
        ("cosas arrogantes", ["n65001016015"]),
        ("admirando", ["n65001016016"]),
        ("personas", ["n65001016017"]),
        ("por causa", ["n65001016019"]),
        ("del provecho", ["n65001016018"]),
    ],
    # 1:17
    37: [
        ("Pero", ["n65001017002"]),
        ("ustedes", ["n65001017001"]),
        ("amados", ["n65001017003"]),
        ("acuérdense", ["n65001017004"]),
        ("de las palabras", ["n65001017005", "n65001017006"]),
        ("predichas", ["n65001017007", "n65001017008"]),
        ("por los apóstoles", ["n65001017009", "n65001017010", "n65001017011"]),
        ("de nuestro", ["n65001017012", "n65001017014"]),
        ("Señor", ["n65001017013"]),
        ("Jesús", ["n65001017015"]),
        ("Cristo", ["n65001017016"]),
    ],
    # 1:18
    38: [
        ("que les", ["n65001018001", "n65001018003"]),
        ("decían", ["n65001018002", "n65001018004"]),
        ("En el último tiempo", ["n65001018005", "n65001018006"]),
        ("habrá", ["n65001018008"]),
        ("burladores", ["n65001018009"]),
        ("que andarán", ["n65001018014"]),
        ("según", ["n65001018010"]),
        ("sus propios", ["n65001018011", "n65001018012"]),
        ("deseos", ["n65001018013"]),
        ("de impiedades", ["n65001018015", "n65001018016"]),
    ],
    # 1:19
    39: [
        ("Estos", ["n65001019001"]),
        ("son", ["n65001019002"]),
        ("los que causan", ["n65001019003"]),
        ("divisiones", ["n65001019004"]),
        ("sensuales", ["n65001019006"]),
        ("que no tienen", ["n65001019008", "n65001019009"]),
        ("el Espíritu", ["n65001019007"]),
    ],
    # 1:20 — ἐποικοδομοῦντες / ἑαυτοὺς are TR-only
    40: [
        ("Pero", ["n65001020002"]),
        ("ustedes", ["n65001020001"]),
        ("amados", ["n65001020003"]),
        (
            "edificándose sobre su santísima fe",
            [
                "n65001020008",
                "n65001020009",
                "n65001020004",
                "n65001020005",
                "n65001020006",
                "n65001020007",
            ],
        ),
    ],
    41: [
        ("orando", ["n65001020013"]),
        ("en el Espíritu", ["n65001020010", "n65001020011"]),
        ("Santo", ["n65001020012"]),
    ],
    # 1:21
    42: [
        ("guárdense", ["n65001021001", "n65001021005"]),
        ("en el amor", ["n65001021002", "n65001021003"]),
        ("de Dios", ["n65001021004"]),
    ],
    43: [
        ("esperando", ["n65001021006"]),
        ("la misericordia", ["n65001021007", "n65001021008"]),
        ("de nuestro", ["n65001021009", "n65001021011"]),
        ("Señor", ["n65001021010"]),
        ("Jesús", ["n65001021012"]),
        ("Cristo", ["n65001021013"]),
        ("para vida", ["n65001021014", "n65001021015"]),
        ("eterna", ["n65001021016"]),
    ],
    # 1:22
    44: [
        ("Y a los que dudan", ["n65001022001", "n65001022002", "n65001022005"]),
        ("tengan misericordia", ["n65001022003", "n65001022004"]),
    ],
    # 1:23 — σώζετε…ἁρπάζοντες are TR-only; keep with οὓς δὲ so Morph gets the clause
    45: [
        (
            "a otros sálvenlos arrebatándolos del fuego",
            [
                "n65001023001",
                "n65001023002",
                "n65001023005",
                "n65001023006",
                "n65001023007",
                "n65001023008",
                "n65001023009",
            ],
        ),
    ],
    46: [
        ("y a otros", ["n65001023011"]),
        (
            "tengan misericordia con temor",
            ["n65001023003", "n65001023004"],
        ),
        ("aborreciendo", ["n65001023010"]),
        ("aun", ["n65001023012"]),
        ("la ropa", ["n65001023017"]),
        ("contaminada", ["n65001023016"]),
        ("por la carne", ["n65001023013", "n65001023014", "n65001023015"]),
    ],
    # 1:24
    47: [
        ("Y al que es", ["n65001024001", "n65001024002"]),
        ("poderoso", ["n65001024003"]),
        ("para guardarlos", ["n65001024004", "n65001024005"]),
        ("sin tropiezo", ["n65001024006"]),
        ("y presentarlos", ["n65001024007", "n65001024008"]),
        ("delante", ["n65001024009"]),
        ("de su gloria", ["n65001024010", "n65001024011", "n65001024012"]),
        ("sin tacha", ["n65001024013"]),
        ("con gran", ["n65001024014"]),
        ("alegría", ["n65001024015"]),
    ],
    # 1:25 — "por medio de Jesús…" / "antes de todo el siglo" lack TR rows (Morph-only)
    48: [
        ("al único", ["n65001025001"]),
        ("Dios", ["n65001025003"]),
        (
            "nuestro Salvador, por medio de Jesús Cristo nuestro Señor",
            ["n65001025004", "n65001025005"],
        ),
    ],
    49: [
        ("sea gloria", ["n65001025006"]),
        ("majestad", ["n65001025007", "n65001025008"]),
        ("dominio", ["n65001025009"]),
        ("y autoridad", ["n65001025010", "n65001025011"]),
        (
            "antes de todo el siglo, y ahora",
            ["n65001025012", "n65001025013"],
        ),
        ("y por todos", ["n65001025014", "n65001025015", "n65001025016"]),
        ("los siglos", ["n65001025017", "n65001025018"]),
    ],
    50: [
        ("Amén", ["n65001025019"]),
    ],
}


def find_surface(spanish: str, surface: str, cursor: int) -> tuple[int, int]:
    """Find surface in spanish starting near cursor; allow flexible spaces."""
    # Exact first
    idx = spanish.find(surface, cursor)
    if idx >= 0:
        return idx, idx + len(surface)
    # Collapse whitespace match
    pat = re.compile(re.escape(surface).replace(r"\ ", r"\s+"), re.I)
    m = pat.search(spanish, cursor)
    if m:
        return m.start(), m.end()
    m = pat.search(spanish)
    if m:
        return m.start(), m.end()
    raise ValueError(f"Surface {surface!r} not in phrase spanish (cursor={cursor})")


def build_units(phrase_index: int, spanish: str, pairs: list[tuple[str, list[str]]]) -> list[dict]:
    units = []
    cursor = 0
    pending_empty: list[str] = []
    for surface, ids in pairs:
        if not ids:
            pending_empty.append(surface)
            continue
        if pending_empty:
            surface = " ".join(pending_empty + [surface])
            pending_empty = []
        start, end = find_surface(spanish, surface, cursor)
        # Prefer the exact slice from the phrase text for punctuation fidelity
        exact = spanish[start:end]
        cursor = end
        units.append(
            {
                "unitId": f"{phrase_index}:{len(units)}",
                "surface": exact,
                "charStart": start,
                "charEnd": end,
                "sourceTokenIds": ids,
                "method": "manual-realign",
            }
        )
    if pending_empty:
        raise ValueError(f"phrase {phrase_index}: trailing empty-id surfaces {pending_empty}")
    return units


def main() -> None:
    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
    if isinstance(phrases, dict):
        phrases = phrases.get("phrases") or phrases.get("entries") or []
    by_index = {int(p["phraseIndex"]): p for p in phrases}

    missing = sorted(set(by_index) - set(MAPPINGS))
    extra = sorted(set(MAPPINGS) - set(by_index))
    if missing or extra:
        raise SystemExit(f"Mapping coverage mismatch missing={missing} extra={extra}")

    out_links = []
    for idx in sorted(by_index):
        p = by_index[idx]
        units = build_units(idx, p["spanish"], MAPPINGS[idx])
        # Validate all phrase token ids are used (warn only for extras we intentionally omit)
        phrase_ids = {r["sourceTokenId"] for r in (p.get("tokenRows") or [])}
        used = {sid for u in units for sid in u["sourceTokenIds"]}
        unused = sorted(phrase_ids - used)
        if unused:
            print(f"WARN phrase {idx}: unused phrase tokenRows {unused}")
        out_links.append(
            {
                "phraseIndex": idx,
                "reference": p["reference"],
                "status": "manual",
                "units": units,
            }
        )

    doc = {
        "bookId": "jude",
        "textualBasis": "Scrivener 1894 TR",
        "schemaVersion": 1,
        "notes": {
            "seed": (
                "Reverse interlinear: Spanish unit → TR sourceTokenIds. "
                "Full-book manual realign 2026-07-24 after auto-zip slide audit."
            ),
            "jude1_3": "Manual realign 2026-07-24: auto-zip had slid tokens (πᾶσαν→Amados, etc.).",
            "tr_only": (
                "1:12 ὑμῖν; 1:14 ἁγίαις; 1:20 ἐποικοδομοῦντες/ἑαυτοὺς; "
                "1:23 σώζετε…ἁρπάζοντες included in reverse links (Morph skips TR-only)."
            ),
            "morph_only_gaps": (
                "Some MorphGNT tokens have no TR sourceTokenId (e.g. 1:25 "
                "διὰ Ἰησοῦ Χριστοῦ… / πρὸ παντὸς τοῦ αἰῶνος); Spanish rides on nearest TR."
            ),
        },
        "stats": {
            "phrases": len(out_links),
            "hand": len(out_links),
            "auto": 0,
            "units": sum(len(link["units"]) for link in out_links),
        },
        "links": out_links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
