#!/usr/bin/env python3
"""
Audit MNA Markdown files and print only actionable errors.

The report is intentionally narrow:

reference | Greek token | current Spanish | error type | suggested fix

Usage:
  python3 MNA/audit_mna.py MNA/data/fixtures/valid-1cor-*.md
  python3 MNA/audit_mna.py --morph MNA/data/MorphGNT/1corintios-morphgnt.txt MNA/data/fixtures/valid-1cor-*.md
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from core.morph_loader import load_morphgnt
from core.ref_converter import convert_ref
from validate_mna import Alignment, Issue, parse_mna_markdown, tokenize_greek, validate_verse


@dataclass
class AuditError:
    ref: str
    greek: str
    spanish: str
    error_type: str
    suggested_fix: str


def strip_diacritics(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_greek_token(s: str) -> str:
    s = strip_diacritics(s.strip().lower())
    s = re.sub(r"[·.,;:!?¿¡⸀⸁⸂⸃()\[\]«»“”\"'’ʼ]", "", s)
    return s.strip()


def issue_alignment(issue: Issue, alignments: list[Alignment]) -> Alignment | None:
    for alignment in alignments:
        if alignment.line_no == issue.line_no:
            return alignment
    return None


def audit_validation_errors(path: Path) -> list[AuditError]:
    errors: list[AuditError] = []
    verses = parse_mna_markdown(path.read_text(encoding="utf-8"))

    for verse in verses:
        for issue in validate_verse(verse):
            if issue.severity != "ERROR":
                continue

            alignment = issue_alignment(issue, verse.alignments)
            errors.append(
                AuditError(
                    ref=issue.ref,
                    greek=alignment.greek if alignment else "",
                    spanish=alignment.span if alignment else "",
                    error_type=issue.message,
                    suggested_fix=suggest_fix(issue.message),
                )
            )

    return errors


def suggest_fix(message: str) -> str:
    if message.startswith("Uncovered NBLA word"):
        return "Map the NBLA word to a Greek token or add it under Extra."
    if message.startswith("Covered word"):
        return "Remove duplicate coverage or move unsupported words out of alignment."
    if message.startswith("Greek token"):
        return "Compare the Greek block and Alignment sequence; restore exact token order."
    if "merged" in message:
        return "Make merge spans adjacent and identical, using merged-forward then merged-backward."
    if "missing" in message.lower():
        return "Use a minimal Spanish supplied gloss in parentheses with [missing]."
    if "LOCKED" in message:
        return "Set Status: LOCKED only after all errors are fixed."
    return "Review this verse against the MNA rules."


def audit_morph_sequence(path: Path, morph: dict[str, list[tuple[str, str, str]]]) -> list[AuditError]:
    errors: list[AuditError] = []
    verses = parse_mna_markdown(path.read_text(encoding="utf-8"))

    for verse in verses:
        try:
            morph_ref = convert_ref(verse.ref.replace("1 Corintios", "1corintios"))
        except ValueError:
            errors.append(
                AuditError(
                    ref=verse.ref,
                    greek="",
                    spanish="",
                    error_type="MorphGNT reference conversion failed",
                    suggested_fix="Normalize the verse heading or update ref_converter.",
                )
            )
            continue

        morph_tokens = morph.get(morph_ref)
        if morph_tokens is None:
            errors.append(
                AuditError(
                    ref=verse.ref,
                    greek="",
                    spanish="",
                    error_type="MorphGNT verse missing",
                    suggested_fix="Check the MorphGNT source file for this reference.",
                )
            )
            continue

        mna_tokens = tokenize_greek(verse.greek)
        morph_greek = [token[0] for token in morph_tokens]

        if len(mna_tokens) != len(morph_greek):
            errors.append(
                AuditError(
                    ref=verse.ref,
                    greek="",
                    spanish="",
                    error_type=f"MorphGNT token count mismatch: MNA has {len(mna_tokens)}, MorphGNT has {len(morph_greek)}",
                    suggested_fix="Compare SBLGNT and MorphGNT tokenization for this verse.",
                )
            )

        for idx, mna_token in enumerate(mna_tokens):
            if idx >= len(morph_greek):
                break
            if normalize_greek_token(mna_token) != normalize_greek_token(morph_greek[idx]):
                alignment = verse.alignments[idx] if idx < len(verse.alignments) else None
                errors.append(
                    AuditError(
                        ref=verse.ref,
                        greek=mna_token,
                        spanish=alignment.span if alignment else "",
                        error_type=f"MorphGNT token mismatch at #{idx + 1}: expected {morph_greek[idx]}",
                        suggested_fix="Adjust the MNA Greek token to match MorphGNT/SBLGNT order.",
                    )
                )

    return errors


def print_report(errors: list[AuditError]) -> None:
    if not errors:
        print("No audit errors found.")
        return

    print("| reference | Greek token | current Spanish | error type | suggested fix |")
    print("|---|---|---|---|---|")
    for error in errors:
        print(
            "| "
            + " | ".join(
                escape_cell(value)
                for value in [
                    error.ref,
                    error.greek,
                    error.spanish,
                    error.error_type,
                    error.suggested_fix,
                ]
            )
            + " |"
        )


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MNA Markdown files and print only errors.")
    parser.add_argument("paths", nargs="+", type=Path, help="MNA Markdown files to audit")
    parser.add_argument("--morph", type=Path, help="Optional MorphGNT file for Greek token sequence verification")
    args = parser.parse_args()

    all_errors: list[AuditError] = []
    morph = load_morphgnt(args.morph) if args.morph else None

    for path in args.paths:
        all_errors.extend(audit_validation_errors(path))
        if morph is not None:
            all_errors.extend(audit_morph_sequence(path, morph))

    print_report(all_errors)
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
