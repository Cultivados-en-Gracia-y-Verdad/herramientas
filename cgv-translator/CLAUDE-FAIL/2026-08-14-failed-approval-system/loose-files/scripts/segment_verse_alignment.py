#!/usr/bin/env python3
"""
Segment whole-verse alignment units into real sub-verse units.

Problem
-------
A verse whose alignment is a single unit spanning the entire Spanish text and
linked to every source token carries no unit-level information. It is not an
alignment; it is a tautology. WORKFLOW.md §10 forbids it.

`rebuild_daniel_reverse_links.py` recomputes sourceTokenIds for units that already
exist. It cannot help here, because these verses have no segmentation to preserve.
This tool produces the segmentation.

Method
------
Monotonic dynamic programming over (source tokens x Spanish words). Both sequences
are partitioned into the same number of consecutive groups; each group of tokens is
paired with a group of Spanish words. Score uses the BLE Spanish glosses already
stored in phrase tokenRows, via the similarity functions in
`rebuild_daniel_reverse_links.py` (single source of truth for normalization).

Output is a SEED, not a verification:
    method: gloss-segment
    status: gloss-seed
G0B must still review every unit.

Modes
-----
--validate   run against verses that already have multi-unit alignment and report
             how well the segmenter reproduces them. Writes nothing.
--apply      write the segmented reverse-link artifact.
Default is a dry run with a report.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from functools import lru_cache  # noqa: E402
from rebuild_daniel_reverse_links import sequence_similarity as _raw_similarity  # noqa: E402


@lru_cache(maxsize=1_000_000)
def sequence_similarity(span: str, gloss: str) -> float:
    """The DP evaluates the same (span, gloss) pair many times; scoring is pure."""
    return _raw_similarity(span, gloss)

WORD_RE = re.compile(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+", re.UNICODE)


def spanish_words(text: str) -> list[tuple[str, int, int]]:
    """Words with character offsets into the phrase text."""
    return [(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(text)]


def token_gloss(token: dict) -> str:
    return str(token.get("ble") or token.get("gloss") or "")


def segment(tokens: list[dict], wordspans: list[tuple[str, int, int]],
            max_tokens: int = 4, max_words: int = 7) -> list[tuple[list[int], int, int]]:
    """
    Partition tokens and words into aligned consecutive groups.

    Returns [(token_indices, first_word_index, last_word_index_exclusive), ...]
    covering every token and every word exactly once, in order.
    """
    T, W = len(tokens), len(wordspans)
    if not T or not W:
        return []

    NEG = float("-inf")
    best = [[NEG] * (W + 1) for _ in range(T + 1)]
    back = [[None] * (W + 1) for _ in range(T + 1)]
    best[0][0] = 0.0

    for ti in range(T + 1):
        for wi in range(W + 1):
            if best[ti][wi] == NEG:
                continue
            if ti == T and wi == W:
                continue
            base = best[ti][wi]
            for a in range(1, min(max_tokens, T - ti) + 1):
                for b in range(1, min(max_words, W - wi) + 1):
                    # last group must consume both sequences to the end
                    if (ti + a == T) != (wi + b == W) and (ti + a == T or wi + b == W):
                        if ti + a == T and wi + b < W and b < max_words:
                            continue
                        if wi + b == W and ti + a < T and a < max_tokens:
                            continue
                    gloss = " ".join(token_gloss(tokens[k]) for k in range(ti, ti + a))
                    span = " ".join(w for w, _, _ in wordspans[wi:wi + b])
                    sim = sequence_similarity(span, gloss)
                    # prefer tight groups; penalise sprawling many-to-many
                    score = base + sim - 0.06 * (a - 1) - 0.04 * (b - 1)
                    if score > best[ti + a][wi + b]:
                        best[ti + a][wi + b] = score
                        back[ti + a][wi + b] = (ti, wi, a, b)

    if best[T][W] == NEG:
        return []

    out, ti, wi = [], T, W
    while (ti, wi) != (0, 0):
        step = back[ti][wi]
        if step is None:
            return []
        pti, pwi, a, b = step
        out.append((list(range(pti, pti + a)), pwi, pwi + b))
        ti, wi = pti, pwi
    out.reverse()
    return out


def build_units(reference: str, phrase_index: int, spanish: str, tokens: list[dict]) -> list[dict]:
    wordspans = spanish_words(spanish)
    groups = segment(tokens, wordspans)
    units = []
    for n, (tok_idx, w0, w1) in enumerate(groups):
        start = wordspans[w0][1]
        end = wordspans[w1 - 1][2]
        units.append({
            "unitId": f"{phrase_index}:{n}",
            "surface": spanish[start:end],
            "charStart": start,
            "charEnd": end,
            "sourceTokenIds": [tokens[i]["sourceTokenId"] for i in tok_idx],
            "method": "gloss-segment",
            "status": "gloss-seed",
        })
    return units


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrases", required=True, type=Path)
    ap.add_argument("--reverse-links", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    phrases = {p["reference"]: p for p in json.loads(args.phrases.read_text(encoding="utf-8"))["phrases"]}
    doc = json.loads(args.reverse_links.read_text(encoding="utf-8"))

    if args.validate:
        agree_tok = total_tok = 0
        exact = considered = 0
        for link in doc["links"]:
            if len(link["units"]) <= 1:
                continue
            p = phrases[link["reference"]]
            produced = build_units(link["reference"], p["phraseIndex"], p["spanish"], p["tokenRows"])
            if not produced:
                continue
            considered += 1
            existing = {t: u["unitId"] for u in link["units"] for t in u["sourceTokenIds"]}
            mine = {t: u["unitId"] for u in produced for t in u["sourceTokenIds"]}
            # agreement = same tokens grouped together as in the reviewed alignment
            ex_groups = {}
            for t, uid in existing.items():
                ex_groups.setdefault(uid, set()).add(t)
            my_groups = {}
            for t, uid in mine.items():
                my_groups.setdefault(uid, set()).add(t)
            ex_sets = {frozenset(v) for v in ex_groups.values()}
            my_sets = {frozenset(v) for v in my_groups.values()}
            agree_tok += sum(len(s) for s in ex_sets & my_sets)
            total_tok += sum(len(s) for s in ex_sets)
            if ex_sets == my_sets:
                exact += 1
        print(f"validation against {considered} already-segmented verses")
        print(f"  identical token grouping : {exact}/{considered} verses")
        print(f"  tokens in matching groups: {agree_tok}/{total_tok} ({agree_tok/max(1,total_tok):.1%})")
        return 0

    rebuilt = failed = 0
    for link in doc["links"]:
        if len(link["units"]) != 1:
            continue
        p = phrases[link["reference"]]
        units = build_units(link["reference"], p["phraseIndex"], p["spanish"], p["tokenRows"])
        if len(units) <= 1:
            failed += 1
            continue
        link["units"] = units
        link["status"] = "gloss-seed"
        rebuilt += 1

    counts = [len(l["units"]) for l in doc["links"]]
    print(f"verses segmented : {rebuilt}")
    print(f"verses unchanged : {failed}")
    print(f"total units now  : {sum(counts)}")
    print(f"whole-verse units remaining: {sum(1 for c in counts if c == 1)}")

    if args.apply:
        out = args.out or args.reverse_links
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"written: {out}")
    else:
        print("dry run; no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
