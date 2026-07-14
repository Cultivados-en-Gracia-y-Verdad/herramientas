#!/usr/bin/env python3
"""Spanish finite-verb conjugation from infinitive gloss + OSHB verb morph.

OSHB verb component shape (after optional language H and prefixes):
  V <stem> <aspect> … <person><gender><number> …
  e.g. Vqp3ms, Vqw3mp, Vqv2ms, Vqrmsa, Vqc

Aspect → Spanish tense (BLE pedagogical defaults):
  p perfect (qatal)      → pretérito  (statives → presente)
  w wayyiqtol            → pretérito
  q weqatal              → futuro
  i imperfect (yiqtol)   → presente
  j jussive              → presente de subjuntivo
  h cohortative          → presente de subjuntivo
  v imperative           → imperativo
  r active participle    → presente 3ª (el/la… → el·que·…)
  s passive participle   → participio (acuerdo en género/número)
  c infinitive construct → infinitivo (unchanged)
  a infinitive absolute  → infinitivo (unchanged)
"""

from __future__ import annotations

import re

# Reuse NT irregular tables / helpers.
from grc_conj_es import (
    IRREGULAR_FUTURE,
    IRREGULAR_IMPERATIVE,
    IRREGULAR_PRESENT,
    IRREGULAR_PRETERITE,
    IRREGULAR_SUBJUNCTIVE,
    _pn_index,
    _regular_future,
    _regular_imperative,
    _regular_imperfect,
    _regular_present,
    _regular_present_subjunctive,
    _regular_preterite,
    _stem_class,
)

FUNC_PREFIXES = {"y", "el", "la", "los", "las", "en", "a", "de", "según", "que", "¡", "¿"}
ARTICLES = {"el", "la", "los", "las"}


def _stem_class_hbo(inf: str) -> str | None:
    cls = _stem_class(inf)
    if cls:
        return cls
    if inf.endswith("ír"):
        return "ir"
    if inf.endswith("ér"):
        return "er"
    if inf.endswith("ár"):
        return "ar"
    return None


def _bare_stem(inf: str) -> str:
    if inf.endswith(("ar", "er", "ir", "ár", "ér", "ír")):
        return inf[:-2]
    return inf


# Perfect of these → Spanish present (stative / knowledge verbs).
STATIVE_ON_PERFECT = {
    "ser",
    "estar",
    "haber",
    "tener",
    "conocer",
    "saber",
    "querer",
    "poder",
    "deber",
    "vivir",
    "habitar",
    "morar",
    "amar",
    "odiar",
    "temer",
    "creer",
    "confiar",
    "entender",
    "comprender",
}

# Extra OT-heavy irregulars not always needed for NT.
IRREGULAR_PRETERITE_EXTRA: dict[str, tuple[str, str, str, str, str, str]] = {
    "crear": ("creé", "creaste", "creó", "creamos", "creasteis", "crearon"),
    "matar": ("maté", "mataste", "mató", "matamos", "matasteis", "mataron"),
    "oir": ("oí", "oíste", "oyó", "oímos", "oísteis", "oyeron"),
    "oír": ("oí", "oíste", "oyó", "oímos", "oísteis", "oyeron"),
    "caer": ("caí", "caíste", "cayó", "caímos", "caísteis", "cayeron"),
    "traer": ("traje", "trajiste", "trajo", "trajimos", "trajisteis", "trajeron"),
    "andar": ("anduve", "anduviste", "anduvo", "anduvimos", "anduvisteis", "anduvieron"),
    "enviar": ("envié", "enviaste", "envió", "enviamos", "enviasteis", "enviaron"),
    "hablar": ("hablé", "hablaste", "habló", "hablamos", "hablasteis", "hablaron"),
    "llamar": ("llamé", "llamaste", "llamó", "llamamos", "llamasteis", "llamaron"),
    "llegar": ("llegué", "llegaste", "llegó", "llegamos", "llegasteis", "llegaron"),
    "buscar": ("busqué", "buscaste", "buscó", "buscamos", "buscasteis", "buscaron"),
    "sacar": ("saqué", "sacaste", "sacó", "sacamos", "sacasteis", "sacaron"),
    "tocar": ("toqué", "tocaste", "tocó", "tocamos", "tocasteis", "tocaron"),
    "acercar": ("acerqué", "acercaste", "acercó", "acercamos", "acercasteis", "acercaron"),
    "levantar": ("levanté", "levantaste", "levantó", "levantamos", "levantasteis", "levantaron"),
    "pastorear": ("pastoreé", "pastoreaste", "pastoreó", "pastoreamos", "pastoreasteis", "pastorearon"),
    "carecer": ("carecí", "careciste", "careció", "carecimos", "carecisteis", "carecieron"),
}

IRREGULAR_PRESENT_EXTRA: dict[str, tuple[str, str, str, str, str, str]] = {
    "oír": ("oigo", "oyes", "oye", "oímos", "oís", "oyen"),
    "oir": ("oigo", "oyes", "oye", "oímos", "oís", "oyen"),
    "conocer": ("conozco", "conoces", "conoce", "conocemos", "conocéis", "conocen"),
    "carecer": ("carezco", "careces", "carece", "carecemos", "carecéis", "carecen"),
    "creer": ("creo", "crees", "cree", "creemos", "creéis", "creen"),
    "construir": ("construyo", "construyes", "construye", "construimos", "construís", "construyen"),
    "huir": ("huyo", "huyes", "huye", "huimos", "huís", "huyen"),
    "destruir": ("destruyo", "destruyes", "destruye", "destruimos", "destruís", "destruyen"),
    "pedir": ("pido", "pides", "pide", "pedimos", "pedís", "piden"),
    "vestir": ("visto", "vistes", "viste", "vestimos", "vestís", "visten"),
    "seguir": ("sigo", "sigues", "sigue", "seguimos", "seguís", "siguen"),
    "servir": ("sirvo", "sirves", "sirve", "servimos", "servís", "sirven"),
    "repetir": ("repito", "repites", "repite", "repetimos", "repetís", "repiten"),
    "sentir": ("siento", "sientes", "siente", "sentimos", "sentís", "sienten"),
    "mentir": ("miento", "mientes", "miente", "mentimos", "mentís", "mienten"),
    "dormir": ("duermo", "duermes", "duerme", "dormimos", "dormís", "duermen"),
    "morir": ("muero", "mueres", "muere", "morimos", "morís", "mueren"),
    "preferir": ("prefiero", "prefieres", "prefiere", "preferimos", "preferís", "prefieren"),
    "advertir": ("advierto", "adviertes", "advierte", "advertimos", "advertís", "advierten"),
    "conseguir": ("consigo", "consigues", "consigue", "conseguimos", "conseguís", "consiguen"),
    "reír": ("río", "ríes", "ríe", "reímos", "reís", "ríen"),
    "sonreír": ("sonrío", "sonríes", "sonríe", "sonreímos", "sonreís", "sonríen"),
    "freír": ("frío", "fríes", "fríe", "freímos", "freís", "fríen"),
}

IRREGULAR_PRETERITE_EXTRA.update(
    {
        "pedir": ("pedí", "pediste", "pidió", "pedimos", "pedisteis", "pidieron"),
        "vestir": ("vestí", "vestiste", "vistió", "vestimos", "vestisteis", "vistieron"),
        "seguir": ("seguí", "seguiste", "siguió", "seguimos", "seguisteis", "siguieron"),
        "servir": ("serví", "serviste", "sirvió", "servimos", "servisteis", "sirvieron"),
        "sentir": ("sentí", "sentiste", "sintió", "sentimos", "sentisteis", "sintieron"),
        "dormir": ("dormí", "dormiste", "durmió", "dormimos", "dormisteis", "durmieron"),
        "morir": ("morí", "moriste", "murió", "morimos", "moristeis", "murieron"),
        "reír": ("reí", "reíste", "rio", "reímos", "reísteis", "rieron"),
        "preferir": ("preferí", "preferiste", "prefirió", "preferimos", "preferisteis", "prefirieron"),
    }
)

IRREGULAR_IMPERATIVE_EXTRA: dict[str, dict[tuple[str, str], str]] = {
    "decir": {("2", "S"): "di", ("2", "P"): "decid"},
    "hacer": {("2", "S"): "haz", ("2", "P"): "haced"},
    "ir": {("2", "S"): "ve", ("2", "P"): "id"},
    "ser": {("2", "S"): "sé", ("2", "P"): "sed"},
    "oír": {("2", "S"): "oye", ("2", "P"): "oíd"},
    "poner": {("2", "S"): "pon", ("2", "P"): "poned"},
    "salir": {("2", "S"): "sal", ("2", "P"): "salid"},
    "tener": {("2", "S"): "ten", ("2", "P"): "tened"},
    "venir": {("2", "S"): "ven", ("2", "P"): "venid"},
}

GERUND_IRREGULAR: dict[str, str] = {
    "decir": "diciendo",
    "hacer": "haciendo",
    "ir": "yendo",
    "poder": "pudiendo",
    "venir": "viniendo",
    "pedir": "pidiendo",
    "sentir": "sintiendo",
    "dormir": "durmiendo",
    "morir": "muriendo",
    "reír": "riendo",
    "oír": "oyendo",
    "creer": "creyendo",
    "leer": "leyendo",
    "traer": "trayendo",
    "caer": "cayendo",
}

PARTICIPLE_IRREGULAR: dict[str, str] = {
    "decir": "dicho",
    "hacer": "hecho",
    "escribir": "escrito",
    "ver": "visto",
    "poner": "puesto",
    "volver": "vuelto",
    "abrir": "abierto",
    "cubrir": "cubierto",
    "morir": "muerto",
    "romper": "roto",
    "resolver": "resuelto",
    "satisfacer": "satisfecho",
}


def parse_hbo_verb(morph: str) -> dict[str, str | None] | None:
    """Parse the first OSHB verb component in a morph string."""
    if not morph:
        return None
    for comp in morph.split("/"):
        c = comp[1:] if comp.startswith(("H", "A")) else comp
        if not c.startswith("V") or len(c) < 3:
            continue
        stem = c[1]
        aspect = c[2]
        tail = c[3:]
        person = gender = number = None
        m = re.search(r"(\d)([mfc])([spd])", tail)
        if m:
            person, gender, number = m.group(1), m.group(2), m.group(3)
        else:
            # participles often: rmsa / rfpa (no person digit)
            m2 = re.match(r"([mfc])([spd])([acd])?", tail)
            if m2:
                gender, number = m2.group(1), m2.group(2)
        return {
            "stem": stem,
            "aspect": aspect,
            "person": person,
            "gender": gender,
            "number": number,
            "raw": c,
        }
    return None


def is_finite_hbo_verb(morph: str) -> bool:
    p = parse_hbo_verb(morph)
    if not p:
        return False
    return p["aspect"] in {"p", "w", "q", "i", "j", "h", "v"} and p["person"] in {"1", "2", "3"}


def _split_gloss(es: str) -> tuple[list[str], str, list[str]]:
    """Return (prefixes, lexical_core, pronoun_tails_already_stripped_externally)."""
    parts = es.split("·")
    prefs: list[str] = []
    i = 0
    while i < len(parts) - 1 and parts[i] in FUNC_PREFIXES:
        prefs.append(parts[i])
        i += 1
    core = "·".join(parts[i:]) if i < len(parts) else ""
    return prefs, core, []


def _pn_from_hbo(person: str | None, number: str | None) -> tuple[str, str] | None:
    if not person or not number:
        return None
    n = "S" if number == "s" else "P" if number in {"p", "d"} else None
    if n is None:
        return None
    return person, n


def _lookup_preterite(inf: str, idx: int) -> str | None:
    if inf in IRREGULAR_PRETERITE_EXTRA:
        return IRREGULAR_PRETERITE_EXTRA[inf][idx]
    if inf in IRREGULAR_PRETERITE:
        return IRREGULAR_PRETERITE[inf][idx]
    cls = _stem_class_hbo(inf)
    if not cls:
        return None
    stem = _bare_stem(inf)
    if cls == "ar":
        endings = ("é", "aste", "ó", "amos", "asteis", "aron")
        if idx == 0 and inf.endswith(("car", "cár")):
            return stem[:-1] + "qué"
        if idx == 0 and inf.endswith(("gar", "gár")):
            return stem[:-1] + "gué"
        if idx == 0 and inf.endswith(("zar", "zár")):
            return stem[:-1] + "cé"
    else:
        endings = ("í", "iste", "ió", "imos", "isteis", "ieron")
    return stem + endings[idx]


def _lookup_present(inf: str, idx: int) -> str | None:
    if inf in IRREGULAR_PRESENT_EXTRA:
        return IRREGULAR_PRESENT_EXTRA[inf][idx]
    if inf in IRREGULAR_PRESENT:
        return IRREGULAR_PRESENT[inf][idx]
    cls = _stem_class_hbo(inf)
    if not cls:
        return None
    stem = _bare_stem(inf)
    endings = ("o", "as", "a", "amos", "áis", "an") if cls == "ar" else ("o", "es", "e", "emos", "éis", "en")
    if cls == "ir":
        endings = ("o", "es", "e", "imos", "ís", "en")
    return stem + endings[idx]


def _lookup_future(inf: str, idx: int) -> str | None:
    if inf in IRREGULAR_FUTURE:
        return IRREGULAR_FUTURE[inf][idx]
    if not _stem_class_hbo(inf):
        return None
    endings = ("é", "ás", "á", "emos", "éis", "án")
    # future uses full infinitive including accented ír
    return inf + endings[idx]


def _lookup_imperative(inf: str, person: str, number: str) -> str | None:
    irr = IRREGULAR_IMPERATIVE_EXTRA.get(inf, {}).get((person, number))
    if irr:
        return irr
    irr = IRREGULAR_IMPERATIVE.get(inf, {}).get((person, number))
    if irr:
        return irr
    cls = _stem_class_hbo(inf)
    if not cls:
        return None
    stem = _bare_stem(inf)
    if person == "2" and number == "S":
        return stem + ("a" if cls == "ar" else "e")
    if person == "3" and number == "S":
        return stem + ("e" if cls == "ar" else "a")
    if person == "2" and number == "P":
        return stem + ("ad" if cls == "ar" else "ed" if cls == "er" else "id")
    if person == "3" and number == "P":
        return stem + ("en" if cls == "ar" else "an")
    if person == "1" and number == "P":
        return stem + ("emos" if cls == "ar" else "amos")
    return None


def _gerund(inf: str) -> str | None:
    if inf in GERUND_IRREGULAR:
        return GERUND_IRREGULAR[inf]
    cls = _stem_class_hbo(inf)
    if not cls:
        return None
    stem = _bare_stem(inf)
    if cls == "ar":
        return stem + "ando"
    return stem + "iendo"


def _past_participle(inf: str) -> str | None:
    if inf in PARTICIPLE_IRREGULAR:
        return PARTICIPLE_IRREGULAR[inf]
    cls = _stem_class_hbo(inf)
    if not cls:
        return None
    stem = _bare_stem(inf)
    return stem + ("ado" if cls == "ar" else "ido")


def _agree_participle(pp: str, gender: str | None, number: str | None) -> str:
    """Agree a masculine-singular past participle in gender/number."""
    if not pp or not pp.endswith("o"):
        return pp
    stem = pp[:-1]
    fem = gender == "f"
    plural = number in {"p", "d"}
    if fem and plural:
        return stem + "as"
    if fem:
        return stem + "a"
    if plural:
        return stem + "os"
    return stem + "o"


def _active_participle_form(inf: str, number: str | None) -> str | None:
    """Hebrew active participle → Spanish present 3rd person by number."""
    idx = 2 if (number or "s") == "s" else 5  # él / ellos
    return _lookup_present(inf, idx)


def _reflexive_clitic(idx: int) -> str:
    return ("me", "te", "se", "nos", "os", "se")[idx]


def _known_infinitive(core: str) -> bool:
    return bool(
        _stem_class_hbo(core)
        or core in IRREGULAR_PRESENT
        or core in IRREGULAR_PRETERITE
        or core in IRREGULAR_PRESENT_EXTRA
        or core in IRREGULAR_PRETERITE_EXTRA
        or core in PARTICIPLE_IRREGULAR
    )


def conjugate_infinitive(inf: str, morph: str, *, force_subjunctive: bool = False) -> str | None:
    """Conjugate a Spanish infinitive (possibly reflexive *se) for OSHB morph."""
    parsed = parse_hbo_verb(morph)
    if not parsed:
        return None

    aspect = parsed["aspect"]
    reflexive = False
    core = inf.lower().strip()
    if core.endswith("se") and len(core) > 4 and _stem_class_hbo(core[:-2]):
        reflexive = True
        core = core[:-2]

    if not _known_infinitive(core) and aspect not in {"r", "s"}:
        return None

    if aspect in {"c", "a"}:
        return inf
    if aspect == "r":
        form = _active_participle_form(core, parsed.get("number"))
        if not form:
            return None
        idx = 2 if (parsed.get("number") or "s") == "s" else 5
        return f"{_reflexive_clitic(idx)}·{form}" if reflexive else form
    if aspect == "s":
        pp = _past_participle(core)
        if not pp:
            return None
        return _agree_participle(pp, parsed.get("gender"), parsed.get("number"))

    pn = _pn_from_hbo(parsed["person"], parsed["number"])
    if not pn:
        return None
    person, number = pn
    idx = _pn_index(person, number)
    if idx is None:
        return None

    form: str | None = None
    use_subj = force_subjunctive or aspect in {"j", "h"}
    if use_subj:
        if core in IRREGULAR_SUBJUNCTIVE:
            form = IRREGULAR_SUBJUNCTIVE[core][idx]
        else:
            cls = _stem_class_hbo(core)
            if not cls:
                return None
            stem = _bare_stem(core)
            if cls == "ar":
                endings = ("e", "es", "e", "emos", "éis", "en")
                if stem.endswith("c"):
                    stem = stem[:-1] + "qu"
                elif stem.endswith("g"):
                    stem = stem[:-1] + "gu"
                elif stem.endswith("z"):
                    stem = stem[:-1] + "c"
            else:
                endings = ("a", "as", "a", "amos", "áis", "an")
            form = stem + endings[idx]
    elif aspect in {"p", "w"}:
        if aspect == "p" and core in STATIVE_ON_PERFECT:
            form = _lookup_present(core, idx)
        else:
            form = _lookup_preterite(core, idx)
    elif aspect == "i":
        form = _lookup_present(core, idx)
    elif aspect == "q":
        form = _lookup_future(core, idx)
    elif aspect == "v":
        form = _lookup_imperative(core, person, number)
    else:
        return None

    if not form:
        return None

    if reflexive:
        return f"{_reflexive_clitic(idx)}·{form}"
    return form


def conjugate_gloss(es: str, morph: str, *, prev_es: str | None = None) -> str | None:
    """Conjugate the lexical verb inside a possibly prefixed BLE gloss."""
    if not es or es == "?" or not morph:
        return None
    parsed = parse_hbo_verb(morph)
    if not parsed:
        return None

    prefs, core, _ = _split_gloss(es)
    if not core:
        return None
    bits = core.split("·")
    head = bits[0]
    tail = bits[1:]

    # Already a causative / periphrasis (hizo·brotar, hacen·gustar): leave alone.
    if tail and head in {
        "hago", "haces", "hace", "hacemos", "hacéis", "hacen",
        "hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron",
        "haré", "harás", "hará", "haremos", "haréis", "harán",
        "hacer",
    }:
        return None

    # לא / אל + yiqtol → present subjunctive (commandments: no mates)
    force_subj = False
    if parsed["aspect"] == "i" and prev_es in {"no", "¡no"}:
        force_subj = True

    def _with_article_que(out_prefs: list[str], conjugated: str, rest: list[str]) -> str:
        prefs_out = list(out_prefs)
        if parsed["aspect"] == "r" and prefs_out and prefs_out[-1] in ARTICLES:
            prefs_out.append("que")
        return "·".join(prefs_out + [conjugated] + rest)

    conjugated = conjugate_infinitive(head, morph, force_subjunctive=force_subj)
    if conjugated is None and "·" not in core:
        conjugated = conjugate_infinitive(core, morph, force_subjunctive=force_subj)
        if conjugated is None:
            return None
        return _with_article_que(prefs, conjugated, [])

    if conjugated is None:
        return None
    return _with_article_que(prefs, conjugated, tail)
