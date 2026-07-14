"""OSHB morphology display for BLE OT interlinear export."""

from __future__ import annotations


def display_morph(token: dict) -> str:
    """Return the OSHB morph code (e.g. HR/Ncfsa, HVqp3ms)."""
    morph = str(token.get("morph", "")).strip()
    if morph:
        return morph
    gram = token.get("gram") or {}
    raw = gram.get("raw")
    return str(raw).strip() if raw else ""


__all__ = ["display_morph"]
