from __future__ import annotations
from pathlib import Path
import json
from collections import Counter, defaultdict
import argparse
import subprocess

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

def apply_rules(book: str, tokens_path: Path, rules_dir: Path, overrides_path: Path | None):
    lemma_defaults   = load(rules_dir / "hbo_lemma_defaults.json")
    lemma_lexicon    = load(rules_dir / "hbo_lemma_lexicon.json")

    rows = read_jsonl(tokens_path)

    overrides = {}
    if overrides_path and overrides_path.exists():
        for o in read_jsonl(overrides_path):
            overrides[(int(o["ch"]), int(o["vs"]), int(o["tok"]))] = str(o["es"])

    changed = 0
    out = []

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
            out.append(r)
            continue

        if es != "?":
            out.append(r)
            continue

        new_es = None
        if lemma in lemma_defaults:
            new_es = lemma_defaults[lemma]
        elif lemma in lemma_lexicon:
            new_es = lemma_lexicon[lemma]
        elif lemma == "ὁ" and morph in article_by_morph:
            new_es = article_by_morph[morph]
        elif lemma == "αὐτός" and morph in autos_by_morph:
            new_es = autos_by_morph[morph]
        elif lemma == "σύ" and morph in su_by_morph:
            new_es = su_by_morph[morph]
        elif lemma == "ἐγώ" and morph in ego_by_morph:
            new_es = ego_by_morph[morph]
        elif lemma == "οὗτος" and morph in houtos_by_morph:
            new_es = houtos_by_morph[morph]
        elif lemma == "τίς" and morph in tis_by_morph:
            new_es = tis_by_morph[morph]
        elif lemma == "ὅς" and morph in hos_by_morph:
            new_es = hos_by_morph[morph]
        elif lemma == "εἰμί" and morph in eimi_by_morph:
            new_es = eimi_by_morph[morph]

        if new_es is not None and new_es != "?":
            r["es"] = new_es
            changed += 1

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
    ap.add_argument("--book", required=True, help="e.g. lucas")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--tokens", default="", help="override tokens jsonl path")
    ap.add_argument("--rules-dir", default="MNA/datasets/rules")
    ap.add_argument("--overrides", default="", help="override overrides jsonl path")
    args = ap.parse_args()

    book = args.book
    tokens_path = Path(args.tokens) if args.tokens else Path(f"MNA/datasets/interlinear/OT/{book}.tokens.jsonl")
    rules_dir = Path(args.rules_dir)
    overrides_path = Path(args.overrides) if args.overrides else Path(f"MNA/datasets/interlinear/OT/_overrides/{book}.overrides.jsonl")

    changed, out = apply_rules(book, tokens_path, rules_dir, overrides_path)
    print("UPDATED TOKENS:", changed)

    total, rem_by_ch, top = audit(book, out, args.top)
    print("TOTAL remaining '?':", total)
    for ch in sorted(rem_by_ch):
        print(f"CH {ch:02d}: remaining '?' = {rem_by_ch[ch]}")

    print(f"TOP {args.top} lemmas still ?:")
    for n, lemma in top:
        print(f"{n}\t{lemma}")

    # If any big function/pronoun lemmas still exist, show morph breakdown automatically
    watch = ["ὁ","αὐτός","σύ","ἐγώ","οὗτος","τίς","ὅς","εἰμί"]
    top_lemmas = {lemma for _, lemma in top}
    for lemma in watch:
        if lemma in top_lemmas:
            t, br = morph_breakdown(book, out, lemma, limit=25)
            print(f"\nMORPH BREAKDOWN: lemma {lemma!r} (unfilled={t})")
            for n, m in br:
                print(f"{n}\t{m}")

    # Hint
    if total == 0:
        print("\nNEXT ACTION: Done — book has 0 remaining '?'.")
    else:
        print("\nNEXT ACTION: If a MORPH BREAKDOWN is shown above, patch the corresponding grc_*_by_morph.json; otherwise add the TOP lemmas to grc_lemma_lexicon.json and rerun this command.")

if __name__ == "__main__":
    main()
