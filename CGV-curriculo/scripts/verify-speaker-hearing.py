#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical speaker / hearing verification for CGV manuals.

G7 and G8 must not PASS on agent self-report. This script is the witness.

    python3 scripts/verify-speaker-hearing.py \\
        --manual curriculo/23.Apocalipsis/manual/manual.md \\
        --gate g7 \\
        --out  curriculo/23.Apocalipsis/reports/SPEAKER_HEARING_REPORT.md

Exit codes:
  0  PASS (no blocking findings for the requested gate)
  1  FAIL (blocking findings)
  2  usage / IO error

What it can prove (deterministic):
  - Actores principales still on the student surface
  - Imperative *Ven* / *ven* triples that invent a subject (esp. Jesús)
  - Prose that asserts *Quien Ven es…* / denies the page's speakers
  - Vocative treated as triple subject (*Señor Jesús → ven*)
  - Stock wooden markers that bury hearing (*El recuento*, flecha lessons, etc.)

What it cannot prove:
  - every subtle inferred-speaker error that does not match these patterns
  - whether silence is *enough* for a scene's drama
  - theological truth of a comment that does not contradict named speakers

Those remain G9 human review — after this stream of mechanical gates.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

STOP_SECTIONS = (
    "\n## Actores",
    "\n## Movimiento",
    "\n## Convergencia",
    "\n## Tensión",
    "\n## Apéndice",
    "\n# Apéndices",
)

# Imperatives often split as their own H3/H4; a triple must not invent who commands.
BARE_VEN_H4 = re.compile(r"^####\s+\*?Ven\*?\s*$", re.I)
BARE_VEN_H3 = re.compile(r"^###\s+.*\bVen\b\s*$", re.I)
TRIPLE_VEN = re.compile(
    r"^\*\s+\*(?P<sub>[^*]+)\*\s*→\s*\*?Ven\*?\s*$",
    re.I,
)
TRIPLE_VEN_LOWER = re.compile(
    r"^\*\s+\*(?P<sub>[^*]+)\*\s*→\s*\*?ven\*?\s*$",
)
ACTORES = re.compile(r"^\*\s+Actores principales:\s*(.+)$")
QUIEN_VEN = re.compile(r"(?i)Qui[eé]n\s+Ven\s+es\b")
DENY_SPIRIT_BRIDE = re.compile(
    r"(?i)No\s+el\s+Esp[ií]ritu\s+ni\s+la\s+novia"
)
ATTRIB_TO_JESUS_VEN = re.compile(
    r"(?i)(Ven\s*[—\-–].*Yo,\s*Jes[uú]s|a\s+Yo,\s*Jes[uú]s|→\s*\*?Ven\*?.{0,40}Jes[uú]s)"
)
FALSE_2218 = re.compile(
    r"(?i)22:18\s*:\s*Yo,\s*Jes[uú]s,\s*doy\s+testimonio"
)
JESUS_NAME = re.compile(r"(?i)\bJes[uú]s\b")
SENOR_JESUS = re.compile(r"(?i)Se[nñ]or\s+Jes[uú]s")
VOCATIVE_H4 = re.compile(r"(?i)ven,?\s+Se[nñ]or\s+Jes[uú]s")

WOODEN_PATTERNS = {
    "el_recuento": re.compile(r"(?i)\bEl\s+recuento\b"),
    "flecha_detiene": re.compile(r"(?i)la\s+flecha\s+se\s+detiene"),
    "fuera_flecha": re.compile(r"(?i)fuera\s+de\s+la\s+flecha"),
    "esto_oir": re.compile(r"(?i)Esto\s+es\s+lo\s+que\s+hay\s+que\s+o[ií]r"),
    "todavia_no": re.compile(r"(?i)\btodav[ií]a\s+no\b"),
    "lo_alcanzado": re.compile(r"(?i)\bLo\s+alcanzado\b"),
    "primer_slot": re.compile(r"(?i)\bprimer\s+slot\b"),
}


@dataclass
class Finding:
    severity: str  # CRITICAL | HIGH | MEDIUM
    code: str
    line: int
    detail: str
    quote: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    h3: int = 0
    comments: int = 0

    def add(self, severity: str, code: str, line: int, detail: str, quote: str = "") -> None:
        self.findings.append(Finding(severity, code, line, detail, quote[:160]))


def student_body(raw: str) -> str:
    cut = len(raw)
    for marker in STOP_SECTIONS:
        i = raw.find(marker)
        if 0 < i < cut:
            cut = i
    return raw[:cut]


def is_comment(line: str) -> bool:
    return line.lstrip().startswith(">")


def analyze(path: Path) -> Report:
    raw = path.read_text(encoding="utf-8")
    body = student_body(raw)
    lines = body.splitlines()
    rep = Report()

    # Rolling context: last speech-frame subjects seen before a bare Ven unit.
    recent_speech: list[tuple[int, str]] = []  # (line, snippet)
    in_ven_unit = False
    ven_unit_start = 0
    last_h4 = ""

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue

        if s.startswith("### "):
            rep.h3 += 1
            in_ven_unit = bool(BARE_VEN_H3.match(s) or re.search(r"—\s*\*?Ven\*?\s*$", s))
            if in_ven_unit:
                ven_unit_start = i
            continue

        if s.startswith("#### "):
            last_h4 = s
            if BARE_VEN_H4.match(s):
                in_ven_unit = True
                ven_unit_start = i
            continue

        if is_comment(s) or s.startswith(">"):
            rep.comments += 1
            text = s.lstrip("> ").strip()
            for key, rx in WOODEN_PATTERNS.items():
                if rx.search(text):
                    rep.counts[key] += 1
            if QUIEN_VEN.search(text):
                rep.add(
                    "CRITICAL",
                    "quien_ven_es",
                    i,
                    "Prose asserts who performs *Ven* as if grammar; check speech frame on the page.",
                    text,
                )
            if DENY_SPIRIT_BRIDE.search(text) and (
                in_ven_unit or "Ven" in text or "ven" in text
            ):
                rep.add(
                    "CRITICAL",
                    "deny_named_speakers",
                    i,
                    "Prose denies Espíritu/novia as speakers of *Ven*.",
                    text,
                )
            if ATTRIB_TO_JESUS_VEN.search(text):
                rep.add(
                    "CRITICAL",
                    "ven_attributed_to_jesus",
                    i,
                    "*Ven* attributed to Jesús in commentary.",
                    text,
                )
            if FALSE_2218.search(text):
                rep.add(
                    "CRITICAL",
                    "false_2218_speaker",
                    i,
                    "Cross-ref invents *Yo, Jesús* as speaker of 22:18.",
                    text,
                )
            continue

        m_act = ACTORES.match(s)
        if m_act:
            rep.counts["actores_line"] += 1
            cast = m_act.group(1)
            rep.add(
                "HIGH",
                "actores_principales",
                i,
                "Actores principales still on student surface (G7 must delete).",
                cast[:120],
            )
            if in_ven_unit and JESUS_NAME.search(cast):
                rep.add(
                    "CRITICAL",
                    "actores_jesus_on_ven",
                    i,
                    "Actores names Jesús on a *Ven* unit — likely invented speaker.",
                    cast[:120],
                )
            continue

        m_trip = TRIPLE_VEN.match(s) or (
            TRIPLE_VEN_LOWER.match(s) if VOCATIVE_H4.search(last_h4) else None
        )
        if m_trip:
            sub = m_trip.group("sub").strip()
            # Vocative as subject of ven
            if SENOR_JESUS.search(sub) and VOCATIVE_H4.search(last_h4):
                rep.add(
                    "CRITICAL",
                    "vocative_as_subject",
                    i,
                    "Vocative *Señor Jesús* placed as subject of *ven*.",
                    s,
                )
            elif JESUS_NAME.search(sub) and (
                in_ven_unit or BARE_VEN_H4.match(last_h4) or "Ven" in last_h4
            ):
                rep.add(
                    "CRITICAL",
                    "jesus_subject_of_ven",
                    i,
                    f"Triple invents subject of *Ven*: {sub}",
                    s,
                )
            elif in_ven_unit and sub.lower() not in {"", "—", "-"}:
                # Any explicit subject on a bare Ven H4/H3 is suspicious when
                # speech was framed on a prior line — flag Jesús-adjacent already;
                # also flag if recent speech named different parties.
                if recent_speech and JESUS_NAME.search(sub):
                    rep.add(
                        "CRITICAL",
                        "jesus_subject_of_ven",
                        i,
                        f"Triple invents subject of *Ven*: {sub}",
                        s,
                    )
            continue

        # Track speech frames for context (dicen / diga / diciendo)
        if re.search(r"\b(dicen|diga|diciendo|dice)\b", s, re.I) and (
            "Espíritu" in s or "novia" in s or "oye" in s or "→" in s
        ):
            recent_speech.append((i, s[:120]))
            if len(recent_speech) > 8:
                recent_speech = recent_speech[-8:]

        # Leave ven unit after enough lines
        if in_ven_unit and i > ven_unit_start + 25:
            in_ven_unit = False

    return rep


def blocking_for_gate(rep: Report, gate: str) -> list[Finding]:
    """G7: speaker CRITICAL + Actores HIGH + stock hearing blockers.
    G8: G7 blockers + woodenness density thresholds.
    """
    block: list[Finding] = []
    for f in rep.findings:
        if f.severity == "CRITICAL":
            block.append(f)
        elif f.severity == "HIGH" and f.code == "actores_principales":
            block.append(f)

    # Stock phrases that mean hearing failed — block G7 when present at all
    # after editorial (Corrector duty).
    stock_zero = ("el_recuento", "esto_oir")
    for key in stock_zero:
        n = rep.counts.get(key, 0)
        if n > 0:
            block.append(
                Finding(
                    "HIGH",
                    f"wooden_{key}",
                    0,
                    f"{n} occurrence(s) of stock marker `{key}` (must be 0 for G7).",
                )
            )

    if gate == "g8":
        # Density: flecha lessons should not dominate remaining comments
        flecha = rep.counts.get("flecha_detiene", 0) + rep.counts.get("fuera_flecha", 0)
        alcanzado = rep.counts.get("lo_alcanzado", 0) + rep.counts.get("primer_slot", 0)
        todavia = rep.counts.get("todavia_no", 0)
        # Absolute caps — mechanical, book-size aware via H3 count
        h3 = max(rep.h3, 1)
        if flecha > max(5, h3 // 20):
            block.append(
                Finding(
                    "HIGH",
                    "wooden_flecha_density",
                    0,
                    f"{flecha} flecha-lesson hits (cap {max(5, h3 // 20)} for {h3} H3).",
                )
            )
        if alcanzado > max(5, h3 // 20):
            block.append(
                Finding(
                    "HIGH",
                    "wooden_slot_density",
                    0,
                    f"{alcanzado} slot-lesson hits (cap {max(5, h3 // 20)}).",
                )
            )
        if todavia > max(10, h3 // 10):
            block.append(
                Finding(
                    "HIGH",
                    "wooden_todavia_density",
                    0,
                    f"{todavia} *todavía no* hits (cap {max(10, h3 // 10)}).",
                )
            )

    return block


def write_report(path: Path, manual: Path, gate: str, rep: Report, blockers: list[Finding]) -> None:
    lines: list[str] = []
    w = lines.append
    w(f"# SPEAKER_HEARING_REPORT — gate `{gate}`")
    w("")
    w(f"Manual: `{manual}`")
    w(f"H3 units (student body): **{rep.h3}** · `>` comments: **{rep.comments}**")
    w("")
    verdict = "PASS" if not blockers else "FAIL"
    w(f"## Verdict: **{verdict}**")
    w("")
    w("This report is a **gate witness**, not human review. G9 still follows after G8.")
    w("")
    w("## Counts")
    w("")
    w("| Marker | n |")
    w("|---|---|")
    w(f"| Actores principales lines | {rep.counts.get('actores_line', 0)} |")
    for key in (
        "el_recuento",
        "esto_oir",
        "flecha_detiene",
        "fuera_flecha",
        "lo_alcanzado",
        "primer_slot",
        "todavia_no",
    ):
        w(f"| `{key}` | {rep.counts.get(key, 0)} |")
    w("")
    w("## Blocking findings")
    w("")
    if not blockers:
        w("- None for this gate.")
    else:
        for f in blockers:
            loc = f"L{f.line}" if f.line else "book"
            q = f" — `{f.quote}`" if f.quote else ""
            w(f"- **{f.severity}** `{f.code}` {loc}: {f.detail}{q}")
    w("")
    other = [f for f in rep.findings if f not in blockers]
    if other:
        w("## Non-blocking / already listed")
        w("")
        w(f"- Additional raw hits recorded: {len(rep.findings)} total findings before gate filter.")
        w("")
    w("## Blind spots")
    w("")
    w("- Subtle inferred speakers that do not match these regexes")
    w("- Whether silence is dramatically sufficient")
    w("- Correctness of architecture / telos")
    w("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical CGV speaker/hearing verification.")
    ap.add_argument("--manual", required=True, type=Path)
    ap.add_argument("--gate", choices=("g7", "g8"), default="g7")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    if not args.manual.is_file():
        print(f"error: no such manual: {args.manual}", file=sys.stderr)
        return 2

    rep = analyze(args.manual)
    blockers = blocking_for_gate(rep, args.gate)
    # Deduplicate actores spam: keep first 20 actores HIGH in blockers display,
    # but any count > 0 still fails.
    shown: list[Finding] = []
    actores_shown = 0
    for f in blockers:
        if f.code == "actores_principales":
            actores_shown += 1
            if actores_shown > 20:
                continue
        shown.append(f)
    if rep.counts.get("actores_line", 0) > 20:
        shown.append(
            Finding(
                "HIGH",
                "actores_principales_summary",
                0,
                f"{rep.counts['actores_line']} Actores principales lines (showing first 20).",
            )
        )

    out = args.out
    if out is None:
        # Default beside manual's course reports/
        course = args.manual.resolve().parent.parent
        out = course / "reports" / "SPEAKER_HEARING_REPORT.md"

    write_report(out, args.manual, args.gate, rep, shown if shown else blockers)

    n_block = len(blockers)
    print(f"→ {out}")
    print(
        f"  gate={args.gate}  H3={rep.h3}  actores={rep.counts.get('actores_line', 0)}  "
        f"blockers={n_block}  → {'PASS' if n_block == 0 else 'FAIL'}"
    )
    if n_block:
        # Print a compact sample
        for f in (shown or blockers)[:12]:
            loc = f"L{f.line}" if f.line else "book"
            print(f"  - {f.severity} {f.code} {loc}: {f.detail}")
        if n_block > 12:
            print(f"  … {n_block - 12} more")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
