from __future__ import annotations
from pathlib import Path
import json
from collections import Counter, defaultdict
import argparse
import subprocess
import sys

# Allow importing sibling helpers when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hbo_enrich_gloss import enrich_gloss  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def read_jsonl(path: Path):
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            raise SystemExit(f"{path}:{i}: invalid JSON: {e}")
    return rows

def apply_rules(
    book: str,
    tokens_path: Path,
    rules_dir: Path,
    overrides_path: Path | None,
    *,
    force: bool = False,
):
    lemma_defaults   = load(rules_dir / "hbo_lemma_defaults.json")
    lemma_lexicon    = load(rules_dir / "hbo_lemma_lexicon.json")

    rows = read_jsonl(tokens_path)

    overrides = {}
    if overrides_path and overrides_path.exists():
        for o in read_jsonl(overrides_path):
            overrides[(int(o["ch"]), int(o["vs"]), int(o["tok"]))] = str(o["es"])

    changed = 0
    out = []
    prev_es_for_book: str | None = None

    for r in rows:
        if r.get("book") != book:
            out.append(r)
            continue

        ch = int(r["ch"]); vs = int(r["vs"]); tok = int(r.get("tok", r.get("w")))
        key = (ch, vs, tok)
        lemma = str(r.get("lemma", ""))
        morph = str(r.get("morph", ""))
        es = str(r.get("es", "?"))

        if key in overrides:
            new_es = overrides[key]
            if es != new_es:
                r["es"] = new_es
                changed += 1
            prev_es_for_book = str(r.get("es", ""))
            out.append(r)
            continue

        # Default fill only unresolved glosses; --force re-applies lexicon to every token.
        if es != "?" and not force:
            enriched = enrich_gloss(es, morph, lemma=lemma, prev_es=prev_es_for_book)
            if enriched != es:
                r["es"] = enriched
                changed += 1
            prev_es_for_book = str(r.get("es", ""))
            out.append(r)
            continue

        new_es = None
        if lemma in lemma_defaults:
            new_es = lemma_defaults[lemma]
        elif lemma in lemma_lexicon:
            new_es = lemma_lexicon[lemma]

        if new_es is None or new_es == "?":
            new_es = es

        new_es = enrich_gloss(new_es, morph, lemma=lemma, prev_es=prev_es_for_book)
        if new_es != "?" and new_es != es:
            r["es"] = new_es
            changed += 1

        prev_es_for_book = str(r.get("es", ""))
        out.append(r)

    tokens_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    return changed, out

def audit(book: str, rows, top_n: int):
    rem_by_ch = defaultdict(int)
    lemma_counts = Counter()
    total = 0
    for r in rows:
        if r.get("book") != book:
            continue
        if r.get("es") == "?":
            total += 1
            rem_by_ch[int(r["ch"])] += 1
            lemma_counts[r.get("lemma","")] += 1
    return total, rem_by_ch, lemma_counts.most_common(top_n)

def morph_breakdown(book: str, rows, lemma: str, limit: int = 20):
    c = Counter()
    total = 0
    for r in rows:
        if r.get("book")==book and r.get("es")=="?" and r.get("lemma")==lemma:
            total += 1
            c[r.get("morph","")] += 1
    return total, c.most_common(limit)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", help="e.g. genesis (required unless --all)")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--tokens", default="", help="override tokens jsonl path")
    ap.add_argument("--rules-dir", default="MNA/datasets/rules")
    ap.add_argument("--overrides", default="", help="override overrides jsonl path")
    ap.add_argument(
        "--force",
        action="store_true",
        help="re-apply lexicon/defaults to tokens even when es is already set",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="process every OT book under MNA/datasets/interlinear/OT/",
    )
    args = ap.parse_args()

    if not args.all and not args.book:
        ap.error("provide --book or --all")
    if args.all and args.tokens:
        ap.error("--tokens cannot be combined with --all")

    rules_dir = Path(args.rules_dir)
    ot_dir = Path("MNA/datasets/interlinear/OT")

    if args.all:
        books = sorted(p.name.replace(".tokens.jsonl", "") for p in ot_dir.glob("*.tokens.jsonl"))
        if not books:
            raise SystemExit(f"no OT token files in {ot_dir}")
    else:
        books = [args.book]

    total_changed = 0
    last_out = []
    for book in books:
        tokens_path = Path(args.tokens) if args.tokens else ot_dir / f"{book}.tokens.jsonl"
        overrides_path = (
            Path(args.overrides)
            if args.overrides
            else ot_dir / "_overrides" / f"{book}.overrides.jsonl"
        )
        changed, last_out = apply_rules(
            book, tokens_path, rules_dir, overrides_path, force=args.force
        )
        total_changed += changed
        print(f"{book}: UPDATED TOKENS: {changed}")

    if args.all:
        print("TOTAL UPDATED TOKENS:", total_changed)
        return

    book = books[0]
    print("UPDATED TOKENS:", total_changed)

    total, rem_by_ch, top = audit(book, last_out, args.top)
    print("TOTAL remaining '?':", total)
    for ch in sorted(rem_by_ch):
        print(f"CH {ch:02d}: remaining '?' = {rem_by_ch[ch]}")

    print(f"TOP {args.top} lemmas still ?:")
    for n, lemma in top:
        print(f"{n}\t{lemma}")

    if total == 0:
        print("\nNEXT ACTION: Done — book has 0 remaining '?'.")
    else:
        print(
            "\nNEXT ACTION: "
            "python3 MNA/scripts/ot_lemma_batch.py "
            f"--book {book} --apply-auto --all-remaining-auto --commit"
            "  (or --propose / --apply-json for manual/AI glosses)"
        )

if __name__ == "__main__":
    main()
