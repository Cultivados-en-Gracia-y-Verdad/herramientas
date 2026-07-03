"""Hebrew text helpers for Paleo conversion."""

from __future__ import annotations

import re
import unicodedata

# Hebrew points, cantillation, and related marks (optional strip).
NIQQUD_RE = re.compile(
    r"[\u0591-\u05C7\u05F3\u05F4]"
)


def strip_niqqud(text: str) -> str:
    return NIQQUD_RE.sub("", text)


def normalize_hebrew(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")
