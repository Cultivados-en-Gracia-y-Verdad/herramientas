#!/usr/bin/env python3
"""Build e-Sword BLE+ interlinear study modules from interlinear exports.

Windows (.bblx): Version=2 RTF fragments (Biblioteca Hispana / iNA27 style).
Mac/mobile (.bbli): native e-Sword HTML tags:
  <grk>/<heb>  original language
  <num>G####</num> / <num>H####</num>  clickable Strong's
  <tvm>…</tvm>  clickable morphology (Robinson / OSHB as stored)
  <red>…</red>  Spanish gloss

This is NOT the official assembled BLE Bible text.
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
    escape_rtf,
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


def normalize_strongs(raw: str) -> str:
    """Ensure Strong's display like G3361 / H7225 for <num> tags."""
    s = (raw or "").strip().upper().replace(" ", "")
    if not s:
        return ""
    if s.startswith(("G", "H")) and s[1:].isdigit():
        return s
    if s.isdigit():
        # Ambiguous bare digits: leave as-is (caller should supply G/H).
        return s
    # e.g. "1254 A" already stripped; keep leading letter if present.
    m = re.match(r"^([GH]?)(\d+)", s)
    if m:
        prefix, digits = m.group(1), m.group(2)
        return f"{prefix}{digits}" if prefix else digits
    return s


def normalize_morph(raw: str) -> str:
    """Pass morph through for <tvm>; only strip OSHB language H- prefix."""
    m = (raw or "").strip()
    if not m:
        return ""
    parts = []
    for comp in m.split("/"):
        # OSHB language prefix is H before a morph class letter (V/N/R/…).
        # Do NOT strip bare A… (ADV, A-NSM, Aramaic A…).
        if re.match(r"^H(?=[VNRPTECDAKSFMW])", comp):
            parts.append(comp[1:])
        else:
            parts.append(comp)
    return "/".join(parts)


def format_token_html(tok: dict[str, str]) -> str:
    """One token in OGNT+-style inline interlinear with working Strong's/morph (Mac .bbli)."""
    surface = escape_html(tok["surface"])
    gloss = escape_html(tok["es"])
    strongs = normalize_strongs(tok["strongs"])
    morph = escape_html(normalize_morph(tok["morph"]))

    lang_tag = "heb" if looks_hebrew(tok["surface"]) else "grk"
    parts = [f"<{lang_tag}>{surface}</{lang_tag}>"]
    if strongs:
        parts.append(f"<num>{escape_html(strongs)}</num>")
    if morph:
        parts.append("<sup>|</sup>")
        parts.append(f"<tvm>{morph}</tvm>")
    if gloss:
        parts.append("<sup>|</sup>")
        parts.append(f"<red>{gloss}</red>")
    return "".join(parts)


def format_token_rtf(tok: dict[str, str]) -> str:
    """One token as Windows e-Sword Version=2 RTF (iNA27-style Spanish interlinear)."""
    surface = escape_rtf(tok["surface"])
    gloss = escape_rtf(tok["es"])
    strongs = normalize_strongs(tok["strongs"])
    morph = normalize_morph(tok["morph"])
    font = r"\f2 " if looks_hebrew(tok["surface"]) else r"\f1 "

    parts: list[str] = [f"{{{font}{surface}}}"]
    if strongs or morph:
        label = strongs
        if strongs and morph:
            label = f"{strongs}:{morph}"
        elif morph:
            label = morph
        parts.append(rf"{{\f0\cf11\super {escape_rtf(label)}}}")
    if gloss:
        parts.append(rf"{{\f0\cf2 {gloss}}}")
    return " ".join(parts)


def format_verse_html(tokens: list[dict[str, str]]) -> str:
    return " ".join(format_token_html(t) for t in tokens)


def format_verse_rtf(tokens: list[dict[str, str]]) -> str:
    # Leading space matches Biblioteca Hispana interlinear verse fragments.
    body = " ".join(format_token_rtf(t) for t in tokens)
    return f" {body}" if body else ""


def load_verses_from_interlinear(
    il_dir: Path,
    books: list[str],
) -> tuple[list[tuple[int, int, int, str]], list[tuple[int, int, int, str]]]:
    """Return (html_rows, rtf_rows) from the same interlinear parse."""
    html_rows: list[tuple[int, int, int, str]] = []
    rtf_rows: list[tuple[int, int, int, str]] = []
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
                key = (book_id, int(ch_s), int(vs_s))
                html_rows.append((*key, format_verse_html(tokens)))
                rtf_rows.append((*key, format_verse_rtf(tokens)))
    html_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    rtf_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return html_rows, rtf_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export BLE+ interlinear study modules for e-Sword (not official BLE)."
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
    args = parser.parse_args()

    if args.book:
        books = [args.book]
    elif args.testament == "ot":
        books = list(OT_BOOKS)
    elif args.testament == "nt":
        books = list(NT_BOOKS)
    else:
        books = list(OT_BOOKS) + list(NT_BOOKS)

    verses_html, verses_rtf = load_verses_from_interlinear(args.interlinear_dir, books)
    if not verses_html:
        print("error: no verses loaded", file=sys.stderr)
        return 1

    book_ids = {b for b, _, _, _ in verses_html}
    include_ot = any(b <= 39 for b in book_ids)
    include_nt = any(b >= 40 for b in book_ids)

    outputs: list[Path] = []
    if args.platform in ("windows", "both"):
        dest = args.output_dir / f"{MODULE_BASENAME}{WINDOWS_SPEC.extension}"
        write_module(
            dest,
            verses_rtf,
            WINDOWS_SPEC,
            include_ot=include_ot,
            include_nt=include_nt,
            strong=True,
            html=True,  # already formatted; do not escape
        )
        outputs.append(dest)
    if args.platform in ("mac", "both"):
        dest = args.output_dir / f"{MODULE_BASENAME}{MAC_SPEC.extension}"
        write_module(
            dest,
            verses_html,
            MAC_SPEC,
            include_ot=include_ot,
            include_nt=include_nt,
            strong=True,
            html=True,
        )
        outputs.append(dest)

    # Remove superseded module filenames.
    for old_name in (
        "BLE.bblx",
        "BLE.bbli",
        "BLE-Interlinear.bblx",
        "BLE-Interlinear.bbli",
        "BLEi.bblx",
        "BLEi.bbli",
    ):
        old = args.output_dir / old_name
        if old.exists():
            old.unlink()
            print(f"removed {old}")

    book_count = len(book_ids)
    for dest in outputs:
        print(f"wrote {dest}")
    print(f"  books: {book_count}")
    print(f"  verses: {len(verses_html)}")
    print(f"  OT: {include_ot}  NT: {include_nt}")
    print(f"  kind: BLE+ interlinear (Windows RTF Version=2 / Mac HTML)")
    print(f"  generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()
    if args.platform in ("windows", "both"):
        print(f"Windows e-Sword: copy {MODULE_BASENAME}.bblx to Documents\\e-Sword\\")
        print("  (RTF interlinear like iNA27+/RV1960+ — not raw HTML tags)")
    if args.platform in ("mac", "both"):
        print(f"e-Sword X (macOS): File → Resources → Import… → {MODULE_BASENAME}.bbli")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
