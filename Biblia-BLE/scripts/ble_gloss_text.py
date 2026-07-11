"""Mid-dot gloss → published BLE text with • on inserted function words."""

from __future__ import annotations

import re
import unicodedata

MARK_WITH_BULLET = frozenset({
    "de", "a", "en", "por", "para", "con", "sin", "que", "medio", "causa",
})
SPLIT_COMPOUNDS = {"del": ("de",), "al": ("a", "el")}


def _split_parts(es: str) -> list[str]:
    parts: list[str] = []
    for raw in es.split("·"):
        part = raw.strip()
        if not part:
            continue
        parts.extend(SPLIT_COMPOUNDS.get(part.lower(), (part,)))
    return parts


def gloss_to_text(es: str) -> str:
    core = es.strip()
    if not core or core == "?":
        return ""
    if "·" not in core:
        return core
    out: list[str] = []
    for part in _split_parts(core):
        if part.lower() in MARK_WITH_BULLET:
            if out:
                out.append(" ")
            out.append(f"{part}•")
        else:
            if out and not out[-1].endswith("•"):
                out.append(" ")
            out.append(part)
    return "".join(out)


def normalize_greek_surface(surface: str) -> str:
    text = unicodedata.normalize("NFC", surface or "").strip()
    for ch in "⸀⸂⸃":
        text = text.replace(ch, "")
    return text.strip(".,;:!?·")


def is_dei_surface(surface: str) -> bool:
    return normalize_greek_surface(surface).casefold() == "δεῖ".casefold()


GLOSS_FIXES = [
    (re.compile(r"\bapartarses\b", re.I), "apartarse"),
    (re.compile(r"\bapropiarses\b", re.I), "apropiarse"),
    (re.compile(r"\bdiscusiónes\b", re.I), "discusiones"),
    (re.compile(r"\bvarónes\b", re.I), "varones"),
]


def fix_gloss_text(es: str) -> str:
    for pattern, replacement in GLOSS_FIXES:
        es = pattern.sub(replacement, es)
    return es
