"""Hebrew Strong's number display for BLE OT interlinear export."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paleo-hebrew" / "scripts"))

from strongs import bare_mna_lemma, strongs_from_mna_lemma  # noqa: E402

PREF_LETTERS = {"c", "d", "b", "l", "m", "k", "i", "s"}


def display_lemma(token: dict) -> str:
    """Show the MNA lemma key as stored (may include prefixes: b/7225)."""
    return str(token.get("lemma", "")).strip()


def display_strongs(token: dict) -> str:
    """Return H#### from the MNA OT lemma field."""
    lemma = str(token.get("lemma", "")).strip()
    strongs = strongs_from_mna_lemma(lemma)
    if strongs:
        return strongs
    # Fallback: any leading digits in bare key
    bare = bare_mna_lemma(lemma)
    m = re.match(r"^(\d+)", bare)
    if m:
        return f"H{int(m.group(1))}"
    return ""


__all__ = ["bare_mna_lemma", "display_lemma", "display_strongs"]
