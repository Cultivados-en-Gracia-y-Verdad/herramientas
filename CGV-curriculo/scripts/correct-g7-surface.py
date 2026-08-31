#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical Corrector for deterministic G7 FAIL findings.

When verify-speaker-hearing --gate g7 FAILs, this is the first Corrector pass:
delete what Corrector must never leave on the student surface.

    python3 scripts/correct-g7-surface.py \\
        --manual curriculo/23.Apocalipsis/manual/manual.md \\
        --dry-run

Applies (student body only, before ## Actores / # Apéndices):

  - Delete `* Actores principales: …` lines
  - Delete the immediately following `>` if it is Actores/recuento filler
  - Delete `>` that are only *El recuento…* / *Esto es lo que hay que oír*
  - Delete CRITICAL speaker-poison lines (Quien Ven es…; Ven —a Yo, Jesús;
    Yo, Jesús → Ven triples; Señor Jesús → ven when vocative)

Does NOT invent replacement prose. Agent Corrector still owns hearing rewrites
and any CRITICAL the regex misses. Re-run verify-g7 after this.

Exit: 0 wrote (or dry-run clean) · 1 nothing to do is still 0 · 2 usage
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STOP_SECTIONS = (
    "\n## Actores",
    "\n## Movimiento",
    "\n## Convergencia",
    "\n## Tensión",
    "\n## Apéndice",
    "\n# Apéndices",
)

ACTORES = re.compile(r"^(\s*)\* Actores principales:\s*.+$")
TRIPLE_JESUS_VEN = re.compile(
    r"^(\s*)\* \*Yo,\s*Jes[uú]s\* → \*?Ven\*?\s*$", re.I
)
TRIPLE_SENOR_VEN = re.compile(
    r"^(\s*)\* \*Se[nñ]or\s+Jes[uú]s\* → \*?ven\*?\s*$", re.I
)
COMMENT = re.compile(r"^(\s*)>\s?(.*)$")

DROP_COMMENT = re.compile(
    r"(?i)("
    r"\bEl\s+recuento\b|"
    r"Esto\s+es\s+lo\s+que\s+hay\s+que\s+o[ií]r|"
    r"Qui[eé]n\s+Ven\s+es\b|"
    r"Ven\s*[—\-–].*Yo,\s*Jes[uú]s|"
    r"\ba\s+Yo,\s*Jes[uú]s\b|"
    r"No\s+el\s+Esp[ií]ritu\s+ni\s+la\s+novia|"
    r"22:18\s*:\s*Yo,\s*Jes[uú]s,\s*doy\s+testimonio|"
    r"la\s+flecha\s+se\s+detiene|"
    r"fuera\s+de\s+la\s+flecha|"
    r"\blo\s+alcanzado\b|"
    r"\bprimer\s+slot\b|"
    r"no\s+cuelga\s+de|"
    r"completa\s+a|"
    r"acompa[nñ]a\s+a|"
    r"^quien(es)?\s+\S|"
    r"^ese\s+<u>|"
    r"no\s+abre\s+otr|"
    r"no\s+suma\s+otr|"
    r"queda\s+en\s+la\s+misma\s+l[ií]nea|"
    # stock closer in commentary only — not Scripture H4
    r"(?<!ha\s)(?<!han\s)todav[ií]a\s+no(?!\s+ha\s+venido)(?!\s+han\s+recibido)"
    r")"
)


def split_student(raw: str) -> tuple[str, str]:
    cut = len(raw)
    for marker in STOP_SECTIONS:
        i = raw.find(marker)
        if 0 < i < cut:
            cut = i
    return raw[:cut], raw[cut:]


def correct_body(body: str) -> tuple[str, dict[str, int]]:
    lines = body.splitlines(keepends=True)
    out: list[str] = []
    stats = {
        "actores": 0,
        "actores_follow_gt": 0,
        "stock_gt": 0,
        "jesus_ven_triple": 0,
        "vocative_triple": 0,
    }
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\n")

        if ACTORES.match(stripped):
            stats["actores"] += 1
            i += 1
            if i < len(lines):
                m = COMMENT.match(lines[i].rstrip("\n"))
                if m and (
                    DROP_COMMENT.search(m.group(2).strip())
                    or re.search(r"(?i)\brecuento\b|Actores|ocupa la l[ií]nea", m.group(2))
                ):
                    stats["actores_follow_gt"] += 1
                    i += 1
            continue

        if TRIPLE_JESUS_VEN.match(stripped):
            stats["jesus_ven_triple"] += 1
            i += 1
            if i < len(lines) and COMMENT.match(lines[i].rstrip("\n")):
                cm = COMMENT.match(lines[i].rstrip("\n"))
                if cm and DROP_COMMENT.search(cm.group(2).strip()):
                    stats["stock_gt"] += 1
                    i += 1
            continue

        if TRIPLE_SENOR_VEN.match(stripped):
            stats["vocative_triple"] += 1
            i += 1
            if i < len(lines) and COMMENT.match(lines[i].rstrip("\n")):
                cm = COMMENT.match(lines[i].rstrip("\n"))
                if cm and (
                    DROP_COMMENT.search(cm.group(2).strip())
                    or re.search(r"(?i)Qui[eé]n\s+ven\s+es", cm.group(2))
                ):
                    stats["stock_gt"] += 1
                    i += 1
            continue

        m = COMMENT.match(stripped)
        if m and DROP_COMMENT.search(m.group(2).strip()):
            stats["stock_gt"] += 1
            i += 1
            continue

        out.append(line)
        i += 1

    text = "".join(out)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical Corrector for G7 FAIL surface.")
    ap.add_argument("--manual", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.manual.is_file():
        print(f"error: no such manual: {args.manual}", file=sys.stderr)
        return 2

    raw = args.manual.read_text(encoding="utf-8")
    body, tail = split_student(raw)
    new_body, stats = correct_body(body)
    total = sum(stats.values())
    print(f"correct-g7-surface — {args.manual}")
    for k, v in stats.items():
        if v:
            print(f"  {k}: {v}")
    if total == 0:
        print("  nothing to correct (deterministic layer clean)")
        return 0

    if args.dry_run:
        print(f"  dry-run: would apply {total} removals")
        return 0

    args.manual.write_text(new_body + tail, encoding="utf-8")
    print(f"  wrote {total} removals — re-run: cgv verify-g7 / verify-g7-editorial.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
