"""MorphGNT tag parsing for observation summaries."""

from __future__ import annotations

TENSE_LABELS = {
    "P": "present",
    "I": "imperfect",
    "F": "future",
    "A": "aorist",
    "X": "perfect",
    "Y": "pluperfect",
    "R": "perfect",
    "L": "pluperfect",
}

MOOD_LABELS = {
    "I": "indicative",
    "S": "subjunctive",
    "D": "imperative",
    "O": "optative",
    "N": "infinitive",
    "P": "participle",
    "M": "imperative",
}

VOICE_LABELS = {
    "A": "active",
    "M": "middle",
    "P": "passive",
    "E": "middle",
    "D": "middle",
    "O": "passive",
    "N": "middle",
}

CASE_LABELS = {
    "N": "nominative",
    "G": "genitive",
    "D": "dative",
    "A": "accusative",
    "V": "vocative",
}


def is_verb_morph(morph: str) -> bool:
    return bool(morph) and morph.startswith("V")


def parse_verb_morph(morph: str) -> dict[str, str | None]:
    if not is_verb_morph(morph) or len(morph) < 6:
        return {}
    return {
        "person": morph[2] if morph[2] in "123" else None,
        "tense": morph[3] if morph[3] != "-" else None,
        "voice": morph[4] if morph[4] != "-" else None,
        "mood": morph[5] if morph[5] != "-" else None,
        "number": morph[7] if len(morph) > 7 and morph[7] in "SP" else None,
    }


def verb_morphology_summary(morphs: list[str]) -> dict:
    moods: dict[str, int] = {}
    tenses: dict[str, int] = {}
    voices: dict[str, int] = {}
    for morph in morphs:
        parsed = parse_verb_morph(morph)
        mood = MOOD_LABELS.get(parsed.get("mood") or "", parsed.get("mood") or "unknown")
        tense = TENSE_LABELS.get(parsed.get("tense") or "", parsed.get("tense") or "unknown")
        voice = VOICE_LABELS.get(parsed.get("voice") or "", parsed.get("voice") or "unknown")
        moods[mood] = moods.get(mood, 0) + 1
        tenses[tense] = tenses.get(tense, 0) + 1
        voices[voice] = voices.get(voice, 0) + 1
    return {
        "part_of_speech": "verb",
        "moods": moods,
        "tenses": tenses,
        "voices": voices,
    }


def is_imperative(morph: str) -> bool:
    parsed = parse_verb_morph(morph)
    return parsed.get("mood") in ("D", "M")


def is_subjunctive(morph: str) -> bool:
    return parse_verb_morph(morph).get("mood") == "S"


def display_morph_rmac(morph: str) -> str:
    """Compact morph label for references (RMAC-style when possible)."""
    if not is_verb_morph(morph):
        return morph
    p = parse_verb_morph(morph)
    parts = ["V"]
    if p.get("tense"):
        parts.append(p["tense"])
    if p.get("voice"):
        parts.append(p["voice"])
    if p.get("mood"):
        parts.append(p["mood"])
    if p.get("person") and p.get("number"):
        parts.append(f"{p['person']}{p['number']}")
    return "-".join(parts) if len(parts) > 1 else morph
