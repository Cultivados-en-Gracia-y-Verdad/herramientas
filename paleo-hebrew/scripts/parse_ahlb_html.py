#!/usr/bin/env python3
"""Extract AHRC AHLB lexicon entries from saved HTML (by Strong's H-number)."""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from strongs import parse_ahrc_strongs_field

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ahrc" / "strongs.jsonl"

PARENT_ROOT_RE = re.compile(
    r"\(([א-ת]{1,4})\)\s*(?:\*\*)?Action:(?:\*\*)?"
    r"|\(([א-ת]{1,4})\)\s*(?:\*\*)?Object:(?:\*\*)?"
)
# Current AHRC pages use plain "Translation:" labels (older scrapes used **markdown**).
ROW_RE = re.compile(
    r"\(\s*(?:masc\.|fem\.|common),?\s*"
    r"([^/|)+]+?)"
    r"(?:\s*/\s*([^)|]+?))?"
    r"\)\s*"
    r"(?:\*\*)?Translation:(?:\*\*)?\s*([^*]+?)"
    r"(?:\s*(?:\*\*)?Definition:(?:\*\*)?\s*([^*]+?))?"
    r"(?:\s*(?:\*\*)?Relationship to Root:(?:\*\*)?\s*([^*]+?))?"
    r"(?:\s*(?:\*\*)?KJV Translations:(?:\*\*)?\s*([^*]+?))?"
    r"\s*(?:\*\*)?Strong's Hebrew #:(?:\*\*)?\s*"
    r"([^\(]+?)(?=\s*\(|\s*$)",
    re.I,
)



def strip_html(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_source_slug(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    name = path.name.lower()
    for slug in (
        "aleph", "beyt", "gimel", "dalet", "hey", "vav", "zayin", "hhet", "tet",
        "yud", "kaph", "lamed", "mem", "nun", "samehh", "ayin", "pey", "tsade",
        "quph", "resh", "shin", "tav", "ghayin",
    ):
        if slug in name:
            return slug
    return path.stem


def parse_ahlb_html(html: str, *, source_slug: str) -> list[dict]:
    text = strip_html(html)
    parent_roots: dict[str, str] = {}
    for m in PARENT_ROOT_RE.finditer(text):
        root = (m.group(1) or m.group(2) or "").strip()
        if not root:
            continue
        start = max(0, m.start() - 200)
        chunk = text[start : m.start()]
        for label in ("Action:", "Object:", "Abstract:", "Definition:"):
            lm = re.search(rf"(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*([^*|(]+)", chunk)
            if lm:
                parent_roots.setdefault(root, lm.group(1).strip())
                break

    entries: list[dict] = []
    seen: set[str] = set()

    # Prefer whole-page scan; pipe-splitting was for older markdown tables.
    for m in ROW_RE.finditer(text):
        hebrew = m.group(1).strip()
        translit = (m.group(2) or "").strip()
        translation = m.group(3).strip().replace(".", " ").strip()
        # Stop field bleed into following labels.
        translation = re.split(
            r"\s+(?:Definition|Relationship to Root|KJV Translations|Strong's Hebrew)\b",
            translation,
            maxsplit=1,
        )[0].strip()
        definition = (m.group(4) or "").strip()
        definition = re.split(
            r"\s+(?:Relationship to Root|KJV Translations|Strong's Hebrew)\b",
            definition,
            maxsplit=1,
        )[0].strip()
        relationship = (m.group(5) or "").strip()
        relationship = re.split(
            r"\s+(?:KJV Translations|Strong's Hebrew)\b",
            relationship,
            maxsplit=1,
        )[0].strip()
        kjv = (m.group(6) or "").strip()
        kjv = re.split(r"\s+Strong's Hebrew\b", kjv, maxsplit=1)[0].strip()
        strongs_raw = m.group(7).strip()

        parent_root = hebrew[:2] if hebrew else ""

        for strongs in parse_ahrc_strongs_field(strongs_raw):
            key = f"{strongs}:{hebrew}:{translation}"
            if key in seen:
                continue
            seen.add(key)
            entries.append({
                "strongs": strongs,
                "hebrew": hebrew,
                "transliteration": translit,
                "translation": translation,
                "definition": definition or None,
                "relationship_to_root": relationship or None,
                "kjv": kjv or None,
                "parent_root": parent_root or None,
                "parent_root_gloss": parent_roots.get(parent_root or ""),
                "source": f"ahlb/{source_slug}.html",
            })

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse AHRC AHLB HTML into strongs.jsonl")
    parser.add_argument("html", type=Path, nargs="?", help="Saved AHLB HTML file")
    parser.add_argument("--url", help="Fetch AHLB page URL")
    parser.add_argument("--slug", help="AHLB letter slug (e.g. aleph)")
    parser.add_argument("--merge", action="store_true", help="Merge with existing strongs.jsonl")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()

    if args.url:
        import urllib.request

        html = urllib.request.urlopen(args.url, timeout=60).read().decode("utf-8", "replace")
        slug = args.slug or Path(urlparse(args.url).path).stem
        source_path = Path(slug)
    elif args.html:
        html = args.html.read_text(encoding="utf-8", errors="replace")
        slug = infer_source_slug(args.html, args.slug)
        source_path = args.html
    else:
        parser.error("provide html file or --url")

    new_rows = parse_ahlb_html(html, source_slug=slug)
    out_path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.merge and out_path.is_file():
        existing = {
            (r["strongs"], r.get("hebrew"), r.get("translation")): r
            for r in (
                json.loads(line)
                for line in out_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        for row in new_rows:
            existing[(row["strongs"], row.get("hebrew"), row.get("translation"))] = row
        rows = sorted(existing.values(), key=lambda r: (r["strongs"], r.get("hebrew", "")))
    else:
        rows = sorted(new_rows, key=lambda r: (r["strongs"], r.get("hebrew", "")))

    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(f"wrote {out_path} ({len(rows)} entries, +{len(new_rows)} from {source_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
