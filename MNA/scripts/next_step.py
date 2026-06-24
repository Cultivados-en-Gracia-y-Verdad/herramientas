from __future__ import annotations
from pathlib import Path
import json
import re
from collections import Counter, defaultdict
import argparse
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grc_inflect_es import inflect_from_lemma, is_nominal_morph

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def pas_from_morph(morph: str, pas_by_morph: dict) -> str | None:
    if morph in pas_by_morph:
        return pas_by_morph[morph]
    if len(morph) < 9 or morph[0] not in ("A", "V"):
        return None
    number, gender = morph[7], morph[8]
    if number == "S":
        return "toda" if gender == "F" else "todo"
    return "todas" if gender == "F" else "todos"


def clean_gloss_word(gloss: str) -> str:
    word = gloss.replace("·", " ").strip().split()[0] if gloss else ""
    return re.sub(r"[.,;:!?»«]+$", "", word).lower()


def guess_gender_from_gloss(gloss: str) -> str | None:
    word = clean_gloss_word(gloss)
    if not word:
        return None
    if word.endswith(("ción", "sión", "dad", "tad", "ez", "umbre", "ión")):
        return "f"
    if word.endswith("a") and not word.endswith("ma"):
        return "f"
    if word.endswith("o"):
        return "m"
    return None


def spanish_gender_for_token(row: dict, spanish_gender: dict) -> str | None:
    lemma = str(row.get("lemma", ""))
    gloss = str(row.get("es", ""))
    if gloss in ("", "?"):
        return None
    if lemma in spanish_gender:
        return spanish_gender[lemma]
    morph = str(row.get("morph", ""))
    if morph.startswith(("A", "N")):
        return guess_gender_from_gloss(gloss)
    return None


def morph_with_gender(morph: str, gender: str) -> str:
    letter = {"m": "M", "f": "F", "n": "N"}.get(gender, "M")
    if len(morph) >= 9:
        return morph[:8] + letter + morph[9:]
    return morph


def next_noun_gender(rows: list, index: int, spanish_gender: dict) -> str | None:
    for j in range(index + 1, min(index + 6, len(rows))):
        row = rows[j]
        if str(row.get("morph", "")).startswith("RA"):
            continue
        gender = spanish_gender_for_token(row, spanish_gender)
        if gender:
            return gender
    return None


def is_tis_negated(rows: list, index: int) -> bool:
    neg = frozenset({"μή", "οὐ", "οὐκ", "οὐχ", "οὐδέ", "οὐδείς", "μηδείς"})
    for j in range(index - 1, max(index - 5, -1), -1):
        prev = rows[j]
        if str(prev.get("lemma", "")) in neg:
            return True
        morph = str(prev.get("morph", ""))
        if morph.startswith(("C", "D", "X", "P")):
            continue
        break
    return False


def tis_indef_gloss(rows: list, index: int, morph: str, tis_table: dict, nadie_table: dict) -> str | None:
    table = nadie_table if is_tis_negated(rows, index) else tis_table
    return table.get(morph)


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
    lemma_defaults   = load(rules_dir / "grc_lemma_defaults.json")
    lemma_lexicon    = load(rules_dir / "grc_lemma_lexicon.json")
    article_by_morph = load(rules_dir / "grc_article_by_morph.json")
    autos_by_morph   = load(rules_dir / "grc_autos_by_morph.json")
    hos_by_morph     = load(rules_dir / "grc_hos_by_morph.json")
    eimi_by_morph    = load(rules_dir / "grc_eimi_by_morph.json")

    # Optional extended pronoun tables (if/when you create them)
    su_by_morph     = load(rules_dir / "grc_su_by_morph.json")
    ego_by_morph    = load(rules_dir / "grc_ego_by_morph.json")
    houtos_by_morph = load(rules_dir / "grc_houtos_by_morph.json")
    tis_indef_by_morph = load(rules_dir / "grc_tis_indef_by_morph.json")
    tis_nadie_by_morph = load(rules_dir / "grc_tis_indef_nadie_by_morph.json")
    pas_by_morph    = load(rules_dir / "grc_pas_by_morph.json")
    raw_gender      = load(rules_dir / "grc_spanish_noun_gender.json")
    spanish_gender  = {k: v for k, v in raw_gender.items() if not str(k).startswith("_")}

    rows = read_jsonl(tokens_path)

    overrides = {}
    if overrides_path and overrides_path.exists():
        for o in read_jsonl(overrides_path):
            overrides[(int(o["ch"]), int(o["vs"]), int(o["tok"]))] = str(o["es"])

    changed = 0
    out = []

    for i, r in enumerate(rows):
        if r.get("book") != book:
            out.append(r)
            continue

        ch = int(r["ch"]); vs = int(r["vs"]); tok = int(r["tok"])
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

        new_es = None
        # Pronouns: morphology before generic lexicon (ἐγώ is not always "yo").
        if lemma == "σύ" and morph in su_by_morph:
            new_es = su_by_morph[morph]
        elif lemma == "ἐγώ" and morph in ego_by_morph:
            new_es = ego_by_morph[morph]
        elif lemma == "πᾶς":
            new_es = pas_from_morph(morph, pas_by_morph)
        elif lemma == "τις":
            new_es = tis_indef_gloss(rows, i, morph, tis_indef_by_morph, tis_nadie_by_morph)
        elif lemma == "ὁ" and morph in article_by_morph:
            noun_gender = next_noun_gender(rows, i, spanish_gender)
            if noun_gender:
                new_es = article_by_morph.get(morph_with_gender(morph, noun_gender))
            if new_es is None:
                new_es = article_by_morph[morph]
        elif lemma == "αὐτός" and morph in autos_by_morph:
            new_es = autos_by_morph[morph]
        elif lemma == "οὗτος" and morph in houtos_by_morph:
            new_es = houtos_by_morph[morph]
        elif lemma == "ὅς" and morph in hos_by_morph:
            new_es = hos_by_morph[morph]
        elif lemma == "εἰμί" and morph in eimi_by_morph:
            new_es = eimi_by_morph[morph]
        elif es == "?":
            if lemma in lemma_defaults:
                new_es = lemma_defaults[lemma]
            elif lemma in lemma_lexicon:
                new_es = lemma_lexicon[lemma]

        if new_es is None and is_nominal_morph(morph):
            base = lemma_lexicon.get(lemma) or lemma_defaults.get(lemma)
            if base and not str(base).startswith("__FILL_"):
                new_es = inflect_from_lemma(lemma, str(base), morph)

        if new_es is not None and new_es != "?" and r.get("es") != new_es:
            r["es"] = new_es
            changed += 1

        out.append(r)

    for i, r in enumerate(out):
        if r.get("book") != book:
            continue
        lemma = str(r.get("lemma", ""))
        morph = str(r.get("morph", ""))
        if lemma == "τις":
            new_es = tis_indef_gloss(out, i, morph, tis_indef_by_morph, tis_nadie_by_morph)
            if new_es and r.get("es") != new_es:
                r["es"] = new_es
                changed += 1
            continue
        if lemma != "ὁ" or morph not in article_by_morph:
            continue
        noun_gender = next_noun_gender(out, i, spanish_gender)
        if not noun_gender:
            continue
        new_es = article_by_morph.get(morph_with_gender(morph, noun_gender))
        if new_es and r.get("es") != new_es:
            r["es"] = new_es
            changed += 1

    for r in out:
        if r.get("book") != book:
            continue
        lemma = str(r.get("lemma", ""))
        morph = str(r.get("morph", ""))
        if not is_nominal_morph(morph):
            continue
        base = lemma_lexicon.get(lemma) or lemma_defaults.get(lemma)
        if not base or str(base).startswith("__FILL_"):
            continue
        new_es = inflect_from_lemma(lemma, str(base), morph)
        if new_es and r.get("es") != new_es:
            r["es"] = new_es
            changed += 1

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
    tokens_path = Path(args.tokens) if args.tokens else Path(f"MNA/datasets/interlinear/NT/{book}.tokens.jsonl")
    rules_dir = Path(args.rules_dir)
    overrides_path = Path(args.overrides) if args.overrides else Path(f"MNA/datasets/interlinear/NT/_overrides/{book}.overrides.jsonl")

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
