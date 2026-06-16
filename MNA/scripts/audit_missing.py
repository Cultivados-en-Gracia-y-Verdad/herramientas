from __future__ import annotations
from pathlib import Path
import json
from collections import Counter, defaultdict
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="e.g. marcos, lucas")
    ap.add_argument("--tokens", default="", help="tokens jsonl path (optional)")
    ap.add_argument("--top", type=int, default=30, help="top N lemmas")
    ap.add_argument("--chapter", type=int, default=0, help="if set, audit only this chapter")
    ap.add_argument("--lemma", default="", help="if set, show morph breakdown for this lemma where es=='?'")
    args = ap.parse_args()

    book = args.book
    tokens = Path(args.tokens) if args.tokens else Path(f"MNA/datasets/interlinear/NT/{book}.tokens.jsonl")

    rem = defaultdict(int)
    top = Counter()
    morph = Counter()
    total = 0

    for line in tokens.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("book") != book:
            continue
        if r.get("es") != "?":
            continue

        ch = int(r["ch"])
        if args.chapter and ch != args.chapter:
            continue

        total += 1
        rem[ch] += 1
        top[r.get("lemma","")] += 1

        if args.lemma and r.get("lemma","") == args.lemma:
            morph[r.get("morph","")] += 1

    print("TOKENS:", tokens)
    if args.chapter:
        print(f"CH {args.chapter:02d}: remaining '?' = {total}")
    else:
        for ch in sorted(rem):
            print(f"CH {ch:02d}: remaining '?' = {rem[ch]}")
        print("TOTAL remaining '?':", total)

    print(f"TOP {args.top} lemmas still ?:")
    for lemma, n in top.most_common(args.top):
        print(f"{n}\t{lemma}")

    if args.lemma:
        print(f"\nMorph breakdown for lemma {args.lemma!r}:")
        for m, n in morph.most_common(60):
            print(f"{n}\t{m}")

if __name__ == "__main__":
    main()
