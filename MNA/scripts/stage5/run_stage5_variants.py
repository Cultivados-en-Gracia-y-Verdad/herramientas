#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

VERSION = "stage5-variant-runner-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def run(cmd: list[str], cwd: Path) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def load_audit(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_outputs(book: str, variant_name: str, mna: Path) -> dict[str, str]:
    source_dataset = mna / "datasets" / "stage5-test" / book
    source_audit = mna / "audits" / "stage5-test" / book

    target = mna / "datasets" / "stage5-variants" / book / variant_name
    target.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    for source_path in [
        source_dataset / "candidate-groups.jsonl",
        source_dataset / "candidate-groups.md",
        source_dataset / "grouping-audit.json",
        source_audit / "candidate-boundary-audit.json",
        source_audit / "candidate-boundary-audit.md",
    ]:
        if source_path.exists():
            dest = target / source_path.name
            shutil.copy2(source_path, dest)
            copied[source_path.name] = str(dest)

    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 5 candidate grouping variants for comparison.")
    parser.add_argument("book")
    parser.add_argument("--thresholds", default="4", help="Comma-separated thresholds. Default: 4")
    parser.add_argument("--streaks", default="2,3", help="Comma-separated disruption streak values. Default: 2,3")
    parser.add_argument("--min-size", type=int, default=2)
    args = parser.parse_args()

    book = args.book.strip().lower()
    mna = root()
    repo = mna.parent

    thresholds = [int(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    streaks = [int(x.strip()) for x in args.streaks.split(",") if x.strip()]

    summary_rows: list[dict[str, Any]] = []

    for threshold in thresholds:
        for streak in streaks:
            variant = f"threshold-{threshold}__streak-{streak}__min-{args.min_size}"
            print(f"\n=== {variant} ===")

            run([
                sys.executable,
                "MNA/scripts/stage5/propose_candidate_groups.py",
                book,
                "--threshold",
                str(threshold),
                "--min-size",
                str(args.min_size),
                "--disruption-streak",
                str(streak),
            ], cwd=repo)

            run([
                sys.executable,
                "MNA/scripts/stage5/audit_candidate_group_boundaries.py",
                book,
            ], cwd=repo)

            audit_path = mna / "audits" / "stage5-test" / book / "candidate-boundary-audit.json"
            audit = load_audit(audit_path)
            copied = copy_outputs(book, variant, mna)

            size_summary = audit.get("size_summary", {})
            confidence_summary = audit.get("confidence_summary", {})

            summary_rows.append({
                "variant": variant,
                "threshold": threshold,
                "disruption_streak": streak,
                "min_size": args.min_size,
                "groups": audit.get("groups_audited"),
                "avg_group_size": size_summary.get("avg"),
                "small_groups_1_to_2": size_summary.get("small_groups_1_to_2"),
                "large_groups_10_plus": size_summary.get("large_groups_10_plus"),
                "low_confidence": confidence_summary.get("low", 0),
                "medium_confidence": confidence_summary.get("medium", 0),
                "medium_high_confidence": confidence_summary.get("medium-high", 0),
                "outputs": copied,
            })

    out_dir = mna / "datasets" / "stage5-variants" / book
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "variant-summary.json"
    summary_md = out_dir / "variant-summary.md"

    summary_json.write_text(json.dumps({
        "record_type": "stage5_variant_summary",
        "version": VERSION,
        "book": book,
        "variants": summary_rows,
    }, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        f"# Stage 5 Variant Summary — {book}",
        "",
        "| Variant | Groups | Avg Size | Small 1–2 | Large 10+ | Low | Medium | Medium-High |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['variant']} | {row['groups']} | {row['avg_group_size']} | {row['small_groups_1_to_2']} | {row['large_groups_10_plus']} | {row['low_confidence']} | {row['medium_confidence']} | {row['medium_high_confidence']} |"
        )
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nStage 5 variant run complete.")
    print(f"SUMMARY JSON: {summary_json}")
    print(f"SUMMARY MD: {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
