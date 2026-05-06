#!/usr/bin/env python3
"""
Generate downstream test reports from locked MNA files.

Reports:
- interlinear view with Greek, MorphGNT, lemma, Spanish, and alignment type
- finite verbs confirmed by MorphGNT finite RMAC morphology
- connectors confirmed by Greek/MorphGNT connector morphology or known connector lemmas
- NBLA Extra spans not attached to a Greek token

Usage:
  python3 MNA/generate_mna_reports.py MNA/data/output/1corintios-1-4.mna.locked.md \
    --morph MNA/data/MorphGNT/1corintios-morphgnt.txt \
    --out-dir MNA/data/output/reports
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from core.morph_loader import load_morphgnt
from core.ref_converter import convert_ref
from validate_mna import Alignment, parse_mna_markdown


CONNECTOR_FORMS = {
    "αλλα",
    "αλλ",
    "γαρ",
    "δε",
    "διο",
    "ει",
    "ειτε",
    "επει",
    "επειδη",
    "εως",
    "ινα",
    "και",
    "μη",
    "ουδε",
    "ουτε",
    "οτι",
    "οταν",
    "ουν",
    "ωστε",
}


@dataclass
class ReportRow:
    ref: str
    greek: str
    spanish: str
    morph: str
    lemma: str
    note: str


def strip_diacritics(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_greek(s: str) -> str:
    s = strip_diacritics(s.strip().lower())
    s = re.sub(r"[·.,;:!?¿¡⸀⸁⸂⸃()\[\]«»“”\"'’ʼ]", "", s)
    return s.strip()


def to_rmac(code: str) -> str:
    code = code.strip()

    if not code.startswith("V"):
        return code

    code = code.replace("--", "-").strip("-")
    parts = [p for p in code.split("-") if p]

    if len(parts) == 2 and parts[0] == "V":
        body = parts[1]
        if len(body) == 6:
            return f"V-{body[:3]}-{body[3:]}"
        if len(body) == 3:
            return f"V-{body}"
        return code

    if len(parts) == 3 and parts[0] == "V":
        middle = parts[1]
        last = parts[2]
        if len(middle) == 4 and middle[0].isdigit():
            return f"V-{middle[1:]}-{middle[0]}{last}"
        return f"V-{middle}-{last}"

    return code


def is_finite_verb(code: str) -> bool:
    if not code.startswith("V"):
        return False

    rmac = to_rmac(code)
    parts = [p for p in rmac.split("-") if p]
    if len(parts) < 2:
        return False

    tvm = parts[1]
    return len(tvm) == 3 and tvm[2] in {"I", "S", "M", "O"}


def is_connector(greek: str, morph: str, lemma: str) -> bool:
    if morph.startswith("V"):
        return False

    if morph.startswith("C"):
        return True

    return normalize_greek(greek) in CONNECTOR_FORMS or normalize_greek(lemma) in CONNECTOR_FORMS


def mna_ref_to_key(ref: str) -> str:
    return convert_ref(ref.replace("1 Corintios", "1corintios"))


def aligned_rows(
    mna_path: Path,
    morph_path: Path,
) -> tuple[list[ReportRow], list[ReportRow], list[ReportRow], list[ReportRow]]:
    morph = load_morphgnt(morph_path)
    verses = parse_mna_markdown(mna_path.read_text(encoding="utf-8"))
    interlinear_rows: list[ReportRow] = []
    finite_rows: list[ReportRow] = []
    connector_rows: list[ReportRow] = []
    extra_rows: list[ReportRow] = []

    for verse in verses:
        morph_tokens = morph[mna_ref_to_key(verse.ref)]
        for index, alignment in enumerate(verse.alignments):
            if index >= len(morph_tokens):
                continue

            morph_greek, morph_code, lemma = morph_tokens[index]
            if normalize_greek(alignment.greek) != normalize_greek(morph_greek):
                raise ValueError(
                    f"{verse.ref} token #{index + 1} mismatch: "
                    f"MNA {alignment.greek} != MorphGNT {morph_greek}"
                )

            row = ReportRow(
                ref=verse.ref,
                greek=alignment.greek,
                spanish=alignment.span,
                morph=to_rmac(morph_code),
                lemma=lemma,
                note=alignment.atype,
            )

            interlinear_rows.append(row)
            if is_finite_verb(morph_code):
                finite_rows.append(row)
            if is_connector(alignment.greek, morph_code, lemma):
                connector_rows.append(row)

        for span, _line_no in verse.extras:
            extra_rows.append(
                ReportRow(
                    ref=verse.ref,
                    greek="[extra]",
                    spanish=span,
                    morph="",
                    lemma="",
                    note="extra",
                )
            )

    return interlinear_rows, finite_rows, connector_rows, extra_rows


def write_report(path: Path, title: str, rows: list[ReportRow]) -> None:
    lines = [
        f"# {title}",
        "",
        f"Rows: {len(rows)}",
        "",
        "| reference | Greek | Spanish | MorphGNT | lemma | alignment |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in [row.ref, row.greek, row.spanish, row.morph, row.lemma, row.note]
            )
            + " |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MNA downstream reports.")
    parser.add_argument("mna", type=Path, help="Locked MNA Markdown file")
    parser.add_argument("--morph", required=True, type=Path, help="MorphGNT file")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    interlinear_rows, finite_rows, connector_rows, extra_rows = aligned_rows(args.mna, args.morph)

    write_report(args.out_dir / "1corintios-1-4.interlinear.md", "1 Corinthians 1-4 Interlinear View", interlinear_rows)
    write_report(args.out_dir / "1corintios-1-4.finite-verbs.md", "1 Corinthians 1-4 Finite Verbs", finite_rows)
    write_report(args.out_dir / "1corintios-1-4.connectors.md", "1 Corinthians 1-4 Greek-Confirmed Connectors", connector_rows)
    write_report(args.out_dir / "1corintios-1-4.extras.md", "1 Corinthians 1-4 NBLA Extra Spans", extra_rows)

    print(f"Interlinear rows: {len(interlinear_rows)}")
    print(f"Finite verbs: {len(finite_rows)}")
    print(f"Connectors: {len(connector_rows)}")
    print(f"Extras: {len(extra_rows)}")
    print(f"Wrote reports to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
