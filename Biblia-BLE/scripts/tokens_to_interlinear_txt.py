#!/usr/bin/env python3
"""Export compact verse interlinear lines from MNA token JSONL (NT or OT).

Format (one line per verse, tab-separated ref):
  mateo 1:1\\tΒίβλος<βίβλος|G976|N-NSF|libro> ...
  genesis 1:1\\tבְּ/רֵאשִׁ֖ית<7225|H7225|HR/Ncfsa|en·principio> ...
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from testament_books import NT_BOOKS, OT_BOOKS
from tokens_to_ble import TOKENS_DIR_NT, TOKENS_DIR_OT, load_tokens, token_index

OUTPUT_DIR_NT = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "NT"
OUTPUT_DIR_OT = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "OT"
MNA_NT = Path(__file__).resolve().parents[2] / "MNA" / "datasets" / "interlinear" / "NT"
MNA_OT = Path(__file__).resolve().parents[2] / "MNA" / "datasets" / "interlinear" / "OT"


def _helpers(testament: str):
    if testament == "ot":
        from hbo_morph import display_morph
        from hbo_strongs import display_lemma, display_strongs

        return display_lemma, display_strongs, display_morph
    from grc_morph import display_morph
    from grc_strongs import display_strongs

    return (lambda t: str(t.get("lemma", "")), display_strongs, display_morph)


def format_token(token: dict, display_lemma, display_strongs, display_morph) -> str:
    surface = str(token.get("surface", ""))
    lemma = display_lemma(token)
    strongs = display_strongs(token)
    morph = display_morph(token)
    es = str(token.get("es", ""))
    return f"{surface}<{lemma}|{strongs}|{morph}|{es}>"


def render_verse_line(book: str, ch: int, vs: int, tokens: list[dict], helpers) -> str:
    display_lemma, display_strongs, display_morph = helpers
    ref = f"{book} {ch}:{vs}"
    body = " ".join(
        format_token(t, display_lemma, display_strongs, display_morph) for t in tokens
    )
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
    helpers,
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
            render_verse_line(book, ch, vs, by_verse[(ch, vs)], helpers)
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
    parser = argparse.ArgumentParser(
        description="Export compact interlinear .txt from NT/OT tokens."
    )
    parser.add_argument("book", nargs="?", help="book slug (e.g. mateo, genesis)")
    parser.add_argument("--all", action="store_true", help="export all books for testament")
    parser.add_argument(
        "--testament",
        choices=("nt", "ot"),
        default="nt",
        help="which testament (default: nt)",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        action="append",
        dest="chapters",
        metavar="N",
        help="only export chapter N (repeatable)",
    )
    parser.add_argument("--tokens-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--to-mna",
        action="store_true",
        help="also write compact .txt into MNA/datasets/interlinear/{NT|OT}/",
    )
    args = parser.parse_args()

    testament = args.testament
    helpers = _helpers(testament)
    tokens_dir = args.tokens_dir or (TOKENS_DIR_OT if testament == "ot" else TOKENS_DIR_NT)
    output_dir = args.output_dir or (OUTPUT_DIR_OT if testament == "ot" else OUTPUT_DIR_NT)
    mna_dir = MNA_OT if testament == "ot" else MNA_NT
    book_list = OT_BOOKS if testament == "ot" else NT_BOOKS

    if args.all:
        books = [b for b in book_list if (tokens_dir / f"{b}.tokens.jsonl").is_file()]
        if not books:
            parser.error(f"no token files found in {tokens_dir}")
    elif args.book:
        books = [args.book]
    else:
        parser.error("provide a book slug or --all")

    for book in books:
        paths = export_book(
            book, tokens_dir, output_dir, helpers, chapters=args.chapters
        )
        for path in paths:
            print(f"wrote {path}")
        if args.to_mna:
            mna_paths = export_book(
                book, tokens_dir, mna_dir, helpers, chapters=args.chapters
            )
            for path in mna_paths:
                print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
