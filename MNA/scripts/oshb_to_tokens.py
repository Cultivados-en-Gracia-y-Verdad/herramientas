#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Convert OSHB morphhb/wlc XML files into OT interlinear token JSONL files.

Examples:
  python3 MNA/scripts/oshb_to_tokens.py --osis Exod --book exodo
  python3 MNA/scripts/oshb_to_tokens.py --all
  python3 MNA/scripts/oshb_to_tokens.py --all --overwrite

Input default:
  MNA/SOURCES/OSHB/morphhb/wlc/<OSIS>.xml

Output default:
  MNA/datasets/interlinear/OT/<book>.tokens.jsonl

Each output row contains:
  book, ref_book, ch, vs, w, surface, lemma, morph, id, es
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

BOOKS: List[Tuple[str, str]] = [
    ("Exod", "exodo"),
    ("Lev", "levitico"),
    ("Num", "numeros"),
    ("Deut", "deuteronomio"),
    ("Josh", "josue"),
    ("Judg", "jueces"),
    ("Ruth", "rut"),
    ("1Sam", "1samuel"),
    ("2Sam", "2samuel"),
    ("1Kgs", "1reyes"),
    ("2Kgs", "2reyes"),
    ("1Chr", "1cronicas"),
    ("2Chr", "2cronicas"),
    ("Ezra", "esdras"),
    ("Neh", "nehemias"),
    ("Esth", "ester"),
    ("Job", "job"),
    ("Ps", "salmos"),
    ("Prov", "proverbios"),
    ("Eccl", "eclesiastes"),
    ("Song", "cantares"),
    ("Isa", "isaias"),
    ("Jer", "jeremias"),
    ("Lam", "lamentaciones"),
    ("Ezek", "ezequiel"),
    ("Dan", "daniel"),
    ("Hos", "oseas"),
    ("Joel", "joel"),
    ("Amos", "amos"),
    ("Obad", "abdias"),
    ("Jonah", "jonas"),
    ("Mic", "miqueas"),
    ("Nah", "nahum"),
    ("Hab", "habacuc"),
    ("Zeph", "sofonias"),
    ("Hag", "hageo"),
    ("Zech", "zacarias"),
    ("Mal", "malaquias"),
]

OSIS_TO_SLUG: Dict[str, str] = dict(BOOKS)


def local_name(tag: str) -> str:
    """Strip XML namespace from a tag."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def text_content(elem: ET.Element) -> str:
    """Return all text inside an element, normalized but preserving internal Hebrew/slash chars."""
    return "".join(elem.itertext()).strip()


def parse_osis_ref(osis_id: str) -> Optional[Tuple[str, int, int]]:
    """Parse Gen.1.1 / Exod.3.14 style OSIS verse IDs."""
    if not osis_id:
        return None
    first = osis_id.split()[0]  # handle possible ranges/extra IDs safely
    parts = first.split(".")
    if len(parts) < 3:
        return None
    book = parts[0]
    try:
        ch = int(parts[1])
        vs = int(re.match(r"\d+", parts[2]).group(0))
    except Exception:
        return None
    return book, ch, vs


def convert_file(src: Path, out: Path, book_slug: str, fallback_ref_book: str, overwrite: bool = False) -> int:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if out.exists() and not overwrite:
        raise FileExistsError(f"Output exists, use --overwrite: {out}")

    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    current_book = fallback_ref_book
    current_ch = None
    current_vs = None
    w_index = 0

    # Full parse is fine for WLC book files and is simpler/safer for nested verse content.
    tree = ET.parse(src)
    root = tree.getroot()

    for elem in root.iter():
        name = local_name(elem.tag)

        if name == "div" and elem.attrib.get("type") == "book":
            current_book = elem.attrib.get("osisID", fallback_ref_book)

        elif name == "verse":
            parsed = parse_osis_ref(elem.attrib.get("osisID", ""))
            if parsed:
                ref_book, current_ch, current_vs = parsed
                current_book = ref_book
                w_index = 0

            # Iterate only direct/nested word elements inside this verse, in order.
            for w_elem in elem.iter():
                if local_name(w_elem.tag) != "w":
                    continue
                surface = text_content(w_elem)
                if not surface:
                    continue
                w_index += 1
                rows.append({
                    "book": book_slug,
                    "ref_book": current_book,
                    "ch": current_ch,
                    "vs": current_vs,
                    "w": w_index,
                    "surface": surface,
                    "lemma": w_elem.attrib.get("lemma", ""),
                    "morph": w_elem.attrib.get("morph", ""),
                    "id": w_elem.attrib.get("id", ""),
                    "es": "?",
                })

    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(rows)


def resolve_source(wlc_dir: Path, osis: str) -> Path:
    """Resolve a source XML path for an OSIS book ID."""
    candidates = [
        wlc_dir / f"{osis}.xml",
        wlc_dir / f"{osis.lower()}.xml",
        wlc_dir / f"{osis.upper()}.xml",
    ]
    for p in candidates:
        if p.exists():
            return p

    # Fallback: case-insensitive scan.
    for p in wlc_dir.glob("*.xml"):
        if p.stem.lower() == osis.lower():
            return p

    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osis", help="OSIS book ID, e.g. Exod")
    ap.add_argument("--book", help="Output book slug, e.g. exodo")
    ap.add_argument("--all", action="store_true", help="Generate all OT books after Genesis")
    ap.add_argument("--wlc-dir", default="MNA/SOURCES/OSHB/morphhb/wlc", help="Directory containing OSHB WLC XML files")
    ap.add_argument("--out-dir", default="MNA/datasets/interlinear/OT", help="Output directory for tokens JSONL")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing output token files")
    args = ap.parse_args()

    wlc_dir = Path(args.wlc_dir)
    out_dir = Path(args.out_dir)

    if args.all:
        jobs = BOOKS
    else:
        if not args.osis:
            raise SystemExit("Provide --osis Exod, or use --all")
        slug = args.book or OSIS_TO_SLUG.get(args.osis)
        if not slug:
            raise SystemExit(f"No slug known for {args.osis}; provide --book")
        jobs = [(args.osis, slug)]

    total = 0
    for osis, slug in jobs:
        src = resolve_source(wlc_dir, osis)
        out = out_dir / f"{slug}.tokens.jsonl"
        try:
            n = convert_file(src, out, slug, osis, overwrite=args.overwrite)
        except FileExistsError as e:
            print(f"SKIP {osis} -> {out}: {e}")
            continue
        print(f"WROTE {out} from {src} rows={n}")
        total += n

    print(f"DONE rows={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
