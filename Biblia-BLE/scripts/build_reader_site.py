#!/usr/bin/env python3
"""Assemble a static web bundle for the BLE interlinear reader.

Layout (relative paths match reader/app.js):
  site/
    reader/          index.html, app.js, styles.css, catalog.json, search-index.json
    output/interlinear/{OT,NT}/*.interlinear.txt

Usage:
  python3 scripts/build_reader_catalog.py   # refresh indexes first
  python3 scripts/build_reader_site.py
  python3 scripts/build_reader_site.py --dest /path/to/cgv-web/docs/ble
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "site"


def copy_tree_files(src: Path, dest: Path, pattern: str) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(src.glob(pattern)):
        if not path.is_file():
            continue
        shutil.copy2(path, dest / path.name)
        count += 1
    return count


def build_site(dest: Path, *, clean: bool = True) -> dict[str, int]:
    if clean and dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    reader_src = ROOT / "reader"
    reader_dest = dest / "reader"
    reader_dest.mkdir(parents=True, exist_ok=True)
    reader_files = 0
    for name in (
        "index.html",
        "app.js",
        "styles.css",
        "catalog.json",
        "search-index.json",
    ):
        src = reader_src / name
        if not src.is_file():
            raise SystemExit(f"missing reader asset: {src}")
        shutil.copy2(src, reader_dest / name)
        reader_files += 1

    il_root = ROOT / "output" / "interlinear"
    counts = {"reader": reader_files, "OT": 0, "NT": 0}
    for testament in ("OT", "NT"):
        src = il_root / testament
        if not src.is_dir():
            raise SystemExit(f"missing interlinear dir: {src}")
        n = copy_tree_files(src, dest / "output" / "interlinear" / testament, "*.interlinear.txt")
        counts[testament] = n
        if n == 0:
            raise SystemExit(f"no .interlinear.txt files in {src}")

    # Landing redirect at site root.
    (dest / "index.html").write_text(
        '<!DOCTYPE html>\n'
        '<html lang="es"><head>'
        '<meta charset="utf-8" />'
        '<meta http-equiv="refresh" content="0; url=reader/" />'
        '<title>BLE Interlinear</title>'
        '<link rel="canonical" href="reader/" />'
        "</head><body>"
        '<p><a href="reader/">Abrir BLE Interlinear</a></p>'
        "</body></html>\n",
        encoding="utf-8",
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static BLE reader site bundle.")
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"output directory (default: {DEFAULT_DEST})",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="do not delete destination before copying",
    )
    args = parser.parse_args()
    counts = build_site(args.dest, clean=not args.no_clean)
    print(f"wrote {args.dest}")
    print(f"  reader assets: {counts['reader']}")
    print(f"  OT chapters:   {counts['OT']}")
    print(f"  NT chapters:   {counts['NT']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
