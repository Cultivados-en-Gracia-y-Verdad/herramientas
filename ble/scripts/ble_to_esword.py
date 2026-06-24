#!/usr/bin/env python3
"""Build an e-Sword Bible module (.bblx) from BLE verse files."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from tokens_to_ble import NT_BOOKS, display_book  # noqa: E402
from validate_ble import parse_verses  # noqa: E402

ROOT = SCRIPT_DIR.parents[1]
DEFAULT_INPUT = SCRIPT_DIR.parent / "output"
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "output" / "esword" / "BLE.bblx"

# Standard Protestant e-Sword book numbers (Matthew = 40 … Revelation = 66).
ESWORD_BOOK_ID: dict[str, int] = {
    "mateo": 40,
    "marcos": 41,
    "lucas": 42,
    "juan": 43,
    "hechos": 44,
    "romanos": 45,
    "1corintios": 46,
    "2corintios": 47,
    "galatas": 48,
    "efesios": 49,
    "filipenses": 50,
    "colosenses": 51,
    "1tesalonicenses": 52,
    "2tesalonicenses": 53,
    "1timoteo": 54,
    "2timoteo": 55,
    "tito": 56,
    "filemon": 57,
    "hebreos": 58,
    "santiago": 59,
    "1pedro": 60,
    "2pedro": 61,
    "1juan": 62,
    "2juan": 63,
    "3juan": 64,
    "judas": 65,
    "apocalipsis": 66,
}

MODULE_DESCRIPTION = "Biblia Literal en Español (Nuevo Testamento)"
MODULE_ABBREV = "BLE"
MODULE_INFO = (
    "BLE — Biblia Literal en Español. Traducción formal palabra por palabra del "
    "Nuevo Testamento griego. Generado desde MNA/BLE."
)


def slug_from_ble_path(path: Path) -> str:
    match = re.match(r"^(.+)\.ble\.md$", path.name, re.IGNORECASE)
    if not match:
        raise ValueError(f"not a BLE file: {path}")
    return match.group(1).lower()


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def load_verses_from_ble_dir(input_dir: Path, books: list[str]) -> list[tuple[int, int, int, str]]:
    rows: list[tuple[int, int, int, str]] = []
    for slug in books:
        path = input_dir / f"{slug}.ble.md"
        if not path.is_file():
            print(f"skip missing {path}", file=sys.stderr)
            continue
        book_id = ESWORD_BOOK_ID.get(slug)
        if not book_id:
            print(f"skip unknown book slug {slug!r}", file=sys.stderr)
            continue
        for _book_label, ch, vs, text in parse_verses(path.read_text(encoding="utf-8")):
            rows.append((book_id, ch, vs, text))
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return rows


def create_esword_module(
    dest: Path,
    verses: list[tuple[int, int, int, str]],
    *,
    description: str = MODULE_DESCRIPTION,
    abbrev: str = MODULE_ABBREV,
    information: str = MODULE_INFO,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    conn = sqlite3.connect(dest)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE Details (
                Description NVARCHAR(250),
                Abbreviation NVARCHAR(50),
                Information TEXT,
                Version INT,
                Font NVARCHAR(50),
                RightToLeft BOOL,
                OT BOOL,
                NT BOOL,
                Apocrypha BOOL,
                Strong BOOL
            )
            """
        )
        cur.execute(
            """
            INSERT INTO Details (
                Description, Abbreviation, Information, Version, Font,
                RightToLeft, OT, NT, Apocrypha, Strong
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (description, abbrev, information, 4, "DEFAULT", 0, 0, 1, 0, 0),
        )
        cur.execute(
            """
            CREATE TABLE Bible (
                Book INT,
                Chapter INT,
                Verse INT,
                Scripture TEXT,
                PRIMARY KEY (Book, Chapter, Verse)
            )
            """
        )
        cur.executemany(
            "INSERT INTO Bible (Book, Chapter, Verse, Scripture) VALUES (?, ?, ?, ?)",
            [(book, ch, vs, escape_html(text)) for book, ch, vs, text in verses],
        )
        cur.execute("CREATE INDEX BookChapterVerseIndex ON Bible (Book, Chapter, Verse)")
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE NT verses to an e-Sword .bblx SQLite module."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"directory with *.ble.md files (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output .bblx path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--book", help="single book slug only")
    parser.add_argument("--all", action="store_true", help="all 27 NT books (default)")
    args = parser.parse_args()

    books = [args.book] if args.book else NT_BOOKS
    verses = load_verses_from_ble_dir(args.input_dir, books)
    if not verses:
        print("error: no verses loaded", file=sys.stderr)
        return 1

    create_esword_module(args.output, verses)

    book_count = len({book for book, _, _, _ in verses})
    print(f"wrote {args.output}")
    print(f"  books: {book_count}")
    print(f"  verses: {len(verses)}")
    print(f"  generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()
    print("Install in e-Sword:")
    print("  Windows: copy BLE.bblx to Documents\\e-Sword\\")
    print("  macOS:   copy BLE.bblx to ~/Documents/e-Sword/")
    print("  Then restart e-Sword and select BLE from the Bible version menu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
