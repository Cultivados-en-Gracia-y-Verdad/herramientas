#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Indentation witness for the CGV manual pipeline.

    OUTLINE (Arquitecto, generated)  ->  this script  ->  Editor reads the surface

Structural depth belongs to the outline. `{NN.Curso}/architecture/{book}-outline.md`
is emitted from clause data; the manuscript's indentation is a copy of it that drifts
every time an agent nests a line by hand. This script compares the two and states
exactly where they disagree.

    python3 scripts/verify-indentation.py \
        --manual  "curriculo/23.Apocalipsis/manual/apocalipsis-manual.md" \
        --outline "curriculo/23.Apocalipsis/architecture/apocalipsis-outline.md" \
        --log     "curriculo/23.Apocalipsis/reports/INDENT_LOG.md"

    ... --apply        rewrite the manual's leading whitespace in place
    ... --dry-run      (default) report only, touch nothing

DESIGN NOTE -- why this script never prints PASS
------------------------------------------------
It compares leading whitespace against one witness. It cannot see whether the outline
itself is right, whether an Escriba split belongs where it landed, or whether a `>` was
written for the depth it now sits at. It states counts and names its blind spots. The
gate is Editor reading the surface, with this as the other witness
(`MANUAL_STANDARD.md` Section 2).

WHAT IT CHANGES
---------------
Leading spaces. Nothing else. No character after the first non-space is ever read back
out to the file: markers, Scripture, Greek, `[^tag]`, clause identifiers and `>` wording
pass through byte-identical. A run that alters a single non-whitespace byte is a bug and
aborts before writing.

Exit codes:  0 log written   2 usage / IO error
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

INDENT_UNIT = 2

# The student-surface contract stops at the first generated workshop section.
# Same boundary as run-manual-checks.py and verify-skeleton-h4-packaging.py --
# a third checker that cuts somewhere else will disagree with both for a reason
# that has nothing to do with the manuscript.
WORKSHOP_CUT = re.compile(
    r"^(## (Actores|Movimiento|Convergencia|Tensión|Apéndice)\b|# Apéndices\b)"
)

RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
RE_MARKER = re.compile(r"^( *)([-+])\s+(.*)$")
RE_EVIDENCE = re.compile(r"^( *)\*\s+(.*)$")
RE_COMMENT = re.compile(r"^( *)>\s?(.*)$")
RE_CONTEXT = re.compile(r"^=\s")
RE_CLAUSE_ID = re.compile(r"\b(\d+:\d+:\d+)\b")
RE_FOOTREF = re.compile(r"\[\^[^\]]+\]")


def norm(text: str) -> str:
    """Identity of a Scripture line for matching. Never written back to the file."""
    t = unicodedata.normalize("NFC", text)
    t = RE_FOOTREF.sub("", t)
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"[«»“”\"']", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class Line:
    __slots__ = ("n", "raw", "kind", "indent", "marker", "text")

    def __init__(self, n: int, raw: str) -> None:
        self.n = n
        self.raw = raw
        self.kind = "other"
        self.indent = 0
        self.marker = ""
        self.text = ""

        if not raw.strip():
            self.kind = "blank"
            return
        if RE_CONTEXT.match(raw):
            self.kind = "context"
            return
        m = RE_HEADING.match(raw)
        if m:
            self.kind = "h" + str(len(m.group(1)))
            self.marker = m.group(1)
            self.text = m.group(2)
            return
        m = RE_MARKER.match(raw)
        if m:
            self.kind = "marker"
            self.indent = len(m.group(1))
            self.marker = m.group(2)
            self.text = m.group(3)
            return
        m = RE_EVIDENCE.match(raw)
        if m:
            self.kind = "evidence"
            self.indent = len(m.group(1))
            self.marker = "*"
            self.text = m.group(2)
            return
        m = RE_COMMENT.match(raw)
        if m:
            self.kind = "comment"
            self.indent = len(m.group(1))
            self.marker = ">"
            self.text = m.group(2)
            return
        self.indent = len(raw) - len(raw.lstrip(" "))
        self.text = raw.strip()


def read_lines(path: Path) -> list[Line]:
    try:
        raw = path.read_text(encoding="utf-8").split("\n")
    except OSError as exc:
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        raise SystemExit(2)
    return [Line(i + 1, r) for i, r in enumerate(raw)]


def unit_key(h3_text: str) -> str:
    """Clause identifier if the H3 carries one; otherwise the normalized title.

    Identifiers are protected data and survive renaming; titles do not.
    """
    m = RE_CLAUSE_ID.search(h3_text)
    return m.group(1) if m else norm(h3_text)


def index_outline(lines: list[Line]) -> tuple[dict, int]:
    """unit key -> ordered list of [marker, normalized text, depth, consumed]."""
    units: dict[str, list] = {}
    current = None
    counted = 0
    for ln in lines:
        if WORKSHOP_CUT.match(ln.raw):
            break
        if ln.kind == "h3":
            current = unit_key(ln.text)
            units.setdefault(current, [])
        elif ln.kind == "h4" and current is not None:
            units[current].append(["####", norm(ln.text), 0, False])
            counted += 1
        elif ln.kind == "marker" and current is not None:
            units[current].append([ln.marker, norm(ln.text), ln.indent, False])
            counted += 1
    return units, counted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manual", required=True, type=Path)
    ap.add_argument("--outline", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--apply", action="store_true", help="rewrite leading whitespace in the manual")
    args = ap.parse_args()

    manual = read_lines(args.manual)
    outline_lines = read_lines(args.outline)
    units, outline_counted = index_outline(outline_lines)

    body_end = len(manual)
    for ln in manual:
        if WORKSHOP_CUT.match(ln.raw):
            body_end = ln.n - 1
            break

    changes: list[tuple] = []          # (lineno, old, new, marker, text)
    siblings: list[tuple] = []         # orphans given sibling depth
    unknown_units: list[str] = []      # H3 the outline does not contain
    missing: list[tuple] = []          # outline lines with no manual line
    clamped: list[tuple] = []

    new_raw = [ln.raw for ln in manual]

    current_unit = None
    known_unit = False
    delta = 0
    last_target = 0

    for ln in manual:
        if ln.n > body_end:
            break

        if ln.kind == "h3":
            current_unit = unit_key(ln.text)
            known_unit = current_unit in units
            if not known_unit:
                unknown_units.append(ln.text.strip())
            delta = 0
            last_target = 0
            continue
        if ln.kind in ("h1", "h2"):
            delta = 0
            last_target = 0
            continue
        if ln.kind in ("blank", "context", "other"):
            continue

        if ln.kind == "h4":
            # An H4 anchors its unit at column 0 in both witnesses.
            delta = 0
            last_target = 0
            continue

        if ln.kind == "marker":
            if not known_unit:
                delta = 0
                last_target = ln.indent
                continue
            key = norm(ln.text)
            target = None
            for entry in units[current_unit]:
                if not entry[3] and entry[0] == ln.marker and entry[1] == key:
                    entry[3] = True
                    target = entry[2]
                    break
            if target is None:
                # Escriba split or renamed this line. Sibling depth: it takes the
                # depth of the line it was split from -- the nearest marker above.
                target = last_target
                siblings.append((ln.n, ln.indent, target, ln.marker, ln.text))
            if target < 0:
                clamped.append((ln.n, target))
                target = 0
            delta = target - ln.indent
            last_target = target
            if delta:
                changes.append((ln.n, ln.indent, target, ln.marker, ln.text))
                new_raw[ln.n - 1] = " " * target + ln.raw.lstrip(" ")
            continue

        if ln.kind in ("evidence", "comment") and delta:
            # Attached lines ride with their host. Their offset from the host is
            # the writer's, not ours -- we move them, we do not re-space them.
            target = ln.indent + delta
            if target < 0:
                clamped.append((ln.n, target))
                target = 0
            new_raw[ln.n - 1] = " " * target + ln.raw.lstrip(" ")

    for key, entries in units.items():
        for marker, text, depth, consumed in entries:
            if not consumed and marker != "####":
                missing.append((key, marker, depth, text))

    # Re-indentation can strand a line on the slide above it: an outdent must
    # open a new slide (MANUAL_STANDARD Section 3). Report, never insert -- a blank
    # line is a slide decision and belongs to Editor's reading.
    outdents: list[tuple] = []
    for i in range(1, min(body_end, len(new_raw))):
        cur, prev = new_raw[i], new_raw[i - 1]
        if not cur.strip() or not prev.strip():
            continue
        ci = len(cur) - len(cur.lstrip(" "))
        pi = len(prev) - len(prev.lstrip(" "))
        if ci < pi:
            outdents.append((i + 1, pi, ci, cur.strip()[:70]))

    # A run that alters a non-whitespace byte is a bug, not an edit.
    for old, new in zip((l.raw for l in manual), new_raw):
        if old.strip() != new.strip():
            sys.stderr.write("ABORT: non-whitespace change at %r -> %r\n" % (old, new))
            return 2

    out = []
    out.append("# INDENT LOG — %s" % args.manual.name)
    out.append("")
    out.append("Outline: `%s`" % args.outline)
    out.append("Manual: `%s`" % args.manual)
    out.append("Mode: **%s**" % ("APPLIED — the manual was rewritten" if args.apply else "dry run — nothing was written"))
    out.append("")
    out.append("## Counts")
    out.append("")
    out.append("| | |")
    out.append("|---|---|")
    out.append("| outline structural lines | %d |" % outline_counted)
    out.append("| manual lines audited (student body, through line %d) | %d |" % (body_end, sum(1 for l in manual if l.n <= body_end and l.kind == "marker")))
    out.append("| depths corrected to the outline | %d |" % len(changes))
    out.append("| lines not in the outline, given sibling depth | %d |" % len(siblings))
    out.append("| outline lines with no match in the manual | %d |" % len(missing))
    out.append("| H3 units the outline does not contain (left alone) | %d |" % len(unknown_units))
    out.append("| outdents now sharing a slide with the line above | %d |" % len(outdents))
    out.append("")

    out.append("## Depths corrected")
    out.append("")
    if changes:
        out.append("| line | was | now | |")
        out.append("|---|---|---|---|")
        for n, old, new, marker, text in changes:
            out.append("| %d | %d | %d | `%s %s` |" % (n, old, new, marker, text[:80].replace("|", "\\|")))
    else:
        out.append("None. Every matched line already sat at the outline's depth.")
    out.append("")

    out.append("## Sibling depth assigned")
    out.append("")
    out.append("The outline does not contain these lines — an Escriba split, a renamed phrase, "
               "or an orphan. Each took the depth of the marker line above it. **Read them.** "
               "A split that belongs one level deeper will not look wrong to this script.")
    out.append("")
    if siblings:
        out.append("| line | was | now | |")
        out.append("|---|---|---|---|")
        for n, old, new, marker, text in siblings:
            out.append("| %d | %d | %d | `%s %s` |" % (n, old, new, marker, text[:80].replace("|", "\\|")))
    else:
        out.append("None.")
    out.append("")

    out.append("## Outdents that now start mid-slide")
    out.append("")
    out.append("A line that outdents from the line above must open a new slide. Re-indentation "
               "can create these. Editor inserts the blank line; this script does not.")
    out.append("")
    if outdents:
        out.append("| line | above | this | |")
        out.append("|---|---|---|---|")
        for n, pi, ci, text in outdents:
            out.append("| %d | %d | %d | `%s` |" % (n, pi, ci, text.replace("|", "\\|")))
    else:
        out.append("None.")
    out.append("")

    out.append("## Outline lines with no match in the manual")
    out.append("")
    out.append("Either the manuscript lost a line, or Escriba rewrote it. **Not repaired here** — "
               "restoring Scripture is not a whitespace edit. Escalate to Escriba.")
    out.append("")
    if missing:
        out.append("| unit | | |")
        out.append("|---|---|---|")
        for key, marker, depth, text in missing:
            out.append("| %s | `%s` (depth %d) | %s |" % (key, marker, depth, text[:80].replace("|", "\\|")))
    else:
        out.append("None.")
    out.append("")

    out.append("## Units the outline does not contain")
    out.append("")
    if unknown_units:
        out.append("Left untouched, and therefore unaudited:")
        out.append("")
        for t in unknown_units:
            out.append("- %s" % t)
    else:
        out.append("None.")
    out.append("")

    out.append("## Blind spots of this run")
    out.append("")
    out.append("- Whether the outline itself is right. It is one witness, not the verdict.")
    out.append("- Whether a sibling-depth line belongs at that depth. The script cannot read a clause.")
    out.append("- Whether a `>` comment still reads correctly at its new depth.")
    out.append("- Everything from line %d on — generated workshop sections, not audited by design." % (body_end + 1))
    out.append("- Attached `*` and `>` lines moved with their host. Their offset from the host was not checked.")
    out.append("")
    out.append("**This is not a PASS.** Read the surface.")
    out.append("")

    try:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text("\n".join(out), encoding="utf-8")
    except OSError as exc:
        sys.stderr.write("cannot write %s: %s\n" % (args.log, exc))
        return 2

    if args.apply and (changes or siblings):
        try:
            args.manual.write_text("\n".join(new_raw), encoding="utf-8")
        except OSError as exc:
            sys.stderr.write("cannot write %s: %s\n" % (args.manual, exc))
            return 2

    sys.stderr.write(
        "%s: %d corrected, %d sibling, %d missing, %d outdent -> %s\n"
        % ("applied" if args.apply else "dry run", len(changes), len(siblings), len(missing), len(outdents), args.log)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
