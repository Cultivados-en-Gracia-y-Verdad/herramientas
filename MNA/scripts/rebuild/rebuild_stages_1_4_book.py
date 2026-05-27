#!/usr/bin/env python3
"""
MNA Rebuild — Stages 1–4 Book

Purpose:
Run the actual implemented MNA rebuild chain for one book.

This script reproduces what already works for 1 Corinthians by running the existing
stage scripts in dependency order.

Stage 1 — Finite verbs
    python3 scripts/stage1/build_finite_verbs.py <book>
    python3 scripts/stage1/update_verification_ledger.py <book> --date <date>

Stage 2 — Predicate anchors
    python3 scripts/stage2/build_predicate_anchors.py <book>
    python3 scripts/stage2/validate_predicate_anchors.py <book>

Stage 3 — Anchor skeleton
    python3 scripts/stage3/build_anchor_skeleton.py <book>
    python3 scripts/stage3/validate_anchor_skeleton.py <book>

Stage 4 — Reviewed trunk layer
    python3 scripts/stage4/rebuild_stage4_book.py <book>

Usage:
    python3 scripts/rebuild/rebuild_stages_1_4_book.py 1corintios --date 2026-05-15

Dry run:
    python3 scripts/rebuild/rebuild_stages_1_4_book.py 1corintios --date 2026-05-15 --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional


STAGES = {
    1: {
        "title": "STAGE 1 — FINITE VERBS",
        "commands": [
            ["scripts/stage1/build_finite_verbs.py", "{book}"],
            ["scripts/stage1/update_verification_ledger.py", "{book}", "--date", "{date}"],
        ],
    },
    2: {
        "title": "STAGE 2 — PREDICATE ANCHORS",
        "commands": [
            ["scripts/stage2/build_predicate_anchors.py", "{book}"],
            ["scripts/stage2/validate_predicate_anchors.py", "{book}"],
        ],
    },
    3: {
        "title": "STAGE 3 — ANCHOR SKELETON",
        "commands": [
            ["scripts/stage3/build_anchor_skeleton.py", "{book}"],
            ["scripts/stage3/validate_anchor_skeleton.py", "{book}"],
        ],
    },
    4: {
        "title": "STAGE 4 — REVIEWED TRUNK LAYER",
        "commands": [
            ["scripts/stage4/rebuild_stage4_book.py", "{book}"],
        ],
    },
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def format_command(command: list[str], book: str, run_date: str) -> list[str]:
    return [part.format(book=book, date=run_date) for part in command]


def ensure_script_exists(root: Path, script_path: str) -> None:
    path = root / script_path
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")


def run_command(root: Path, cmd_parts: list[str], dry_run: bool) -> int:
    script = cmd_parts[0]
    ensure_script_exists(root, script)
    cmd = [sys.executable] + cmd_parts
    print("$ " + " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=str(root)).returncode


def run_stage(root: Path, book: str, stage_num: int, run_date: str, dry_run: bool) -> int:
    stage = STAGES[stage_num]
    print()
    print("=" * 72)
    print(stage["title"])
    print("=" * 72)

    for command_template in stage["commands"]:
        cmd_parts = format_command(command_template, book, run_date)
        code = run_command(root, cmd_parts, dry_run)
        if code != 0:
            print(f"{stage['title']} FAILED")
            return code

    print(f"{stage['title']}: PASS")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run MNA stages 1–4 for a book in order.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--date", default=date.today().isoformat(), help="Verification ledger date for Stage 1")
    parser.add_argument("--from-stage", type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument("--to-stage", type=int, default=4, choices=[1, 2, 3, 4])
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    args = parser.parse_args(argv)

    if args.from_stage > args.to_stage:
        print("from-stage cannot be greater than to-stage", file=sys.stderr)
        return 1

    root = mna_root_from_script()
    book = args.book.strip().lower()

    print("MNA Rebuild — Stages 1–4 Book")
    print(f"BOOK: {book}")
    print(f"ROOT: {root}")
    print(f"RANGE: Stage {args.from_stage} → Stage {args.to_stage}")
    print(f"DATE: {args.date}")

    for stage_num in range(args.from_stage, args.to_stage + 1):
        code = run_stage(root, book, stage_num, args.date, args.dry_run)
        if code != 0:
            print()
            print("REBUILD STOPPED")
            print(f"FAILED AT STAGE {stage_num}")
            print("STATUS: FAIL")
            return code

    print()
    print("MNA Rebuild — Stages 1–4 Complete")
    print(f"BOOK: {book}")
    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
