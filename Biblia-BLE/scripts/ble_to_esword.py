#!/usr/bin/env python3
"""Build e-Sword interlinear study modules from BLE interlinear exports.

This is NOT the official BLE Bible text. Each verse is HTML with original
surface + Spanish gloss (+ Strong's) in traditional interlinear columns.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from esword_lib import (  # noqa: E402
    ESWORD_BOOK_ID,
    MAC_SPEC,
    MODULE_BASENAME,
    WINDOWS_SPEC,
    escape_html,
    write_module,
)
from testament_books import NT_BOOKS, OT_BOOKS  # noqa: E402

ROOT = SCRIPT_DIR.parent
DEFAULT_IL_DIR = ROOT / "output" / "interlinear"
DEFAULT_OUT_DIR = ROOT / "output" / "esword"

TOKEN_RE = re.compile(r"([^\s<]+)<([^|]*)\|([^|]*)\|([^|]*)\|([^>]*)>")
REF_RE = re.compile(r"^(\S+)\s+(\d+):(\d+)\t(.*)$")


def parse_tokens(body: str) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    for m in TOKEN_RE.finditer(body):
        tokens.append(
            {
                "surface": m.group(1),
                "lemma": m.group(2),
                "strongs": m.group(3),
                "morph": m.group(4),
                "es": m.group(5),
            }
        )
    return tokens


def looks_hebrew(surface: str) -> bool:
    return any("\u0590" <= ch <= "\u05FF" for ch in surface)


def format_token_plain(tok: dict[str, str], *, show_strongs: bool = True) -> str:
    """Compact traditional interlinear unit: surface/gloss[Strong's]."""
    surface = tok["surface"]
    gloss = tok["es"]
    strongs = tok["strongs"]
    if show_strongs and strongs:
        return f"{surface}/{gloss}[{strongs}]"
    return f"{surface}/{gloss}"


def format_verse_text(tokens: list[dict[str, str]], *, show_strongs: bool = True) -> str:
    return " ".join(format_token_plain(t, show_strongs=show_strongs) for t in tokens)


def load_verses_from_interlinear(
    il_dir: Path,
    books: list[str],
    *,
    show_strongs: bool = True,
) -> list[tuple[int, int, int, str]]:
    rows: list[tuple[int, int, int, str]] = []
    for slug in books:
        book_id = ESWORD_BOOK_ID.get(slug)
        if not book_id:
            print(f"skip unknown book slug {slug!r}", file=sys.stderr)
            continue
        testament = "OT" if book_id <= 39 else "NT"
        folder = il_dir / testament
        paths = sorted(folder.glob(f"{slug}-*.interlinear.txt"))
        if not paths:
            print(f"skip missing interlinear for {slug}", file=sys.stderr)
            continue
        for path in paths:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                m = REF_RE.match(line)
                if not m:
                    continue
                _book, ch_s, vs_s, body = m.groups()
                tokens = parse_tokens(body)
                if not tokens:
                    continue
                text = format_verse_text(tokens, show_strongs=show_strongs)
                rows.append((book_id, int(ch_s), int(vs_s), text))
    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE interlinear study modules for e-Sword (not official BLE)."
    )
    parser.add_argument(
        "--interlinear-dir",
        type=Path,
        default=DEFAULT_IL_DIR,
        help=f"interlinear root with OT/NT (default: {DEFAULT_IL_DIR})",
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
    parser.add_argument(
        "--testament",
        choices=("ot", "nt", "both"),
        default="both",
        help="which testament(s) to include (default: both)",
    )
    parser.add_argument(
        "--no-strongs",
        action="store_true",
        help="omit Strong's numbers from each column",
    )
    args = parser.parse_args()

    if args.book:
        books = [args.book]
    elif args.testament == "ot":
        books = list(OT_BOOKS)
    elif args.testament == "nt":
        books = list(NT_BOOKS)
    else:
        books = list(OT_BOOKS) + list(NT_BOOKS)

    verses = load_verses_from_interlinear(
        args.interlinear_dir,
        books,
        show_strongs=not args.no_strongs,
    )
    if not verses:
        print("error: no verses loaded", file=sys.stderr)
        return 1

    book_ids = {b for b, _, _, _ in verses}
    include_ot = any(b <= 39 for b in book_ids)
    include_nt = any(b >= 40 for b in book_ids)

    outputs: list[Path] = []
    if args.platform in ("windows", "both"):
        dest = args.output_dir / f"{MODULE_BASENAME}{WINDOWS_SPEC.extension}"
        write_module(
            dest,
            verses,
            WINDOWS_SPEC,
            include_ot=include_ot,
            include_nt=include_nt,
            strong=not args.no_strongs,
            html=False,
        )
        outputs.append(dest)
    if args.platform in ("mac", "both"):
        dest = args.output_dir / f"{MODULE_BASENAME}{MAC_SPEC.extension}"
        write_module(
            dest,
            verses,
            MAC_SPEC,
            include_ot=include_ot,
            include_nt=include_nt,
            strong=not args.no_strongs,
            html=False,
        )
        outputs.append(dest)

    # Remove old official-looking BLE.* modules if present.
    for old in (
        args.output_dir / "BLE.bblx",
        args.output_dir / "BLE.bbli",
    ):
        if old.exists():
            old.unlink()
            print(f"removed {old} (was assembled BLE text)")

    book_count = len(book_ids)
    for dest in outputs:
        print(f"wrote {dest}")
    print(f"  books: {book_count}")
    print(f"  verses: {len(verses)}")
    print(f"  OT: {include_ot}  NT: {include_nt}")
    print(f"  kind: interlinear study (not official BLE)")
    print(f"  generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()
    if args.platform in ("windows", "both"):
        print(f"Windows e-Sword: copy {MODULE_BASENAME}.bblx to Documents\\e-Sword\\")
    if args.platform in ("mac", "both"):
        print(f"e-Sword X (macOS): File → Resources → Import… → {MODULE_BASENAME}.bbli")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
