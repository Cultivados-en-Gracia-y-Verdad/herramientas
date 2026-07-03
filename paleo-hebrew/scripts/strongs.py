"""Strong's number helpers (Hebrew H####, Greek G####)."""

from __future__ import annotations

import re

HBO_LEMMA_NUM = re.compile(r"^(\d+)")


def normalize_hebrew_strongs(value: str | int) -> str | None:
    text = str(value).strip().upper()
    if not text:
        return None
    if text.startswith("H"):
        digits = text[1:].lstrip("0") or "0"
        return f"H{int(digits)}"
    m = re.match(r"^H?0*(\d+)", text)
    if m:
        return f"H{int(m.group(1))}"
    m = re.match(r"^h\.0*(\d+)", text, re.I)
    if m:
        return f"H{int(m.group(1))}"
    return None


def strongs_from_mna_lemma(lemma: str) -> str | None:
    m = HBO_LEMMA_NUM.match(str(lemma).strip())
    if not m:
        return None
    return normalize_hebrew_strongs(m.group(1))


def parse_ahrc_strongs_field(raw: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r",\s*", raw.strip()):
        part = part.strip()
        if not part:
            continue
        norm = normalize_hebrew_strongs(part.replace("h.", "H"))
        if norm:
            out.append(norm)
    return out
