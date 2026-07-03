"""Load square Hebrew ↔ Paleo letter mappings."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def load_square_to_paleo() -> dict[str, str]:
    payload = json.loads((DATA_DIR / "letter-map.json").read_text(encoding="utf-8"))
    return dict(payload["square_to_paleo"])


@lru_cache(maxsize=1)
def load_paleo_to_square() -> dict[str, str]:
    square_to_paleo = load_square_to_paleo()
    paleo_to_square: dict[str, str] = {}
    for square, paleo in square_to_paleo.items():
        paleo_to_square.setdefault(paleo, square)
    return paleo_to_square
