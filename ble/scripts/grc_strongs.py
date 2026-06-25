"""Strong's number display for BLE interlinear export."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parents[2] / "MNA" / "datasets" / "rules"


def _norm_lemma(lemma: str) -> str:
    return re.sub(r"\([^)]*\)", "", lemma)


def _format_strongs(value: str | int) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if text.upper().startswith("G"):
        return f"G{int(text[1:])}"
    return f"G{int(text)}"


@lru_cache(maxsize=1)
def _lemma_strongs() -> dict[str, str]:
    path = RULES_DIR / "grc_lemma_strongs.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


@lru_cache(maxsize=1)
def _supplement() -> dict[str, str]:
    path = RULES_DIR / "grc_lemma_strongs_supplement.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def strongs_for_lemma(lemma: str) -> str:
    if not lemma:
        return ""
    mapping = _lemma_strongs()
    supplement = _supplement()
    for key in (lemma, _norm_lemma(lemma)):
        if key in supplement:
            return _format_strongs(supplement[key])
        if key in mapping:
            return _format_strongs(mapping[key])
    return ""


def display_strongs(token: dict) -> str:
    if token.get("strongs") not in (None, ""):
        return _format_strongs(token["strongs"])
    return strongs_for_lemma(str(token.get("lemma", "")))
