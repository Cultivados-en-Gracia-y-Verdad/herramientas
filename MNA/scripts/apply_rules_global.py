from pathlib import Path
import json
import argparse

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="e.g. marcos")
    ap.add_argument("--tokens", required=True, help="path to <book>.tokens.jsonl")
    ap.add_argument("--rules-dir", default="MNA/datasets/rules")
    ap.add_argument("--overrides", default="", help="path to overrides jsonl (optional)")
    args = ap.parse_args()

    book = args.book
    book_jsonl = Path(args.tokens)
    rules_dir = Path(args.rules_dir)
    overrides_path = Path(args.overrides) if args.overrides else None

    lemma_defaults   = load(rules_dir / "grc_lemma_defaults.json")
    lemma_lexicon    = load(rules_dir / "grc_lemma_lexicon.json")
    article_by_morph = load(rules_dir / "grc_article_by_morph.json")
    autos_by_morph   = load(rules_dir / "grc_autos_by_morph.json")
    hos_by_morph     = load(rules_dir / "grc_hos_by_morph.json")
    eimi_by_morph    = load(rules_dir / "grc_eimi_by_morph.json")

    rows = read_jsonl(book_jsonl)

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

        ch = int(r["ch"]); vs = int(r["vs"]); tok = int(r["tok"])
        key = (ch, vs, tok)
        lemma = str(r.get("lemma", ""))
        morph = str(r.get("morph", ""))
        es = str(r.get("es", "?"))

        # overrides always win
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
        elif lemma == "ὅς" and morph in hos_by_morph:
            new_es = hos_by_morph[morph]
        elif lemma == "εἰμί" and morph in eimi_by_morph:
            new_es = eimi_by_morph[morph]

        if new_es is not None and new_es != "?":
            r["es"] = new_es
            changed += 1

        out.append(r)

    book_jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print("UPDATED TOKENS:", changed)

if __name__ == "__main__":
    main()
