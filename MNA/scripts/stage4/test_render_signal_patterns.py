#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-test-signal-pattern-renderer-v4-compact-subject"


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
    return str(row.get("rmac") or row.get("morphology") or "—")


def compact_person_number(row):
    person = str(row.get("person") or "")
    number = str(row.get("number") or "")
    p = {"first": "1", "second": "2", "third": "3", "1": "1", "2": "2", "3": "3"}.get(person, person)
    n = {"singular": "S", "plural": "P", "S": "S", "P": "P"}.get(number, number)
    return f"{p}{n}" if p and n else "—"


def compact_subject(row):
    explicit = str(row.get("explicit_subject_before") or "").strip()
    pn = compact_person_number(row)
    if explicit:
        return f"{explicit} ({pn})"
    return pn


def subject_recurrence_key(row):
    explicit = str(row.get("explicit_subject_before") or "").strip()
    if explicit:
        return f"LEX:{explicit}"
    return f"MORPH:{compact_person_number(row)}"


def marker(row):
    parts = []
    if row.get("s_marker"):
        parts.append(row["s_marker"])
    if row.get("m_marker"):
        parts.append(row["m_marker"])
    return " ".join(parts) if parts else "—"


def connector_form(row):
    return (
        row.get("connector_form")
        or row.get("explicit_connector_before")
        or "—"
    )


def connector_lemma(row):
    return row.get("connector_lemma") or "—"


def connector_index(row):
    value = row.get("connector_token_index")
    return str(value) if value not in (None, "") else "—"


def connector_distance(row):
    value = row.get("connector_distance_to_anchor")
    return str(value) if value not in (None, "") else "—"


def connector_before(row):
    value = row.get("connector_before_anchor")
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "—"


def connector_display(row):
    form = connector_form(row)
    if form == "—":
        return "—"
    return f"{form} (idx={connector_index(row)}, dist={connector_distance(row)})"


def recurrence_tag(row, previous_subjects, previous_profiles, previous_connectors):
    tags = []
    subj = subject_recurrence_key(row)
    prof = verbal_profile(row)
    conn = connector_form(row)

    if subj and subj in previous_subjects:
        tags.append("SUBJ-RECUR")
    if prof and prof in previous_profiles:
        tags.append("VERB-RECUR")
    if conn != "—" and conn in previous_connectors:
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
    out.append("| # | Ref | Verb | Subject | RMAC | Markers | Connector | Conn Lemma | Conn Before | Recurrence |")
    out.append("|---:|---|---|---|---|---|---|---|---|---|")

    prev_subjects = set()
    prev_profiles = set()
    prev_connectors = set()

    for r in rows:
        rec = recurrence_tag(r, prev_subjects, prev_profiles, prev_connectors)
        out.append("| " + " | ".join([
            str(r.get("order", "")),
            f"{r['chapter']}:{r['verse']}",
            str(r.get("greek_form", "")),
            compact_subject(r),
            verbal_profile(r),
            marker(r),
            connector_display(r),
            connector_lemma(r),
            connector_before(r),
            rec,
        ]) + " |")
        prev_subjects.add(subject_recurrence_key(r))
        prof = verbal_profile(r)
        if prof:
            prev_profiles.add(prof)
        conn = connector_form(r)
        if conn != "—":
            prev_connectors.add(conn)

    out.append("")
    out.append("## Visual Recurrence Lines")
    out.append("")
    out.append("```text")
    prev_subjects = set()
    for r in rows:
        subj = compact_subject(r)
        ref = f"{r['chapter']}:{r['verse']}"
        rec = "↩" if subject_recurrence_key(r) in prev_subjects else " "
        conn = connector_display(r)
        out.append(f"{ref:<6} {marker(r):<7} CONN={conn:<22} {rec} SUBJ={subj:<22} VERB={r.get('greek_form','')} RMAC={verbal_profile(r)}")
        prev_subjects.add(subject_recurrence_key(r))
    out.append("```")

    out.append("")
    out.append("## Connector Field Check")
    out.append("")
    connector_rows = [r for r in rows if connector_form(r) != "—" or r.get("connector_before_anchor") is True]
    out.append(f"Connector rows in selected range: `{len(connector_rows)}`")
    out.append("")
    out.append("| Ref | Verb | connector_form | connector_lemma | connector_token_index | connector_distance_to_anchor | connector_before_anchor |")
    out.append("|---|---|---|---|---|---|---|")
    for r in connector_rows:
        out.append("| " + " | ".join([
            f"{r['chapter']}:{r['verse']}",
            str(r.get("greek_form", "")),
            connector_form(r),
            connector_lemma(r),
            connector_index(r),
            connector_distance(r),
            connector_before(r),
        ]) + " |")

    out.append("")
    out.append("## Legend")
    out.append("")
    out.append("- `↩` = subject signal has appeared earlier in the selected range.")
    out.append("- `SUBJ-RECUR` = subject signal recurrence using explicit subject when present, otherwise person/number.")
    out.append("- `VERB-RECUR` = same RMAC code recurs.")
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
