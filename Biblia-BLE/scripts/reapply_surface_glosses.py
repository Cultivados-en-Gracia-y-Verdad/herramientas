#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads((ROOT / "MNA/datasets/rules/grc_surface_glosses.json").read_text(encoding="utf-8"))
SURFACE_RULES = {k.casefold(): v for k, v in RULES.items()}
TOKENS_DIR = ROOT / "MNA/datasets/interlinear/NT"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from testament_books import NT_BOOKS
from ble_gloss_text import normalize_greek_surface

def norm(s): return normalize_greek_surface(s)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("book", nargs="?"); p.add_argument("--all", action="store_true")
    args = p.parse_args()
    books = NT_BOOKS if args.all else ([args.book] if args.book else [])
    total = 0
    for book in books:
        path = TOKENS_DIR / f"{book}.tokens.jsonl"
        if not path.is_file(): continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        changed = 0
        for row in rows:
            entry = SURFACE_RULES.get(norm(row.get("surface","")).casefold())
            if not entry: continue
            new = entry.get(row.get("morph","")) or entry.get("default")
            if new and row.get("es") != new:
                row["es"] = new; changed += 1
        if changed:
            path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows)+"\n", encoding="utf-8")
            print(f"{book}: {changed}"); total += changed
    print(f"total: {total}")

if __name__ == "__main__": main()
