#!/usr/bin/env python3
"""
MNA Markdown Validator

Validates cleaned MNA alignment files using MNA rules:

- One verse at a time
- Every Greek token must be mapped exactly once
- Every NBLA word must be accounted for by alignment or Extra
- No punctuation is counted as Spanish coverage
- Missing glosses must be Spanish, not English placeholders
- Merge pairs must be explicit and balanced
- No ROOTS/downstream sections are allowed

SPAN RULE ENFORCEMENT:

- direct = one Greek token to exactly one NBLA word
- expanded = one Greek token to two or more NBLA words
- merged-forward / merged-backward = multiple Greek tokens sharing one Spanish span
- missing = supplied Spanish only, parenthesized, and the exact supplied span must not appear in NBLA
- non-missing Spanish spans must appear contiguously in the NBLA verse

Usage:
  python3 validate_mna.py path/to/mna-clean.md
  python3 validate_mna.py path/to/mna-clean.md --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ALLOWED_TYPES = {
    "direct",
    "expanded",
    "merged-forward",
    "merged-backward",
    "missing",
}

FORBIDDEN_SECTIONS = {
    "verbos",
    "cláusulas",
    "clausulas",
    "conectores",
    "estructura",
    "roots",
}

FORBIDDEN_MISSING_GLOSSES = {
    "and",
    "but",
    "than",
    "the",
    "that",
    "would",
    "anything",
    "all",
    "by",
    "from",
    "of",
    "to",
    "in",
}

PUNCT_RE = re.compile(r"^[\W_]+$", re.UNICODE)

ALIGNMENT_LINE_RE = re.compile(
    r"^(?P<greek>.+?)\s*→\s*(?P<span>.+?)\s*\[(?P<atype>[a-z-]+)\]\s*$"
)

EXTRA_LINE_RE = re.compile(r"^(?P<span>.+?)\s*→\s*\[extra\]\s*$")

HEADING_RE = re.compile(r"^###\s+(?P<ref>.+?)\s*$")
SECTION_RE = re.compile(r"^####\s+(?P<section>.+?)\s*$")


def strip_diacritics(s: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_word(s: str) -> str:
    s = s.strip().lower()
    s = strip_diacritics(s)
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(
        r"^[^\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\wáéíóúüñÁÉÍÓÚÜÑ]+$",
        "",
        s,
        flags=re.UNICODE,
    )
    return s


def tokenize_greek(text: str) -> list[str]:
    raw = text.split()
    tokens: list[str] = []

    for tok in raw:
        cleaned = tok.strip()
        cleaned = cleaned.strip(".,;:··?¿!¡«»[](){}\"“”‘’")
        cleaned = cleaned.replace("⸂", "").replace("⸃", "")
        cleaned = cleaned.replace("⸀", "").replace("⸁", "")

        if cleaned:
            tokens.append(cleaned)

    return tokens


def tokenize_spanish_words(text: str) -> list[str]:
    text = re.sub(r"^[\[]|[\]]$", "", text.strip())

    words = re.findall(
        r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?",
        text,
    )

    return [normalize_word(w) for w in words if normalize_word(w)]


def is_parenthesized(span: str) -> bool:
    span = span.strip()
    return span.startswith("(") and span.endswith(")")


def span_words(span: str) -> list[str]:
    span = span.strip()

    if is_parenthesized(span):
        return []

    if PUNCT_RE.match(span):
        return []

    return tokenize_spanish_words(span)


def supplied_words(span: str) -> list[str]:
    span = span.strip()

    if is_parenthesized(span):
        span = span[1:-1]

    return tokenize_spanish_words(span)


def contains_contiguous_span(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return True

    if len(needle) > len(haystack):
        return False

    for i in range(0, len(haystack) - len(needle) + 1):
        if haystack[i : i + len(needle)] == needle:
            return True

    return False


def list_multiset_diff(a: Iterable[str], b: Iterable[str]) -> list[str]:
    counts: dict[str, int] = {}

    for x in b:
        counts[x] = counts.get(x, 0) + 1

    diff: list[str] = []

    for x in a:
        if counts.get(x, 0) > 0:
            counts[x] -= 1
        else:
            diff.append(x)

    return diff


@dataclass
class Alignment:
    greek: str
    span: str
    atype: str
    line_no: int


@dataclass
class Verse:
    ref: str
    start_line: int
    greek: str = ""
    nbla: str = ""
    alignments: list[Alignment] = field(default_factory=list)
    extras: list[tuple[str, int]] = field(default_factory=list)
    validation_status: str | None = None
    sections: list[str] = field(default_factory=list)


@dataclass
class Issue:
    ref: str
    line_no: int
    severity: str
    message: str


def parse_mna_markdown(text: str) -> list[Verse]:
    lines = text.splitlines()
    verses: list[Verse] = []

    current: Verse | None = None
    section: str | None = None
    capture_greek = False
    capture_nbla = False

    for idx, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)

        if heading:
            current = Verse(ref=heading.group("ref").strip(), start_line=idx)
            verses.append(current)
            section = None
            capture_greek = False
            capture_nbla = False
            continue

        if current is None:
            continue

        sec = SECTION_RE.match(line)

        if sec:
            section = sec.group("section").strip().lower()
            current.sections.append(section)
            capture_greek = False
            capture_nbla = False
            continue

        if line.strip().lower() == "greek:":
            capture_greek = True
            capture_nbla = False
            continue

        if line.strip().lower() == "nbla:":
            capture_nbla = True
            capture_greek = False
            continue

        if line.strip().startswith("####"):
            capture_greek = False
            capture_nbla = False

        if capture_greek:
            if line.strip():
                current.greek += (" " if current.greek else "") + line.strip()
            continue

        if capture_nbla:
            if not line.strip():
                capture_nbla = False
                continue

            current.nbla += (" " if current.nbla else "") + line.strip()
            continue

        if section == "alignment":
            m = ALIGNMENT_LINE_RE.match(line.strip())

            if m:
                current.alignments.append(
                    Alignment(
                        greek=m.group("greek").strip(),
                        span=m.group("span").strip(),
                        atype=m.group("atype").strip(),
                        line_no=idx,
                    )
                )

        elif section == "extra":
            m = EXTRA_LINE_RE.match(line.strip())

            if m:
                current.extras.append((m.group("span").strip(), idx))

        elif section == "validation":
            if "status:" in line.lower():
                current.validation_status = line.split(":", 1)[1].strip().upper()

    return verses


def validate_verse(v: Verse) -> list[Issue]:
    issues: list[Issue] = []

    def add(line: int, msg: str, severity: str = "ERROR") -> None:
        issues.append(Issue(v.ref, line, severity, msg))

    if not v.greek:
        add(v.start_line, "Missing Greek block")

    if not v.nbla:
        add(v.start_line, "Missing NBLA block")

    for sec in v.sections:
        if sec in FORBIDDEN_SECTIONS:
            add(v.start_line, f"Forbidden downstream section present: {sec}")

    greek_tokens = tokenize_greek(v.greek)
    aligned_greek = [a.greek for a in v.alignments]

    if len(aligned_greek) != len(greek_tokens):
        add(
            v.start_line,
            f"Greek token count mismatch: source has {len(greek_tokens)}, alignment has {len(aligned_greek)}",
        )

    for i, expected in enumerate(greek_tokens):
        if i >= len(aligned_greek):
            add(v.start_line, f"Missing alignment for Greek token #{i + 1}: {expected}")
            continue

        found = aligned_greek[i]

        if found != expected:
            add(
                v.alignments[i].line_no,
                f"Greek token sequence mismatch at #{i + 1}: expected '{expected}', found '{found}'",
            )

    nbla_words = tokenize_spanish_words(v.nbla)

    for a in v.alignments:
        words = span_words(a.span)

        if a.atype not in ALLOWED_TYPES:
            add(a.line_no, f"Invalid alignment type: [{a.atype}]")
            continue

        if a.atype == "missing" and not is_parenthesized(a.span):
            add(a.line_no, "[missing] span must be parenthesized")

        if a.atype != "missing" and is_parenthesized(a.span):
            add(a.line_no, "Only [missing] spans may be parenthesized")

        if a.atype == "missing":
            glosses = supplied_words(a.span)

            for gloss in glosses:
                if gloss in FORBIDDEN_MISSING_GLOSSES:
                    add(
                        a.line_no,
                        f"Missing gloss appears to be English, not Spanish: {a.span}",
                    )

            if glosses and contains_contiguous_span(nbla_words, glosses):
                add(
                    a.line_no,
                    f"missing_contains_exact_nbla_span: [missing] span appears in NBLA: {a.span}",
                )

        if a.atype != "missing":
            if not words:
                add(
                    a.line_no,
                    f"empty_span: non-missing alignment has no NBLA words: {a.span}",
                )

            elif not contains_contiguous_span(nbla_words, words):
                add(
                    a.line_no,
                    f"non_contiguous_or_missing_span: Spanish span is not contiguous in NBLA: {a.span}",
                )

        if a.atype == "direct":
            if len(words) != 1:
                add(
                    a.line_no,
                    f"direct_span_size: [direct] must cover exactly one NBLA word: {a.span}",
                )

        if a.atype == "expanded":
            if len(words) < 2:
                add(
                    a.line_no,
                    f"expanded_span_size: [expanded] must cover two or more NBLA words: {a.span}",
                )

        if a.atype in {"merged-forward", "merged-backward"}:
            if len(words) < 1:
                add(
                    a.line_no,
                    f"merged_empty_span: merge alignment must carry a Spanish span: {a.span}",
                )

    for i, a in enumerate(v.alignments):
        if a.atype == "merged-forward":
            if i + 1 >= len(v.alignments):
                add(a.line_no, "merged-forward must be followed by merged-backward")
                continue

            nxt = v.alignments[i + 1]

            if nxt.atype != "merged-backward":
                add(a.line_no, "merged-forward must be followed by merged-backward")

            elif nxt.span != a.span:
                add(
                    a.line_no,
                    "merged-forward and following merged-backward must share identical Spanish span",
                )

        if a.atype == "merged-backward":
            if i == 0:
                add(a.line_no, "merged-backward must follow merged-forward or merged-backward")
                continue

            prev = v.alignments[i - 1]

            if prev.atype not in {"merged-forward", "merged-backward"}:
                add(a.line_no, "merged-backward must follow merged-forward or merged-backward")

    covered_words: list[str] = []

    for a in v.alignments:
        if a.atype == "merged-backward":
            continue

        covered_words.extend(span_words(a.span))

    for span, line_no in v.extras:
        extra_words = span_words(span)

        if extra_words and not contains_contiguous_span(nbla_words, extra_words):
            add(
                line_no,
                f"extra_non_contiguous_or_missing_span: Extra span is not contiguous in NBLA: {span}",
            )

        covered_words.extend(extra_words)

    nbla_sorted = sorted(nbla_words)
    covered_sorted = sorted(covered_words)

    if nbla_sorted != covered_sorted:
        missing = list_multiset_diff(nbla_words, covered_words)
        extra = list_multiset_diff(covered_words, nbla_words)

        if missing:
            add(v.start_line, "Uncovered NBLA word(s): " + ", ".join(missing))

        if extra:
            add(v.start_line, "Covered word(s) not found in NBLA: " + ", ".join(extra))

    if v.validation_status != "LOCKED":
        add(
            v.start_line,
            "Validation status must be LOCKED after passing cleanup",
            severity="WARN",
        )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate cleaned MNA Markdown alignment files."
    )

    parser.add_argument("path", type=Path, help="Path to cleaned MNA Markdown file")
    parser.add_argument("--verbose", action="store_true", help="Print per-verse pass summaries")

    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: file not found: {args.path}", file=sys.stderr)
        return 1

    text = args.path.read_text(encoding="utf-8")
    verses = parse_mna_markdown(text)

    if not verses:
        print(
            "ERROR: no verses found. Expected headings like: ### 1 Corintios 1:1",
            file=sys.stderr,
        )
        return 1

    all_issues: list[Issue] = []

    for verse in verses:
        issues = validate_verse(verse)
        all_issues.extend(issues)

        if args.verbose and not issues:
            print(f"PASS {verse.ref}")

    errors = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARN"]

    for issue in all_issues:
        print(f"{issue.severity}: {issue.ref}: line {issue.line_no}: {issue.message}")

    print("---")
    print(f"Verses checked: {len(verses)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
