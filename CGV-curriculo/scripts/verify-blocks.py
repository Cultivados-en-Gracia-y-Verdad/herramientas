#!/usr/bin/env python3
"""Deterministic witness for a book's block inventory.

    python3 verify-blocks.py --blocks {NN.Curso}/blocks.md --lbf .../libro.lbf.md

Checks what a machine can settle:
  1. every unit declares a boundary marker, a form, a contenido and clause IDs
  2. the declared marker actually occurs inside the unit's verse range
  3. the units tile the book — no gap, no overlap, last unit reaches the final verse
  4. the form name is either present in the unit or declared as derived from its marker

It does NOT decide whether a boundary is real or whether a contenido is faithful. That is the
reading. A script and a reading are two different witnesses; neither is the gate alone.
"""
import argparse, re, sys, unicodedata

def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def load_lbf(path):
    verses, order = {}, []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\S+\s+(\d+):(\d+)\s+(.*)$", line.rstrip("\n"))
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            verses[key] = m.group(3)
            order.append(key)
    return verses, order

REF = re.compile(r"(\d+):(\d+)\s*(?:[–—-]\s*(?:(\d+):)?(\d+))?\s*$")

def parse_ref(text):
    m = REF.search(text.strip())
    if not m: return None
    c1, v1 = int(m.group(1)), int(m.group(2))
    if m.group(4) is None: return (c1, v1), (c1, v1)
    c2 = int(m.group(3)) if m.group(3) else c1
    return (c1, v1), (c2, int(m.group(4)))

FIELD = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[—:-]\s*(.*)$")

def parse_blocks(path):
    units, cur = [], None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("### "):
            if cur: units.append(cur)
            head = line[4:].strip()
            parts = re.split(r"\s+[—–]\s+", head, maxsplit=1)
            cur = {"heading": head, "ref": parse_ref(parts[0]),
                   "title": parts[1] if len(parts) > 1 else "", "fields": {}, "body": []}
        elif cur is not None:
            m = FIELD.match(line)
            if m: cur["fields"][fold(m.group(1))] = m.group(2).strip()
            cur["body"].append(line)
    if cur: units.append(cur)
    return [u for u in units if u["ref"]]

def quoted(s):
    out = re.findall(r"[*_]([^*_]{4,})[*_]|«([^»]{4,})»|\"([^\"]{4,})\"", s)
    return [next(g for g in t if g) for t in out]

def span_text(verses, a, b):
    keys = [k for k in verses if a <= k <= b]
    return " ".join(verses[k] for k in sorted(keys)), len(keys)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True); ap.add_argument("--lbf", required=True)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    verses, order = load_lbf(a.lbf)
    if not verses: sys.exit(f"FAIL  no verses parsed from {a.lbf}")
    units = parse_blocks(a.blocks)
    if not units: sys.exit(f"FAIL  no units parsed from {a.blocks}")

    findings = []
    def bad(u, what): findings.append((u["heading"][:58], what))

    # 1 + 2 + 4 — per unit
    for u in units:
        f, (s, e) = u["fields"], u["ref"]
        text, n = span_text(verses, s, e)
        if n == 0: bad(u, f"range {s[0]}:{s[1]}–{e[0]}:{e[1]} covers no verse in the LBF file"); continue

        marker = f.get("boundary evidence") or f.get("evidencia de limite") or ""
        if not marker: bad(u, "no boundary evidence declared")
        else:
            qs = quoted(marker)
            if not qs: bad(u, "boundary evidence quotes no formula — quote it from LBF")
            elif not any(fold(q) in fold(text) for q in qs):
                bad(u, f"declared marker {qs[0]!r} does not occur in {s[0]}:{s[1]}–{e[0]}:{e[1]}")

        form = f.get("form") or f.get("forma") or ""
        if not form: bad(u, "no form declared")
        else:
            head_words = [w for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", u["title"])]
            present = any(fold(w) in fold(text) for w in head_words)
            derived = bool(re.search(r"deriva|derivad|del marcador|from the marker", fold(form)))
            if not present and not derived:
                bad(u, "form name uses no word present in the unit and declares no derivation "
                       "from its marker (Constitution §5.4)")

        if not (f.get("contenido") or f.get("content")): bad(u, "no contenido statement")
        cl = f.get("clausulas") or f.get("clauses") or ""
        if not cl or not re.search(r"\d+:\d+:\d+", cl):
            bad(u, "contenido cites no clause IDs (Constitution §5.5)")

    # 2b — series must state a count, and say where the count came from
    series_lines = []
    grab = False
    for raw in open(a.blocks, encoding="utf-8"):
        low = fold(raw)
        if raw.startswith("#") and "series" in low:
            grab = True; continue
        if raw.startswith("#") and grab and "series" not in low:
            grab = False
        if grab and raw.strip().startswith("|") and not set(raw.strip()) <= set("|-: "):
            series_lines.append(raw.strip())
    header_skipped = False
    for row in series_lines:
        cells = [c.strip() for c in row.strip("|").split("|")]
        if not header_skipped:
            header_skipped = True
            if fold(cells[0]) in ("series", "serie"):
                continue
        name = cells[0] or "(unnamed series)"
        joined = fold(" ".join(cells))
        if not re.search(r"\b\d+\b|\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce)\b", joined):
            findings.append((name[:56], "series states no count — say how many, in the book's own words"))
        # Template column 3 is "Marker that defines it". A non-empty marker cell is
        # the count's source. Also accept an explicit decisión / agrupación note.
        marker_cell = fold(cells[2]) if len(cells) > 2 else ""
        if not (
            marker_cell
            or re.search(r"marcador|marker|formula|f[oó]rmula|decisi[oó]n|juicio|agrupad", joined)
        ):
            findings.append((name[:56],
                "does not say whether the count came from the markers or from a decision "
                "(Constitution §5.4 — a bare number hides a judgment)"))

    # 2c — form names must come from the book, not from a category system
    IMPORTED = ("apocalipti", "gattung", "oraculo de salvacion", "pleito del pacto",
                "himno", "midrash", "vaticinio", "teofania generica")
    for u in units:
        blob = fold(u["heading"] + " " + " ".join(u["fields"].values()))
        for bad in IMPORTED:
            if bad in blob:
                findings.append((u["heading"][:56],
                    f"form named with an imported category ({bad!r}) — use the text's own word"))

    # 3 — tiling
    spans = sorted((u["ref"][0], u["ref"][1], u["heading"][:58]) for u in units)
    for i in range(len(spans) - 1):
        (_, end, h1), (start, _, h2) = spans[i][:3], spans[i + 1][:3]
        after = [k for k in sorted(verses) if k > end]
        if not after: findings.append((h1, "unit ends past the end of the book")); continue
        if after[0] != start:
            findings.append((h1, f"gap or overlap: next unit starts {start[0]}:{start[1]}, "
                                 f"expected {after[0][0]}:{after[0][1]}"))
    last = max(verses)
    if spans and spans[-1][1] != last:
        findings.append((spans[-1][2], f"last unit ends {spans[-1][1][0]}:{spans[-1][1][1]}, "
                                       f"book ends {last[0]}:{last[1]}"))

    if not a.quiet:
        print(f"blocks : {a.blocks}\nlbf    : {a.lbf}\nunits  : {len(units)}   verses: {len(verses)}\n")
    if findings:
        print(f"FAIL  {len(findings)} finding(s)\n")
        for h, w in findings: print(f"  {h}\n      {w}")
        print("\nThis is evidence, not a verdict. Classify each finding before repairing anything.")
        return 1
    print("PASS  every unit declares a marker that occurs in its range, a form, a contenido and "
          "clause IDs; the units tile the book.")
    print("The reading is still required: whether the boundaries are real and the contenido faithful.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
