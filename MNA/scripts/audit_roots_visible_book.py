#!/usr/bin/env python3

import argparse
import re
from pathlib import Path

from roots_engine_v2_rewrite import render_json_file

WARN_PATTERNS = [
    r"\[ADVERTENCIA:",
    r"\[F sin NBLA:",
]

FAIL_PATTERNS = [
    r"==-==",
]


def verse_sort_key(path: Path):
    try:
        chapter = int(path.parent.name)
    except ValueError:
        chapter = 999999
    try:
        verse = int(path.stem)
    except ValueError:
        verse = 999999
    return chapter, verse


def classify(rendered: str) -> str:
    for pattern in FAIL_PATTERNS:
        if re.search(pattern, rendered):
            return "FAIL"

    for pattern in WARN_PATTERNS:
        if re.search(pattern, rendered):
            return "WARN"

    if "[sin verbo finito detectado]" in rendered:
        return "INFO"

    return "PASS"


def audit_book(book: str, base_dir: Path, out_path: Path):
    book_dir = base_dir / book
    if not book_dir.exists():
        raise FileNotFoundError(f"Book directory not found: {book_dir}")

    json_files = sorted(book_dir.glob("*/*.json"), key=verse_sort_key)

    counts = {
        "PASS": 0,
        "WARN": 0,
        "FAIL": 0,
        "INFO": 0,
    }

    sections = [f"# ROOTS Audit Report — {book}\n"]

    for path in json_files:
        chapter, verse = verse_sort_key(path)
        ref = f"{book} {chapter}:{verse}"

        try:
            rendered = render_json_file(path).strip()
        except Exception as e:
            status = "FAIL"
            rendered = f"[EXCEPCIÓN: {e}]"
        else:
            status = classify(rendered)

        counts[status] += 1

        sections.append(f"\n## {status} — {ref}\n")
        sections.append("\n```text\n")
        sections.append(rendered)
        sections.append("\n```\n")

    summary = [
        "# RESUMEN\n",
        f"- PASS: {counts['PASS']}\n",
        f"- WARN: {counts['WARN']}\n",
        f"- FAIL: {counts['FAIL']}\n",
        f"- INFO: {counts['INFO']}\n",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(summary + sections), encoding="utf-8")

    print(f"Audit written to: {out_path}")
    print(counts)


def main():
    parser = argparse.ArgumentParser(description="Audit ROOTS visible structures for a whole book")
    parser.add_argument("book", help="Book folder name under MNA/data/interlinear")
    parser.add_argument(
        "--base-dir",
        default="MNA/data/interlinear",
        help="Base interlinear directory",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output markdown report path",
    )

    args = parser.parse_args()

    out_path = (
        Path(args.out)
        if args.out
        else Path("MNA/outputs/roots-visible") / f"{args.book}-audit.md"
    )

    audit_book(args.book, Path(args.base_dir), out_path)


if __name__ == "__main__":
    main()
