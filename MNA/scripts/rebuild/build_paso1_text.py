#!/usr/bin/env python3
"""
MNA ROOTS — Build Paso 1 Text

Paso 1 — COPIAR TEXTO

Purpose:
- Read the NBLA source for a book.
- Produce one JSONL row per verse.
- This is the first dependency in the Pasos 1–4 rebuild chain.

Expected input:
  data/NBLA/<book>.nbla.md

Expected output:
  datasets/roots-pasos/<book>/paso1-text.jsonl

Accepted source line patterns:
  1:1 Texto...
  1.1 Texto...
  1corintios 1:1 Texto...
  1 Corintios 1:1 Texto...
  ### 1 Corintios 1:1
  Texto...  (captured as the verse text for the latest heading)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
REF_LINE_RE = re.compile(r"^(?:(?P<book>[1-3]?\s*\S+)\s+)?(?P<chapter>\d+)[:.](?P<verse>\d+)\s+(?P<text>.+?)\s*$")
REF_ONLY_RE = re.compile(r"^(?:(?P<book>[1-3]?\s*\S+)\s+)?(?P<chapter>\d+)[:.](?P<verse>\d+)\s*$")


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def parse_heading_ref(line: str) -> Optional[tuple[int, int]]:
    heading_match = HEADING_RE.match(line.strip())
    if not heading_match:
        return None
    content = heading_match.group(1).strip()
    ref_match = REF_ONLY_RE.search(content)
    if not ref_match:
        ref_match = REF_LINE_RE.search(content)
    if not ref_match:
        return None
    return int(ref_match.group("chapter")), int(ref_match.group("verse"))


def parse_ref_line(line: str) -> Optional[tuple[int, int, str]]:
    match = REF_LINE_RE.match(line.strip())
    if not match:
        return None
    return int(match.group("chapter")), int(match.group("verse")), normalize_text(match.group("text"))


def read_nbla_verses(path: Path, book: str) -> list[dict]:
    rows: list[dict] = []
    pending_ref: Optional[tuple[int, int]] = None

    if not path.exists():
        raise FileNotFoundError(f"NBLA source not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue

            ref_line = parse_ref_line(line)
            if ref_line:
                chapter, verse, text = ref_line
                rows.append(
                    {
                        "reference": f"{book} {chapter}:{verse}",
                        "book": book,
                        "chapter": chapter,
                        "verse": verse,
                        "paso": 1,
                        "step_title": "COPIAR TEXTO",
                        "nbla_text": text,
                    }
                )
                pending_ref = None
                continue

            heading_ref = parse_heading_ref(line)
            if heading_ref:
                pending_ref = heading_ref
                continue

            if pending_ref:
                chapter, verse = pending_ref
                rows.append(
                    {
                        "reference": f"{book} {chapter}:{verse}",
                        "book": book,
                        "chapter": chapter,
                        "verse": verse,
                        "paso": 1,
                        "step_title": "COPIAR TEXTO",
                        "nbla_text": normalize_text(line),
                    }
                )
                pending_ref = None

    # Deduplicate by reference while preserving last seen text.
    by_ref: dict[str, dict] = {}
    for row in rows:
        by_ref[row["reference"]] = row

    return sorted(by_ref.values(), key=lambda r: (int(r["chapter"]), int(r["verse"])))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build ROOTS Paso 1 text dataset from NBLA source.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        input_path = root / "data" / "NBLA" / f"{book}.nbla.md"
        output_path = root / "datasets" / "roots-pasos" / book / "paso1-text.jsonl"

        rows = read_nbla_verses(input_path, book)
        if not rows:
            raise ValueError(f"No NBLA verse rows parsed from {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as out:
            metadata = {
                "record_type": "metadata",
                "book": book,
                "paso": 1,
                "step_title": "COPIAR TEXTO",
                "source": str(input_path.relative_to(root)),
                "rows": len(rows),
            }
            out.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")

        print("MNA ROOTS — Paso 1")
        print(f"BOOK: {book}")
        print(f"INPUT: {input_path}")
        print(f"OUTPUT: {output_path}")
        print(f"ROWS: {len(rows)}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA ROOTS Paso 1 FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
