from __future__ import annotations
from pathlib import Path
import json, re
from collections import defaultdict
import argparse

def parse_ref(ref: str):
    # MorphGNT uses BBCCVV
    if not re.fullmatch(r"\d{6}", ref):
        raise ValueError(f"Bad ref: {ref!r}")
    bb = int(ref[0:2])
    ch = int(ref[2:4])
    vs = int(ref[4:6])
    return bb, ch, vs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="e.g. marcos, lucas")
    ap.add_argument("--src", required=True, help="MorphGNT file path, e.g. MNA/SOURCES/MorphGNT/63-Lk-morphgnt.txt")
    ap.add_argument("--out", default="", help="Output tokens jsonl path (optional)")
    args = ap.parse_args()

    book = args.book
    src = Path(args.src)
    out = Path(args.out) if args.out else Path(f"MNA/datasets/interlinear/NT/{book}.tokens.jsonl")

    lines = [ln for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]
    by_verse = defaultdict(list)

    for i, ln in enumerate(lines, start=1):
        parts = ln.split()
        if len(parts) != 7:
            raise SystemExit(f"{src}:{i}: expected 7 fields, got {len(parts)}: {ln!r}")

        ref = parts[0]
        _, ch, vs = parse_ref(ref)

        pos = parts[1]
        morph_tail = parts[2]
        morph = f"{pos}{morph_tail}"

        surface = parts[3]   # keep punctuation/markers
        lemma = parts[6]     # TRUE lemma

        by_verse[(ch, vs)].append((surface, lemma, morph))

    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for (ch, vs) in sorted(by_verse.keys()):
        for tok_i, (surface, lemma, morph) in enumerate(by_verse[(ch, vs)], start=1):
            rows.append({
                "book": book,
                "ch": ch,
                "vs": vs,
                "tok": tok_i,
                "surface": surface,
                "lemma": lemma,
                "morph": morph,
                "es": "?"
            })

    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print("WROTE", out, "rows", len(rows), "max_ch", max(r["ch"] for r in rows))

if __name__ == "__main__":
    main()
