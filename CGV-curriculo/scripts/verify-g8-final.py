#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G8_FINAL_VERIFY mechanical stream — must pass before human review (G9).

Runs, in order:
  1. verify-speaker-hearing.py --gate g8   (includes G7 speaker rules + density)
  2. run-manual-checks.py                 (evidence report; does not alone PASS G8)
  3. build-context-quotes.py --check      (if --lbf)
  4. verify-blocks.py                     (if --blocks)

Speaker/hearing FAIL blocks. Quote/blocks FAIL blocks. run-manual-checks always
writes evidence; packaging CRITICAL gaps are left for human+report reading, but
missing --manual is fatal.

    python3 scripts/verify-g8-final.py \\
        --manual curriculo/23.Apocalipsis/manual/manual.md \\
        --lbf    …/Apocalipsis.lbf.md \\
        --blocks curriculo/23.Apocalipsis/blocks.md \\
        --book   Apocalipsis

Exit: 0 PASS · 1 FAIL · 2 usage
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(label: str, argv: list[str], *, must_pass: bool) -> tuple[str, bool, str]:
    r = subprocess.run(argv, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    ok = r.returncode == 0
    if not must_pass:
        ok = True  # evidence only
    print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {label}" + ("" if must_pass else " (evidence)"))
    if r.returncode != 0 and must_pass:
        print("\n".join(out.strip().splitlines()[:30]))
    return label, ok if must_pass else (r.returncode == 0 or True), out


def main() -> int:
    ap = argparse.ArgumentParser(description="G8 mechanical final verification stream.")
    ap.add_argument("--manual", required=True, type=Path)
    ap.add_argument("--lbf", type=Path)
    ap.add_argument("--blocks", type=Path)
    ap.add_argument("--book", default="libro")
    ap.add_argument("--reports-dir", type=Path)
    args = ap.parse_args()

    if not args.manual.is_file():
        print(f"error: no such manual: {args.manual}", file=sys.stderr)
        return 2

    reports = args.reports_dir or (args.manual.resolve().parent.parent / "reports")
    reports.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, bool]] = []

    # 1) Speaker / hearing (blocking)
    hearing_out = reports / "SPEAKER_HEARING_REPORT.md"
    r = subprocess.run(
        [
            sys.executable,
            str(HERE / "verify-speaker-hearing.py"),
            "--manual",
            str(args.manual),
            "--gate",
            "g8",
            "--out",
            str(hearing_out),
        ]
    )
    print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  Speaker/hearing (g8)")
    results.append(("speaker-hearing", r.returncode == 0))

    # 2) Manual checks (always run; evidence — exit 0 of that script is always 0 today)
    py_out = reports / "PYTHON_REPORT.md"
    cmd = [
        sys.executable,
        str(HERE / "run-manual-checks.py"),
        "--manual",
        str(args.manual),
        "--book",
        args.book,
        "--out",
        str(py_out),
    ]
    if args.lbf and args.lbf.is_file():
        cmd.extend(["--lbf", str(args.lbf)])
    r2 = subprocess.run(cmd)
    print(f"{'PASS' if r2.returncode == 0 else 'FAIL'}  Manual checks (evidence)")
    results.append(("manual-checks", r2.returncode == 0))

    # 3) Context quotes
    if args.lbf and args.lbf.is_file():
        r3 = subprocess.run(
            [
                sys.executable,
                str(HERE / "build-context-quotes.py"),
                "--manual",
                str(args.manual),
                "--lbf",
                str(args.lbf),
                "--check",
            ]
        )
        print(f"{'PASS' if r3.returncode == 0 else 'FAIL'}  Context quotes")
        results.append(("context-quotes", r3.returncode == 0))

    # 4) Blocks
    if args.blocks and args.blocks.is_file():
        text = args.blocks.read_text(encoding="utf-8")
        if "NOT STARTED" not in text and args.lbf and args.lbf.is_file():
            r4 = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "verify-blocks.py"),
                    "--blocks",
                    str(args.blocks),
                    "--lbf",
                    str(args.lbf),
                ]
            )
            print(f"{'PASS' if r4.returncode == 0 else 'FAIL'}  Blocks")
            results.append(("blocks", r4.returncode == 0))

    # 5) H4 length on the student surface (blocking) — catches mega-claims like
    #    packed epistolary greetings that never got actor-core peel / re-cut.
    h4_re = __import__("re").compile(r"^#### \*(.+?)\*\s*$", __import__("re").M)
    body = args.manual.read_text(encoding="utf-8")
    for stop in (
        "\n## Actores",
        "\n## Movimiento",
        "\n## Convergencia",
        "\n## Tensión",
        "\n## Apéndice",
        "\n# Apéndices",
    ):
        i = body.find(stop)
        if 0 < i:
            body = body[:i]
            break
    MAX_H4 = 180
    long_h4 = [(len(t), t[:90]) for t in h4_re.findall(body) if len(t) > MAX_H4]
    if long_h4:
        print(f"FAIL  H4 length (>{MAX_H4} chars): {len(long_h4)}")
        for n, sample in sorted(long_h4, reverse=True)[:8]:
            print(f"  {n} chars: {sample}…")
        results.append(("h4-length", False))
    else:
        print(f"PASS  H4 length (no H4 >{MAX_H4} chars on student surface)")
        results.append(("h4-length", True))

    bad = [name for name, ok in results if not ok]
    print()
    if bad:
        print(f"G8_FINAL_VERIFY mechanical: FAIL — {', '.join(bad)}")
        print(f"See {hearing_out}")
        return 1
    print("G8_FINAL_VERIFY mechanical: PASS")
    print("Human sufficiency reading is G9 — not this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
