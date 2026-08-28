#!/usr/bin/env python3
"""Rebuild 1 Peter (1 Pedro) phrase map + phrases.json from filled LBF span seed."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERR = ROOT.parent
MORPH = HERR / "MNA" / "SOURCES" / "MorphGNT" / "81-1Pe-morphgnt.txt"
BLE = HERR / "Biblia-BLE" / "output" / "1pedro.ble.md"
FILLED = ROOT / "translations" / "phrase-maps" / "1peter-spans-filled.json"
OUT_MAP = ROOT / "translations" / "phrase-maps" / "1peter.json"
OUT_PHRASES = ROOT / "translations" / "1peter-phrases.json"
OUT_DOC = ROOT / "translations" / "1pedro.md"
LBF_OUT = HERR / "Biblia-LBF" / "translation" / "nt" / "1pedro.md"
STRONGS = HERR / "MNA" / "datasets" / "rules" / "grc_lemma_strongs.json"

BOOK_CODE = 60
BOOK_LABEL = "1 Peter"
DOC_TITLE = "1 Pedro"


def token_id(ch: int, vs: int, pos: int) -> str:
    return f"n{BOOK_CODE}{ch:03d}{vs:03d}{pos:03d}"


def parse_morph(path: Path) -> dict[tuple[int, int], list[dict]]:
    verses: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        vid = parts[0]
        ch, vs = int(vid[2:4]), int(vid[4:6])
        verses[(ch, vs)].append(
            {
                "pos": parts[1],
                "parsing": parts[2],
                "surface_punct": parts[3],
                "surface": parts[4],
                "norm": parts[5],
                "lemma": parts[6],
            }
        )
    return verses


def load_strongs() -> dict[str, str]:
    if not STRONGS.is_file():
        return {}
    return {k: str(v).upper() for k, v in json.loads(STRONGS.read_text(encoding="utf-8")).items()}


def fold(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def strongs_for(lemma: str, index: dict[str, str]) -> str:
    if lemma in index:
        return index[lemma]
    f = fold(lemma)
    for k, v in index.items():
        if fold(k) == f:
            return v
    return ""


def load_ble() -> dict[tuple[int, int], str]:
    out: dict[tuple[int, int], str] = {}
    if not BLE.is_file():
        return out
    for line in BLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(?:1Pedro|1\s*Pedro)\s+(\d+):(\d+)\s+(.+)$", line)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()
    return out


def ble_seed_for_span(ble: str, start: int, end: int, n_tokens: int) -> str:
    if not ble:
        return ""
    words = ble.split()
    if not words or n_tokens <= 0:
        return ble
    a = max(0, int((start - 1) / n_tokens * len(words)))
    b = min(len(words), int(end / n_tokens * len(words)))
    if b <= a:
        b = min(len(words), a + 1)
    return " ".join(words[a:b]).replace("•", " ").strip()


def main() -> int:
    if not FILLED.is_file():
        raise SystemExit(f"Missing filled spans: {FILLED}")

    spans = json.loads(FILLED.read_text(encoding="utf-8"))
    verses = parse_morph(MORPH)
    strongs_index = load_strongs()
    ble = load_ble()

    phrase_map: list[dict] = []
    phrases: list[dict] = []
    local_counts: dict[tuple[int, int], int] = defaultdict(int)

    for phrase_index, span in enumerate(spans):
        ch, vs = int(span["ch"]), int(span["vs"])
        a, b = int(span["start"]), int(span["end"])
        spanish = str(span.get("spanish") or "").strip()
        if not spanish:
            raise SystemExit(f"Empty spanish at {ch}:{vs} {a}-{b}")
        tokens = verses[(ch, vs)]
        ids = [token_id(ch, vs, p) for p in range(a, b + 1)]
        greek = " ".join(tokens[p - 1]["surface"] for p in range(a, b + 1))
        token_rows = [
            {
                "sourceTokenId": token_id(ch, vs, p),
                "greek": tokens[p - 1]["surface"],
                "lemma": tokens[p - 1]["lemma"],
                "strongs": strongs_for(tokens[p - 1]["lemma"], strongs_index),
                "rmac": f"{tokens[p - 1]['pos']}{tokens[p - 1]['parsing'].strip('-')}",
                "morphology": "",
                "ble": "",
                "rv1909": "",
            }
            for p in range(a, b + 1)
        ]
        local_i = local_counts[(ch, vs)]
        local_counts[(ch, vs)] += 1

        phrase_map.append(
            {
                "reference": f"{BOOK_LABEL} {ch}:{vs}",
                "phraseIndex": phrase_index,
                "localIndex": local_i,
                "start": a,
                "end": b,
                "sourceTokenIds": ids,
                "greek": greek,
            }
        )
        phrases.append(
            {
                "reference": f"{BOOK_LABEL} {ch}:{vs}",
                "phraseIndex": phrase_index,
                "greek": greek,
                "spanish": spanish,
                "sourceTokenIds": ids,
                "tokenRows": token_rows,
                "rv1909Text": "",
                "bleText": ble_seed_for_span(ble.get((ch, vs), ""), a, b, len(tokens)),
                "suggestionSource": "lbf-preliminary",
                "approval": {
                    "status": "preliminary",
                    "approvedAt": "",
                    "approvedBy": "lbf-rebuild",
                },
                "gates": None,
                "aiProposal": None,
            }
        )

    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAP.write_text(
        json.dumps({"book": "1peter", "version": 1, "phrases": phrase_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_PHRASES.write_text(json.dumps(phrases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    by_verse: dict[tuple[int, int], list[str]] = defaultdict(list)
    for p in phrases:
        m = re.search(r"(\d+):(\d+)$", p["reference"])
        by_verse[(int(m.group(1)), int(m.group(2)))].append(p["spanish"])

    lines = [f"# {DOC_TITLE}", "", f"> La Biblia Fiel — {DOC_TITLE} (borrador preliminar).", ""]
    cur_ch = None
    for (ch, vs) in sorted(by_verse.keys()):
        if ch != cur_ch:
            cur_ch = ch
            lines += [f"## Capítulo {ch}", ""]
        lines += [f"### {ch}:{vs}", "", " ".join(by_verse[(ch, vs)]).strip(), ""]
    doc = "\n".join(lines).rstrip() + "\n"
    OUT_DOC.write_text(doc, encoding="utf-8")
    LBF_OUT.parent.mkdir(parents=True, exist_ok=True)
    LBF_OUT.write_text(doc, encoding="utf-8")

    print(f"phrases: {len(phrases)} (preliminary {len(phrases)})")
    print(f"wrote {OUT_MAP}")
    print(f"wrote {OUT_PHRASES}")
    print(f"wrote {OUT_DOC}")
    print(f"wrote {LBF_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
