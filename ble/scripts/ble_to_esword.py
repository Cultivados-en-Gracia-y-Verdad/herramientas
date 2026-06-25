#!/usr/bin/env python3
"""Build e-Sword Bible modules (.bblx Windows, .bbli macOS) from BLE verse files."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from esword_lib import (  # noqa: E402
    ESWORD_BOOK_ID,
    MAC_SPEC,
    WINDOWS_SPEC,
    write_module,
)
from tokens_to_ble import NT_BOOKS  # noqa: E402
from validate_ble import parse_verses  # noqa: E402

DEFAULT_INPUT = SCRIPT_DIR.parent / "output"
DEFAULT_OUT_DIR = SCRIPT_DIR.parent / "output" / "esword"


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE NT verses to e-Sword modules."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"directory with *.ble.md files (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--platform",
        choices=("windows", "mac", "both"),
        default="both",
        help="target e-Sword platform (default: both)",
    )
    parser.add_argument("--book", help="single book slug only")
    parser.add_argument("--all", action="store_true", help="all 27 NT books (default)")
    args = parser.parse_args()

    books = [args.book] if args.book else NT_BOOKS
    verses = load_verses_from_ble_dir(args.input_dir, books)
    if not verses:
        print("error: no verses loaded", file=sys.stderr)
        return 1

    outputs: list[Path] = []
    if args.platform in ("windows", "both"):
        dest = args.output_dir / f"BLE{WINDOWS_SPEC.extension}"
        write_module(dest, verses, WINDOWS_SPEC)
        outputs.append(dest)
    if args.platform in ("mac", "both"):
        dest = args.output_dir / f"BLE{MAC_SPEC.extension}"
        write_module(dest, verses, MAC_SPEC)
        outputs.append(dest)

    book_count = len({book for book, _, _, _ in verses})
    for dest in outputs:
        print(f"wrote {dest}")
    print(f"  books: {book_count}")
    print(f"  verses: {len(verses)}")
    print(f"  generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()
    if args.platform in ("windows", "both"):
        print("Windows e-Sword: copy BLE.bblx to Documents\\e-Sword\\")
    if args.platform in ("mac", "both"):
        print("e-Sword X (macOS): File → Resources → Import… → BLE.bbli")
        print("  (or double-click BLE.bbli in Finder)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
