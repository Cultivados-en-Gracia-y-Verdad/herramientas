"""RMAC display helpers for BLE interlinear export."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "MNA" / "scripts"))

from morphgnt_to_rmac import display_morph, morphgnt_to_rmac  # noqa: E402

__all__ = ["display_morph", "morphgnt_to_rmac"]
