#!/usr/bin/env python3
"""Map AHRC / Paleo-Hebrew lemma evidence into BLE-style Spanish gloss candidates.

AHRC is investigative input (concrete English sense + parent root), not automatic truth.
This module turns indexed AHRC rows into Spanish gloss *candidates* for MNA OT batches.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHRC_JSONL = ROOT / "data" / "ahrc" / "strongs.jsonl"
COMPARE_JSONL = ROOT / "data" / "index" / "lemma-compare.jsonl"
LETTERS_DIR = ROOT / "data" / "letters"

from strongs import bare_mna_lemma, strongs_from_mna_lemma  # noqa: E402

# Common AHRC English headwords → BLE Spanish lexical base (no prefixes).
EN_TO_ES = {
    "mist": "niebla",
    "desire": "desear",
    "yearn": "anhelar",
    "brother": "hermano",
    "sister": "hermana",
    "light": "luz",
    "sign": "señal",
    "father": "padre",
    "mother": "madre",
    "house": "casa",
    "son": "hijo",
    "daughter": "hija",
    "king": "rey",
    "queen": "reina",
    "man": "hombre",
    "woman": "mujer",
    "land": "tierra",
    "earth": "tierra",
    "water": "agua",
    "fire": "fuego",
    "stone": "piedra",
    "tree": "árbol",
    "fruit": "fruto",
    "seed": "semilla",
    "blood": "sangre",
    "bone": "hueso",
    "flesh": "carne",
    "heart": "corazón",
    "hand": "mano",
    "eye": "ojo",
    "ear": "oído",
    "mouth": "boca",
    "word": "palabra",
    "name": "nombre",
    "day": "día",
    "night": "noche",
    "year": "año",
    "city": "ciudad",
    "wall": "muro",
    "door": "puerta",
    "gate": "puerta",
    "path": "camino",
    "way": "camino",
    "road": "camino",
    "horse": "caballo",
    "donkey": "asno",
    "mule": "mula",
    "ox": "buey",
    "sheep": "oveja",
    "lamb": "cordero",
    "prophet": "profeta",
    "priest": "sacerdote",
    "servant": "siervo",
    "gold": "oro",
    "silver": "plata",
    "iron": "hierro",
    "bronze": "bronce",
    "copper": "cobre",
    "net": "red",
    "netting": "celosía",
    "lattice": "celosía",
    "network": "celosía",
    "lily": "lirio",
    "lilly": "lirio",
    "join": "unir",
    "joint": "juntura",
    "ledge": "travesaño",
    "border": "borde",
    "rim": "borde",
    "pillar": "columna",
    "porch": "pórtico",
    "vestibule": "pórtico",
    "hall": "pórtico",
    "seat": "asiento",
    "throne": "trono",
    "floor": "suelo",
    "ground": "suelo",
    "ceiling": "techo",
    "beam": "viga",
    "chain": "cadena",
    "cord": "cuerda",
    "line": "cuerda",
    "measure": "medida",
    "cast": "fundición",
    "molten": "fundición",
    "bath": "bato",
    "shout": "grito",
    "cry": "grito",
    "joy": "gozo",
    "delight": "deleite",
    "beaten": "batido",
    "hammered": "batido",
    "cut": "cortar",
    "divide": "dividir",
    "carve": "cincelar",
    "engrave": "grabar",
    "outer": "exterior",
    "inner": "interior",
    "angry": "irritado",
    "sullen": "irritado",
    "vexed": "irritado",
    "heavy": "pesado",
    "noble": "noble",
    "metropolis": "ciudad",
    "city": "ciudad",
    "jug": "cántaro",
    "flask": "cántaro",
    "bravery": "valentía",
    "strength": "fuerza",
    "failure": "pecado",
    "rejoicing": "gozoso",
    "advice": "aconsejar",
    "craft": "artesano",
    "craftsman": "artesano",
    "workman": "artesano",
    "abyss": "abismo",
    "deep": "abismo",
    "body": "cuerpo",
    "hear": "oír",
    "listen": "oír",
    "fear": "temer",
    "run": "correr",
    "strong": "fuerte",
    "life": "vida",
    "sin": "pecado",
    "lord": "señor",
    "elder": "anciano",
    "portion": "porción",
    "knowledge": "conocimiento",
    "garment": "vestido",
    "clothing": "vestido",
    "sabbath": "sábado",
    "prophet": "profeta",
    "mule": "mula",
    "horse": "caballo",
    # High-impact OT repair mappings
    "happy": "dichoso",
    "blessed": "dichoso",
    "lost": "malvado",
    "wicked": "malvado",
    "vision": "visión",
    "perceive": "ver",
    "death": "muerte",
    "sea": "mar",
    "prepare": "preparar",
    "camp": "campamento",
    "pluck": "cantar",
    "sing": "cantar",
    "praise": "alabar",
    "fire": "fuego",
    "gold": "oro",
    "gate": "puerta",
    "bone": "hueso",
    "sister": "hermana",
    "throne": "trono",
    "donkey": "asno",
    "ox": "buey",
    "pillar": "columna",
    "wall": "muro",
    "thus": "así",
    "treasure": "tesoro",
    "copper": "cobre",
    "brass": "bronce",
    "curtain": "cortina",
    "carcass": "cadáver",
    "prince": "príncipe",
    "captain": "príncipe",
    "counsel": "aconsejar",
    "rejoicing": "gozo",
    "joy": "gozo",
}


def load_ahrc(path: Path = AHRC_JSONL) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    if not path.is_file():
        return by
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        by.setdefault(row["strongs"], []).append(row)
    return by


def load_compare(path: Path = COMPARE_JSONL) -> dict[str, dict]:
    if not path.is_file():
        return {}
    return {
        json.loads(line)["strongs"]: json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def load_letter_notes(path: Path = LETTERS_DIR) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.is_dir():
        return out
    for p in path.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        letter = data.get("letter") or p.stem
        out[letter] = data
    return out


def clean_ahrc_translation(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"\s*\(V\)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def ahrc_translation_to_es(translation: str) -> str | None:
    """Best-effort English AHRC headword → Spanish base gloss."""
    cleaned = clean_ahrc_translation(translation)
    if not cleaned:
        return None
    # Prefer first alternative before slash/comma.
    head = re.split(r"[/,;]| or ", cleaned, maxsplit=1)[0].strip()
    key = head.lower()
    if key in EN_TO_ES:
        return EN_TO_ES[key]
    # Multi-word: try last content word (COMMON PHRASE → last noun/verb)
    words = [w for w in re.split(r"\s+", key) if w and w not in {"the", "a", "an", "to", "of"}]
    for w in reversed(words):
        if w in EN_TO_ES:
            return EN_TO_ES[w]
    return None


def letter_hint(hebrew: str, letters: dict[str, dict]) -> list[str]:
    hints = []
    for ch in hebrew or "":
        note = letters.get(ch)
        if not note:
            continue
        meanings = note.get("meanings") or []
        pict = note.get("pictograph")
        bit = f"{ch}={pict or note.get('name')}"
        if meanings:
            bit += f"({', '.join(meanings[:3])})"
        hints.append(bit)
    return hints


def paleo_evidence_for_lemma(
    lemma: str,
    *,
    ahrc_by: dict[str, list[dict]] | None = None,
    compare: dict[str, dict] | None = None,
    letters: dict[str, dict] | None = None,
) -> dict:
    """Return paleo/AHRC evidence package for one MNA lemma key."""
    ahrc_by = ahrc_by if ahrc_by is not None else load_ahrc()
    compare = compare if compare is not None else load_compare()
    letters = letters if letters is not None else load_letter_notes()

    strongs = strongs_from_mna_lemma(lemma)
    bare = bare_mna_lemma(lemma)
    out: dict = {
        "lemma": lemma,
        "bare": bare,
        "strongs": strongs,
        "ahrc": [],
        "cgv_from_compare": [],
        "letter_hints": [],
        "es_candidates": [],
        "notes": [],
    }
    if not strongs:
        out["notes"].append("no Strong's parsed from lemma")
        return out

    rows = ahrc_by.get(strongs, [])
    out["ahrc"] = rows
    for row in rows:
        es = ahrc_translation_to_es(row.get("translation") or "")
        if es and es not in out["es_candidates"]:
            out["es_candidates"].append(es)
        hebrew = row.get("hebrew") or ""
        for hint in letter_hint(hebrew, letters):
            if hint not in out["letter_hints"]:
                out["letter_hints"].append(hint)
        if row.get("parent_root_gloss"):
            out["notes"].append(
                f"parent {row.get('parent_root')}: {row.get('parent_root_gloss')}"
            )
        if row.get("definition"):
            out["notes"].append(f"def: {row['definition']}")

    cmp = compare.get(strongs) or {}
    mna = cmp.get("mna") or {}
    for g in (mna.get("lexicon_glosses") or []) + (mna.get("gloss_es") or []):
        g = str(g).strip()
        if not g or g == "?":
            continue
        # Prefer bare lexical base without prefixes when possible.
        base = g.split("·")[-1]
        if base and base not in out["cgv_from_compare"]:
            out["cgv_from_compare"].append(base)
        # Do NOT auto-promote CGV compare glosses into es_candidates:
        # Strong's buckets mix many MNA lemma keys and can pollute proper names.

    return out


def best_paleo_es(lemma: str, **kwargs) -> tuple[str | None, dict]:
    evidence = paleo_evidence_for_lemma(lemma, **kwargs)
    cands = evidence.get("es_candidates") or []
    return (cands[0] if cands else None), evidence
