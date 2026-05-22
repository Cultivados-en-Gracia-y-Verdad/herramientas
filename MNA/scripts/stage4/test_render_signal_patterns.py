#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-test-signal-pattern-renderer-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def parse_ref(value: str):
    ch, vs = value.split(":", 1)
    return int(ch), int(vs)


def in_range(row, start, end):
    ref = (int(row["chapter"]), int(row["verse"]))
    return start <= ref <= end


def verbal_profile(row):
    return "/".join([
        str(row.get("tense") or ""),
        str(row.get("voice") or ""),
        str(row.get("mood") or ""),
        str(row.get("person") or ""),
        str(row.get("number") or ""),
    ])


def compact_subject(signal: str):
    if signal.startswith("MORPH:"):
        return signal.replace("MORPH:", "")
    if signal.startswith("LEX:"):
        return signal.replace("LEX:", "")
    return signal or "—"


def marker(row):
    parts = []
    if row.get("s_marker"):
        parts.append(row["s_marker"])
    if row.get("m_marker"):
        parts.append(row["m_marker"])
    return " ".join(parts) if parts else "—"


def connector(row):
    return row.get("connector_form") or "—"


def recurrence_tag(row, previous_subjects, previous_profiles, previous_connectors):
    tags = []
    subj = row.get("subject_signal") or ""
    prof = verbal_profile(row)
    conn = row.get("connector_form") or ""

    if subj and subj in previous_subjects:
        tags.append("SUBJ-RECUR")
    if prof and prof in previous_profiles:
        tags.append("VERB-RECUR")
    if conn and conn in previous_connectors:
        tags.append("CONN-RECUR")
    return ", ".join(tags) if tags else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="TEMP Stage 4: render Stage 3 signals for visible pattern review.")
    ap.add_argument("book")
    ap.add_argument("--from", dest="from_ref", required=True)
    ap.add_argument("--to", dest="to_ref", required=True)
    args = ap.parse_args()

    book = args.book.strip().lower()
    start = parse_ref(args.from_ref)
    end = parse_ref(args.to_ref)
    mna = root()

    in_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    out_dir = mna / "datasets" / "stage4-test" / book
    out_path = out_dir / f"signal-patterns-{args.from_ref.replace(':','-')}-{args.to_ref.replace(':','-')}.md"

    rows = [r for r in load_jsonl(in_path) if in_range(r, start, end)]

    out = []
    out.append(f"# Stage 4 TEST — Signal Pattern View: {book} {args.from_ref}–{args.to_ref}")
    out.append("")
    out.append("TEMPORARY TEST OUTPUT — NOT CANONICAL")
    out.append("")
    out.append("Purpose: render Stage 3 raw signals so recurrence and possible local blocks become visible.")
    out.append("")
    out.append("No H2/H1/H0 decisions are made here.")
    out.append("")
    out.append("## Compact Pattern Table")
    out.append("")
    out.append("| # | Ref | Verb | Subject | Verb Profile | Markers | Connector | Recurrence |")
    out.append("|---:|---|---|---|---|---|---|---|")

    prev_subjects = set()
    prev_profiles = set()
    prev_connectors = set()

    for r in rows:
        rec = recurrence_tag(r, prev_subjects, prev_profiles, prev_connectors)
        out.append("| " + " | ".join([
            str(r.get("order", "")),
            f"{r['chapter']}:{r['verse']}",
            str(r.get("greek_form", "")),
            compact_subject(str(r.get("subject_signal") or "")),
            verbal_profile(r),
            marker(r),
            connector(r),
            rec,
        ]) + " |")
        if r.get("subject_signal"):
            prev_subjects.add(r["subject_signal"])
        prof = verbal_profile(r)
        if prof:
            prev_profiles.add(prof)
        if r.get("connector_form"):
            prev_connectors.add(r["connector_form"])

    out.append("")
    out.append("## Visual Recurrence Lines")
    out.append("")
    out.append("```text")
    prev_subjects = set()
    for r in rows:
        subj = compact_subject(str(r.get("subject_signal") or ""))
        ref = f"{r['chapter']}:{r['verse']}"
        rec = "↩" if r.get("subject_signal") in prev_subjects else " "
        conn = connector(r)
        out.append(f"{ref:<6} {marker(r):<7} {conn:<8} {rec} SUBJ={subj:<18} VERB={r.get('greek_form','')}")
        if r.get("subject_signal"):
            prev_subjects.add(r["subject_signal"])
    out.append("```")

    out.append("")
    out.append("## Legend")
    out.append("")
    out.append("- `↩` = subject signal has appeared earlier in the selected range.")
    out.append("- `SUBJ-RECUR` = subject signal recurrence.")
    out.append("- `VERB-RECUR` = same tense/voice/mood/person/number profile recurs.")
    out.append("- `CONN-RECUR` = same raw connector form recurs.")
    out.append("- `[S]` and `[M]` are raw Stage 3 signals, not break decisions.")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8")

    print("MNA Stage 4 TEST — Signal Pattern Renderer")
    print(f"BOOK: {book}")
    print(f"RANGE: {args.from_ref}-{args.to_ref}")
    print(f"ROWS: {len(rows)}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
