#!/usr/bin/env python3
"""Bootstrap a fresh OT book from the repository's OSHB/WLC XML.

This script creates source/working artifacts only. It never translates, aligns,
verifies, approves, or publishes anything.

Usage:
    python3 scripts/bootstrap_oshb_book.py zechariah
    python3 scripts/bootstrap_oshb_book.py zechariah --dry-run

The output contract matches the existing Translator OSHB layout:
    translations/oshb-spine/<book>/<book>-oshb-spine.json
    translations/oshb-spine/<book>/<book>-phrases.json

Fresh phrases have blank Spanish and suggestionSource="blank". OSHB lexical or
interlinear glosses are evidence only and are never promoted into LBF Spanish.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


BOOKS = {
    "daniel": {
        "label": "Daniel",
        "osis": "Dan",
        "xml": "Dan.xml",
        "book_code": 27,
        "ble_slug": "daniel",
    },
    "zechariah": {
        "label": "Zechariah",
        "osis": "Zech",
        "xml": "Zech.xml",
        "book_code": 38,
        "ble_slug": "zacarias",
    },
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def strongs_from_lemma(lemma: str) -> str:
    match = re.search(r"(\d{3,5})", lemma or "")
    return f"H{match.group(1)}" if match else ""


def language_from_morph(morph: str) -> str:
    return "arc" if str(morph or "").startswith("A") else "he"


def source_token_id(book_code: int, chapter: int, verse: int, position: int) -> str:
    # Keep source identity on MT/OSHB coordinates even when the working LBF
    # reference is remapped to Protestant/KJV numbering.
    return f"h{book_code:02d}{chapter:03d}{verse:03d}{position:03d}"


def parse_reference(text: str, expected_osis: str) -> tuple[int, int] | None:
    match = re.fullmatch(rf"{re.escape(expected_osis)}\.(\d+)\.(\d+)", text.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def mapped_reference(verse: ET.Element, osis: str, mt_chapter: int, mt_verse: int) -> tuple[int, int]:
    """Return Protestant/KJV coordinates when OSHB explicitly supplies them."""
    for child in list(verse):
        if local_name(child.tag) != "note":
            continue
        note_text = "".join(child.itertext()).strip()
        match = re.search(rf"\bKJV:{re.escape(osis)}\.(\d+)\.(\d+)\b", note_text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return mt_chapter, mt_verse


def direct_words(verse: ET.Element) -> list[ET.Element]:
    # Declared OT snapshot rule (WORKFLOW §6): only direct <w> children.
    # Nested qere lives in variant notes and is not a second source.
    return [child for child in list(verse) if local_name(child.tag) == "w"]


def load_optional_glosses(root: Path, book: dict) -> dict[str, str]:
    """Load token glosses if an existing CGV OT interlinear is available.

    Missing gloss data is normal for a fresh book. A gloss is display/evidence
    data only and never becomes phrase.spanish.
    """
    candidates = [
        root.parent / "cgv-data" / "interlinears" / "OT" / f"{book['ble_slug']}.tokens.jsonl",
        root.parent / "cgv-data" / "datasets" / "interlinear" / "OT" / f"{book['ble_slug']}.tokens.jsonl",
        root.parent / "MNA" / "datasets" / "interlinear" / "OT" / f"{book['ble_slug']}.tokens.jsonl",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return {}

    glosses: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        token_id = str(
            row.get("sourceTokenId")
            or row.get("source_token_id")
            or row.get("id")
            or ""
        )
        gloss = str(row.get("es") or row.get("gloss") or "")
        if token_id and gloss:
            glosses[token_id] = gloss
    return glosses


def build_documents(root: Path, book_id: str) -> tuple[dict, dict]:
    if book_id not in BOOKS:
        raise SystemExit(f"Unsupported OSHB bootstrap book: {book_id}")
    book = BOOKS[book_id]
    xml_path = root.parent / "MNA" / "SOURCES" / "OSHB" / "morphhb" / "wlc" / book["xml"]
    if not xml_path.is_file():
        raise SystemExit(f"OSHB source missing: {xml_path}")

    tree = ET.parse(xml_path)
    document_root = tree.getroot()
    glosses = load_optional_glosses(root, book)

    verses: dict[str, dict] = {}
    phrases: list[dict] = []
    total_tokens = 0
    hebrew_tokens = 0
    aramaic_tokens = 0

    for verse in document_root.iter():
        if local_name(verse.tag) != "verse":
            continue
        parsed = parse_reference(str(verse.get("osisID") or ""), book["osis"])
        if parsed is None:
            continue
        mt_chapter, mt_verse = parsed
        chapter, verse_number = mapped_reference(verse, book["osis"], mt_chapter, mt_verse)

        tokens: list[dict] = []
        token_rows: list[dict] = []
        for position, word in enumerate(direct_words(verse), start=1):
            surface = "".join(word.itertext()).strip()
            lemma = str(word.get("lemma") or "")
            morph = str(word.get("morph") or "")
            lang = language_from_morph(morph)
            token_id = source_token_id(book["book_code"], mt_chapter, mt_verse, position)
            oshb_id = str(word.get("id") or "")
            gloss = glosses.get(token_id, "") or glosses.get(oshb_id, "")

            token = {
                "sourceTokenId": token_id,
                "w": position,
                "oshbIndex": position,
                "surface": surface,
                "lemma": lemma,
                "morph": morph,
                "lang": lang,
                "oshbId": oshb_id,
                "es": gloss,
            }
            tokens.append(token)
            token_rows.append({
                "sourceTokenId": token_id,
                "greek": surface,
                "surface": surface,
                "lemma": lemma,
                "strongs": strongs_from_lemma(lemma),
                "rmac": morph,
                "morphology": "Aramaic" if lang == "arc" else "Hebrew",
                "ble": gloss,
                "rv1909": "",
                "lang": lang,
                "w": position,
                "oshbIndex": position,
                "oshbId": oshb_id,
            })
            total_tokens += 1
            if lang == "arc":
                aramaic_tokens += 1
            else:
                hebrew_tokens += 1

        if not tokens:
            continue

        mt_cv = f"{mt_chapter}:{mt_verse}"
        reference = f"{book['label']} {chapter}:{verse_number}"
        mt_reference = f"{book['label']} {mt_chapter}:{mt_verse}"
        source_ids = [token["sourceTokenId"] for token in tokens]
        source_text = " ".join(token["surface"] for token in tokens if token["surface"]).strip()
        gloss_text = " ".join(token["es"] for token in tokens if token["es"]).strip()

        verses[mt_cv] = {
            "ch": mt_chapter,
            "vs": mt_verse,
            "tokens": tokens,
        }
        phrases.append({
            "reference": reference,
            "mtReference": mt_reference,
            "phraseIndex": len(phrases),
            "greek": source_text,
            "spanish": "",
            "sourceTokenIds": source_ids,
            "tokenRows": token_rows,
            "bleText": gloss_text,
            "suggestionSource": "blank",
            "chapter": chapter,
            "verse": verse_number,
            "mtChapter": mt_chapter,
            "mtVerse": mt_verse,
            "textualBasis": "OSHB/WLC",
        })

    if not phrases:
        raise SystemExit(f"No verses parsed from {xml_path}")

    seen_refs: set[str] = set()
    duplicate_refs: list[str] = []
    for phrase in phrases:
        ref = phrase["reference"]
        if ref in seen_refs:
            duplicate_refs.append(ref)
        seen_refs.add(ref)
    if duplicate_refs:
        raise SystemExit(f"Mapped Protestant references are not unique: {duplicate_refs[:5]}")

    spine_doc = {
        "bookId": book_id,
        "textualBasis": "OSHB/WLC",
        "schemaVersion": 1,
        "sourceTokenIdScheme": f"h{book['book_code']:02d}{{ch:03}}{{vs:03}}{{w:03}}",
        "notes": {
            "spine": (
                f"OSHB word stream from MNA/SOURCES/OSHB/morphhb/wlc/{book['xml']}. "
                "Source token IDs use MT coordinates; explicit OSHB KJV notes map working LBF references."
            )
        },
        "stats": {
            "verses": len(phrases),
            "tokens": total_tokens,
            "hebrew": hebrew_tokens,
            "aramaic": aramaic_tokens,
        },
        "verses": verses,
    }
    phrase_doc = {
        "bookId": book_id,
        "textualBasis": "OSHB/WLC",
        "schemaVersion": 1,
        "scope": "full book (Protestant refs; MT source coordinates retained)",
        "verseNumbering": "Protestant working references with MT source identity",
        "phrases": phrases,
    }
    return spine_doc, phrase_doc


def write_new(path: Path, document: dict) -> None:
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a fresh Translator OT book from OSHB/WLC")
    parser.add_argument("book", choices=sorted(BOOKS))
    parser.add_argument("--dry-run", action="store_true", help="parse and validate without writing files")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    spine_doc, phrase_doc = build_documents(root, args.book)
    out_dir = root / "translations" / "oshb-spine" / args.book
    spine_path = out_dir / f"{args.book}-oshb-spine.json"
    phrase_path = out_dir / f"{args.book}-phrases.json"

    print(
        f"{args.book}: {spine_doc['stats']['verses']} verses, "
        f"{spine_doc['stats']['tokens']} source tokens "
        f"({spine_doc['stats']['hebrew']} Hebrew, {spine_doc['stats']['aramaic']} Aramaic)"
    )
    print(f"fresh phrases: {len(phrase_doc['phrases'])}; approved: 0")

    if args.dry_run:
        print("DRY RUN: no files written")
        return 0

    write_new(spine_path, spine_doc)
    try:
        write_new(phrase_path, phrase_doc)
    except Exception:
        # Avoid leaving half a bootstrap behind if the second write cannot complete.
        if spine_path.exists():
            spine_path.unlink()
        raise

    print(spine_path)
    print(phrase_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
