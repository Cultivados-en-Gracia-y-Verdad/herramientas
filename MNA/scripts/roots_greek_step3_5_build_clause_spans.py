#!/usr/bin/env python3

"""
ROOTS Greek Step 3.5
Build conservative Greek clause spans from finite anchors.

INPUTS
------
1. Step 1 verbs/connectors DB:
   MNA/roots-greek/db/{book}-verbs-connectors.tsv
2. Raw Greek/morph source from interlinear JSON:
   MNA/data/interlinear/{book}/{chapter}/{verse}.json

OUTPUT
------
MNA/roots-greek/dataset/{book}-clause-spans.tsv

CORE PRINCIPLE
--------------
This script builds clause spans, not hierarchy.

Confirmed:
- finite verb anchor
- Greek token order
- span text produced mechanically

Suggested/conservative:
- span boundaries

No Spanish.
No interpretation.
No connector ownership confirmation.
No PASO 6-8 hierarchy.
"""

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

FINITE_ENDINGS = {"I", "S", "M", "D"}

SUBORDINATING_CONNECTORS = {
    "ἵνα", "ὅπως", "ὅτι", "ἐάν", "ἐὰν", "εἰ", "εἴ", "εἴπερ", "ὅταν",
    "ἐπεί", "ἐπεὶ", "ἐπειδή", "ἐπειδὴ", "ἕως", "καθώς", "καθὼς", "καθάπερ",
    "ὡς", "ὥσπερ", "ὥστε",
}

PRE_FINITE_CARRY = {
    "δέ", "δὲ", "καί", "καὶ", "τε", "ἀλλά", "ἀλλὰ", "ἀλλʼ", "ἢ", "ἤ", "μή", "μὴ",
    "οὐ", "οὐκ", "οὐχ", "οὔτε", "μηδέ", "μηδὲ", "οὐδέ", "οὐδὲ", "μήτε",
}

MEN_PARTICLES = {"μέν", "μὲν"}
DE_PARTICLES = {"δέ", "δὲ"}
PAIR_PARTICLES = MEN_PARTICLES | DE_PARTICLES
PAIR_HEADS = {"ὃς", "ὅς", "ἣ", "ἥ", "ὅ", "οἳ", "οἵ", "αἳ", "αἵ", "ἃ", "ἅ"}
PAIR_LEAD_INS = {"καί", "καὶ"}

HEADER = [
    "BOOK", "CH", "VS", "CLAUSE_ID", "FINITE_G_IDX", "FINITE_GREEK", "FINITE_LEMMA", "FINITE_RMAC",
    "SPAN_START", "SPAN_END", "SPAN_GIDX", "SPAN_TEXT", "SPAN_STATUS", "BOUNDARY_NOTES",
]


@dataclass
class Token:
    g_idx: int
    greek: str
    lemma: str
    rmac: str


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
    status: str
    notes: str


def clean_surface(text: str) -> str:
    return str(text or "").strip().strip(".,;:·—⸁⸃[]();?·")


def is_verb(rmac: str) -> bool:
    return bool(rmac) and rmac.startswith("V-")


def is_finite(rmac: str) -> bool:
    if not is_verb(rmac):
        return False
    parts = rmac.split("-")
    return len(parts) >= 2 and len(parts[1]) >= 3 and parts[1][-1] in FINITE_ENDINGS


def greek_index(col: Dict) -> int:
    gt = col.get("greek_tokens") or []
    if not gt:
        return 999999
    try:
        return int(gt[0])
    except Exception:
        return 999999


def read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_tokens(data: Dict) -> List[Token]:
    tokens: List[Token] = []
    for col in sorted(data.get("columns", []), key=greek_index):
        greek = str(col.get("greek", "") or "").strip()
        if not greek:
            continue
        tokens.append(
            Token(
                g_idx=greek_index(col),
                greek=greek,
                lemma=str(col.get("lemma", "") or ""),
                rmac=str(col.get("rmac", "") or ""),
            )
        )
    return tokens


def verse_sort_key(path: Path) -> Tuple[int, int]:
    try:
        return int(path.parent.name), int(path.stem)
    except Exception:
        return 999999, 999999


def carry_start_left(tokens: List[Token], start_pos: int, floor_pos: int) -> Tuple[int, List[str]]:
    notes: List[str] = []
    pos = start_pos

    while pos - 1 >= floor_pos:
        prev = tokens[pos - 1]
        if clean_surface(prev.greek) in PRE_FINITE_CARRY:
            pos -= 1
            notes.append(f"carried pre-finite token {prev.greek}")
            continue
        break

    return pos, notes


def connector_start_left(tokens: List[Token], start_pos: int, floor_pos: int) -> Tuple[int, List[str]]:
    notes: List[str] = []
    pos = start_pos

    while pos - 1 >= floor_pos:
        prev = tokens[pos - 1]
        if clean_surface(prev.greek) in SUBORDINATING_CONNECTORS:
            pos -= 1
            notes.append(f"included preceding subordinate connector {prev.greek}")
            continue
        break

    return pos, notes


def paired_particle_start_left(tokens: List[Token], start_pos: int, floor_pos: int) -> Tuple[int, List[str]]:
    """Keep simple μὲν/δὲ paired heads with the finite clause they introduce.

    This is mechanical span repair, not hierarchy:
    - ὃς μὲν + finite -> include ὃς μὲν with that finite clause.
    - ὃς δὲ + finite -> include ὃς δὲ with that finite clause.
    - δὲ + finite may be reached either before or after generic particle carry.
    - καὶ ὃς μὲν + finite -> include καὶ as lead-in only when adjacent.
    """
    notes: List[str] = []
    pos = start_pos

    particle_pos = None

    if pos - 1 >= floor_pos and clean_surface(tokens[pos - 1].greek) in PAIR_PARTICLES:
        particle_pos = pos - 1
    elif clean_surface(tokens[pos].greek) in PAIR_PARTICLES:
        particle_pos = pos

    if particle_pos is None:
        return pos, notes

    head_pos = particle_pos - 1
    if head_pos >= floor_pos and clean_surface(tokens[head_pos].greek) in PAIR_HEADS:
        pos = head_pos
        notes.append(
            f"included paired particle head {tokens[head_pos].greek} {tokens[particle_pos].greek}"
        )

        lead_pos = head_pos - 1
        if lead_pos >= floor_pos and clean_surface(tokens[lead_pos].greek) in PAIR_LEAD_INS:
            pos = lead_pos
            notes.append(f"included paired particle lead-in {tokens[lead_pos].greek}")

    return pos, notes


def build_spans_for_verse(book: str, ch: str, vs: str, tokens: List[Token]) -> List[ClauseSpan]:
    finite_positions = [i for i, tok in enumerate(tokens) if is_finite(tok.rmac)]
    spans: List[ClauseSpan] = []

    if not finite_positions:
        return spans

    proposed_starts: List[int] = []
    proposed_ends: List[int] = []

    for idx, finite_pos in enumerate(finite_positions):
        start = finite_pos if idx == 0 else finite_positions[idx - 1] + 1
        end = finite_positions[idx + 1] - 1 if idx + 1 < len(finite_positions) else len(tokens) - 1

        proposed_starts.append(start)
        proposed_ends.append(end)

    for idx, finite_pos in enumerate(finite_positions):
        floor = proposed_starts[idx]
        start = finite_pos
        notes: List[str] = []

        start, paired_notes = paired_particle_start_left(tokens, start, floor)
        notes.extend(paired_notes)

        start, carry_notes = carry_start_left(tokens, start, floor)
        notes.extend(carry_notes)

        start, paired_notes = paired_particle_start_left(tokens, start, floor)
        notes.extend(paired_notes)

        start, connector_notes = connector_start_left(tokens, start, floor)
        notes.extend(connector_notes)

        if idx == 0:
            start = 0
            if finite_pos > 0:
                notes.append("first finite clause includes pre-anchor material")

        proposed_starts[idx] = start

    for idx in range(len(proposed_ends) - 1):
        proposed_ends[idx] = min(proposed_ends[idx], proposed_starts[idx + 1] - 1)

    for idx, finite_pos in enumerate(finite_positions, start=1):
        start = proposed_starts[idx - 1]
        end = proposed_ends[idx - 1]
        if end < start:
            end = finite_pos

        finite = tokens[finite_pos]
        span_tokens = tokens[start:end + 1]

        boundary_notes: List[str] = []
        if start == 0 and finite_pos > 0:
            boundary_notes.append("includes pre-anchor material")
        if idx < len(finite_positions):
            boundary_notes.append("ends before next finite anchor")
        else:
            boundary_notes.append("ends at verse boundary")

        local_start = finite_pos
        _, paired_notes = paired_particle_start_left(tokens, local_start, start)
        _, carry_notes = carry_start_left(tokens, local_start, start)
        _, paired_notes_after_carry = paired_particle_start_left(tokens, local_start - len(carry_notes), start)
        _, connector_notes = connector_start_left(tokens, local_start, start)
        boundary_notes.extend(carry_notes)
        boundary_notes.extend(paired_notes)
        boundary_notes.extend(paired_notes_after_carry)
        boundary_notes.extend(connector_notes)

        spans.append(
            ClauseSpan(
                book=book,
                ch=ch,
                vs=vs,
                clause_id=f"C{idx}",
                finite=finite,
                start=tokens[start].g_idx,
                end=tokens[end].g_idx,
                tokens=span_tokens,
                status="suggested-span",
                notes="; ".join(dict.fromkeys(boundary_notes)),
            )
        )

    return spans


def render_span_text(tokens: List[Token]) -> str:
    parts: List[str] = []
    for tok in tokens:
        if is_finite(tok.rmac):
            parts.append(f"=={tok.greek}==")
        else:
            parts.append(tok.greek)
    return " ".join(parts).strip()


def render_gidx(tokens: List[Token]) -> str:
    return ",".join(f"{tok.g_idx:02d}" for tok in tokens)


def export_book(book: str, interlinear_dir: Path, out_dir: Path) -> List[List[str]]:
    rows: List[List[str]] = []
    book_dir = interlinear_dir / book

    for json_path in sorted(book_dir.glob("*/*.json"), key=verse_sort_key):
        data = read_json(json_path)
        ch = str(data["chapter"])
        vs = str(data["verse"])
        tokens = iter_tokens(data)
        spans = build_spans_for_verse(book, ch, vs, tokens)

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
                render_span_text(span.tokens),
                span.status,
                span.notes,
            ])

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-clause-spans.tsv"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(rows)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 3.5: build Greek clause spans.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--interlinear-dir", default="MNA/data/interlinear")
    parser.add_argument("--out-dir", default="MNA/roots-greek/dataset")
    args = parser.parse_args()

    rows = export_book(args.book, Path(args.interlinear_dir), Path(args.out_dir))
    out_path = Path(args.out_dir) / f"{args.book}-clause-spans.tsv"

    print(f"Wrote {out_path}")
    print({"clause_spans": len(rows), "status": "suggested-span"})


if __name__ == "__main__":
    main()
