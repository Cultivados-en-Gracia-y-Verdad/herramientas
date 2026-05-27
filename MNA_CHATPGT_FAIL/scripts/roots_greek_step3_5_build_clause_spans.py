#!/usr/bin/env python3

"""ROOTS Greek Step 3.5
Mechanical Greek clause span engine.

PASS 1
-------
Build neutral finite-anchor regions.

PASS 2
-------
Apply explicit pre-finite migration rules.

PASS 3
-------
Normalize boundaries and emit audit disclosures.

This script does NOT build hierarchy.
It only proposes clause span ownership.
"""

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

FINITE_ENDINGS = {"I", "S", "M", "D"}

PAIR_HEADS = {
    "ὃς", "ὅς", "ἣ", "ἥ", "ὅ",
    "οἳ", "οἵ", "αἳ", "αἵ", "ἃ", "ἅ",
}

MEN_PARTICLES = {"μέν", "μὲν"}
DE_PARTICLES = {"δέ", "δὲ"}
PAIR_PARTICLES = MEN_PARTICLES | DE_PARTICLES
PAIR_LEAD_INS = {"καί", "καὶ"}

SUBORDINATING_CONNECTORS = {
    "εἰ", "εἴ", "ἐάν", "ἐὰν",
    "ἵνα", "ὅτι", "ὅπως",
    "ὡς", "ὥστε",
}

POST_FINITE_TAIL_STARTERS = SUBORDINATING_CONNECTORS

HEADER = [
    "BOOK", "CH", "VS", "CLAUSE_ID",
    "FINITE_G_IDX", "FINITE_GREEK", "FINITE_LEMMA", "FINITE_RMAC",
    "SPAN_START", "SPAN_END", "SPAN_GIDX",
    "SPAN_TEXT", "SPAN_STATUS", "BOUNDARY_NOTES",
]


@dataclass
class Token:
    g_idx: int
    greek: str
    lemma: str
    rmac: str


@dataclass
class ClauseRegion:
    clause_id: str
    finite: Token
    finite_pos: int
    start_pos: int
    end_pos: int
    original_start_pos: int
    notes: List[str] = field(default_factory=list)

    @property
    def migrated_left(self) -> bool:
        return self.start_pos < self.original_start_pos


@dataclass
class ClauseSpan:
    book: str
    ch: str
    vs: str
    clause_id: str
    finite: Token
    start: int
    end: int
    tokens: List[Token]
    notes: str


def clean_surface(text: str) -> str:
    return str(text or "").strip().strip(".,;:·—⸁⸃[]();?")


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_tokens(data) -> List[Token]:
    rows = []

    for col in sorted(
        data.get("columns", []),
        key=lambda c: int((c.get("greek_tokens") or [999999])[0])
    ):
        greek = str(col.get("greek", "") or "").strip()
        if not greek:
            continue
        rows.append(Token(
            g_idx=int((col.get("greek_tokens") or [999999])[0]),
            greek=greek,
            lemma=str(col.get("lemma", "") or ""),
            rmac=str(col.get("rmac", "") or ""),
        ))

    return rows


def is_finite(rmac: str) -> bool:
    if not rmac.startswith("V-"):
        return False
    parts = rmac.split("-")
    if len(parts) < 2:
        return False
    morph = parts[1]
    return len(morph) >= 3 and morph[-1] in FINITE_ENDINGS


def build_neutral_regions(tokens: List[Token]) -> List[ClauseRegion]:
    finite_positions = [i for i, tok in enumerate(tokens) if is_finite(tok.rmac)]
    regions = []

    for idx, pos in enumerate(finite_positions):
        start = 0 if idx == 0 else pos
        end = (
            finite_positions[idx + 1] - 1
            if idx + 1 < len(finite_positions)
            else len(tokens) - 1
        )

        regions.append(ClauseRegion(
            clause_id=f"C{idx + 1}",
            finite=tokens[pos],
            finite_pos=pos,
            start_pos=start,
            original_start_pos=start,
            end_pos=end,
        ))

    return regions


def move_pair_structures(tokens, regions):
    for idx in range(1, len(regions)):
        region = regions[idx]
        start = region.start_pos

        if start <= 0:
            continue

        prev = clean_surface(tokens[start - 1].greek)

        if prev in PAIR_PARTICLES:
            particle_pos = start - 1
            head_pos = particle_pos - 1

            if head_pos >= 0:
                head = clean_surface(tokens[head_pos].greek)

                if head in PAIR_HEADS:
                    region.start_pos = head_pos
                    region.notes.append(
                        f"migrated paired head {tokens[head_pos].greek} {tokens[particle_pos].greek}"
                    )

                    lead_pos = head_pos - 1
                    if lead_pos >= 0:
                        lead = clean_surface(tokens[lead_pos].greek)
                        if lead in PAIR_LEAD_INS:
                            region.start_pos = lead_pos
                            region.notes.append(
                                f"migrated paired lead-in {tokens[lead_pos].greek}"
                            )


def move_subordinate_connectors(tokens, regions):
    for region in regions:
        start = region.start_pos

        if start <= 0:
            continue

        prev = clean_surface(tokens[start - 1].greek)

        if prev in SUBORDINATING_CONNECTORS:
            region.start_pos = start - 1
            region.notes.append(
                f"migrated subordinate connector {tokens[start - 1].greek}"
            )


def move_post_finite_tails(tokens, regions):
    for idx in range(1, len(regions)):
        prev_region = regions[idx - 1]
        region = regions[idx]

        search_start = prev_region.finite_pos + 1
        search_end = region.start_pos - 1

        if search_start > search_end:
            continue

        for pos in range(search_start, search_end + 1):
            surface = clean_surface(tokens[pos].greek)

            if surface in POST_FINITE_TAIL_STARTERS:
                region.start_pos = pos
                region.notes.append(
                    f"migrated post-finite tail beginning with {tokens[pos].greek}"
                )
                break


def normalize_boundaries(regions):
    for idx in range(len(regions) - 1):
        current = regions[idx]
        nxt = regions[idx + 1]
        current.end_pos = nxt.start_pos - 1

        if current.end_pos < current.finite_pos:
            current.end_pos = current.finite_pos
            current.notes.append("boundary normalized at finite anchor to prevent empty span")


def build_spans(book, ch, vs, tokens, regions):
    rows = []

    for region in regions:
        span_tokens = tokens[region.start_pos:region.end_pos + 1]

        rows.append(ClauseSpan(
            book=book,
            ch=ch,
            vs=vs,
            clause_id=region.clause_id,
            finite=region.finite,
            start=span_tokens[0].g_idx,
            end=span_tokens[-1].g_idx,
            tokens=span_tokens,
            notes="; ".join(region.notes) or "neutral finite-anchor region",
        ))

    return rows


def render_text(tokens):
    out = []

    for tok in tokens:
        if is_finite(tok.rmac):
            out.append(f"=={tok.greek}==")
        else:
            out.append(tok.greek)

    return " ".join(out)


def render_gidx(tokens):
    return ",".join(f"{t.g_idx:02d}" for t in tokens)


def export_book(book, interlinear_dir, out_dir):
    rows = []

    for path in sorted((interlinear_dir / book).glob("*/*.json")):
        data = read_json(path)
        ch = str(data["chapter"])
        vs = str(data["verse"])
        tokens = read_tokens(data)

        regions = build_neutral_regions(tokens)
        move_pair_structures(tokens, regions)
        move_subordinate_connectors(tokens, regions)
        move_post_finite_tails(tokens, regions)
        normalize_boundaries(regions)
        spans = build_spans(book, ch, vs, tokens, regions)

        for span in spans:
            rows.append([
                span.book,
                span.ch,
                span.vs,
                span.clause_id,
                f"{span.finite.g_idx:02d}",
                span.finite.greek,
                span.finite.lemma,
                span.finite.rmac,
                f"{span.start:02d}",
                f"{span.end:02d}",
                render_gidx(span.tokens),
                render_text(span.tokens),
                "suggested-span",
                span.notes,
            ])

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-clause-spans.tsv"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)

    print(f"Wrote {out_path}")
    print({"clause_spans": len(rows)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("book")
    parser.add_argument("--interlinear-dir", default="MNA/data/interlinear")
    parser.add_argument("--out-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    export_book(args.book, Path(args.interlinear_dir), Path(args.out_dir))


if __name__ == "__main__":
    main()
