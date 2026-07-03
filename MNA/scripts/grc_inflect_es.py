"""Spanish nominal inflection from lemma gloss + MorphGNT tag."""

from __future__ import annotations

import json
from pathlib import Path

PUNCT = ".,;:!?»«"

RULES_DIR = Path(__file__).resolve().parents[1] / "datasets" / "rules"

INVARIANT_LEMMAS: frozenset[str] = frozenset(
    {
        "θεός",
        "Χριστός",
        "Ἰησοῦς",
        "Ἰησοῦ",
        "πνεῦμα",
        "Ἰσραήλ",
        "Ἰερουσαλήμ",
        "οὐδείς",
        "μηδείς",
        "μηδέν",
        "οὐδέν",
        "δύο",
        "τρεῖς",
        "τρία",
        "τέσσαρες",
        "πέντε",
        "ἕξ",
        "ἑπτά",
        "ὀκτώ",
        "ἐννέα",
        "δέκα",
        "τις",
        "τίς",
        "πᾶς",
        "ὁ",
        "ἐγώ",
        "σύ",
        "αὐτός",
        "προφήτης",
        "ἀδελφός",
        "ἕκαστος",
        "εὐθύς",
    }
)

INVARIANT_GLOSS_PREFIXES = ("__FILL_",)

SPANISH_GENDER: dict[str, str] = {}

# infinitive -> (pres_act, past_masc_sg, past_fem_sg, past_masc_pl, past_fem_pl)
IRREGULAR_PARTICIPLES: dict[str, tuple[str, str, str, str, str]] = {
    "abrir": ("abriendo", "abierto", "abierta", "abiertos", "abiertas"),
    "cubrir": ("cubriendo", "cubierto", "cubierta", "cubiertos", "cubiertas"),
    "decir": ("diciendo", "dicho", "dicha", "dichos", "dichas"),
    "escribir": ("escribiendo", "escrito", "escrita", "escritos", "escritas"),
    "hacer": ("haciendo", "hecho", "hecha", "hechos", "hechas"),
    "morir": ("muriendo", "muerto", "muerta", "muertos", "muertas"),
    "poner": ("poniendo", "puesto", "puesta", "puestos", "puestas"),
    "romper": ("rompiendo", "roto", "rota", "rotos", "rotas"),
    "ver": ("viendo", "visto", "vista", "vistos", "vistas"),
    "volver": ("volviendo", "vuelto", "vuelta", "vueltos", "vueltas"),
    "freír": ("friendo", "frito", "frita", "fritos", "fritas"),
    "imprimir": ("imprimiendo", "impreso", "impresa", "impresos", "impresas"),
    "satisfacer": ("satisfaciendo", "satisfecho", "satisfecha", "satisfechos", "satisfechas"),
}


def load_spanish_gender(rules_dir: Path | None = None) -> dict[str, str]:
    global SPANISH_GENDER
    path = (rules_dir or RULES_DIR) / "grc_spanish_noun_gender.json"
    if not path.is_file():
        SPANISH_GENDER = {}
        return SPANISH_GENDER
    raw = json.loads(path.read_text(encoding="utf-8"))
    SPANISH_GENDER = {k: v for k, v in raw.items() if not str(k).startswith("_")}
    return SPANISH_GENDER


def split_punct(gloss: str) -> tuple[str, str]:
    core = gloss
    punct = ""
    while core and core[-1] in PUNCT:
        punct = core[-1] + punct
        core = core[:-1]
    return core, punct


def is_participle_morph(morph: str) -> bool:
    return morph.startswith("V") and len(morph) > 5 and morph[5] == "P"


def is_nominal_morph(morph: str) -> bool:
    if not morph or len(morph) < 9:
        return False
    pos = morph[0]
    if pos in ("N", "A"):
        return True
    return is_participle_morph(morph)


def morph_number(morph: str) -> str | None:
    if morph[0] in ("N", "A"):
        return morph[7] if len(morph) > 7 and morph[7] in ("S", "P") else None
    if is_participle_morph(morph):
        return morph[7] if len(morph) > 7 and morph[7] in ("S", "P") else None
    return None


def morph_gender(morph: str) -> str | None:
    if len(morph) <= 8:
        return None
    g = morph[8]
    if g in ("M", "F", "N"):
        return g
    return None


def greek_gender_norm(morph: str) -> str | None:
    g = morph_gender(morph)
    if not g:
        return None
    return "M" if g == "N" else g


def guess_gender_from_gloss(gloss: str) -> str | None:
    word = gloss.lower()
    if word.endswith(("ción", "sión", "dad", "tad", "ez", "umbre", "ión", "tis")):
        return "F"
    if word.endswith("a") and not word.endswith("ma"):
        return "F"
    if word.endswith("o"):
        return "M"
    return None


def effective_gender(lemma: str, base_gloss: str, morph: str) -> str | None:
    """Spanish inflection gender (M/F), not always Greek morph[8]."""
    if morph[0] == "A" or is_participle_morph(morph):
        return greek_gender_norm(morph)

    if lemma in SPANISH_GENDER:
        letter = SPANISH_GENDER[lemma].lower()
        return {"m": "M", "f": "F", "n": "N"}.get(letter)

    core, _ = split_punct(base_gloss)
    if not core or "·" in core:
        return greek_gender_norm(morph)

    if morph[0] == "N":
        guessed = guess_gender_from_gloss(core)
        if guessed:
            return guessed

    return greek_gender_norm(morph)


def pluralize(word: str) -> str:
    base = word
    if word.endswith(("á", "é", "í", "ó", "ú")):
        base = word[:-1] + {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}[word[-1]]
    if base.endswith(("a", "e", "i", "o", "u")):
        return base + "s"
    if word.endswith(("a", "e", "i", "o", "u")):
        return word + "s"
    if word.endswith("z"):
        return word[:-1] + "ces"
    return word + "es"


def inflect_word(word: str, gender: str, number: str) -> str | None:
    if not word or "·" in word:
        return None
    if word[0].isupper() and word not in ("Israel",):
        return None

    g = "M" if gender == "N" else gender

    if word.endswith("or"):
        stem = word[:-2]
        if number == "S":
            return stem + "ora" if g == "F" else word
        return stem + ("oras" if g == "F" else "ores")

    if word.endswith("o"):
        stem = word[:-1]
        if number == "S":
            return stem + ("a" if g == "F" else "o")
        return stem + ("as" if g == "F" else "os")

    if word.endswith("a"):
        if number == "S":
            return word
        if word.endswith("ía"):
            return word[:-1] + "as"
        return word[:-1] + "as"

    if word.endswith("e"):
        if number == "S":
            return word
        return pluralize(word)

    if number == "P":
        return pluralize(word)
    return word


def _participle_tense_voice(morph: str) -> tuple[str, str]:
    return morph[3] if len(morph) > 3 else "-", morph[4] if len(morph) > 4 else "-"


def _pick_irregular_past(inf: str, gender: str, number: str) -> str | None:
    forms = IRREGULAR_PARTICIPLES.get(inf)
    if not forms:
        return None
    _, m_s, f_s, m_p, f_p = forms
    g = morph_gender_to_spanish(gender)
    if number == "P":
        return f_p if g == "F" else m_p
    return f_s if g == "F" else m_s


def morph_gender_to_spanish(greek_g: str) -> str:
    return "F" if greek_g == "F" else "M"


def inflect_present_participle(inf: str) -> str | None:
    if inf in IRREGULAR_PARTICIPLES:
        return IRREGULAR_PARTICIPLES[inf][0]
    if inf.endswith("ar"):
        return inf[:-2] + "ando"
    if inf.endswith("er"):
        return inf[:-2] + "iendo"
    if inf.endswith("ir"):
        return inf[:-2] + "iendo"
    return None


def inflect_past_participle(inf: str, morph: str) -> str | None:
    irregular = _pick_irregular_past(inf, morph_gender(morph) or "M", morph_number(morph) or "S")
    if irregular:
        return irregular

    gender = morph_gender_to_spanish(morph_gender(morph) or "M")
    number = morph_number(morph) or "S"

    if inf.endswith("ar"):
        stem = inf[:-2]
        if number == "P":
            return stem + ("adas" if gender == "F" else "ados")
        return stem + ("ada" if gender == "F" else "ado")

    if inf.endswith("er") or inf.endswith("ir"):
        stem = inf[:-2]
        if number == "P":
            return stem + ("idas" if gender == "F" else "idos")
        return stem + ("ida" if gender == "F" else "ido")

    return None


def inflect_participle_gloss(gloss: str, morph: str) -> str | None:
    if not is_participle_morph(morph):
        return None
    if gloss.startswith(INVARIANT_GLOSS_PREFIXES) or gloss in ("", "?"):
        return None

    core, punct = split_punct(gloss)
    if not core or "·" in core:
        return None

    tense, voice = _participle_tense_voice(morph)
    use_past = voice == "P" or tense in ("A", "X")
    if use_past:
        part = inflect_past_participle(core, morph)
    else:
        part = inflect_present_participle(core)

    if not part or part == core:
        return None
    return part + punct


def inflect_gloss(gloss: str, morph: str, lemma: str = "") -> str | None:
    if not is_nominal_morph(morph):
        return None
    if gloss.startswith(INVARIANT_GLOSS_PREFIXES) or gloss in ("", "?"):
        return None

    if is_participle_morph(morph):
        return inflect_participle_gloss(gloss, morph)

    core, punct = split_punct(gloss)
    if not core or "·" in core:
        return None

    number = morph_number(morph)
    if number not in ("S", "P"):
        return None

    gender = effective_gender(lemma, gloss, morph)
    if not gender:
        return None

    greek_norm = greek_gender_norm(morph)
    if morph[0] == "N" and number == "S" and greek_norm and gender != greek_norm:
        return core + punct

    inflected = inflect_word(core, gender, number)
    if not inflected or inflected == core:
        return None
    return inflected + punct


def morph_case(morph: str) -> str | None:
    if len(morph) <= 6:
        return None
    if morph[0] in ("N", "A") or morph.startswith(("RA", "RR", "RD", "RI", "RP")):
        case = morph[6]
        if case in "NGDAV":
            return case
    return None


def has_genitive_article_before(prev_row: dict | None) -> bool:
    if not prev_row:
        return False
    if str(prev_row.get("lemma")) != "ὁ":
        return False
    morph = str(prev_row.get("morph", ""))
    if not morph.startswith("RA"):
        return False
    return morph_case(morph) == "G"


def prev_carries_de_mark(prev_row: dict | None) -> bool:
    if not prev_row:
        return False
    lemma = str(prev_row.get("lemma", ""))
    if lemma in {"ἀπό", "ἐκ", "ἐξ", "παρά", "ὑπό", "διά", "κατά", "μετά", "πρό", "ἀντί", "περί"}:
        return True
    es = str(prev_row.get("es", "")).strip().lower()
    return es == "de" or es.startswith("de·") or es in {"del", "de·la", "de·los", "de·las", "de·lo"} or es.endswith("·de")


def strip_genitive_mark(gloss: str) -> str:
    core, punct = split_punct(gloss)
    if core.lower().startswith("de·"):
        return core[3:] + punct
    if core.lower().startswith("de "):
        return core[3:] + punct
    return gloss


def apply_genitive_case(gloss: str, morph: str, prev_row: dict | None = None) -> str | None:
    """Add or remove de· for genitive N/A, depending on a preceding genitive article."""
    if morph_case(morph) != "G" or morph[0] not in ("N", "A"):
        return None
    if gloss in ("", "?") or gloss.startswith(INVARIANT_GLOSS_PREFIXES):
        return None

    core, punct = split_punct(gloss)
    if not core or "·" in core:
        return None

    has_de = core.lower().startswith("de·") or core.lower().startswith("de ")
    if has_genitive_article_before(prev_row) or prev_carries_de_mark(prev_row):
        if has_de:
            stripped = strip_genitive_mark(gloss)
            return stripped if stripped != gloss else None
        return None

    if has_de:
        return None
    return f"de·{core}" + punct


def inflect_genitive_mark(gloss: str, morph: str, prev_row: dict | None = None) -> str | None:
    return apply_genitive_case(gloss, morph, prev_row)


def inflect_from_lemma(lemma: str, base_gloss: str, morph: str) -> str | None:
    if lemma in INVARIANT_LEMMAS:
        return None
    return inflect_gloss(base_gloss, morph, lemma)


load_spanish_gender()
