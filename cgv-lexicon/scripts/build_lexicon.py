#!/usr/bin/env python3
"""Build CGV lexicon JSONL from MNA rules datasets."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
RULES = REPO / "MNA" / "datasets" / "rules"
OUT = ROOT / "data"


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_strongs(*maps: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for mapping in maps:
        for lemma, strongs in mapping.items():
            out.setdefault(str(lemma), str(strongs))
    return out


def normalize_strongs(value: str, lang: str) -> str:
    text = str(value).strip().upper()
    prefix = "G" if lang == "grc" else "H"
    if text.startswith(prefix):
        return f"{prefix}{int(text[1:])}"
    if text.isdigit():
        return f"{prefix}{int(text)}"
    return text


def hbo_strongs_from_lemma(lemma: str) -> str | None:
    """OSHB lemmas like '1254 a', '430', 'b/7225' → H#### when possible."""
    text = str(lemma).strip()
    m = re.match(r"^(\d+)", text)
    if not m:
        return None
    return normalize_strongs(m.group(1), "hbo")


def build_greek() -> list[dict]:
    lexicon = load_json(RULES / "grc_lemma_lexicon.json")
    defaults = load_json(RULES / "grc_lemma_defaults.json")
    strongs = merge_strongs(
        load_json(RULES / "grc_lemma_strongs.json"),
        load_json(RULES / "grc_lemma_strongs_supplement.json"),
    )

    lemmas = sorted(set(lexicon) | set(defaults) | set(strongs))
    entries: list[dict] = []

    for lemma in lemmas:
        gloss = lexicon.get(lemma) or defaults.get(lemma)
        if not gloss or str(gloss).startswith("__FILL_"):
            gloss = None
        s = strongs.get(lemma)
        if not gloss and not s:
            continue
        sources: list[str] = []
        if lemma in lexicon:
            sources.append("grc_lemma_lexicon")
        elif lemma in defaults:
            sources.append("grc_lemma_defaults")
        if s:
            sources.append("grc_lemma_strongs")
        entry: dict = {
            "lang": "grc",
            "lemma": lemma,
            "sources": sources,
        }
        if gloss:
            entry["gloss_es"] = gloss
        if s:
            entry["strongs"] = normalize_strongs(s, "grc")
        entries.append(entry)

    return entries


def build_hebrew() -> list[dict]:
    lexicon = load_json(RULES / "hbo_lemma_lexicon.json")
    entries: list[dict] = []

    for lemma in sorted(lexicon):
        gloss = lexicon[lemma]
        if not gloss or str(gloss).startswith("__FILL_"):
            continue
        s = hbo_strongs_from_lemma(lemma)
        entry: dict = {
            "lang": "hbo",
            "lemma": lemma,
            "gloss_es": gloss,
            "sources": ["hbo_lemma_lexicon"],
        }
        if s:
            entry["strongs"] = s
        entries.append(entry)

    return entries


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    grc = build_greek()
    hbo = build_hebrew()

    write_jsonl(OUT / "grc.entries.jsonl", grc)
    write_jsonl(OUT / "hbo.entries.jsonl", hbo)

    manifest = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": "cgv-lexicon/scripts/build_lexicon.py",
        "grc": {
            "entries": len(grc),
            "with_gloss": sum(1 for e in grc if e.get("gloss_es")),
            "with_strongs": sum(1 for e in grc if e.get("strongs")),
        },
        "hbo": {
            "entries": len(hbo),
            "with_gloss": sum(1 for e in hbo if e.get("gloss_es")),
            "with_strongs": sum(1 for e in hbo if e.get("strongs")),
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"wrote {OUT / 'grc.entries.jsonl'} ({len(grc)} entries)")
    print(f"wrote {OUT / 'hbo.entries.jsonl'} ({len(hbo)} entries)")
    print(f"wrote {OUT / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
