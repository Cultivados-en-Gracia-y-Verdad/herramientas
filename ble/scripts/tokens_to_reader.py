#!/usr/bin/env python3
"""Export human-readable interlinear markdown from MNA token JSONL."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tokens_to_ble import NT_BOOKS, TOKENS_DIR, display_book, load_tokens

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "interlinear" / "NT"


def md_cell(value: str) -> str:
    return str(value).replace("|", "\\|")


def render_verse(label: str, ch: int, vs: int, tokens: list[dict]) -> str:
    lines = [
        f"## {label} {ch}:{vs}",
        "",
        "| # | Griego | Lemma | Morph | Español |",
        "|---:|---|---|---|---|",
    ]
    for token in tokens:
        es = str(token.get("es", ""))
        if es == "?" or not es.strip():
            es = f"**{es or '?'}**"
        lines.append(
            "| {tok} | {surface} | {lemma} | {morph} | {es} |".format(
                tok=token["tok"],
                surface=md_cell(token.get("surface", "")),
                lemma=md_cell(token.get("lemma", "")),
                morph=md_cell(token.get("morph", "")),
                es=md_cell(es),
            )
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def render_chapter(book_slug: str, ch: int, verses: dict[int, list[dict]]) -> str:
    label = display_book(book_slug)
    header = (
        f"# {label} {ch} — Interlinear (literal)\n\n"
        "Formato: cada token griego conserva el orden original y muestra "
        "lema, morfología y el token español literal.\n\n"
        f"<!-- producer: ble/scripts/tokens_to_reader.py "
        f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->\n\n"
    )
    body = "".join(
        render_verse(label, ch, vs, verses[vs])
        for vs in sorted(verses)
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
            chapters[ch][vs].sort(key=lambda item: int(item["tok"]))
    return chapters


def export_book(
    book: str,
    tokens_dir: Path,
    output_dir: Path,
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
            "Formato: cada token griego conserva el orden original y muestra "
            "lema, morfología y el token español literal.\n\n"
        ]
        for ch in selected:
            if ch not in by_chapter:
                continue
            for vs in sorted(by_chapter[ch]):
                parts.append(render_verse(label, ch, vs, by_chapter[ch][vs]))
        dest = output_dir / f"{book}.reader.md"
        dest.write_text("".join(parts), encoding="utf-8")
        written.append(dest)
        return written

    for ch in selected:
        if ch not in by_chapter:
            print(f"warning: {book} chapter {ch} not found", file=sys.stderr)
            continue
        dest = output_dir / f"{book}-{ch:02d}.reader.md"
        dest.write_text(render_chapter(book, ch, by_chapter[ch]), encoding="utf-8")
        written.append(dest)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE interlinear reader markdown from MNA NT tokens."
    )
    parser.add_argument("book", nargs="?", help="book slug (e.g. mateo)")
    parser.add_argument("--all", action="store_true", help="export all 27 NT books")
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
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.all:
        books = NT_BOOKS
    elif args.book:
        books = [args.book]
    else:
        parser.error("provide a book slug or --all")

    for book in books:
        paths = export_book(
            book,
            args.tokens_dir,
            args.output_dir,
            chapters=args.chapters,
            single_file=args.single_file,
        )
        for path in paths:
            print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
