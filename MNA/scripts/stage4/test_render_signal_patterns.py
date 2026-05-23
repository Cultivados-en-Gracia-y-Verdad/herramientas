#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-test-signal-pattern-renderer-v6-map-view"


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


def connector_items(row):
    items = row.get("connectors_before_anchor") or []
    if isinstance(items, list) and items:
        return items
    form = row.get("connector_form") or row.get("explicit_connector_before") or ""
    if not form:
        return []
    distances = row.get("connector_distance_to_anchor") or []
    if not isinstance(distances, list):
        distances = [distances]
    forms = form.split()
    out = []
    for i, f in enumerate(forms):
        dist = distances[i] if i < len(distances) else ""
        out.append({"form": f, "distance_to_anchor": dist})
    return out


def connector_form(row):
    items = connector_items(row)
    if not items:
        return "—"
    return " ".join(str(i.get("form", "")) for i in items if i.get("form")) or "—"


def connector_display(row):
    items = connector_items(row)
    if not items:
        return "—"
    parts = []
    for item in items:
        form = item.get("form", "")
        dist = item.get("distance_to_anchor", "")
        parts.append(f"{form}({dist})" if dist not in (None, "") else str(form))
    return " ".join(parts)


def seen_flag(value, seen):
    return "↩" if value and value in seen else "—"


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
    out.append("No H2/H1/H0 decisions are made here.")
    out.append("")

    out.append("## Structural Map View")
    out.append("")
    out.append("```text")
    out.append("REF     MK      CONN             SUBJ       VERB                 RMAC")
    out.append("──────  ─────── ──────────────── ────────── ─────────────────── ─────────")
    prev_ref = None
    for r in rows:
        ref = f"{r['chapter']}:{r['verse']}"
        if prev_ref and ref != prev_ref:
            out.append("")
        out.append(f"{ref:<6}  {marker(r):<7} {connector_display(r):<16} {compact_subject(r):<10} {str(r.get('greek_form','')):<19} {verbal_profile(r)}")
        prev_ref = ref
    out.append("```")
    out.append("")

    out.append("## Compact Pattern Table")
    out.append("")
    out.append("| # | Ref | Verb | Subject | RMAC | Markers | Conn | S↩ | V↩ | C↩ |")
    out.append("|---:|---|---|---|---|---|---|---|---|---|")

    prev_subjects = set()
    prev_profiles = set()
    prev_connectors = set()

    for r in rows:
        subj_key = subject_recurrence_key(r)
        prof = verbal_profile(r)
        conn = connector_form(r)
        out.append("| " + " | ".join([
            str(r.get("order", "")),
            f"{r['chapter']}:{r['verse']}",
            str(r.get("greek_form", "")),
            compact_subject(r),
            prof,
            marker(r),
            connector_display(r),
            seen_flag(subj_key, prev_subjects),
            seen_flag(prof, prev_profiles),
            seen_flag(conn, prev_connectors) if conn != "—" else "—",
        ]) + " |")
        prev_subjects.add(subj_key)
        if prof:
            prev_profiles.add(prof)
        if conn != "—":
            prev_connectors.add(conn)

    out.append("")
    out.append("## Legend")
    out.append("")
    out.append("- `Conn` renders raw connectors as `connector(distance-to-anchor)`, e.g. `γάρ(2)`.")
    out.append("- `S↩` = same subject signal appeared earlier in the selected range.")
    out.append("- `V↩` = same RMAC code appeared earlier in the selected range.")
    out.append("- `C↩` = same raw connector form appeared earlier in the selected range.")
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
