#!/usr/bin/env python3
"""
MNA Stage 4 — Apply All Review Batches

PURPOSE
- Apply all existing datasets/review-batches/<book>-*.jsonl files in order.
- Promote the verse range covered by each batch before applying it.
- Reduce repeated manual commands.

This script shells into the existing Stage 4 tools:
- promote_suggested_trunk_rows.py
- apply_suggested_trunk_review_batch.py

Safety rules remain inside those scripts:
- human_override=true rows are protected unless --force is used.
- review batches only update existing promoted rows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_batch_refs(path: Path) -> list[tuple[int, int, str]]:
    refs: list[tuple[int, int, str]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            obj = json.loads(stripped)
            if obj.get("record_type") == "metadata":
                continue
            reference = str(obj.get("reference"))
            try:
                _book, cv = reference.rsplit(" ", 1)
                chapter, verse = cv.split(":", 1)
                refs.append((int(chapter), int(verse), reference))
            except Exception as exc:
                raise ValueError(f"Could not parse reference at {path}:{line_number}: {reference}") from exc

    return refs


def batch_sort_key(path: Path) -> tuple[int, int, str]:
    refs = load_batch_refs(path)
    if not refs:
        return (9999, 9999, path.name)
    first = min((chapter, verse) for chapter, verse, _reference in refs)
    return (first[0], first[1], path.name)


def run_command(cmd: list[str], cwd: Path, dry_run: bool) -> int:
    print("$ " + " ".join(cmd))
    if dry_run:
        return 0
    completed = subprocess.run(cmd, cwd=str(cwd))
    return completed.returncode


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Promote and apply all Stage 4 review batches for a book.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    parser.add_argument("--force", action="store_true", help="Pass --force to batch applier")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        batch_dir = root / "datasets" / "review-batches"

        batches = sorted(batch_dir.glob(f"{book}-*.jsonl"), key=batch_sort_key)
        if not batches:
            raise FileNotFoundError(f"No batch files found in {batch_dir} for {book}")

        promote_script = root / "scripts" / "stage4" / "promote_suggested_trunk_rows.py"
        apply_script = root / "scripts" / "stage4" / "apply_suggested_trunk_review_batch.py"

        print("MNA Stage 4 — Apply All Review Batches")
        print(f"BOOK: {book}")
        print(f"BATCH COUNT: {len(batches)}")
        print(f"BATCH DIR: {batch_dir}")
        print()

        applied_batches = 0

        for batch in batches:
            refs = load_batch_refs(batch)
            if not refs:
                print(f"SKIP empty batch: {batch}")
                continue

            start = min((chapter, verse) for chapter, verse, _reference in refs)
            end = max((chapter, verse) for chapter, verse, _reference in refs)
            from_ref = f"{start[0]}:{start[1]}"
            to_ref = f"{end[0]}:{end[1]}"
            rel_batch = batch.relative_to(root)

            print(f"=== {rel_batch} ({from_ref}–{to_ref}) ===")

            promote_cmd = [
                sys.executable,
                str(promote_script.relative_to(root)),
                book,
                "--from",
                from_ref,
                "--to",
                to_ref,
            ]
            code = run_command(promote_cmd, root, args.dry_run)
            if code != 0:
                print(f"FAILED during promotion for {rel_batch}", file=sys.stderr)
                return code

            apply_cmd = [
                sys.executable,
                str(apply_script.relative_to(root)),
                book,
                str(rel_batch),
            ]
            if args.force:
                apply_cmd.append("--force")

            code = run_command(apply_cmd, root, args.dry_run)
            if code != 0:
                print(f"FAILED during batch apply for {rel_batch}", file=sys.stderr)
                return code

            applied_batches += 1
            print()

        print("MNA Stage 4 — Apply All Review Batches Complete")
        print(f"BATCHES PROCESSED: {applied_batches}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 apply all review batches FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
