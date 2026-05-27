#!/usr/bin/env python3
"""Run the ROOTS-GREEK rebuild pipeline for one book.

This script intentionally runs each stage as a separate process so failures stop
at the exact broken step and preserve each script's own terminal output.
"""

import argparse
import subprocess
import sys
from pathlib import Path


PIPELINE = [
    ("Step 3.5 clause spans", "roots_greek_step3_5_build_clause_spans.py"),
    ("Step 5 structure tree", "roots_greek_step5_build_structure_tree.py"),
    ("Step 6B rich Paso 6 render", "roots_greek_step6b_render_paso6_rich.py"),
]


def run_step(label: str, script: Path, book: str) -> None:
    print("\n" + "=" * 80)
    print(label)
    print("=" * 80)
    cmd = [sys.executable, str(script), book]
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ROOTS-GREEK rebuild pipeline for one book.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--scripts-dir", default="MNA/scripts")
    args = parser.parse_args()

    scripts_dir = Path(args.scripts_dir)

    for label, script_name in PIPELINE:
        script = scripts_dir / script_name
        if not script.exists():
            raise SystemExit(f"Missing pipeline script: {script}")
        run_step(label, script, args.book)

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Rendered output: MNA/roots-greek/output/{args.book}-paso6-rich.md")


if __name__ == "__main__":
    main()
