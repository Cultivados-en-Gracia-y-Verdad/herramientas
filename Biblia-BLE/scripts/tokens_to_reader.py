#!/usr/bin/env python3
"""Export human-readable interlinear markdown from MNA token JSONL (NT or OT)."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tokens_to_ble import (
    TOKENS_DIR_NT,
    TOKENS_DIR_OT,
    display_book,
    load_tokens,
    token_index,
)
from testament_books import NT_BOOKS, OT_BOOKS

OUTPUT_DIR_NT = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "NT"
OUTPUT_DIR_OT = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "OT"


def md_cell(value: str) -> str:
    return str(value).replace("|", "\\|")


def _lang_helpers(testament: str):
    if testament == "ot":
        from hbo_morph import display_morph
        from hbo_strongs import display_lemma, display_strongs

        return {
            "surface_col": "Hebreo",
            "morph_col": "Morph",
            "blurb": (
                "Formato: cada token hebreo conserva el orden original y muestra "
                "lema (Strong's key), número Strong's, morfología OSHB y el token español literal."
            ),
            "display_morph": display_morph,
            "display_strongs": display_strongs,
            "display_lemma": display_lemma,
        }
    from grc_morph import display_morph
    from grc_strongs import display_strongs

    return {
        "surface_col": "Griego",
        "morph_col": "RMAC",
        "blurb": (
            "Formato: cada token griego conserva el orden original y muestra "
            "lema, número Strong's, morfología RMAC y el token español literal."
        ),
        "display_morph": display_morph,
        "display_strongs": display_strongs,
        "display_lemma": lambda token: str(token.get("lemma", "")),
    }


def render_verse(label: str, ch: int, vs: int, tokens: list[dict], helpers: dict) -> str:
    surface_col = helpers["surface_col"]
    morph_col = helpers["morph_col"]
    lines = [
        f"## {label} {ch}:{vs}",
        "",
        f"| # | {surface_col} | Lemma | Strong's | {morph_col} | Español |",
        "|---:|---|---|---|---|---|",
    ]
    for token in tokens:
        es = str(token.get("es", ""))
        if es == "?" or not es.strip():
            es = f"**{es or '?'}**"
        lines.append(
            "| {tok} | {surface} | {lemma} | {strongs} | {morph} | {es} |".format(
                tok=token_index(token),
                surface=md_cell(token.get("surface", "")),
                lemma=md_cell(helpers["display_lemma"](token)),
                strongs=md_cell(helpers["display_strongs"](token)),
                morph=md_cell(helpers["display_morph"](token)),
                es=md_cell(es),
            )
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_chapter(
    book_slug: str,
    ch: int,
    verses: dict[int, list[dict]],
    helpers: dict,
) -> str:
    label = display_book(book_slug)
    header = (
        f"# {label} {ch} — Interlinear (literal)\n\n"
        f"{helpers['blurb']}\n\n"
        f"<!-- producer: Biblia-BLE/scripts/tokens_to_reader.py "
        f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->\n\n"
    )
    body = "".join(
        render_verse(label, ch, vs, verses[vs], helpers) for vs in sorted(verses)
    )
    return header + body


def group_by_chapter(tokens: list[dict]) -> dict[int, dict[int, list[dict]]]:
    chapters: dict[int, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for token in tokens:
        ch = int(token["ch"])
        vs = int(token["vs"])
        chapters[ch][vs].append(token)
    for ch in chapters:
        for vs in chapters[ch]:
            chapters[ch][vs].sort(key=token_index)
    return chapters


def export_book(
    book: str,
    tokens_dir: Path,
    output_dir: Path,
    helpers: dict,
    chapters: list[int] | None = None,
    single_file: bool = False,
) -> list[Path]:
    source = tokens_dir / f"{book}.tokens.jsonl"
    tokens = load_tokens(source)
    if not tokens:
        raise ValueError(f"empty token file: {source}")

    by_chapter = group_by_chapter(tokens)
    selected = chapters if chapters else sorted(by_chapter)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if single_file:
        label = display_book(book)
        parts = [
            f"# {label} — Interlinear (literal)\n\n"
            f"{helpers['blurb']}\n\n"
        ]
        for ch in selected:
            if ch not in by_chapter:
                continue
            for vs in sorted(by_chapter[ch]):
                parts.append(render_verse(label, ch, vs, by_chapter[ch][vs], helpers))
        dest = output_dir / f"{book}.reader.md"
        dest.write_text("".join(parts), encoding="utf-8")
        written.append(dest)
        return written

    for ch in selected:
        if ch not in by_chapter:
            print(f"warning: {book} chapter {ch} not found", file=sys.stderr)
            continue
        dest = output_dir / f"{book}-{ch:02d}.reader.md"
        dest.write_text(render_chapter(book, ch, by_chapter[ch], helpers), encoding="utf-8")
        written.append(dest)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE interlinear reader markdown from MNA tokens (NT or OT)."
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
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="one .reader.md per book instead of per chapter",
    )
    parser.add_argument("--tokens-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    testament = args.testament
    helpers = _lang_helpers(testament)
    tokens_dir = args.tokens_dir or (TOKENS_DIR_OT if testament == "ot" else TOKENS_DIR_NT)
    output_dir = args.output_dir or (OUTPUT_DIR_OT if testament == "ot" else OUTPUT_DIR_NT)
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
            book,
            tokens_dir,
            output_dir,
            helpers,
            chapters=args.chapters,
            single_file=args.single_file,
        )
        for path in paths:
            print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
