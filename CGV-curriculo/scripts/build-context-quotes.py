#!/usr/bin/env python3
"""Emit or verify the H2 context quote (`=` lines) from LBF.

    build-context-quotes.py --manual m.md --lbf libro.lbf.md --check
    build-context-quotes.py --manual m.md --lbf libro.lbf.md --write [--out o.md]

Every `##` H2 opens with its whole passage, verbatim from LBF, one `=` line per verse, grouped
into slides under the character budget. Scripture is generated here, never typed by an agent:
--check proves every `=` line is byte-identical to its LBF verse.
"""
import argparse, re, sys

H2 = re.compile(r"^##\s+(?!#)(.*)$")
SPAN = re.compile(r"(\d+):(\d+)\s*[–—-]\s*(?:(\d+):)?(\d+)|(\d+):(\d+)")
VERSE = re.compile(r"^=\s+\*\*(\d+)(?::(\d+))?\*\*\s+(.*)$")
BUDGET = 280

def load_lbf(path):
    v = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\S+\s+(\d+):(\d+)\s+(.*)$", line.rstrip("\n"))
        if m: v[(int(m.group(1)), int(m.group(2)))] = m.group(3).strip()
    return v

def span_of(heading):
    m = SPAN.search(heading)
    if not m: return None
    if m.group(1):
        c1, v1 = int(m.group(1)), int(m.group(2))
        c2 = int(m.group(3)) if m.group(3) else c1
        return (c1, v1), (c2, int(m.group(4)))
    c, v = int(m.group(5)), int(m.group(6))
    return (c, v), (c, v)

def label(key, start, end):
    return f"{key[0]}:{key[1]}" if start[0] != end[0] else f"{key[1]}"

def emit(verses, start, end):
    keys = sorted(k for k in verses if start <= k <= end)
    if not keys: return None, []
    lines, slide, size = [], [], 0
    for k in keys:
        line = f"= **{label(k, start, end)}** {verses[k]}"
        if slide and size + len(line) > BUDGET:
            lines.extend(slide); lines.append(""); slide, size = [], 0
        slide.append(line); size += len(line)
    lines.extend(slide)
    return lines, keys

def existing_block(body, i):
    """span of the `=` block (plus its blank separators) directly after heading index i"""
    j = i + 1
    while j < len(body) and body[j].strip() == "": j += 1
    if j >= len(body) or not body[j].startswith("= "): return None
    k = j
    while k < len(body) and (body[k].startswith("= ") or
          (body[k].strip() == "" and k + 1 < len(body) and body[k+1].startswith("= "))):
        k += 1
    return j, k

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", required=True); ap.add_argument("--lbf", required=True)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.check == a.write: sys.exit("choose exactly one of --check / --write")

    verses = load_lbf(a.lbf)
    body = open(a.manual, encoding="utf-8").read().split("\n")
    if not verses: sys.exit(f"FAIL  no verses parsed from {a.lbf}")

    findings, skipped, out, i, n_h2, n_quoted, n_lines = [], [], [], 0, 0, 0, 0
    while i < len(body):
        line = body[i]
        m = H2.match(line)
        if not m:
            out.append(line); i += 1; continue
        n_h2 += 1
        head = m.group(1)
        sp = span_of(head)
        blk = existing_block(body, i)
        if not sp:
            skipped.append(head[:56])   # appendices and other spanless H2s: expected, not a defect
            out.append(line); i += 1; continue
        want, keys = emit(verses, *sp)
        if want is None:
            findings.append((head[:56], f"span {sp[0][0]}:{sp[0][1]}–{sp[1][0]}:{sp[1][1]} covers no LBF verse"))
            out.append(line); i += 1; continue

        if a.check:
            if not blk:
                findings.append((head[:56], f"no context quote ({len(keys)} verses missing)"))
            else:
                have = [l for l in body[blk[0]:blk[1]] if l.startswith("= ")]
                n_quoted += 1; n_lines += len(have)
                hv = {}
                for l in have:
                    mm = VERSE.match(l)
                    if mm: hv[mm.group(1) + (":" + mm.group(2) if mm.group(2) else "")] = mm.group(3)
                    else: findings.append((head[:56], f"malformed `=` line: {l[:60]}"))
                for k in keys:
                    lab = label(k, *sp)
                    if lab not in hv: findings.append((head[:56], f"verse {lab} missing from the quote"))
                    elif hv[lab] != verses[k]:
                        findings.append((head[:56], f"verse {lab} does not match LBF — the quote has drifted"))
                for lab in hv:
                    if lab not in [label(k, *sp) for k in keys]:
                        findings.append((head[:56], f"verse {lab} quoted but outside the H2 span"))
            out.append(line); i += 1; continue

        # --write : replace any existing block, then insert a fresh one
        out.append(line); out.append("")
        out.extend(want); out.append("")
        n_quoted += 1; n_lines += len([l for l in want if l.startswith("= ")])
        i = blk[1] if blk else i + 1
        while i < len(body) and body[i].strip() == "": i += 1

    if a.check:
        print(f"manual : {a.manual}\nH2s    : {n_h2}   quoted: {n_quoted}   `=` lines: {n_lines}"
              f"   no span (appendices etc.): {len(skipped)}\n")
        if findings:
            print(f"FAIL  {len(findings)} finding(s)\n")
            for h, w in findings[:40]: print(f"  {h}\n      {w}")
            if len(findings) > 40: print(f"  … and {len(findings)-40} more")
            print("\nThis is evidence, not a verdict.")
            return 1
        print("PASS  every H2 carries its whole passage, byte-identical to LBF.")
        return 0

    dest = a.out or a.manual
    open(dest, "w", encoding="utf-8").write("\n".join(out))
    print(f"wrote {n_quoted} context quotes ({n_lines} verses) into {dest}")
    for h in skipped: print(f"  no span, skipped: {h}")
    for h, w in findings: print(f"  SKIPPED {h}\n      {w}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
