#!/usr/bin/env python3
"""Pre-Generate gate on the Observer clause spans.

    verify-clause-spans.py --progress {NN.Curso}/observation/<libro>-progress-filled.json \
                           --lbf cgv-data/bibles/LBF/<libro>.lbf.md

Runs on the Observer export BEFORE the Compiler runs, because a span that ends on a
leaner becomes an H4 that ends on a leaner, and by then it has cost a full Generate.

`selectedSpan` holds SPANISH WORD INDICES (chapter:verse:wordIndex, 0-based), not Greek
token ids — even though `wordId()` and `finiteAlignmentId()` emit the same string shape.
Reading one as the other produces plausible nonsense. This script reconstructs the Spanish
exactly as the Compiler will.

Exit 0 clean · 1 findings · 2 usage.
"""
import argparse, importlib.util, json, pathlib, re, sys, unicodedata

HERE = pathlib.Path(__file__).resolve().parent
WORD = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", re.I)


def _sibling(name):
    spec = importlib.util.spec_from_file_location("sib", HERE / name)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def load_lbf(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\S+\s+(\d+):(\d+)\s+(.*)$", line.rstrip("\n"))
        if m:
            out[f"{int(m.group(1))}:{int(m.group(2))}"] = [w.group(0) for w in WORD.finditer(m.group(3))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--progress", required=True)
    ap.add_argument("--lbf", required=True)
    ap.add_argument("--max-dangling", type=int, default=0)
    a = ap.parse_args()

    pack = _sibling("verify-skeleton-h4-packaging.py")   # one dangling vocabulary, not two
    verses = load_lbf(a.lbf)
    if not verses:
        sys.exit(f"FAIL  no verses parsed from {a.lbf}")

    data = json.load(open(a.progress, encoding="utf-8")).get("data", {})
    key = next((k for k in data if k.endswith(":v3") and "spanish-clause-builder" in k), None)
    if not key:
        sys.exit("FAIL  no spanish-clause-builder:*:v3 block in this progress export")
    clauses = data[key]

    # A span may legitimately skip words: an independent clause excludes embedded dependent
    # material, which the Compiler emits on its own `-` line. A gap is only LOSS when the
    # skipped word is claimed by no clause at all. Checked against every other span, not
    # assumed — flagging correct nesting as damage is worse than not checking.
    claimed = {}
    for cid, rec in clauses.items():
        for sid in rec.get("selectedSpan") or []:
            claimed.setdefault(sid, []).append(cid)

    dangling, oneword, lost, empty, surplus, missing = [], [], [], [], [], []
    for cid, rec in clauses.items():
        span = rec.get("selectedSpan") or []
        if not span:
            missing.append((cid, "clause has no selected span")); continue
        vk = ":".join(span[0].split(":")[:2])
        ws = verses.get(vk)
        if ws is None:
            missing.append((cid, f"verse {vk} not in LBF")); continue

        idxs = [int(s.split(":")[2]) for s in span if ":".join(s.split(":")[:2]) == vk]
        if not idxs: continue

        in_range = [i for i in idxs if i < len(ws)]
        over = len(idxs) - len(in_range)
        if not in_range:
            empty.append((cid, f"every index is past the end of {vk} ({len(ws)} words) — this H4 renders EMPTY"))
            continue
        if over:
            surplus.append((cid, f"{over} index(es) past the end of {vk} — dropped silently when rendered"))

        text = " ".join(ws[i] for i in sorted(in_range))
        if len(in_range) == 1:
            oneword.append((cid, f"single-word span: {text!r}"))
        gaps = sorted(set(range(min(in_range), max(in_range) + 1)) - set(in_range))
        orphaned = [g for g in gaps if f"{vk}:{g}" not in claimed]
        if orphaned:
            lost.append((cid, "words in no clause at all: " + ", ".join(f"{g}={ws[g]!r}" for g in orphaned[:6])))
        if pack.is_dangling_ending(text):
            dangling.append((cid, ws[max(in_range)], text[-52:]))

    total = len(clauses)
    print(f"progress : {a.progress}")
    print(f"clauses  : {total}\n")
    print(f"  BLOCKING")
    print(f"    spans that render empty    {len(empty)}")
    print(f"    words lost to no clause    {len(lost)}")
    print(f"    unusable / missing         {len(missing)}")
    print(f"  REVIEW")
    print(f"    spans ending on a leaner   {len(dangling)}")
    print(f"    single-word spans          {len(oneword)}")
    print(f"  HYGIENE")
    print(f"    surplus out-of-range idx   {len(surplus)}  (dropped when rendered; text is correct)")

    if dangling:
        print("\nSPANS ENDING ON A LEANER — each becomes an H4 that ends on a leaner:")
        for cid, tail, text in sorted(dangling)[:40]:
            print(f"  {cid:12} …{tail:8} | {text}")
        if len(dangling) > 40:
            print(f"  … and {len(dangling)-40} more")
    for label, items in (("RENDERS EMPTY", empty), ("WORDS LOST", lost),
                         ("UNUSABLE", missing), ("SURPLUS INDICES", surplus)):
        if items:
            print(f"\n{label}:")
            for cid, why in sorted(items)[:15]:
                print(f"  {cid:12} {why}")

    print("\nEvidence, not a verdict. A postposed particle («Recuerda, pues») is a complete clause and")
    print("the word list cannot tell it from a leaner. A gap where the skipped words belong to another")
    print("clause is correct nesting, not damage — only orphaned words are loss. Repair in Observer,")
    print("never in the skeleton, which regenerates.")

    return 1 if (empty or lost or missing or len(dangling) > a.max_dangling) else 0


if __name__ == "__main__":
    sys.exit(main())
