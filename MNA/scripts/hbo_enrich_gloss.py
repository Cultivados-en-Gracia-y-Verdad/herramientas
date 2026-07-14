#!/usr/bin/env python3
"""Enrich OT Spanish glosses from OSHB morphology (suffixes, noun number).

Pronominal suffixes (Sp3ms, Sp1cs, …) are present in morph but were not reflected
in `es`. This module appends Spanish clitics in the same style as NT BLE
(a·él, de·mí, …).
"""

from __future__ import annotations

import re

from hbo_conj_es import conjugate_gloss

# OSHB: Sp + person + gender + number
SUFFIX_ES: dict[str, str] = {
    "1cs": "mí",
    "1ms": "mí",
    "1fs": "mí",
    "1cp": "nosotros",
    "2ms": "ti",
    "2fs": "ti",
    "2cs": "ti",
    "2mp": "vosotros",
    "2fp": "vosotras",
    "2cp": "vosotros",
    "3ms": "él",
    "3fs": "ella",
    "3cs": "él",
    "3mp": "ellos",
    "3fp": "ellas",
    "3cp": "ellos",
}

PRONOUN_TAILS = set(SUFFIX_ES.values())

# Safe pluralizations for high-frequency common nouns (not proper names).
PLURAL_ES: dict[str, str] = {
    "hijo": "hijos",
    "hija": "hijas",
    "hermano": "hermanos",
    "hermana": "hermanas",
    "hombre": "hombres",
    "mujer": "mujeres",
    "rey": "reyes",
    "siervo": "siervos",
    "profeta": "profetas",
    "sacerdote": "sacerdotes",
    "ciudad": "ciudades",
    "pueblo": "pueblos",
    "nación": "naciones",
    "palabra": "palabras",
    "día": "días",
    "año": "años",
    "mano": "manos",
    "ojo": "ojos",
    "oído": "oídos",
    "pie": "pies",
    "agua": "aguas",
    "cielo": "cielos",
    "estrella": "estrellas",
    "montaña": "montañas",
    "monte": "montes",
    "valle": "valles",
    "casa": "casas",
    "puerta": "puertas",
    "muro": "muros",
    "altar": "altares",
    "ofrenda": "ofrendas",
    "mandamiento": "mandamientos",
    "estatuto": "estatutos",
    "juicio": "juicios",
    "enemigo": "enemigos",
    "amigo": "amigos",
    "anciano": "ancianos",
    "juez": "jueces",
    "príncipe": "príncipes",
    "caballo": "caballos",
    "carro": "carros",
    "asno": "asnos",
    "buey": "bueyes",
    "oveja": "ovejas",
    "cordero": "corderos",
}

SP_RE = re.compile(r"Sp([123])([mfc])([spd])")
# Noun plural: N…p… in a morph component (not proper-name-only Np alone as whole token)
NOUN_PLURAL_RE = re.compile(r"(?:^|/)H?N(?![pg])[^/]*p", re.I)


def parse_pronominal_suffix(morph: str) -> str | None:
    m = SP_RE.search(morph or "")
    if not m:
        return None
    key = f"{m.group(1)}{m.group(2)}{m.group(3)}"
    if key in SUFFIX_ES:
        return SUFFIX_ES[key]
    # fall back: ignore unexpected gender
    return SUFFIX_ES.get(f"{m.group(1)}c{m.group(3)}")


def strip_pronoun_tail(es: str) -> str:
    parts = es.split("·")
    while parts and parts[-1] in PRONOUN_TAILS:
        parts.pop()
    return "·".join(parts) if parts else es


def noun_wants_plural(morph: str) -> bool:
    """True for common-noun plurals; false for proper names (…/Np or HNp)."""
    morph = morph or ""
    # Pure proper name: HNp or …/Np without other noun content
    comps = [c[1:] if c.startswith("H") else c for c in morph.split("/")]
    has_common_plural = False
    for c in comps:
        if not c.startswith("N"):
            continue
        if c == "Np" or c.startswith("Np"):
            continue  # proper name
        if "p" in c[1:]:  # number p somewhere in noun features
            has_common_plural = True
    return has_common_plural


def apply_plural(es: str, morph: str) -> str:
    if not noun_wants_plural(morph):
        return es
    parts = es.split("·")
    if not parts:
        return es
    # Pluralize the lexical head (last non-function segment if prefixed)
    # e.g. y·hijo → y·hijos ; el·hijo → el·hijos (article agreement later)
    idx = len(parts) - 1
    head = parts[idx]
    if head in PLURAL_ES:
        parts[idx] = PLURAL_ES[head]
        # light article agreement
        if idx > 0 and parts[idx - 1] == "el":
            parts[idx - 1] = "los"
        elif idx > 0 and parts[idx - 1] == "la":
            parts[idx - 1] = "las"
        return "·".join(parts)
    return es


def enrich_gloss(es: str, morph: str, *, lemma: str = "", prev_es: str | None = None) -> str:
    """Return lexicon gloss enriched with conjugation, plural, and suffix."""
    if not es or es == "?":
        return es
    base = strip_pronoun_tail(es)
    base = apply_plural(base, morph)

    conjugated = conjugate_gloss(base, morph, prev_es=prev_es)
    if conjugated:
        base = conjugated

    # אדות (H182): with suffix, prefer pronoun-only so "sobre mí" reads cleanly
    bare = lemma.split("/")[-1] if lemma else ""
    bare_num = re.match(r"^(\d+)", bare)
    pron = parse_pronominal_suffix(morph)
    if bare_num and bare_num.group(1) == "182" and pron:
        return pron

    if pron and (not base.endswith(f"·{pron}")):
        return f"{base}·{pron}" if base else pron
    return base
