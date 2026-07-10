"""Spanish finite-verb conjugation from infinitive gloss + MorphGNT verb tag."""

from __future__ import annotations

import json
from pathlib import Path

from grc_inflect_es import (
    INVARIANT_GLOSS_PREFIXES,
    inflect_past_participle,
    is_participle_morph,
    split_punct,
)

RULES_DIR = Path(__file__).resolve().parents[1] / "datasets" / "rules"

EIMI_BY_MORPH: dict[str, str] = {}


def load_eimi_by_morph(rules_dir: Path | None = None) -> dict[str, str]:
    global EIMI_BY_MORPH
    path = (rules_dir or RULES_DIR) / "grc_eimi_by_morph.json"
    if not path.is_file():
        EIMI_BY_MORPH = {}
        return EIMI_BY_MORPH
    EIMI_BY_MORPH = json.loads(path.read_text(encoding="utf-8"))
    return EIMI_BY_MORPH


def parse_verb_morph(morph: str) -> dict[str, str | None] | None:
    if not morph.startswith("V-") or len(morph) < 6:
        return None
    return {
        "person": morph[2] if morph[2] in "123" else None,
        "tense": morph[3] if morph[3] != "-" else None,
        "voice": morph[4] if morph[4] != "-" else None,
        "mood": morph[5] if morph[5] != "-" else None,
        "number": morph[7] if len(morph) > 7 and morph[7] in "SP" else None,
        "gender": morph[8] if len(morph) > 8 and morph[8] in "MFN" else None,
    }


def is_infinitive_verb_morph(morph: str) -> bool:
    return morph.startswith("V") and len(morph) > 5 and morph[5] == "N"


def is_finite_verb_morph(morph: str) -> bool:
    parsed = parse_verb_morph(morph)
    if not parsed:
        return False
    return parsed["person"] in ("1", "2", "3") and parsed["mood"] in ("I", "S", "D", "O", "M")


def _pn_index(person: str, number: str) -> int | None:
    return {
        ("1", "S"): 0,
        ("2", "S"): 1,
        ("3", "S"): 2,
        ("1", "P"): 3,
        ("2", "P"): 4,
        ("3", "P"): 5,
    }.get((person, number))


def _stem_class(inf: str) -> str | None:
    core, _ = split_punct(inf.lower())
    if core.endswith("ar"):
        return "ar"
    if core.endswith("er"):
        return "er"
    if core.endswith("ir"):
        return "ir"
    return None


IRREGULAR_PRETERITE: dict[str, tuple[str, str, str, str, str, str]] = {
    "decir": ("dije", "dijiste", "dijo", "dijimos", "dijisteis", "dijeron"),
    "bendecir": ("bendije", "bendijiste", "bendijo", "bendijimos", "bendijisteis", "bendijeron"),
    "contradecir": ("contradije", "contradijiste", "contradijo", "contradijimos", "contradijisteis", "contradijeron"),
    "hacer": ("hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron"),
    "satisfacer": ("satisfice", "satisficiste", "satisfizo", "satisficimos", "satisficisteis", "satisficieron"),
    "tener": ("tuve", "tuviste", "tuvo", "tuvimos", "tuvisteis", "tuvieron"),
    "poner": ("puse", "pusiste", "puso", "pusimos", "pusisteis", "pusieron"),
    "venir": ("vine", "viniste", "vino", "vinimos", "vinisteis", "vinieron"),
    "querer": ("quise", "quisiste", "quiso", "quisimos", "quisisteis", "quisieron"),
    "poder": ("pude", "pudiste", "pudo", "pudimos", "pudisteis", "pudieron"),
    "saber": ("supe", "supiste", "supo", "supimos", "supisteis", "supieron"),
    "caber": ("cupe", "cupiste", "cupo", "cupimos", "cupisteis", "cupieron"),
    "haber": ("hube", "hubiste", "hubo", "hubimos", "hubisteis", "hubieron"),
    "traer": ("traje", "trajiste", "trajo", "trajimos", "trajisteis", "trajeron"),
    "caer": ("caí", "caíste", "cayó", "caímos", "caísteis", "cayeron"),
    "dar": ("di", "diste", "dio", "dimos", "disteis", "dieron"),
    "ver": ("vi", "viste", "vio", "vimos", "visteis", "vieron"),
    "ser": ("fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron"),
    "ir": ("fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron"),
    "estar": ("estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron"),
}

IRREGULAR_PRESENT: dict[str, tuple[str, str, str, str, str, str]] = {
    "ser": ("soy", "eres", "es", "somos", "sois", "son"),
    "ir": ("voy", "vas", "va", "vamos", "vais", "van"),
    "tener": ("tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen"),
    "venir": ("vengo", "vienes", "viene", "venimos", "venís", "vienen"),
    "poner": ("pongo", "pones", "pone", "ponemos", "ponéis", "ponen"),
    "salir": ("salgo", "sales", "sale", "salimos", "salís", "salen"),
    "decir": ("digo", "dices", "dice", "decimos", "decís", "dicen"),
    "haber": ("he", "has", "ha", "hemos", "habéis", "han"),
    "saber": ("sé", "sabes", "sabe", "sabemos", "sabéis", "saben"),
    "querer": ("quiero", "quieres", "quiere", "queremos", "queréis", "quieren"),
    "poder": ("puedo", "puedes", "puede", "podemos", "podéis", "pueden"),
    "ver": ("veo", "ves", "ve", "vemos", "veis", "ven"),
    "hacer": ("hago", "haces", "hace", "hacemos", "hacéis", "hacen"),
    "caber": ("quepo", "cabes", "cabe", "cabemos", "cabéis", "caben"),
    "convenir": ("convengo", "convenes", "conviene", "convenimos", "convenís", "convienen"),
    "rogar": ("ruego", "ruegas", "ruega", "rogamos", "rogáis", "ruegan"),
    "negar": ("niego", "niegas", "niega", "negamos", "negáis", "niegan"),
    "confesar": ("confieso", "confiesas", "confiesa", "confesamos", "confesáis", "confiesan"),
    "recordar": ("recuerdo", "recuerdas", "recuerda", "recordamos", "recordáis", "recuerdan"),
}

IRREGULAR_IMPERATIVE: dict[str, dict[tuple[str, str], str]] = {
    "rogar": {("2", "S"): "ruega"},
    "recordar": {("2", "S"): "recuerda"},
}

IRREGULAR_SUBJUNCTIVE: dict[str, tuple[str, str, str, str, str, str]] = {
    "llegar": ("llegue", "llegues", "llegue", "lleguemos", "lleguéis", "lleguen"),
}

IRREGULAR_FUTURE: dict[str, tuple[str, str, str, str, str, str]] = {
    "decir": ("diré", "dirás", "dirá", "diremos", "diréis", "dirán"),
    "hacer": ("haré", "harás", "hará", "haremos", "haréis", "harán"),
    "tener": ("tendré", "tendrás", "tendrá", "tendremos", "tendréis", "tendrán"),
    "poner": ("pondré", "pondrás", "pondrá", "pondremos", "pondréis", "pondrán"),
    "venir": ("vendré", "vendrás", "vendrá", "vendremos", "vendréis", "vendrán"),
    "querer": ("querré", "querrás", "querrá", "querremos", "querréis", "querrán"),
    "poder": ("podré", "podrás", "podrá", "podremos", "podréis", "podrán"),
    "saber": ("sabré", "sabrás", "sabrá", "sabremos", "sabréis", "sabrán"),
    "caber": ("cabré", "cabrás", "cabrá", "cabremos", "cabréis", "cabrán"),
    "haber": ("habré", "habrás", "habrá", "habremos", "habréis", "habrán"),
    "salir": ("saldré", "saldrás", "saldrá", "saldremos", "saldréis", "saldrán"),
    "valer": ("valdré", "valdrás", "valdrá", "valdremos", "valdréis", "valdrán"),
}


def _regular_present(inf: str, idx: int) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    endings = ("o", "as", "a", "amos", "áis", "an") if cls == "ar" else ("o", "es", "e", "emos", "éis", "en")
    return stem + endings[idx]


def _regular_imperfect(inf: str, idx: int) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    if cls == "ar":
        endings = ("aba", "abas", "aba", "ábamos", "abais", "aban")
    else:
        endings = ("ía", "ías", "ía", "íamos", "íais", "ían")
    return stem + endings[idx]


def _regular_future(inf: str, idx: int) -> str | None:
    if not _stem_class(inf):
        return None
    endings = ("é", "ás", "á", "emos", "éis", "án")
    return inf + endings[idx]


def _regular_preterite(inf: str, idx: int) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    if cls == "ar":
        endings = ("é", "aste", "ó", "amos", "asteis", "aron")
    else:
        endings = ("í", "iste", "ió", "imos", "isteis", "ieron")
    return stem + endings[idx]


def _regular_present_subjunctive(inf: str, idx: int) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    if cls == "ar":
        endings = ("e", "es", "e", "emos", "éis", "en")
    else:
        endings = ("a", "as", "a", "amos", "áis", "an")
    return stem + endings[idx]


def _regular_imperfect_subjunctive(inf: str, idx: int) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    if cls == "ar":
        endings = ("ara", "aras", "ara", "áramos", "arais", "aran")
    else:
        endings = ("iera", "ieras", "iera", "iéramos", "ierais", "ieran")
    return stem + endings[idx]


def _regular_imperative(inf: str, person: str, number: str) -> str | None:
    cls = _stem_class(inf)
    if not cls:
        return None
    stem = inf[:-2]
    if person == "2" and number == "S":
        return stem + ("a" if cls == "ar" else "e")
    if person == "3" and number == "S":
        return stem + "a"
    if person == "2" and number == "P":
        return stem + ("ad" if cls == "ar" else "ed")
    if person == "3" and number == "P":
        return stem + ("an" if cls == "ar" else "en")
    if person == "1" and number == "P":
        return stem + ("emos" if cls == "ar" else "amos")
    return None


def _participle_for_voice(inf: str, number: str, gender: str = "M") -> str | None:
    morph_stub = f"V--PAP{number}{gender}M-"
    return inflect_past_participle(inf.lower(), morph_stub)


def _aux_perfect(person: str, number: str, *, pluperfect: bool = False) -> str:
    if pluperfect:
        table = ("había", "habías", "había", "habíamos", "habíais", "habían")
    else:
        table = ("he", "has", "ha", "hemos", "habéis", "han")
    idx = _pn_index(person, number)
    return table[idx if idx is not None else 2]


def _lookup_form(
    inf: str,
    tense: str,
    mood: str,
    person: str,
    number: str,
    voice: str,
) -> str | None:
    idx = _pn_index(person, number)
    if idx is None:
        return None

    core, punct = split_punct(inf.lower())

    if mood in ("S", "O"):
        if core in IRREGULAR_SUBJUNCTIVE:
            return IRREGULAR_SUBJUNCTIVE[core][idx] + punct
        if tense in ("A", "X"):
            form = _regular_present_subjunctive(core, idx)
        else:
            form = _regular_imperfect_subjunctive(core, idx)
        return (form + punct) if form else None

    if mood in ("D", "M"):
        irr = IRREGULAR_IMPERATIVE.get(core, {}).get((person, number))
        if irr:
            return irr + punct
        form = _regular_imperative(core, person, number)
        return (form + punct) if form else None

    if mood != "I":
        return None

    if voice == "P":
        part = _participle_for_voice(core, number)
        if not part:
            return None
        if tense == "P":
            aux = "es" if number == "S" else "son"
        elif tense == "A":
            aux = "fue" if number == "S" else "fueron"
        elif tense == "F":
            aux = "será" if number == "S" else "serán"
        elif tense == "X":
            aux = _aux_perfect(person, number)
        elif tense == "Y":
            aux = _aux_perfect(person, number, pluperfect=True)
        elif tense == "I":
            aux = "era" if number == "S" else "eran"
        else:
            return None
        return f"{aux} {part}{punct}"

    if tense == "P" and core in IRREGULAR_PRESENT:
        return IRREGULAR_PRESENT[core][idx] + punct
    if tense == "P":
        form = _regular_present(core, idx)
    elif tense == "I":
        form = _regular_imperfect(core, idx)
    elif tense == "F":
        if core in IRREGULAR_FUTURE:
            return IRREGULAR_FUTURE[core][idx] + punct
        form = _regular_future(core, idx)
    elif tense == "A":
        if core in IRREGULAR_PRETERITE:
            return IRREGULAR_PRETERITE[core][idx] + punct
        form = _regular_preterite(core, idx)
    elif tense == "X":
        part = _participle_for_voice(core, number)
        if not part:
            return None
        return f"{_aux_perfect(person, number)} {part}{punct}"
    elif tense == "Y":
        part = _participle_for_voice(core, number)
        if not part:
            return None
        return f"{_aux_perfect(person, number, pluperfect=True)} {part}{punct}"
    else:
        return None

    return (form + punct) if form else None


def conjugate_finite(inf: str, morph: str) -> str | None:
    parsed = parse_verb_morph(morph)
    if not parsed or not is_finite_verb_morph(morph):
        return None
    person = parsed["person"]
    number = parsed["number"] or "S"
    if not person:
        return None
    return _lookup_form(
        inf,
        parsed["tense"] or "P",
        parsed["mood"] or "I",
        person,
        number,
        parsed["voice"] or "A",
    )


def conjugate_infinitive(inf: str, morph: str) -> str | None:
    if not is_infinitive_verb_morph(morph):
        return None
    core, punct = split_punct(inf)
    if not core or "·" in core:
        return None
    return core + punct


def inflect_ginomai(morph: str) -> str | None:
    """Conjugate γίνομαι as llegar + a·ser instead of mangling llegar·a·ser."""
    if is_infinitive_verb_morph(morph):
        return "llegar·a·ser"
    if is_participle_morph(morph):
        tense = morph[3] if len(morph) > 3 else "P"
        if tense == "P":
            return "llegando a·ser"
        return "llegado a·ser"
    if not is_finite_verb_morph(morph):
        return None
    parsed = parse_verb_morph(morph)
    if not parsed:
        return None
    person = parsed["person"] or "3"
    number = parsed["number"] or "S"
    tense = parsed["tense"] or "P"
    mood = parsed["mood"] or "I"
    voice = parsed["voice"] or "M"
    if voice == "P" and mood == "I" and tense in ("A", "X", "Y"):
        voice = "M"
    llegar_form = _lookup_form("llegar", tense, mood, person, number, voice)
    if not llegar_form and voice != "A":
        llegar_form = _lookup_form("llegar", tense, mood, person, number, "A")
    if not llegar_form:
        return None
    core, punct = split_punct(llegar_form)
    return f"{core} a·ser{punct}"


def inflect_verb_gloss(gloss: str, morph: str, lemma: str = "") -> str | None:
    if gloss.startswith(INVARIANT_GLOSS_PREFIXES) or gloss in ("", "?"):
        return None
    if lemma == "γίνομαι":
        return inflect_ginomai(morph)
    if lemma == "εἰμί" and morph in EIMI_BY_MORPH:
        return EIMI_BY_MORPH[morph]
    if is_infinitive_verb_morph(morph):
        return conjugate_infinitive(gloss, morph)
    if is_finite_verb_morph(morph):
        return conjugate_finite(gloss, morph)
    return None


def inflect_verb_from_lemma(lemma: str, base_gloss: str, morph: str) -> str | None:
    if lemma == "γίνομαι":
        return inflect_ginomai(morph)
    if lemma == "εἰμί" and morph in EIMI_BY_MORPH:
        return EIMI_BY_MORPH[morph]
    return inflect_verb_gloss(base_gloss, morph, lemma)


load_eimi_by_morph()
