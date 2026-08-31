#!/usr/bin/env python3
"""Remove stock mechanical connector glosses from CGV manual `>` lines."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STOCK_SENTENCE = re.compile(
    r"|".join(
        [
            r"^Ese <u>[^<]+</u> no (?:abre|suma) otr[oa]\b",
            r"^Ese <u>[^<]+</u> no sigue el\b",
            r"^<u>Así</u> también no abre\b",
            r"^Este <u>que</u> no abre otr[oa]\b",
            r"^No suma otr[oa]\b",
            r"^No cuelga suelto\b",
            r"^No queda suelto\b",
            r"^No queda muda\b",
            r"^Eso decían\b",
            r"^El resto, todavía no\.?$",
            r"^Qué, todavía no\.?$",
            r"^Quién, todavía no\.?$",
            r"^Quiénes, todavía no\.?$",
            r"^Qué dice, todavía no\.?$",
            r"^Quién es ella, abajo\.?$",
            r"^Por qué, abajo\.?$",
            r"^Cómo, anidado\.?$",
            r"^Dónde, todavía no\.?$",
            r"^Quienes ocupan la línea\b",
            r"^Lo alcanzado:",
            r"^Ya no es .+\. Quienes ocupan la línea\b",
            r"^Ya no son .+\. Quienes ocupan la línea\b",
        ]
    ),
    re.I,
)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def is_stock(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return True
    if STOCK_SENTENCE.search(s):
        return True
    if re.match(
        r"^(?:Ese <u>[^<]+</u> no (?:abre|suma) otr[oa]|No suma otr[oa]|Este <u>que</u> no abre otr[oa]).*$",
        s,
        re.I,
    ):
        return True
    return False


def clean_body(body: str) -> str | None:
    body = body.strip()
    if not body:
        return None
    kept = [s for s in split_sentences(body) if not is_stock(s)]
    if not kept:
        return None
    return " ".join(kept)


def process_line(line: str) -> str | None:
    m = re.match(r"^(\s*)>\s*(.*)$", line)
    if not m:
        return line
    indent, body = m.group(1), m.group(2)
    cleaned = clean_body(body)
    if cleaned is None:
        return None
    if cleaned == body.strip():
        return line
    return f"{indent}> {cleaned}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lines = args.manual.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    removed = trimmed = kept = 0

    for line in lines:
        if re.match(r"^\s*>", line):
            new_line = process_line(line)
            if new_line is None:
                removed += 1
                continue
            if new_line != line:
                trimmed += 1
            else:
                kept += 1
            out.append(new_line)
        else:
            out.append(line)

    # collapse 3+ consecutive blank lines to 1 inside body only
    compact: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                compact.append(line)
        else:
            blank_run = 0
            compact.append(line)

    text = "\n".join(compact)
    if args.manual.read_text(encoding="utf-8").endswith("\n"):
        text += "\n"

    if args.dry_run:
        print(f"Would remove {removed} comment lines, trim {trimmed}, keep {kept}")
        return 0

    args.manual.write_text(text, encoding="utf-8")
    print(f"Removed {removed} stock-only comment lines")
    print(f"Trimmed stock sentences from {trimmed} lines")
    print(f"Left {kept} comment lines unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
