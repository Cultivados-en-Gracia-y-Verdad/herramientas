#!/usr/bin/env python3

import subprocess
from pathlib import Path

BASE = Path(".")
ALIGN_DIR = BASE / "data" / "alignments"
G_DIR = BASE / "data" / "g-tokens"
S_DIR = BASE / "data" / "s-tokens"
VALIDATOR = BASE / "scripts" / "validate_alignment.py"

failures = []

for alignment_file in sorted(ALIGN_DIR.glob("*.tsv")):
    if alignment_file.name.endswith(".original.tsv"):
        continue
    stem = alignment_file.stem

    g_file = G_DIR / f"{stem}.txt"
    s_file = S_DIR / f"{stem}.txt"

    if not g_file.exists():
        failures.append((stem, f"Missing Greek token file: {g_file}"))
        continue

    if not s_file.exists():
        failures.append((stem, f"Missing Spanish token file: {s_file}"))
        continue

    result = subprocess.run(
        [
            "python3",
            str(VALIDATOR),
            str(g_file),
            str(s_file),
            str(alignment_file),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"PASS {stem}")
    else:
        print(f"FAIL {stem}")
        failures.append((stem, result.stdout.strip()))

print()

if failures:
    print("SUMMARY: FAIL")
    print()
    for stem, message in failures:
        print(f"--- {stem} ---")
        print(message)
        print()
    raise SystemExit(1)

print("SUMMARY: ALL PASS")