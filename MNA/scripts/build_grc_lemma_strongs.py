#!/usr/bin/env python3
"""Build lemma → Strong's mapping for MorphGNT NT tokens.

Sources (jtauber/greek-lemma-mappings):
  - canonical_strongs.yaml — MorphGNT spellings under each Strong's entry
  - lexemes.yaml — primary Strong's numbers where present
  - alt_mapping.yaml — variant spellings → canonical lexeme keys

Output: MNA/datasets/rules/grc_lemma_strongs.json
Supplement (hand-curated gaps): grc_lemma_strongs_supplement.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "datasets" / "rules"
SOURCES_DIR = RULES_DIR / "sources"
OUTPUT = RULES_DIR / "grc_lemma_strongs.json"
SUPPLEMENT = RULES_DIR / "grc_lemma_strongs_supplement.json"

BASE_URL = "https://raw.githubusercontent.com/jtauber/greek-lemma-mappings/master"
SOURCE_FILES = {
    "canonical_strongs.yaml": f"{BASE_URL}/canonical_strongs.yaml",
    "lexemes.yaml": f"{BASE_URL}/lexemes.yaml",
    "alt_mapping.yaml": f"{BASE_URL}/alt_mapping.yaml",
}


def download(name: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    url = SOURCE_FILES[name]
    print(f"downloading {url} …", file=sys.stderr)
    urllib.request.urlretrieve(url, dest)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def norm_lemma(lemma: str) -> str:
    return re.sub(r"\([^)]*\)", "", lemma)


def format_strongs(value: int | str) -> str:
    return f"G{int(value)}"


def build_variant_map(alt: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for canon, variants in alt.items():
        out[str(canon)] = str(canon)
        if not isinstance(variants, list):
            continue
        for variant in variants:
            out[str(variant)] = str(canon)
    return out


def from_canonical_strongs(canonical: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for num, entry in canonical.items():
        if not isinstance(entry, dict):
            continue
        g = format_strongs(num)
        for lemmas in entry.values():
            if not isinstance(lemmas, list):
                continue
            for lemma in lemmas:
                out.setdefault(str(lemma), g)
    return out


def from_lexemes(lexemes: dict, variant_to_canon: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}

    def add(lemma: str, strongs: int | str) -> None:
        out.setdefault(lemma, format_strongs(strongs))

    for lemma, entry in lexemes.items():
        if not isinstance(entry, dict):
            continue
        strongs = entry.get("strongs")
        if strongs is not None and not isinstance(strongs, list):
            add(str(lemma), strongs)

    for variant, canon in variant_to_canon.items():
        entry = lexemes.get(canon)
        if not isinstance(entry, dict):
            continue
        strongs = entry.get("strongs")
        if strongs is not None and not isinstance(strongs, list):
            add(variant, strongs)

    return out


def merge_mappings(*maps: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for mapping in maps:
        for lemma, strongs in mapping.items():
            out.setdefault(lemma, strongs)
    return out


def add_normalized_keys(mapping: dict[str, str]) -> dict[str, str]:
    out = dict(mapping)
    for lemma, strongs in mapping.items():
        normed = norm_lemma(lemma)
        if normed and normed != lemma:
            out.setdefault(normed, strongs)
    return out


def load_supplement() -> dict[str, str]:
    if not SUPPLEMENT.exists():
        return {}
    data = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def audit_nt_coverage(mapping: dict[str, str]) -> tuple[int, int, list[str]]:
    tokens_dir = ROOT / "datasets" / "interlinear" / "NT"
    missing: dict[str, int] = {}
    total = 0

    def lookup(lemma: str) -> str:
        for key in (lemma, norm_lemma(lemma)):
            if key in mapping:
                return mapping[key]
        return ""

    for path in sorted(tokens_dir.glob("*.tokens.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            lemma = json.loads(line)["lemma"]
            if not lookup(lemma):
                missing[lemma] = missing.get(lemma, 0) + 1

    return total, sum(missing.values()), sorted(missing, key=lambda l: (-missing[l], l))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build grc_lemma_strongs.json")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="download source YAML into datasets/rules/sources/ if missing",
    )
    parser.add_argument("--audit", action="store_true", help="report NT token coverage")
    args = parser.parse_args()

    if args.fetch:
        for name in SOURCE_FILES:
            download(name, SOURCES_DIR / name)

    canonical_path = SOURCES_DIR / "canonical_strongs.yaml"
    lexemes_path = SOURCES_DIR / "lexemes.yaml"
    alt_path = SOURCES_DIR / "alt_mapping.yaml"
    for path in (canonical_path, lexemes_path, alt_path):
        if not path.exists():
            print(
                f"missing {path}; run with --fetch or place jtauber YAML files there",
                file=sys.stderr,
            )
            return 1

    canonical = load_yaml(canonical_path)
    lexemes = load_yaml(lexemes_path)
    alt = load_yaml(alt_path)
    variant_to_canon = build_variant_map(alt)

    mapping = merge_mappings(
        from_canonical_strongs(canonical),
        from_lexemes(lexemes, variant_to_canon),
        load_supplement(),
    )
    mapping = add_normalized_keys(mapping)

    OUTPUT.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} ({len(mapping)} lemmas)")

    if args.audit:
        total, missing_tokens, missing_lemmas = audit_nt_coverage(mapping)
        pct = 100.0 * (total - missing_tokens) / total if total else 0.0
        print(
            f"NT coverage: {total - missing_tokens}/{total} tokens ({pct:.2f}%)",
            file=sys.stderr,
        )
        if missing_lemmas:
            print(f"still missing {len(missing_lemmas)} lemmas:", file=sys.stderr)
            for lemma in missing_lemmas[:20]:
                print(f"  {lemma}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
