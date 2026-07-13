"""Strong's number helpers (Hebrew H####, Greek G####)."""

from __future__ import annotations

import re

HBO_LEMMA_NUM = re.compile(r"^(\d+)")
# MNA OT lemmas often carry morph prefixes: c/d/4428, b/2403 b, c/l/1141
HBO_LEMMA_ANY = re.compile(r"(?:^|/)(\d+)(?:\s*[a-zA-Z+]+)?$")
PREF_LETTERS = {"c", "d", "b", "l", "m", "k", "i", "s"}


def normalize_hebrew_strongs(value: str | int) -> str | None:
    text = str(value).strip().upper()
    if not text:
        return None
    if text.startswith("H"):
        m = re.match(r"^H0*(\d+)", text)
        if not m:
            return None
        return f"H{int(m.group(1))}"
    m = re.match(r"^H?0*(\d+)", text)
    if m:
        return f"H{int(m.group(1))}"
    m = re.match(r"^h\.0*(\d+)", text, re.I)
    if m:
        return f"H{int(m.group(1))}"
    return None


def bare_mna_lemma(lemma: str) -> str:
    """Strip MNA morph prefixes (c/d/b/l/m/k/…) leaving the Strong's key."""
    parts = str(lemma).strip().split("/")
    i = 0
    while i < len(parts) - 1 and parts[i] in PREF_LETTERS:
        i += 1
    return "/".join(parts[i:])


def strongs_from_mna_lemma(lemma: str) -> str | None:
    bare = bare_mna_lemma(lemma)
    m = HBO_LEMMA_NUM.match(bare)
    if m:
        return normalize_hebrew_strongs(m.group(1))
    m = HBO_LEMMA_ANY.search(str(lemma).strip())
    if m:
        return normalize_hebrew_strongs(m.group(1))
    return None


def parse_ahrc_strongs_field(raw: str) -> list[str]:
    out: list[str] = []
    text = str(raw or "")
    # Accept h.1234 / H1234 / 1234 even when the field also mentions Aramaic ids.
    for m in re.finditer(r"(?:h\.|H)?0*(\d{1,5})", text, flags=re.I):
        norm = normalize_hebrew_strongs(m.group(1))
        if norm and norm not in out:
            out.append(norm)
    return out
