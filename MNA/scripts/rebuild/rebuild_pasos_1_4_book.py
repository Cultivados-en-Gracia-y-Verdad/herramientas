#!/usr/bin/env python3
"""
MNA Rebuild — Pasos 1–4 Book

Purpose:
Produce Pasos 1–4 sequentially for a book.

Dependency order:
1. Paso 1 — Copiar texto
2. Paso 2 — Verbos finitos
3. Paso 3 — Cláusulas
4. Paso 4 — Conectores

Rule:
Each step must depend on the previous step's output.
The runner will not continue if an expected prior-step output is missing.

Important:
This file is a rebuild orchestrator. It requires the actual step scripts to exist.
It does not pretend Step 4 can be rebuilt if Step 1–3 outputs are missing.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Candidate scripts. The first existing script in each list is used.
# These names intentionally support current/evolving repo conventions.
STEP_SCRIPT_CANDIDATES = {
    1: [
        "scripts/roots/build_paso1_text.py",
        "scripts/stage4/build_paso1_text.py",
        "scripts/rebuild/build_paso1_text.py",
    ],
    2: [
        "scripts/roots/build_paso2_finite_verbs.py",
        "scripts/stage4/build_paso2_finite_verbs.py",
        "scripts/rebuild/build_paso2_finite_verbs.py",
    ],
    3: [
        "scripts/roots/build_paso3_clauses.py",
        "scripts/stage4/build_paso3_clauses.py",
        "scripts/rebuild/build_paso3_clauses.py",
    ],
    4: [
        "scripts/roots/build_paso4_connectors.py",
        "scripts/stage4/build_paso4_connectors.py",
        "scripts/rebuild/build_paso4_connectors.py",
    ],
}

# Expected step outputs. These are the canonical staged rebuild locations.
STEP_OUTPUTS = {
    1: "datasets/roots-pasos/{book}/paso1-text.jsonl",
    2: "datasets/roots-pasos/{book}/paso2-finite-verbs.jsonl",
    3: "datasets/roots-pasos/{book}/paso3-clauses.jsonl",
    4: "datasets/roots-pasos/{book}/paso4-connectors.jsonl",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_script(root: Path, step: int) -> Optional[Path]:
    for candidate in STEP_SCRIPT_CANDIDATES[step]:
        path = root / candidate
        if path.exists():
            return path
    return None


def step_output(root: Path, book: str, step: int) -> Path:
    return root / STEP_OUTPUTS[step].format(book=book)


def run_step(root: Path, book: str, step: int, dry_run: bool) -> int:
    script = resolve_script(root, step)
    output = step_output(root, book, step)

    print()
    print("=" * 72)
    print(f"PASO {step}")
    print("=" * 72)

    if script is None:
        print(f"MISSING SCRIPT for Paso {step}")
        for candidate in STEP_SCRIPT_CANDIDATES[step]:
            print(f"  - {candidate}")
        return 2

    # Enforce dependency on previous step output.
    if step > 1:
        prior_output = step_output(root, book, step - 1)
        if not prior_output.exists():
            print(f"MISSING REQUIRED PRIOR OUTPUT for Paso {step}: {prior_output}")
            print(f"Run/fix Paso {step - 1} first.")
            return 3

    cmd = [sys.executable, str(script.relative_to(root)), book]
    print("$ " + " ".join(cmd))

    if not dry_run:
        code = subprocess.run(cmd, cwd=str(root)).returncode
        if code != 0:
            print(f"PASO {step} FAILED")
            return code

    if not dry_run and not output.exists():
        print(f"PASO {step} did not produce expected output: {output}")
        return 4

    print(f"EXPECTED OUTPUT: {output}")
    print(f"PASO {step}: PASS")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sequentially rebuild Pasos 1–4 for a book.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--from-step", type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument("--to-step", type=int, default=4, choices=[1, 2, 3, 4])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.from_step > args.to_step:
        print("from-step cannot be greater than to-step", file=sys.stderr)
        return 1

    root = mna_root_from_script()
    book = args.book.strip().lower()

    print("MNA Rebuild — Pasos 1–4 Book")
    print(f"BOOK: {book}")
    print(f"ROOT: {root}")
    print(f"RANGE: Paso {args.from_step} → Paso {args.to_step}")

    for step in range(args.from_step, args.to_step + 1):
        code = run_step(root, book, step, args.dry_run)
        if code != 0:
            print()
            print("REBUILD STOPPED")
            print(f"FAILED AT PASO {step}")
            print("STATUS: FAIL")
            return code

    print()
    print("MNA Rebuild — Pasos 1–4 Complete")
    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
