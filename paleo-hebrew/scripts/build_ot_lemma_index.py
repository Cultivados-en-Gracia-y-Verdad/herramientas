#!/usr/bin/env python3
"""Build OT lemma index from MNA token JSONL, keyed by Strong's H-number."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TOKENS_DIR = REPO / "MNA" / "datasets" / "interlinear" / "OT"
RULES = REPO / "MNA" / "datasets" / "rules"
OUT = ROOT / "data" / "index" / "ot-lemmas.jsonl"

from hebrew_text import strip_niqqud  # noqa: E402
from strongs import strongs_from_mna_lemma  # noqa: E402


def load_lexicon() -> dict[str, str]:
    path = RULES / "hbo_lemma_lexicon.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Index OT tokens by Strong's number.")
    parser.add_argument("--tokens-dir", type=Path, default=TOKENS_DIR)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()

    lexicon = load_lexicon()
    by_strongs: dict[str, dict] = {}

    for path in sorted(args.tokens_dir.glob("*.tokens.jsonl")):
        book = path.stem.replace(".tokens", "")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            lemma_key = str(row.get("lemma", ""))
            strongs = strongs_from_mna_lemma(lemma_key)
            if not strongs:
                continue

            entry = by_strongs.setdefault(strongs, {
                "strongs": strongs,
                "mna_lemma_keys": set(),
                "gloss_es": set(),
                "lexicon_glosses": set(),
                "surfaces": set(),
                "books": set(),
                "count": 0,
                "samples": [],
            })

            entry["mna_lemma_keys"].add(lemma_key)
            es = str(row.get("es", "")).strip()
            if es:
                entry["gloss_es"].add(es)
            lex_gloss = lexicon.get(lemma_key)
            if lex_gloss:
                entry["lexicon_glosses"].add(lex_gloss)

            surface = strip_niqqud(str(row.get("surface", "")).replace("/", ""))
            if surface:
                entry["surfaces"].add(surface)

            entry["books"].add(book)
            entry["count"] += 1

            if len(entry["samples"]) < 8:
                ref = f"{book} {row['ch']}:{row['vs']}"
                sample = {"ref": ref, "surface": surface, "es": es, "morph": row.get("morph")}
                if sample not in entry["samples"]:
                    entry["samples"].append(sample)

    rows: list[dict] = []
    for strongs in sorted(by_strongs, key=lambda s: int(s[1:])):
        raw = by_strongs[strongs]
        rows.append({
            "strongs": strongs,
            "mna_lemma_keys": sorted(raw["mna_lemma_keys"]),
            "gloss_es": sorted(raw["gloss_es"]),
            "lexicon_glosses": sorted(raw["lexicon_glosses"]),
            "surfaces": sorted(raw["surfaces"])[:12],
            "books": sorted(raw["books"]),
            "token_count": raw["count"],
            "samples": raw["samples"],
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({len(rows)} Strong's numbers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
