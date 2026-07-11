#!/usr/bin/env python3
"""Export compact verse interlinear lines from MNA token JSONL.

Format (one line per verse, tab-separated ref):
  mateo 1:1\\tΒίβλος<βίβλος|G976|N-NSF|libro> γενέσεως<γένεσις|G1078|N-GSF|de·genealogía> ...
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from testament_books import NT_BOOKS
from grc_morph import display_morph
from grc_strongs import display_strongs
from tokens_to_ble import TOKENS_DIR_NT, load_tokens, token_index

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "NT"
READER_MD_DIR = (
    Path(__file__).resolve().parents[2] / "MNA" / "datasets" / "interlinear" / "NT"
)


def format_token(token: dict) -> str:
    surface = str(token.get("surface", ""))
    lemma = str(token.get("lemma", ""))
    strongs = display_strongs(token)
    rmac = display_morph(token)
    es = str(token.get("es", ""))
    return f"{surface}<{lemma}|{strongs}|{rmac}|{es}>"


def render_verse_line(book: str, ch: int, vs: int, tokens: list[dict]) -> str:
    ref = f"{book} {ch}:{vs}"
    body = " ".join(format_token(t) for t in tokens)
    return f"{ref}\t{body}"


def group_verses(tokens: list[dict]) -> dict[tuple[int, int], list[dict]]:
    by_verse: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for token in tokens:
        by_verse[(int(token["ch"]), int(token["vs"]))].append(token)
    for key in by_verse:
        by_verse[key].sort(key=token_index)
    return by_verse


def export_book(
    book: str,
    tokens_dir: Path,
    output_dir: Path,
    chapters: list[int] | None = None,
) -> list[Path]:
    source = tokens_dir / f"{book}.tokens.jsonl"
    tokens = load_tokens(source)
    if not tokens:
        raise ValueError(f"empty token file: {source}")

    by_verse = group_verses(tokens)
    chapter_nums = chapters if chapters else sorted({ch for ch, _ in by_verse})
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for ch in chapter_nums:
        lines = [
            render_verse_line(book, ch, vs, by_verse[(ch, vs)])
            for vs in sorted(vs for c, vs in by_verse if c == ch)
        ]
        if not lines:
            print(f"warning: {book} chapter {ch} not found", file=sys.stderr)
            continue
        dest = output_dir / f"{book}-{ch:02d}.interlinear.txt"
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(dest)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Export compact interlinear .txt from NT tokens.")
    parser.add_argument("book", nargs="?", help="book slug (e.g. mateo)")
    parser.add_argument("--all", action="store_true", help="export all NT books")
    parser.add_argument(
        "--chapter",
        type=int,
        action="append",
        dest="chapters",
        metavar="N",
        help="only export chapter N (repeatable)",
    )
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR_NT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--to-mna",
        action="store_true",
        help=f"also write to {READER_MD_DIR}",
    )
    args = parser.parse_args()

    if args.all:
        books = NT_BOOKS
    elif args.book:
        books = [args.book]
    else:
        parser.error("provide a book slug or --all")

    for book in books:
        paths = export_book(book, args.tokens_dir, args.output_dir, chapters=args.chapters)
        for path in paths:
            print(f"wrote {path}")
        if args.to_mna:
            mna_paths = export_book(book, args.tokens_dir, READER_MD_DIR, chapters=args.chapters)
            for path in mna_paths:
                print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
