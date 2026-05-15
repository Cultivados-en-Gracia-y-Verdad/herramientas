#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


ALIGNMENT_DIR = Path("data/alignments/filemon")
JSON_DIR = Path("data/interlinear/filemon/1")

BUILD_SCRIPT = Path("scripts/build_interlinear_json.py")
ENRICH_SCRIPT = Path("scripts/enrich_interlinear_json.py")


def fail(message: str) -> None:
    print("FAIL")
    print()
    print(f"- {message}")
    sys.exit(1)


def run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        fail("command failed: " + " ".join(command))

    if result.stdout.strip():
        print(result.stdout.strip())


def verse_number(path: Path) -> int:
    # filemon-1-12.tsv -> 12
    stem = path.stem
    return int(stem.split("-")[-1])


def main() -> None:
    if not ALIGNMENT_DIR.exists():
        fail(f"alignment directory not found: {ALIGNMENT_DIR}")

    if not BUILD_SCRIPT.exists():
        fail(f"build script not found: {BUILD_SCRIPT}")

    if not ENRICH_SCRIPT.exists():
        fail(f"enrich script not found: {ENRICH_SCRIPT}")

    tsv_files = sorted(
        [
            p for p in ALIGNMENT_DIR.glob("filemon-1-*.tsv")
            if not p.name.endswith(".original.tsv")
        ],
        key=verse_number
    )

    if not tsv_files:
        fail(f"no TSV files found in {ALIGNMENT_DIR}")

    print(f"Found {len(tsv_files)} Filemón TSV files.")
    print()

    for tsv_path in tsv_files:
        verse = verse_number(tsv_path)
        json_path = JSON_DIR / f"{verse}.json"

        print(f"=== Filemón 1:{verse} ===")

        run_command([
            "python3",
            str(BUILD_SCRIPT),
            str(tsv_path)
        ])

        run_command([
            "python3",
            str(ENRICH_SCRIPT),
            str(json_path)
        ])

        print()

    print("PASS all Filemón JSON files built and enriched.")


if __name__ == "__main__":
    main()