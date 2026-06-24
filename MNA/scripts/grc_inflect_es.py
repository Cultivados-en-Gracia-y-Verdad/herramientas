"""Spanish nominal inflection from lemma gloss + MorphGNT tag."""

from __future__ import annotations

PUNCT = ".,;:!?»«"

INVARIANT_LEMMAS: frozenset[str] = frozenset(
    {
        "θεός",
        "Χριστός",
        "Ἰησοῦς",
        "Ἰησοῦ",
        "πνεῦμα",
        "Ἰουδαῖος",
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
    }
)

INVARIANT_GLOSS_PREFIXES = ("__FILL_",)


def split_punct(gloss: str) -> tuple[str, str]:
    core = gloss
    punct = ""
    while core and core[-1] in PUNCT:
        punct = core[-1] + punct
        core = core[:-1]
    return core, punct


def is_nominal_morph(morph: str) -> bool:
    if not morph or len(morph) < 9:
        return False
    pos = morph[0]
    if pos in ("N", "A"):
        return True
    return pos == "V" and len(morph) > 5 and morph[5] == "P"


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

    if word.endswith("e") or word.endswith("l") or word.endswith("z"):
        if number == "S":
            return word
        if word.endswith(("s", "x", "z")):
            return word + "es"
        return word + "s"

    if word.endswith("a"):
        if number == "S":
            return word
        if word.endswith("ía"):
            return word[:-1] + "as"
        return word[:-1] + "as"

    if number == "P":
        return word + ("es" if word[-1] not in "aeiouáéíóú" else "s")
    return word


def inflect_gloss(gloss: str, morph: str) -> str | None:
    if not is_nominal_morph(morph):
        return None
    if gloss.startswith(INVARIANT_GLOSS_PREFIXES) or gloss in ("", "?"):
        return None

    core, punct = split_punct(gloss)
    if not core or "·" in core:
        return None

    gender = morph[8]
    number = morph[7]
    if gender not in ("M", "F", "N") or number not in ("S", "P"):
        return None

    inflected = inflect_word(core, gender, number)
    if not inflected or inflected == core:
        return None
    return inflected + punct


def inflect_from_lemma(lemma: str, base_gloss: str, morph: str) -> str | None:
    if lemma in INVARIANT_LEMMAS:
        return None
    return inflect_gloss(base_gloss, morph)
