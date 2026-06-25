#!/usr/bin/env python3
"""Assemble BLE verse files from MNA interlinear token JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS_DIR_NT = ROOT / "MNA" / "datasets" / "interlinear" / "NT"
TOKENS_DIR_OT = ROOT / "MNA" / "datasets" / "interlinear" / "OT"
TOKENS_DIR = TOKENS_DIR_NT  # default
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"

from testament_books import NT_BOOKS, OT_BOOKS  # noqa: E402


def token_index(token: dict) -> int:
    if "tok" in token:
        return int(token["tok"])
    if "w" in token:
        return int(token["w"])
    raise KeyError(f"token missing tok/w: {token}")


def display_book(slug: str) -> str:
    if slug and slug[0].isdigit():
        return slug
    return slug[:1].upper() + slug[1:]


def gloss_to_text(es: str) -> str:
    return es.replace("·", " ").strip()


def load_tokens(path: Path) -> list[dict]:
    tokens: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                tokens.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {error}") from error
    return tokens


def assemble_verse(glosses: list[str]) -> str:
    parts = [gloss_to_text(g) for g in glosses if g and g != "?"]
    return " ".join(parts)


def tokens_to_verses(tokens: list[dict]) -> list[tuple[int, int, str]]:
    by_verse: dict[tuple[int, int], list[tuple[int, str]]] = defaultdict(list)
    book_slug = tokens[0]["book"] if tokens else ""

    for token in tokens:
        key = (int(token["ch"]), int(token["vs"]))
        by_verse[key].append((token_index(token), str(token.get("es", ""))))

    verses: list[tuple[int, int, str]] = []
    unresolved = 0

    for (ch, vs) in sorted(by_verse):
        ordered = [es for _, es in sorted(by_verse[(ch, vs)], key=lambda item: item[0])]
        if any(es == "?" or not es.strip() for es in ordered):
            unresolved += sum(1 for es in ordered if es == "?" or not es.strip())
        text = assemble_verse(ordered)
        verses.append((ch, vs, text))

    if unresolved:
        print(f"warning: {book_slug}: {unresolved} unresolved token gloss(es)", file=sys.stderr)

    return verses


def render_ble(book_slug: str, verses: list[tuple[int, int, str]]) -> str:
    label = display_book(book_slug)
    lines = [f"{label} {ch}:{vs} {text}" for ch, vs, text in verses]
    header = (
        f"<!-- BLE — Biblia Literal en Español\n"
        f"     book: {book_slug}\n"
        f"     producer: ble/scripts/tokens_to_ble.py\n"
        f"     generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"-->\n"
    )
    return header + "\n".join(lines) + "\n"


def build_book(book: str, tokens_dir: Path, output_dir: Path) -> Path:
    source = tokens_dir / f"{book}.tokens.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"missing token file: {source}")

    tokens = load_tokens(source)
    if not tokens:
        raise ValueError(f"empty token file: {source}")

    verses = tokens_to_verses(tokens)
    content = render_ble(book, verses)

    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / f"{book}.ble.md"
    dest.write_text(content, encoding="utf-8")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build BLE verse files from MNA interlinear tokens.")
    parser.add_argument("book", nargs="?", help="book slug (e.g. mateo, genesis)")
    parser.add_argument("--all", action="store_true", help="build all books for the selected testament")
    parser.add_argument(
        "--testament",
        choices=("nt", "ot"),
        default="nt",
        help="which testament to build (default: nt)",
    )
    parser.add_argument(
        "--tokens-dir",
        type=Path,
        default=None,
        help="token JSONL directory (default: interlinear/NT or OT)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"output directory (default: {OUTPUT_DIR})",
    )
    args = parser.parse_args()

    tokens_dir = args.tokens_dir or (TOKENS_DIR_OT if args.testament == "ot" else TOKENS_DIR_NT)
    book_list = OT_BOOKS if args.testament == "ot" else NT_BOOKS

    if args.all:
        books = [b for b in book_list if (tokens_dir / f"{b}.tokens.jsonl").is_file()]
        if not books:
            parser.error(f"no token files found in {tokens_dir}")
    elif args.book:
        books = [args.book]
    else:
        parser.error("provide a book slug or --all")

    for book in books:
        dest = build_book(book, tokens_dir, args.output_dir)
        line_count = sum(1 for _ in dest.open(encoding="utf-8"))
        print(f"wrote {dest} ({line_count} lines)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
