"""Convert MorphGNT morphology tags to Robinson RMAC codes for display."""

from __future__ import annotations

TENSE_RMAC = {"P": "P", "I": "I", "F": "F", "A": "A", "R": "X", "L": "Y", "X": "X"}
VOICE_RMAC = {
    "A": "A",
    "M": "M",
    "P": "P",
    "E": "E",
    "D": "M",
    "O": "P",
    "N": "E",
}
MOOD_RMAC = {
    "I": "I",
    "S": "S",
    "O": "O",
    "D": "M",
    "M": "M",
    "N": "N",
    "P": "P",
}
NUMBER_RMAC = {"S": "S", "P": "P"}

POS_PREFIX = {
    "N": "N",
    "A": "A",
    "C": "CONJ",
    "D": "ADV",
    "I": "INJ",
    "P": "PREP",
    "X": "PRT",
    "RA": "T",
    "RD": "D",
    "RI": "I",
    "RR": "R",
    "RP": "P",
}

PRONOUN_PERSON = {
    "ἐγώ": "1",
    "σύ": "2",
    "ἡμεῖς": "1",
    "ὑμεῖς": "2",
    "αὐτός": "3",
    "ἑαυτοῦ": "3",
    "ἑαυτός": "3",
}


def _ch(morph: str, index: int) -> str:
    return morph[index] if len(morph) > index else "-"


def _declension_suffix(morph: str, *, allow_no_gender: bool = False) -> str:
    case = _ch(morph, 6)
    number = _ch(morph, 7)
    gender = _ch(morph, 8)
    if case in "-?" or number in "-?":
        return ""
    if gender in "-?":
        if allow_no_gender:
            return f"{case}{number}"
        return ""
    return f"{case}{number}{gender}"


def _degree_suffix(morph: str) -> str:
    degree = _ch(morph, 9)
    if degree == "C":
        return "-C"
    if degree == "S":
        return "-S"
    return ""


def _verb_rmac(morph: str) -> str:
    code = morph[2:] if morph.startswith("V-") else morph
    if len(code) < 4:
        return morph
    person = code[0]
    tense = TENSE_RMAC.get(code[1], code[1])
    voice = VOICE_RMAC.get(code[2], code[2])
    mood = MOOD_RMAC.get(code[3], code[3])
    number = NUMBER_RMAC.get(code[5], code[5]) if len(code) > 5 else ""
    if person in {"1", "2", "3"} and number:
        return f"V-{tense}{voice}{mood}-{person}{number}"
    return f"V-{tense}{voice}{mood}"


def _declined_rmac(prefix: str, morph: str, lemma: str = "") -> str:
    if prefix == "P" and lemma in PRONOUN_PERSON:
        suffix = _declension_suffix(morph, allow_no_gender=True)
        if suffix:
            return f"P-{PRONOUN_PERSON[lemma]}{suffix}{_degree_suffix(morph)}"
    suffix = _declension_suffix(morph)
    if not suffix:
        return prefix
    return f"{prefix}-{suffix}{_degree_suffix(morph)}"


def morphgnt_to_rmac(morph: str, lemma: str = "") -> str:
    """Return Robinson RMAC code for a MorphGNT morphology string."""
    if not morph or morph == "-":
        return morph

    if morph.startswith("V-"):
        return _verb_rmac(morph)

    if morph.startswith(("RA", "RD", "RI", "RR", "RP")):
        prefix = POS_PREFIX[morph[:2]]
        return _declined_rmac(prefix, morph, lemma)

    pos = morph[0]
    if pos in ("N", "A"):
        return _declined_rmac(POS_PREFIX[pos], morph, lemma)

    if pos in POS_PREFIX:
        return POS_PREFIX[pos]

    return morph


def display_morph(token: dict) -> str:
    """RMAC for interlinear display; prefers stored rmac field when present."""
    if token.get("rmac"):
        return str(token["rmac"])
    return morphgnt_to_rmac(str(token.get("morph", "")), str(token.get("lemma", "")))
