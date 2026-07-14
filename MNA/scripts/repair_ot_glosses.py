#!/usr/bin/env python3
"""Repair high-confidence wrong OT lemma → Spanish glosses.

Wrong glosses live in MNA/datasets/rules/hbo_lemma_lexicon.json (not BLE assembly).
This script:
  1) patches curated bare Strong's bases
  2) recomposes all prefixed keys for those bases
  3) optionally force-refreshes every OT token file
  4) optionally rebuilds Biblia-BLE OT output

Examples (from repo root `herramientas`):

  python3 MNA/scripts/repair_ot_glosses.py --dry-run
  python3 MNA/scripts/repair_ot_glosses.py --apply --force-tokens
  python3 MNA/scripts/repair_ot_glosses.py --apply --force-tokens --rebuild-ble
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEXICON = REPO_ROOT / "MNA" / "datasets" / "rules" / "hbo_lemma_lexicon.json"
DEFAULT_OT = REPO_ROOT / "MNA" / "datasets" / "interlinear" / "OT"
NEXT_STEP = REPO_ROOT / "MNA" / "scripts" / "next_stepOT.py"
TOKENS_TO_BLE = REPO_ROOT / "Biblia-BLE" / "scripts" / "tokens_to_ble.py"

PREFIX_GLOSS = {
    "c": "y",
    "d": "el",
    "b": "en",
    "l": "a",
    "m": "de",
    "k": "según",
    "i": "¡",
    "s": "que",
}
PREF_SET = set(PREFIX_GLOSS)

# Feminine Spanish bases → use la/las-style article for d- prefix.
FEMININE_BASES = {
    "muerte",
    "visión",
    "mano",
    "tierra",
    "casa",
    "mujer",
    "hermana",
    "señal",
    "puerta",
    "columna",
    "miel",
    "gloria",
    "ira",
    "fuerza",
    "valentía",
    "oveja",
    "medida",
    "cortina",
    "derecha",
    "porción",
    "leche",
    "maldad",
    "ciudad",
    "cuerda",
    "asna",
    "nuera",
    "lumbrera",
    "era",
    "hierba",
    "especie",
    "estrella",
    "misericordia",
    "paz",
    "ley",
    "ofrenda",
    "justicia",
    "verdad",
    "espada",
    "mentira",
    "ala",
    "maldad",
    "rebelión",
    "bondad",
    "caña",
    "lanza",
    "flecha",
    "sabiduría",
    "salvación",
    "infidelidad",
    "integridad",
    "izquierda",
    "espalda",
    "red",
    "espiga",
    "abominación",
    "abertura",
    "palma",
    "oscuridad",
    "suegra",
    "mula",
    "cuerda",
    "fuerza",
    "apariencia",
    "bendición",
    "violencia",
    "altura",
    "púrpura",
    "cabaña",
    "olla",
    "infamia",
    "cortina",
    "estaca",
    "llanura",
    "muchedumbre",
    "cobertura",
    "cadena",
    "vigilia",
    "juntura",
    "pérdida",
    "hendidura",
    "corriente",
    "copa",
    "masa",
    "sábana",
    "embriaguez",
    "visión",
    "ribera",
    "posesión",
    "calumnia",
    "dueña",
    "punta",
    "vendimia",
    "destrucción",
    "empalizada",
    "capucha",
    "sarna",
    "pedernal",
    "orla",
    "cesta",
    "proporción",
    "palmera",
    "cabra",
    "temblor",
    "collar",
    "brazalete",
    "excremento",
    "sartén",
    "túnica",
    "zurdo",
}

# Curated bare-key repairs: exact lexicon bare key → Spanish lexical base.
# Only high-confidence semantic replacements (not near-synonym polish).
BARE_CORRECTIONS: dict[str, str] = {
    # Confirmed opening-verse failures
    "835": "dichoso",
    "7563": "malvado",
    "2377": "visión",
    "2372": "ver",
    "4194": "muerte",
    "3220": "mar",
    "1870": "camino",
    "2167": "cantar",
    "4264": "campamento",
    "3559 a": "preparar",
    # High-frequency clearly wrong bases (AHRC/KJV checked)
    "1": "padre",
    "2091": "oro",
    "784": "fuego",
    "8179": "puerta",
    "5030": "profeta",
    "6106": "hueso",
    "269": "hermana",
    "3678": "trono",
    "2543": "asno",
    "7794": "buey",
    "226": "señal",
    "5982": "columna",
    "899 b": "vestido",
    "7023": "muro",
    "3541": "así",
    "3225": "derecha",
    "3034": "alabar",
    "8057": "gozo",
    "3289": "aconsejar",
    "214": "tesoro",
    "5178 a": "cobre",
    "3581 b": "fuerza",
    "1366": "límite",
    "6817": "clamar",
    "3407": "cortina",
    "5038": "cadáver",
    "8269": "príncipe",
    "241": "oído",
    # Remaining opening-verse failures after first pass
    "2400": "pecador",
    "3887": "escarnecedor",
    "3147": "Jotam",
    "5126": "Nun",
    "8334": "servidor",
    "3004": "tierra·seca",
    "5975": "estar",
    # Pass 2 — highest-impact wrong lemmas (freq × clear semantic error)
    "7227 a": "mucho",
    "7235 a": "multiplicar",
    "8337": "seis",
    "1241": "ganado",
    "6235": "diez",
    "5656": "servicio",
    "3196": "vino",
    "5387 a": "príncipe",
    "587": "nosotros",
    "3513": "honrar",
    "7535": "solamente",
    "8083": "ocho",
    "7992": "tercero",
    "4592": "poco",
    "4438": "reino",
    "6098": "consejo",
    "1817 c": "puerta",
    "4910": "reinar",
    "2654 a": "deleitar",
    "3885 a": "pernoctar",
    "2506 a": "porción",
    "8672": "nueve",
    "3707": "enojar",
    "7442 b": "gritar",
    "1644": "expulsar",
    "2461": "leche",
    "5057": "líder",
    "7321": "gritar",
    "215": "alumbrar",
    "3974": "lumbrera",
    "238": "oír",
    "553": "fortalecer",
    "2656": "deleite",
    "3515": "pesado",
    "1637": "era",
    "3602": "así",
    "8398": "mundo",
    "8643": "grito",
    "3618": "nuera",
    "860": "asna",
    "5766 b": "malvado",
    "2370": "ver",
    "3341": "encender",
    "1497": "despojar",
    "7562": "maldad",
    "6509": "fructificar",
    "7151": "ciudad",
    "183": "anhelar",
    "6504": "dividir",
    "5688": "cuerda",
    "5794": "fuerte",
    # Pass 2b — Genesis 1 visibility + ordinals/plant lexicon
    "1876": "brotar",
    "1877": "hierba",
    "6212": "hierba",
    "6529": "fruto",
    "4327": "especie",
    "4475": "dominio",
    "6996 a": "pequeño",
    "6996 b": "pequeño",
    "3556": "estrella",
    "7243": "cuarto",
    # Pass 3 — ranked n>=30 clear semantic errors
    "3967": "cien",
    "505": "mil",
    "4941": "juicio",
    "2719": "espada",
    "4427 a": "reinar",
    "6242": "veinte",
    "7272": "pie",
    "2617 a": "misericordia",
    "2398": "pecar",
    "7965": "paz",
    "2142": "recordar",
    "8451": "ley",
    "4503": "ofrenda",
    "6635 a": "ejército",
    "4687": "mandamiento",
    "2026": "matar",
    "2077": "sacrificio",
    "6666": "justicia",
    "8121": "sol",
    "7931": "habitar",
    "2706": "estatuto",
    "571": "verdad",
    "4467": "reino",
    "5012": "profetizar",
    "8267": "mentira",
    "3671": "ala",
    "7451 b": "maldad",
    "2708": "estatuto",
    "7911": "olvidar",
    "3722 a": "expiar",
    "6588": "rebelión",
    "1616": "extranjero",
    "2896 b": "bondad",
    "1481 a": "peregrinar",
    "7133 a": "ofrenda",
    "7198": "arco",
    "779": "maldecir",
    "7070": "caña",
    "5157": "heredar",
    "2232": "sembrar",
    "1581": "camello",
    "2595": "lanza",
    "5237": "extranjero",
    "2671": "flecha",
    "2549": "quinto",
    # Pass 3b — commandments / Ps 23 / high-freq proper-name collisions
    "7523": "matar",
    "5003": "adulterar",
    "1589": "hurtar",
    "2637": "carecer",
    "1732": "David",
    "2351": "afuera",
    "5027": "mirar",
    "4994": "por·favor",
    # Pass 4 — ranked n>=15 clear semantic errors
    "5439": "alrededor",
    "5493": "apartar",
    "6662": "justo",
    "3467": "salvar",
    "995": "entender",
    "8055": "alegrarse",
    "5437": "rodear",
    "2451": "sabiduría",
    "4605": "arriba",
    "2450": "sabio",
    "2803": "pensar",
    "2803 a": "pensar",
    "2534": "furor",
    "3190": "hacer·bien",
    "5045": "sur",
    "7489 a": "hacer·mal",
    "2734": "encenderse",
    "8002": "ofrenda·de·paz",
    "2603 a": "tener·gracia",
    "4217": "oriente",
    "2199": "clamar",
    "7673 a": "cesar",
    "6921": "oriente",
    "5117": "descansar",
    "4284": "pensamiento",
    "2505 a": "repartir",
    "8040": "izquierda",
    "1544": "ídolo",
    "6663": "justificar",
    "2740": "ardor",
    "268": "espalda",
    "2620": "refugiarse",
    "7561": "actuar·malvado",
    "4603": "actuar·infielmente",
    "3468": "salvación",
    "6224": "décimo",
    "8345": "sexto",
    "4604": "infidelidad",
    "8537": "integridad",
    "2895": "ser·bueno",
    "7568": "red",
    "5766 a": "malvado",
    "5619": "apedrear",
    "4962": "hombre",
    "4289": "brasero",
    "1438": "cortar",
    "6818": "grito",
    "5633 a": "señor",
    "8056": "gozoso",
    "457": "ídolo",
    "7579": "sacar·agua",
    "4295": "abajo",
    "2426": "muro",
    "4526": "borde",
    "3885 b": "pernoctar",
    "833": "hacer·dichoso",
    "6091": "ídolo",
    "7641 b": "espiga",
    "2673": "dividir",
    # Pass 5 — ranked n>=10 clear errors + proper-name collisions
    "3477": "recto",
    "1157": "por",
    "1167": "dueño",
    "270": "asir",
    "8346": "sesenta",
    "1097": "sin",
    "160": "amor",
    "3051": "dar",
    "3474": "enderezar",
    "1881": "ley",
    "650": "arroyo",
    "5526 b": "cubrir",
    "47": "poderoso",
    "3342": "lagar",
    "386": "fuerte",
    "155": "manto",
    "653": "oscuridad",
    "6240": "diez",
    "6635 b": "ejército",
    "4616": "a·fin·de",
    "2428": "fuerza",
    "5337": "librar",
    "157": "amar",
    "3709": "palma",
    "1540": "descubrir",
    "2205": "anciano",
    "6607": "abertura",
    "2930 a": "contaminar",
    "6828": "norte",
    "1984 b": "alabar",
    "8130": "odiar",
    "3644": "como",
    "5158 a": "torrente",
    "2346": "muro",
    "227 a": "entonces",
    "5104": "río",
    "8441": "abominación",
    "1115": "sin",
    "3498": "dejar",
    "3282": "porque",
    "2891": "limpiar",
    "3499 a": "resto",
    "2889": "limpio",
    "2491 a": "muerto",
    "7043": "menospreciar",
    "7819 a": "degollar",
    "1397": "varón",
    "8610": "asir",
    "7919 a": "entender",
    "6160": "desierto",
    "6505": "mula",
    "3867 a": "unir",
    "3867 b": "unir",
    "3775": "oveja",
    "1472": "cadáver",
    "2782": "decidir",
    "6616": "cuerda",
    "4055": "vestido",
    "2655": "deleite",
    "2545": "suegra",
    "1496": "piedra·labrada",
    "5154": "bronce",
    "4749": "batido",
    "1602": "aborrecer",
    "2009": "he·aquí",
    # Pass 5b — remaining false proper-name collisions n>=10
    "8354": "beber",
    "4758": "apariencia",
    "8074": "asolar",
    "1486": "suerte",
    "1293": "bendición",
    "319": "fin",
    "2555": "violencia",
    "4791": "altura",
    "8163 b": "macho·cabrío",
    "1234": "hender",
    "6555": "romper",
    "646": "efod",
    "4784": "rebelar",
    "657 a": "extremo",
    "4501": "candelabro",
    "3490": "huérfano",
    "1280": "barra",
    "8435": "generaciones",
    "4751": "amargo",
    "1767": "suficiente",
    "713": "púrpura",
    "1219": "cercar",
    "875": "pozo",
    "6845": "ocultar",
    "3409": "muslo",
    "8071": "vestido",
    "5521": "cabaña",
    "8227 b": "damán",
    "7257": "recostar",
    "6459": "imagen",
    "5518 a": "olla",
    "2154": "infamia",
    "4775": "rebelar",
    "4539": "cortina",
    "6456": "imagen",
    "3489": "estaca",
    "188": "¡ay!",
    "4805": "rebelde",
    "4522": "tributo",
    # Pass 6 — ranked n>=5 clear errors + false proper names
    "1237": "llanura",
    "1423": "cabrito",
    "2053": "gancho",
    "6835": "cántaro",
    "185": "deseo",
    "46": "poderoso",
    "8029": "tercero",
    "4768": "muchedumbre",
    "6973": "aborrecer",
    "6895": "maldecir",
    "6237": "diezmar",
    "551": "ciertamente",
    "5429": "sea",
    "5408": "despedazar",
    "5253": "apartar",
    "4468": "reino",
    "436": "encina",
    "4340": "cuerda",
    "3682": "cobertura",
    "2404": "cincelar",
    "1541": "descubrir",
    "8302 b": "muro",
    "7973": "proyectil",
    "7117": "fin",
    "6805": "marchar",
    "5970": "triunfar",
    "5459": "tesoro",
    "504": "buey",
    "4694": "baluarte",
    "4395": "fruto",
    "4225": "juntura",
    "2553": "ídolo",
    "8639": "sueño·profundo",
    "8333": "cadena",
    "8262": "detestar",
    "821": "vigilia",
    "7290": "adormecer",
    "1865": "puro",
    "7": "perecer",
    # Pass 6b — more false-name collisions n>=5
    "7806": "entrelazar",
    "3462": "dormir",
    "6879": "infectar",
    "6556": "brecha",
    "887": "heder",
    "178": "odre",
    "162": "¡ah!",
    "1605": "reprender",
    "4753": "mirra",
    "231": "hisopo",
    "73": "faja",
    "5736": "exceder",
    # Pass 7 — ranked n>=3 clear errors + false names
    "9": "pérdida",
    "8622": "ciclo",
    "8157": "hendidura",
    "7903": "yacer",
    "7743": "inclinarse",
    "7641 a": "corriente",
    "7256": "cuarto",
    "7184": "copa",
    "6926": "oriente",
    "6385": "dividir",
    "6182": "masa",
    "579": "sobrevenir",
    "5687": "cordón",
    "5466": "sábana",
    "5442": "matorral",
    "5435": "embriaguez",
    "5387 b": "príncipe",
    "5310 b": "dispersar",
    "5257 b": "príncipe",
    "4448 a": "hablar",
    "4237": "luz",
    "4236": "visión",
    "3648": "enternecer",
    "3456": "asolar",
    "3231": "a·derecha",
    "2416 d": "viviente",
    "2138": "varón",
    "1610": "cuerpo",
    "1415": "ribera",
    "1057": "bacá",
    "874": "explicar",
    "6850": "susurrar",
    "8443": "cumbre",
    # false names n>=3
    "4181": "posesión",
    "1681": "calumnia",
    "1404": "dueña",
    "8571": "punta",
    "57": "duelo",
    "8658": "topacio",
    "3465": "dormido",
    "3463": "dormido",
    "2239": "palmo",
    "1492": "vellón",
    "1482": "cachorro",
    "1239": "investigar",
    "1210": "vendimia",
    "6875": "bálsamo",
    "2151 b": "glotón",
    "2156": "vid",
    "11": "destrucción",
    "92": "manojo",
    "6357": "olivino",
    "4770": "cebado",
    "4734": "talla",
    "4529": "derretir",
    "4518": "tazón",
    "4142": "cercar",
    "1573": "junco",
    "1488": "vellón",
    "943": "enredar",
    "6076 a": "empalizada",
    "4533": "capucha",
    "4484": "mina",
    "3023": "cansado",
    "1618": "sarna",
    # Pass 8 — ranked n>=1 clear errors + remaining false names
    "8163 a": "peludo",
    "6864": "pedernal",
    "2791 b": "artesano",
    "1383": "orla",
    "6803": "cesta",
    "6495": "abertura",
    "6495+": "abertura",
    "5522": "cabaña",
    "4815": "amargo",
    "4530": "proporción",
    "8569": "oposición",
    "8560": "palmera",
    "8166": "cabra",
    "8": "perecer",
    "7771 a": "clamor",
    "7461 a": "temblor",
    "7289": "manto",
    "7242": "collar",
    "7232": "mucho",
    "7228": "mucho",
    "685": "brazalete",
    "678": "noble",
    "6627": "excremento",
    "6145": "enemigo",
    "5779": "aconsejar",
    "546": "ciertamente",
    "5235": "extranjero",
    "5214": "arar",
    "5173": "encantamiento",
    "4802": "sartén",
    "4690": "columna",
    "4063": "vestido",
    "3424": "posesión",
    "334": "zurdo",
    "4254": "túnica",
    "4166": "fundición",
    # Pass 8b — final false-name leftovers n>=1
    "76": "pústeula",
    "6978": "medida",
    "6978+": "medida",
    "6368": "hollín",
    "5697 b": "novilla",
    "1887": "he·aquí",
    "1469": "pichón",
    "1407": "cilantro",
    "1235": "beqa",
    "1216": "hincharse",
    "6798": "marchitarse",
    "648": "tardío",
    "6356": "hoyo",
    "4786": "dolor",
    "4760": "buche",
    "1384": "jorobado",
    "4515": "sandalia",
    # Josh 14:6 neighborhood — proper names / places / אדות misread as common words
    "1537": "Gilgal",
    "3612": "Caleb",
    "3312": "Jefune",
    "7074": "quenezeo",
    "182": "acerca·de",
    "6946": "Cades",
    "6947": "Barnea",
    "6947+": "Cades",
}


def split_lemma(lemma: str) -> tuple[list[str], str]:
    parts = lemma.split("/")
    prefs: list[str] = []
    i = 0
    while i < len(parts) - 1 and parts[i] in PREF_SET:
        prefs.append(parts[i])
        i += 1
    return prefs, "/".join(parts[i:])


def article_for(base: str) -> str:
    if base in FEMININE_BASES:
        return "la"
    head = base.split("·")[0]
    if head in FEMININE_BASES:
        return "la"
    if base.endswith(("ción", "sión", "dad", "tad", "umbre")) or head.endswith(
        ("ción", "sión", "dad", "tad", "umbre")
    ):
        return "la"
    return "el"


def compose(prefs: list[str], base: str) -> str:
    if not prefs:
        return base
    parts: list[str] = []
    for p in prefs:
        if p == "d":
            parts.append(article_for(base))
        else:
            parts.append(PREFIX_GLOSS[p])
    parts.append(base)
    return "·".join(parts)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def planned_updates(lex: dict[str, str]) -> dict[str, tuple[str, str]]:
    """Return lemma -> (old, new) for bare + recomposed prefixed keys.

    Also inserts missing bare keys from BARE_CORRECTIONS (e.g. first-time gentilics).
    """
    updates: dict[str, tuple[str, str]] = {}
    for bare, base in BARE_CORRECTIONS.items():
        old = lex.get(bare)
        if old != base:
            updates[bare] = (old if old is not None else "∅", base)
    for key, old in lex.items():
        prefs, bare = split_lemma(key)
        if bare not in BARE_CORRECTIONS:
            continue
        new = compose(prefs, BARE_CORRECTIONS[bare])
        if old != new:
            updates[key] = (old, new)
    return updates


def apply_lexicon_repairs(lex_path: Path, *, dry_run: bool) -> dict[str, str]:
    lex = load_json(lex_path)
    updates = planned_updates(lex)
    print(f"Lexicon keys to change: {len(updates)}")
    for key, (old, new) in sorted(updates.items(), key=lambda kv: (kv[0].count("/"), kv[0]))[:40]:
        print(f"  {key}: {old!r} → {new!r}")
    if len(updates) > 40:
        print(f"  ... and {len(updates) - 40} more")

    if dry_run:
        return {k: v[1] for k, v in updates.items()}

    for key, (_old, new) in updates.items():
        lex[key] = new
    write_json(lex_path, lex)
    print(f"WROTE {lex_path}")
    return {k: v[1] for k, v in updates.items()}


def force_refresh_tokens() -> int:
    cmd = [
        sys.executable,
        str(NEXT_STEP),
        "--all",
        "--force",
        "--rules-dir",
        str(REPO_ROOT / "MNA" / "datasets" / "rules"),
    ]
    print("RUN:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def rebuild_ble() -> int:
    cmd = [
        sys.executable,
        str(TOKENS_TO_BLE),
        "--all",
        "--testament",
        "ot",
    ]
    print("RUN:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT / "Biblia-BLE")


def spot_check() -> None:
    checks = [
        ("salmos", 1, 1),
        ("isaias", 1, 1),
        ("josue", 1, 1),
        ("josue", 14, 6),
        ("genesis", 1, 1),
        ("genesis", 1, 10),
    ]
    for book, ch, vs in checks:
        path = DEFAULT_OT / f"{book}.tokens.jsonl"
        glosses = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if int(row["ch"]) == ch and int(row["vs"]) == vs:
                    glosses.append(str(row.get("es", "")))
        text = " ".join(g.replace("·", "•") for g in glosses)
        print(f"CHECK {book} {ch}:{vs}: {text[:160]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--dry-run", action="store_true", help="show planned lexicon changes only")
    ap.add_argument("--apply", action="store_true", help="write lexicon repairs")
    ap.add_argument("--force-tokens", action="store_true", help="re-apply lexicon to all OT tokens")
    ap.add_argument("--rebuild-ble", action="store_true", help="rebuild Biblia-BLE OT .ble.md files")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        args.dry_run = True

    apply_lexicon_repairs(args.lexicon, dry_run=not args.apply)

    if args.apply and args.force_tokens:
        rc = force_refresh_tokens()
        if rc != 0:
            return rc
        spot_check()

    if args.apply and args.rebuild_ble:
        rc = rebuild_ble()
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
