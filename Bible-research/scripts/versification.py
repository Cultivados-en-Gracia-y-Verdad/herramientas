#!/usr/bin/env python3
"""Map MACULA references (org / MT versification) to Protestant (eng) numbering.

MACULA WLC ships the original (Masoretic) versification: Joel has 4 chapters,
Malachi 3, and Psalm superscriptions occupy numbered verses. Protestant Bibles
renumber all of that. Every reference this project publishes must be Protestant,
so each clause carries both.

Tables are the Copenhagen Alliance standard mappings (`data/versification/`).
In `eng.json`, `mappedVerses` maps an English reference to its org counterpart;
we invert that. English verse 0 marks an unnumbered Psalm superscription.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VRS_DIR = ROOT / "data" / "versification"

REF_RANGE = re.compile(r"^(?P<book>\S+)\s+(?P<ch>\d+):(?P<start>\d+)(?:-(?P<end>\d+))?$")

# The standard table omits verse merges where MT splits what Protestant joins.
# MT Num 25:19 ("it was after the plague") opens the same Protestant verse that
# MT Num 26:1 ("YHWH said to Moses") continues; both are Protestant Num 26:1.
SUPPLEMENT: dict[tuple[str, int, int], tuple[int, int]] = {
    ("NUM", 25, 19): (26, 1),
}


def _expand(ref: str) -> list[tuple[str, int, int]]:
    """'PSA 3:1-9' -> [(PSA,3,1) ... (PSA,3,9)]."""
    m = REF_RANGE.match(ref.strip())
    if not m:
        return []
    book = m.group("book")
    ch = int(m.group("ch"))
    start = int(m.group("start"))
    end = int(m.group("end") or start)
    return [(book, ch, v) for v in range(start, end + 1)]


@lru_cache(maxsize=1)
def _tables() -> tuple[dict[tuple[str, int, int], tuple[int, int]], dict[str, list[int]]]:
    eng = json.loads((VRS_DIR / "eng.json").read_text(encoding="utf-8"))

    org_to_eng: dict[tuple[str, int, int], tuple[int, int]] = {}
    for eng_ref, org_ref in eng["mappedVerses"].items():
        eng_cells = _expand(eng_ref)
        org_cells = _expand(org_ref)
        if not eng_cells or not org_cells:
            continue
        if len(eng_cells) == len(org_cells):
            pairs = zip(org_cells, eng_cells)
        else:
            # Ranges of unequal length (verse merges/splits): collapse onto the
            # first English cell so a reference never disappears.
            pairs = ((o, eng_cells[0]) for o in org_cells)
        for (obook, och, ov), (_, ech, ev) in pairs:
            org_to_eng.setdefault((obook, och, ov), (ech, ev))

    org_to_eng.update(SUPPLEMENT)

    max_verses = {b: [int(x) for x in v] for b, v in eng["maxVerses"].items()}
    return org_to_eng, max_verses


def to_protestant(book: str, chapter: int | None, verse: int | None) -> dict:
    """Return Protestant chapter/verse for a MACULA (org) reference.

    `verse_protestant` of 0 means an unnumbered Psalm superscription.
    """
    if not book or chapter is None:
        return {
            "chapter_protestant": chapter,
            "verse_protestant": verse,
            "ref_protestant": None,
            "is_superscription": False,
            "versification_shift": False,
        }

    org_to_eng, _ = _tables()
    key = (book, int(chapter), int(verse) if verse is not None else 0)
    mapped = org_to_eng.get(key)
    if mapped is None:
        ch, vs = int(chapter), (int(verse) if verse is not None else None)
        shifted = False
    else:
        ch, vs = mapped
        shifted = (ch, vs) != (int(chapter), int(verse or 0))

    is_super = vs == 0
    if vs is None:
        ref = f"{book} {ch}"
    elif is_super:
        ref = f"{book} {ch}:title"
    else:
        ref = f"{book} {ch}:{vs}"

    return {
        "chapter_protestant": ch,
        "verse_protestant": vs,
        "ref_protestant": ref,
        "is_superscription": is_super,
        "versification_shift": shifted,
    }


def validate(observed: dict[str, set[tuple[int, int]]]) -> list[str]:
    """Check mapped refs fall inside the Protestant canon's verse counts."""
    _, max_verses = _tables()
    problems: list[str] = []
    for book, cells in sorted(observed.items()):
        limits = max_verses.get(book)
        if not limits:
            problems.append(f"{book}: no Protestant verse table")
            continue
        for ch, vs in sorted(cells):
            mapped = to_protestant(book, ch, vs)
            pch, pvs = mapped["chapter_protestant"], mapped["verse_protestant"]
            if pch is None or pch < 1 or pch > len(limits):
                problems.append(f"{book} {ch}:{vs} -> chapter {pch} outside 1..{len(limits)}")
                continue
            if pvs is None:
                continue
            if pvs < 0 or pvs > limits[pch - 1]:
                problems.append(
                    f"{book} {ch}:{vs} -> {book} {pch}:{pvs} outside 0..{limits[pch - 1]}"
                )
    return problems


if __name__ == "__main__":
    checks = [
        ("JOL", 3, 1, "JOL 2:28"),
        ("JOL", 4, 1, "JOL 3:1"),
        ("MAL", 3, 19, "MAL 4:1"),
        ("PSA", 22, 2, "PSA 22:1"),
        ("PSA", 22, 1, "PSA 22:title"),
        ("PSA", 23, 1, "PSA 23:1"),
        ("PSA", 110, 1, "PSA 110:1"),
        ("PSA", 51, 3, "PSA 51:1"),
        ("JON", 2, 1, "JON 1:17"),
        ("ISA", 7, 14, "ISA 7:14"),
        ("GEN", 32, 1, "GEN 31:55"),
    ]
    bad = 0
    for book, ch, vs, expected in checks:
        got = to_protestant(book, ch, vs)["ref_protestant"]
        ok = got == expected
        bad += 0 if ok else 1
        print(f"{'ok ' if ok else 'BAD'} {book} {ch}:{vs} -> {got} (expected {expected})")
    raise SystemExit(1 if bad else 0)
