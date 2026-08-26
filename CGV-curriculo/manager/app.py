#!/usr/bin/env python3
"""Launch the graphical CGV Manager."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cgv_manager.web import main


if __name__ == "__main__":
    main()
