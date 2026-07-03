#!/usr/bin/env python3
"""Compare one Hebrew lemma across MNA OT tokens, CGV lexicon, and AHRC."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPARE = ROOT / "data" / "index" / "lemma-compare.jsonl"

from strongs import normalize_hebrew_strongs, strongs_from_mna_lemma  # noqa: E402


def load_compare() -> dict[str, dict]:
    if not COMPARE.is_file():
        return {}
    return {
        json.loads(line)["strongs"]: json.loads(line)
        for line in COMPARE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def resolve_strongs(value: str, index: dict[str, dict]) -> str | None:
    norm = normalize_hebrew_strongs(value) or strongs_from_mna_lemma(value)
    if norm and norm in index:
        return norm
    if norm:
        return norm
    return None


def print_entry(entry: dict) -> None:
    strongs = entry["strongs"]
    print(f"=== {strongs} ===")

    mna = entry.get("mna")
    if mna:
        print("\n[MNA OT]")
        print(f"  tokens: {mna['token_count']} in {', '.join(mna['books'])}")
        print(f"  lemma keys: {', '.join(mna['mna_lemma_keys'])}")
        if mna.get("surfaces"):
            print(f"  Hebrew: {', '.join(mna['surfaces'][:6])}")
        if mna.get("lexicon_glosses"):
            print(f"  CGV lexicon: {', '.join(mna['lexicon_glosses'])}")
        if mna.get("gloss_es"):
            print(f"  token glosses: {', '.join(mna['gloss_es'][:8])}")
        print("  samples:")
        for s in mna.get("samples", [])[:5]:
            print(f"    {s['ref']}: {s.get('surface', '')} → {s.get('es', '')}")
    else:
        print("\n[MNA OT] not in current OT token files")

    ahrc = entry.get("ahrc") or []
    if ahrc:
        print("\n[AHRC]")
        for row in ahrc:
            print(f"  {row.get('hebrew', '')} ({row.get('transliteration', '')})")
            print(f"    translation: {row.get('translation', '')}")
            if row.get("definition"):
                print(f"    definition: {row['definition']}")
            if row.get("parent_root"):
                gloss = row.get("parent_root_gloss") or ""
                print(f"    parent root {row['parent_root']}: {gloss}".rstrip(": "))
            if row.get("kjv"):
                print(f"    KJV: {row['kjv']}")
            print(f"    source: https://www.ancient-hebrew.org/{row.get('source', '')}")
    else:
        print("\n[AHRC] not indexed — import AHLB page with parse_ahlb_html.py")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lemma-to-lemma compare (OT + AHRC).")
    parser.add_argument("query", nargs="?", help="Strong's (H430), MNA lemma (430), or Hebrew")
    parser.add_argument("--list", action="store_true", help="List indexed lemmas")
    parser.add_argument("--linked-only", action="store_true", help="With --list, show OT+AHRC only")
    parser.add_argument("--book", help="With --list, filter by OT book slug")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    index = load_compare()
    if not index:
        print("No compare index. Run:", file=sys.stderr)
        print("  python3 scripts/build_ot_lemma_index.py", file=sys.stderr)
        print("  python3 scripts/parse_ahlb_html.py ...", file=sys.stderr)
        print("  python3 scripts/build_lemma_compare.py", file=sys.stderr)
        return 1

    if args.list:
        rows = sorted(index.values(), key=lambda r: int(r["strongs"][1:]))
        if args.linked_only:
            rows = [r for r in rows if r.get("in_ot") and r.get("in_ahrc")]
        if args.book:
            book = args.book.lower()
            rows = [
                r for r in rows
                if r.get("mna") and book in r["mna"].get("books", [])
            ]
        for row in rows[: args.limit]:
            mna = row.get("mna") or {}
            gloss = ", ".join((mna.get("lexicon_glosses") or mna.get("gloss_es") or [])[:2])
            ahrc = (row.get("ahrc") or [{}])[0].get("translation", "")
            flag = "●" if row.get("in_ot") and row.get("in_ahrc") else "○"
            print(f"{flag} {row['strongs']:6}  CGV: {gloss[:28]:28}  AHRC: {str(ahrc)[:24]}")
        return 0

    if not args.query:
        parser.error("provide query or --list")

    strongs = resolve_strongs(args.query, index)
    if not strongs:
        print(f"No match for {args.query!r}", file=sys.stderr)
        return 1

    entry = index.get(strongs)
    if not entry:
        entry = {"strongs": strongs, "mna": None, "ahrc": []}
    print_entry(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
