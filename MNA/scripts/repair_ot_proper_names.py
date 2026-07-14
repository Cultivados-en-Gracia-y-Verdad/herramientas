#!/usr/bin/env python3
"""Repair OT lexicon proper-name glosses from Open Scriptures HebrewStrong.xml.

Target: Strong's entries tagged n-pr* (person / place / gentilic) whose MNA Spanish
gloss was polluted by neighboring common-word senses (Jerusalén→disparar, etc.).

Examples (from repo root `herramientas`):

  python3 MNA/scripts/repair_ot_proper_names.py --dry-run
  python3 MNA/scripts/repair_ot_proper_names.py --apply --force-tokens
  python3 MNA/scripts/repair_ot_proper_names.py --apply --force-tokens --rebuild-ble
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEXICON = REPO_ROOT / "MNA" / "datasets" / "rules" / "hbo_lemma_lexicon.json"
DEFAULT_STRONGS = REPO_ROOT / "MNA" / "datasets" / "rules" / "sources" / "HebrewStrong.xml"
STRONGS_URL = (
    "https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/HebrewStrong.xml"
)
NEXT_STEP = REPO_ROOT / "MNA" / "scripts" / "next_stepOT.py"
TOKENS_TO_BLE = REPO_ROOT / "Biblia-BLE" / "scripts" / "tokens_to_ble.py"
EXPORT_INTERLINEAR = REPO_ROOT / "Biblia-BLE" / "scripts" / "export_interlinear.py"

NS = {"h": "http://openscriptures.github.com/morphhb/namespace"}

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

# Manual overrides when Strong's English→Spanish or OSHB compound splits need care.
MANUAL: dict[str, str] = {
    "1537": "Gilgal",
    "182": "acerca·de",
    "842": "Asera",
    "3091": "Josué",
    "3312": "Jefune",
    "3612": "Caleb",
    "4713": "egipcio",
    "4709": "Mizpa",
    "4708": "Mizpa",
    "6946": "Cades",
    "6947": "Barnea",
    "6947+": "Cades",
    "7074": "quenezeo",
    "7585": "Seol",
    "8096": "Simei",
    # Dual-sense Strong's wrongly overwritten in an earlier pass — restore lexical bases
    "4853 a": "carga",
    "4853 b": "carga",
    "7161 a": "cuerno",
    "7161 b": "cuerno",
}

# High-frequency / conventional Spanish Bible names (RVR/NBLA-ish).
EN_TO_ES: dict[str, str] = {
    "Abraham": "Abraham",
    "Abram": "Abram",
    "Isaac": "Isaac",
    "Jacob": "Jacob",
    "Israel": "Israel",
    "Joseph": "José",
    "Moses": "Moisés",
    "Aaron": "Aarón",
    "Joshua": "Josué",
    "Jehoshua": "Josué",
    "Jehoshuah": "Josué",
    "Judah": "Judá",
    "Levi": "Leví",
    "Shimei": "Simei",
    "Shimhi": "Simei",
    "Shimi": "Simei",
    "Shimeah": "Simea",
    "Mitspah": "Mizpa",
    "Mizpah": "Mizpa",
    "Mizpeh": "Mizpa",
    "Asherah": "Asera",
    "Sheol": "Seol",
    "Egyptian": "egipcio",
    "Egyptians": "egipcio",
    "Reuben": "Rubén",
    "Simeon": "Simeón",
    "Issachar": "Isacar",
    "Zebulun": "Zabulón",
    "Dan": "Dan",
    "Naphtali": "Neftalí",
    "Gad": "Gad",
    "Asher": "Aser",
    "Benjamin": "Benjamín",
    "Ephraim": "Efraín",
    "Ephraimites": "efraimita",
    "Manasseh": "Manasés",
    "Caleb": "Caleb",
    "Jephunneh": "Jefune",
    "Kenezite": "quenezeo",
    "Kenizzite": "quenezeo",
    "Kenizzites": "quenezeo",
    "Samuel": "Samuel",
    "Shemuel": "Samuel",
    "Saul": "Saúl",
    "Shaul": "Saúl",
    "David": "David",
    "Solomon": "Salomón",
    "Jonathan": "Jonatán",
    "Jerusalem": "Jerusalén",
    "Zion": "Sión",
    "Jordan": "Jordán",
    "Moab": "Moab",
    "Ammon": "Amón",
    "Amalek": "Amalec",
    "Edom": "Edom",
    "Esau": "Esaú",
    "Ishmael": "Ismael",
    "Hagar": "Agar",
    "Sarah": "Sara",
    "Sarai": "Sarai",
    "Rebekah": "Rebeca",
    "Rachel": "Raquel",
    "Leah": "Lea",
    "Ruth": "Rut",
    "Boaz": "Booz",
    "Naomi": "Noemí",
    "Hannah": "Ana",
    "Eli": "Elí",
    "Phinehas": "Finees",
    "Eleazar": "Eleazar",
    "Ithamar": "Itamar",
    "Korah": "Coré",
    "Dathan": "Datán",
    "Abiram": "Abiram",
    "Balaam": "Balaam",
    "Bileam": "Bileam",
    "Balak": "Balac",
    "Baal": "Baal",
    "Baalim": "Baales",
    "Asherah": "Asera",
    "Ashtoreth": "Astoret",
    "Dagon": "Dagón",
    "Philistine": "filisteo",
    "Philistines": "filisteo",
    "Egyptian": "egipcio",
    "Egyptians": "egipcio",
    "Egypt": "Egipto",
    "Assyria": "Asiria",
    "Asshur": "Asur",
    "Babylon": "Babilonia",
    "Babel": "Babel",
    "Chaldea": "Caldea",
    "Chaldean": "caldeo",
    "Chaldeans": "caldeo",
    "Chaldees": "caldeo",
    "Persia": "Persia",
    "Media": "Media",
    "Syria": "Siria",
    "Aram": "Aram",
    "Damascus": "Damasco",
    "Tyre": "Tiro",
    "Sidon": "Sidón",
    "Nineveh": "Nínive",
    "Lebanon": "Líbano",
    "Carmel": "Carmelo",
    "Hermon": "Hermón",
    "Sinai": "Sinaí",
    "Horeb": "Horeb",
    "Seir": "Seir",
    "Paran": "Parán",
    "Kadesh": "Cades",
    "Kadeshbarnea": "Cades-barnea",
    "Gilgal": "Gilgal",
    "Jericho": "Jericó",
    "Ai": "Hai",
    "Bethel": "Betel",
    "Bethlehem": "Belén",
    "Hebron": "Hebrón",
    "Shechem": "Siquem",
    "Shiloh": "Siloh",
    "Samaria": "Samaria",
    "Megiddo": "Meguido",
    "Jezreel": "Jezreel",
    "Beersheba": "Beerseba",
    "Beer-sheba": "Beerseba",
    "Gaza": "Gaza",
    "Gath": "Gat",
    "Ashdod": "Asdod",
    "Ashkelon": "Ascalón",
    "Ekron": "Ecrón",
    "Gilead": "Galaad",
    "Bashan": "Basán",
    "Heshbon": "Hesbón",
    "Nebo": "Nebo",
    "Pisgah": "Pisga",
    "Peor": "Peor",
    "Sheol": "Seol",
    "Eden": "Edén",
    "Nod": "Nod",
    "Ur": "Ur",
    "Haran": "Harán",
    "Padanaram": "Padan-aram",
    "Padan-aram": "Padan-aram",
    "Mesopotamia": "Mesopotamia",
    "Canaan": "Canaán",
    "Hivite": "heo",
    "Hittite": "heteo",
    "Amorite": "amoreo",
    "Jebusite": "jebuseo",
    "Perizzite": "perezeo",
    "Girgashite": "giraaseo",
    "Kenite": "queneo",
    "Midian": "Madián",
    "Midianite": "madianita",
    "Amalekite": "amalecita",
    "Ammonite": "amonita",
    "Moabite": "moabita",
    "Edomite": "edomita",
    "Ishmaelite": "ismaelita",
    "Hebrew": "hebreo",
    "Jew": "judío",
    "Jews": "judío",
    "Israelite": "israelita",
    "Levites": "levita",
    "Levite": "levita",
    "Aaronites": "aaronita",
    "Gibeon": "Gabaón",
    "Gibeonite": "gabaonita",
    "Ahab": "Acab",
    "Jezebel": "Jezabel",
    "Elijah": "Elías",
    "Elisha": "Eliseo",
    "Jehu": "Jehú",
    "Athaliah": "Atalía",
    "Hezekiah": "Ezequías",
    "Josiah": "Josías",
    "Jeremiah": "Jeremías",
    "Isaiah": "Isaías",
    "Ezekiel": "Ezequiel",
    "Daniel": "Daniel",
    "Hosea": "Oseas",
    "Joel": "Joel",
    "Amos": "Amós",
    "Obadiah": "Abdías",
    "Jonah": "Jonás",
    "Micah": "Miqueas",
    "Nahum": "Nahúm",
    "Habakkuk": "Habacuc",
    "Zephaniah": "Sofonías",
    "Haggai": "Hageo",
    "Zechariah": "Zacarías",
    "Malachi": "Malaquías",
    "Ezra": "Esdras",
    "Nehemiah": "Nehemías",
    "Esther": "Ester",
    "Mordecai": "Mardoqueo",
    "Haman": "Amán",
    "Job": "Job",
    "Elihu": "Eliú",
    "Uz": "Uz",
    "Noah": "Noé",
    "Shem": "Sem",
    "Ham": "Cam",
    "Japheth": "Jafet",
    "Adam": "Adán",
    "Eve": "Eva",
    "Cain": "Caín",
    "Abel": "Abel",
    "Seth": "Set",
    "Enoch": "Enoc",
    "Methuselah": "Matusalén",
    "Lamech": "Lamec",
    "Nimrod": "Nimrod",
    "Pharaoh": "Faraón",
    "Potiphar": "Potifar",
    "Rahab": "Rahab",
    "Deborah": "Débora",
    "Barak": "Barac",
    "Gideon": "Gedeón",
    "Abimelech": "Abimelec",
    "Jephthah": "Jefté",
    "Samson": "Sansón",
    "Delilah": "Dalila",
    "Eliab": "Eliab",
    "Jesse": "Isaí",
    "Abner": "Abner",
    "Joab": "Joab",
    "Absalom": "Absalón",
    "Adonijah": "Adonías",
    "Bathsheba": "Betsabé",
    "Uriah": "Urías",
    "Nathan": "Natán",
    "Zadok": "Sadoc",
    "Abiathar": "Abiatar",
    "Ahithophel": "Ahitofel",
    "Hushai": "Husai",
    "Rehoboam": "Roboam",
    "Jeroboam": "Jeroboam",
    "Asa": "Asa",
    "Jehoshaphat": "Josafat",
    "Jehoram": "Joram",
    "Ahaziah": "Ocozías",
    "Joash": "Joás",
    "Amaziah": "Amasías",
    "Uzziah": "Uzías",
    "Jotham": "Jotam",
    "Ahaz": "Acaz",
    "Manasseh": "Manasés",
    "Amon": "Amón",
    "Jehoiakim": "Joacim",
    "Jehoiachin": "Joaquín",
    "Zedekiah": "Sedequías",
    "Nebuchadnezzar": "Nabucodonosor",
    "Nebuchadrezzar": "Nabucodonosor",
    "Belshazzar": "Belsasar",
    "Cyrus": "Ciro",
    "Darius": "Darío",
    "Artaxerxes": "Artajerjes",
    "Zerubbabel": "Zorobabel",
    "Jeshua": "Jesúa",
    "Joshua": "Josué",
    "Nun": "Nun",
    "Hobab": "Hobab",
    "Jethro": "Jetro",
    "Reuel": "Reuel",
    "Zipporah": "Séfora",
    "Miriam": "Miriam",
    "Hur": "Hur",
    "Bezaleel": "Bezalel",
    "Aholiab": "Aholiab",
    "Othniel": "Otoniel",
    "Ehud": "Ehud",
    "Shamgar": "Samgar",
    "Tola": "Tola",
    "Jair": "Jair",
    "Ibzan": "Ibzán",
    "Elon": "Elón",
    "Abdon": "Abdón",
    "Elkanah": "Elcana",
    "Peninnah": "Penina",
    "Hophni": "Ofni",
    "Ichabod": "Icabod",
    "Kish": "Cis",
    "Abiel": "Abiel",
    "Ner": "Ner",
    "Michal": "Mical",
    "Merab": "Merab",
    "Rizpah": "Rispa",
    "Mephibosheth": "Mefiboset",
    "Ziba": "Siba",
    "Barzillai": "Barzilai",
    "Shimei": "Simei",
    "Sheba": "Seba",
    "Adoniram": "Adoniram",
    "Hiram": "Hiram",
    "Huram": "Huram",
    "Queen of Sheba": "reina·de·Seba",
    "Sheba": "Seba",
    "Ophir": "Ofir",
    "Tarshish": "Tarsis",
    "Ethiopia": "Etiopía",
    "Cush": "Cus",
    "Put": "Fut",
    "Lud": "Lud",
    "Elam": "Elam",
    "Shinar": "Sinar",
    "Gomer": "Gomer",
    "Magog": "Magog",
    "Madai": "Madai",
    "Javan": "Javán",
    "Tubal": "Tubal",
    "Meshech": "Mesec",
    "Tiras": "Tiras",
    "Caphtor": "Caftor",
    "Pathros": "Patros",
    "No": "No",
    "Noph": "Nof",
    "On": "On",
    "Rameses": "Ramesés",
    "Pithom": "Pitón",
    "Succoth": "Sucot",
    "Etham": "Etam",
    "Pi-hahiroth": "Pi-hahirot",
    "Migdol": "Migdol",
    "Baalzephon": "Baal-zefón",
    "Marah": "Mara",
    "Elim": "Elim",
    "Rephidim": "Refidim",
    "Taberah": "Tabera",
    "Kibrothhattaavah": "Seol-hatava",
    "Hazeroth": "Hazerot",
    "Eziongeber": "Ezión-geber",
    "Ezion-geber": "Ezión-geber",
    "Punon": "Punón",
    "Oboth": "Obot",
    "Ijeabarim": "Ije-abarim",
    "Dibon": "Dibón",
    "Aroer": "Aroer",
    "Jabbok": "Jaboc",
    "Arnon": "Arnón",
    "Sihon": "Sechón",
    "Og": "Og",
    "Edrei": "Edrei",
    "Ashtaroth": "Astarot",
    "Machir": "Maquir",
    "Jair": "Jair",
    "Nobah": "Nobá",
    "Kenath": "Quenat",
    "Gilboa": "Gilboa",
    "Endor": "Endor",
    "Aphek": "Afec",
    "Ebenezer": "Eben-ezer",
    "Mizpah": "Mizpa",
    "Mizpeh": "Mizpa",
    "Ramah": "Ramá",
    "Gibeah": "Gabaa",
    "Nob": "Nob",
    "Keilah": "Keila",
    "Ziklag": "Siclag",
    "Carmel": "Carmelo",
    "Maon": "Maón",
    "En-gedi": "En-gadi",
    "Engedi": "En-gadi",
    "Hachilah": "Haquila",
    "Jeshimon": "Jesimón",
    "Mahanaim": "Mahanaim",
    "Penuel": "Penuel",
    "Succoth": "Sucot",
    "Abelmeholah": "Abel-mehola",
    "Abel-meholah": "Abel-mehola",
    "Tishbite": "tisbita",
    "Shunem": "Sunem",
    "Shunammite": "sunamita",
    "Dothan": "Dotán",
    "Rimmon": "Rimón",
    "Timnah": "Timna",
    "Ajalon": "Ajalón",
    "Aijalon": "Ajalón",
    "Bethhoron": "Bet-horón",
    "Beth-horon": "Bet-horón",
    "Gezer": "Gezer",
    "Lachish": "Laquis",
    "Eglon": "Eglón",
    "Debir": "Debir",
    "Anak": "Anac",
    "Anakim": "anaceo",
    "Anakims": "anaceo",
    "Nephilim": "nefilim",
    "Rephaim": "refaíta",
    "Rephaims": "refaíta",
    "Zamzummim": "zamzumeo",
    "Emim": "emeo",
    "Horim": "horeo",
    "Avim": "aveo",
    "Caphtorim": "caftoreo",
    "Pathrusim": "patruseo",
    "Casluhim": "casluheo",
    "Nazirite": "nazareo",
    "Nazarite": "nazareo",
    "YHWH": "YHWH",
    "Jehovah": "YHWH",
    "Yahweh": "YHWH",
    "LORD": "YHWH",
    "God": "Dios",
    "Elohim": "Dios",
}

# English usage fragments that are NOT usable proper-name glosses.
EN_BLACKLIST = {
    "destruction",
    "father of gibeon",
    "plain of the vineyards",
    "multitude",
    "grove",
    "spies",
    "place that was far off",
    "aven",
    "ornan",
    "asarelah",
    "haakashtari",
}


def split_lemma(lemma: str) -> tuple[list[str], str]:
    parts = lemma.split("/")
    prefs: list[str] = []
    i = 0
    while i < len(parts) - 1 and parts[i] in PREF_SET:
        prefs.append(parts[i])
        i += 1
    return prefs, "/".join(parts[i:])


def compose(prefs: list[str], base: str) -> str:
    if not prefs:
        return base
    parts: list[str] = []
    for p in prefs:
        if p == "d":
            # Gentilics / common nouns that are lowercase stay with el/la heuristic.
            head = base.split("·")[0]
            if head[:1].islower() and head.endswith(("a", "ción", "sión", "dad", "tad", "umbre")):
                parts.append("la")
            elif head[:1].islower():
                parts.append("el")
            else:
                parts.append("el")
        else:
            parts.append(PREFIX_GLOSS[p])
    parts.append(base)
    return "·".join(parts)


def strongs_num(bare: str) -> str | None:
    m = re.match(r"^(\d+)", bare.strip())
    return m.group(1) if m else None


def extract_en_name(usage: str) -> str | None:
    u = (usage or "").strip()
    if not u:
        return None
    # Strong's often appends "Compare …" / "See also …" after a period.
    u = re.split(r"\.\s*(?:See|Compare)\b", u, maxsplit=1, flags=re.I)[0]
    u = re.sub(r"\b(?:See also|See|Compare)\b.*$", "", u, flags=re.I)
    u = u.rstrip(".").strip()
    if not u:
        return None

    def clean_piece(piece: str) -> str | None:
        first = piece.strip()
        if first.lower().startswith("the "):
            first = first[4:].strip()
        # Hebrew(-ess, woman) → Hebrew
        first = re.sub(r"\([^)]*\)", "", first).strip()
        first = re.sub(r"\(-.*$", "", first).strip()
        if not first:
            return None
        if "×" in first or first.lower().startswith("they "):
            return None
        if first.lower() in EN_BLACKLIST:
            return None
        if "." in first or "Compare" in first or "See" in first:
            return None
        if len(first.split()) > 3:
            return None
        if first[:1].islower() or first[:1] == "(":
            return None
        if first.startswith("("):
            return None
        if " of " in first.lower() and not first.lower().startswith(("beer", "beth", "abel")):
            return None
        first = re.split(r"\s*\(", first, maxsplit=1)[0].strip()
        return first or None

    alts = [clean_piece(p) for p in u.split(",")]
    alts = [a for a in alts if a]
    if not alts:
        return None
    # Prefer an alternative we already know how to Spanish-render
    # (e.g. Jehoshua, Jehoshuah, Joshua → Joshua).
    for a in alts:
        if a in EN_TO_ES:
            return a
    return alts[0]


def transliterate_fallback(en: str) -> str:
    """Best-effort English Bible name → Spanish-ish form."""
    s = en.strip().replace(".", "")
    s = s.replace("ph", "f").replace("Ph", "F")
    # Hyphenated place names: keep hyphens; no spaces expected after extract.
    parts = s.split("-")
    titled = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        titled.append(p[:1].upper() + p[1:])
    return "-".join(titled)


def en_to_es_name(en: str) -> str:
    if en in EN_TO_ES:
        return EN_TO_ES[en]
    compact = en.replace("-", "")
    for k, v in EN_TO_ES.items():
        if k.replace("-", "") == compact:
            return v

    # Beth-X / BethX → Bet-X (Spanish Bible convention)
    if en.startswith("Beth-"):
        rest = en[5:]
        if rest:
            return f"Bet-{EN_TO_ES.get(rest, transliterate_fallback(rest))}"
    if en.startswith("Beth") and len(en) > 4:
        rest = en[4:]
        if rest:
            return f"Bet-{EN_TO_ES.get(rest, transliterate_fallback(rest))}"
    if en.startswith("Beer-") or en in ("Beersheba", "Beer-sheba"):
        if "sheba" in en.lower():
            return "Beerseba"
    if "meholah" in en.lower() and en.lower().startswith("abel"):
        return "Abel-mehola"

    if en.endswith("ites") and en[:-1] in EN_TO_ES:
        return EN_TO_ES[en[:-1]]
    if en.endswith("ite") and en in EN_TO_ES:
        return EN_TO_ES[en]
    if en.endswith("ites"):
        stem = en[:-4]
        base = EN_TO_ES.get(stem, transliterate_fallback(stem))
        head = base[:1].lower() + base[1:] if base[:1].isupper() else base
        return head if head.endswith(("ita", "eo")) else f"{head}ita"
    if en.endswith("ite"):
        stem = en[:-3]
        base = EN_TO_ES.get(stem, transliterate_fallback(stem))
        head = base[:1].lower() + base[1:] if base[:1].isupper() else base
        return head if head.endswith(("ita", "eo")) else f"{head}ita"
    return transliterate_fallback(en)


def ensure_strongs_xml(path: Path) -> Path:
    if path.is_file() and path.stat().st_size > 1000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"DOWNLOAD {STRONGS_URL}")
    urllib.request.urlretrieve(STRONGS_URL, path)
    return path


def load_proper_name_map(strongs_xml: Path) -> dict[str, str]:
    """Map bare Strong's number string → Spanish gloss base."""
    root = ET.parse(strongs_xml).getroot()
    out: dict[str, str] = {}
    skipped = 0
    for entry in root.findall("h:entry", NS):
        eid = entry.get("id") or ""
        if not eid.startswith("H"):
            continue
        w = entry.find("h:w", NS)
        if w is None:
            continue
        pos = w.get("pos") or ""
        # Only pure proper-name / gentilic entries. Skip dual common+name
        # (e.g. n-m n-pr-m "burden…") to avoid polluting lexical senses.
        pos_tokens = [t for t in pos.replace(",", " ").split() if t]
        if not pos_tokens:
            continue
        if not all(t.startswith("n-pr") or "gent" in t for t in pos_tokens):
            continue
        usage = entry.findtext("h:usage", default="", namespaces=NS) or ""
        en = extract_en_name(usage)
        if not en:
            skipped += 1
            continue
        if "×" in en or en.lower().startswith("they "):
            skipped += 1
            continue
        num = str(int(eid[1:]))  # strip zeros
        es = en_to_es_name(en)
        out[num] = es
    # Manual wins
    out.update(MANUAL)
    print(f"Proper-name map: {len(out)} Strong's numbers (skipped usage parse: {skipped})")
    return out


def planned_updates(lex: dict[str, str], name_map: dict[str, str]) -> dict[str, tuple[str, str]]:
    updates: dict[str, tuple[str, str]] = {}

    # Ensure bare keys for every lexicon bare that matches a proper name.
    bares_in_lex: set[str] = set()
    for key in lex:
        _prefs, bare = split_lemma(key)
        bares_in_lex.add(bare)

    # Also ensure MANUAL keys and mapped numbers present as bare.
    for bare in list(bares_in_lex) + list(MANUAL.keys()):
        num = strongs_num(bare)
        if bare in MANUAL:
            target = MANUAL[bare]
        elif num and num in name_map:
            # For letter/+ variants, use the number's Spanish name
            if bare.endswith("+") and bare in MANUAL:
                target = MANUAL[bare]
            else:
                target = name_map[num]
        else:
            continue
        old = lex.get(bare)
        if old != target:
            updates[bare] = (old if old is not None else "∅", target)

    for key, old in lex.items():
        prefs, bare = split_lemma(key)
        num = strongs_num(bare)
        if bare in MANUAL:
            target_base = MANUAL[bare]
        elif num and num in name_map:
            target_base = name_map[num]
        else:
            continue
        new = compose(prefs, target_base)
        if old != new:
            updates[key] = (old, new)
    return updates


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def apply_updates(lex_path: Path, updates: dict[str, tuple[str, str]], *, dry_run: bool) -> None:
    print(f"Lexicon keys to change: {len(updates)}")
    # Show highest-impact-looking samples first (uncapitalized old glosses)
    samples = sorted(
        updates.items(),
        key=lambda kv: (
            0 if (kv[1][0] not in (None, "∅") and kv[1][0][:1].islower()) else 1,
            kv[0].count("/"),
            kv[0],
        ),
    )
    for key, (old, new) in samples[:50]:
        print(f"  {key}: {old!r} → {new!r}")
    if len(samples) > 50:
        print(f"  ... and {len(samples) - 50} more")
    if dry_run:
        return
    lex = load_json(lex_path)
    for key, (_old, new) in updates.items():
        lex[key] = new
    write_json(lex_path, lex)
    print(f"WROTE {lex_path}")


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
    cmd = [sys.executable, str(TOKENS_TO_BLE), "--all", "--testament", "ot"]
    print("RUN:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT / "Biblia-BLE")


def rebuild_interlinear_sample() -> int:
    # Full OT interlinear is large; refresh a few name-heavy books.
    books = ["josue", "genesis", "1samuel", "1reyes", "1cronicas"]
    rc = 0
    for book in books:
        cmd = [sys.executable, str(EXPORT_INTERLINEAR), book, "--testament", "ot"]
        print("RUN:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=REPO_ROOT / "Biblia-BLE") or rc
    return rc


def spot_check() -> None:
    checks = [
        ("josue", 14, 6),
        ("genesis", 12, 1),
        ("1samuel", 1, 1),
        ("1reyes", 1, 1),
        ("salmos", 2, 6),
    ]
    ot = REPO_ROOT / "MNA" / "datasets" / "interlinear" / "OT"
    for book, ch, vs in checks:
        path = ot / f"{book}.tokens.jsonl"
        glosses = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if int(row["ch"]) == ch and int(row["vs"]) == vs:
                    glosses.append(str(row.get("es", "")))
        text = " ".join(g.replace("·", "•") for g in glosses)
        print(f"CHECK {book} {ch}:{vs}: {text[:200]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--strongs-xml", type=Path, default=DEFAULT_STRONGS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-tokens", action="store_true")
    ap.add_argument("--rebuild-ble", action="store_true")
    ap.add_argument("--rebuild-interlinear", action="store_true")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        args.dry_run = True

    strongs_xml = ensure_strongs_xml(args.strongs_xml)
    name_map = load_proper_name_map(strongs_xml)
    lex = load_json(args.lexicon)
    updates = planned_updates(lex, name_map)
    apply_updates(args.lexicon, updates, dry_run=not args.apply)

    if args.apply and args.force_tokens:
        rc = force_refresh_tokens()
        if rc != 0:
            return rc
        spot_check()

    if args.apply and args.rebuild_ble:
        rc = rebuild_ble()
        if rc != 0:
            return rc

    if args.apply and args.rebuild_interlinear:
        rc = rebuild_interlinear_sample()
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
