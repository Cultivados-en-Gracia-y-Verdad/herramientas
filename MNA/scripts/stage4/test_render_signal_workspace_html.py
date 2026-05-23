#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERSION = "stage4-test-html-observation-workspace-v2-hide-lemma"

SUBJECT_COLORS = {
    "3S": "subject-3s",
    "3P": "subject-3p",
    "1P": "subject-1p",
    "2P": "subject-2p",
    "1S": "subject-1s",
    "2S": "subject-2s",
}

CONNECTOR_CLASSES = {
    "γάρ": "conn-gar",
    "γὰρ": "conn-gar",
    "εἰ": "conn-ei",
    "Εἰ": "conn-ei",
    "δὲ": "conn-de",
    "δέ": "conn-de",
    "ὅτι": "conn-hoti",
    "ὅταν": "conn-hotan",
    "καὶ": "conn-kai",
    "καί": "conn-kai",
    "ἄρα": "conn-ara",
    "ἵνα": "conn-hina",
    "ὥσπερ": "conn-compare",
    "οὕτως": "conn-compare",
    "ἔπειτα": "conn-seq",
    "εἶτα": "conn-seq",
    "τότε": "conn-seq",
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def parse_ref(value: str) -> tuple[int, int]:
    ch, vs = value.split(":", 1)
    return int(ch), int(vs)


def in_range(row: dict[str, Any], start: tuple[int, int], end: tuple[int, int]) -> bool:
    ref = (int(row["chapter"]), int(row["verse"]))
    return start <= ref <= end


def compact_person_number(row: dict[str, Any]) -> str:
    person = str(row.get("person") or "")
    number = str(row.get("number") or "")
    p = {"first": "1", "second": "2", "third": "3", "1": "1", "2": "2", "3": "3"}.get(person, person)
    n = {"singular": "S", "plural": "P", "S": "S", "P": "P"}.get(number, number)
    return f"{p}{n}" if p and n else "—"


def clear_subject(row: dict[str, Any]) -> str:
    explicit = str(row.get("explicit_subject_before") or "").strip()
    pn = compact_person_number(row)
    if explicit:
        return f"{explicit} ({pn})"
    return pn


def subject_class(row: dict[str, Any]) -> str:
    return SUBJECT_COLORS.get(compact_person_number(row), "subject-other")


def marker(row: dict[str, Any]) -> str:
    parts = []
    if row.get("s_marker"):
        parts.append(row["s_marker"])
    if row.get("m_marker"):
        parts.append(row["m_marker"])
    return " ".join(parts) if parts else "—"


def connector_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    items = row.get("connectors_before_anchor") or []
    if isinstance(items, list) and items:
        return items
    form = row.get("connector_form") or ""
    if not form:
        return []
    distances = row.get("connector_distance_to_anchor") or []
    if not isinstance(distances, list):
        distances = [distances]
    forms = str(form).split()
    out = []
    for i, f in enumerate(forms):
        dist = distances[i] if i < len(distances) else ""
        out.append({"form": f, "distance_to_anchor": dist})
    return out


def connector_badges(row: dict[str, Any]) -> str:
    items = connector_items(row)
    if not items:
        return '<span class="muted">—</span>'
    badges = []
    for item in items:
        form = str(item.get("form", ""))
        dist = item.get("distance_to_anchor", "")
        cls = CONNECTOR_CLASSES.get(form, "conn-other")
        label = f"{form}({dist})" if dist not in (None, "") else form
        badges.append(f'<span class="conn {cls}">{html.escape(label)}</span>')
    return " ".join(badges)


def connector_forms(row: dict[str, Any]) -> list[str]:
    return [str(i.get("form", "")) for i in connector_items(row) if i.get("form")]


def rmac(row: dict[str, Any]) -> str:
    return str(row.get("rmac") or row.get("morphology") or "—")


def rmac_class(code: str) -> str:
    if "-S" in code:
        return "rmac-subjunctive"
    if code.startswith("V-X"):
        return "rmac-perfect"
    if code.startswith("V-F"):
        return "rmac-future"
    if code.startswith("V-A"):
        return "rmac-aorist"
    if code.startswith("V-P"):
        return "rmac-present"
    return "rmac-other"


def row_to_html(row: dict[str, Any]) -> str:
    ref = f"{row['chapter']}:{row['verse']}"
    verb = html.escape(str(row.get("greek_form", "")))
    subj = html.escape(clear_subject(row))
    code = html.escape(rmac(row))
    mk = html.escape(marker(row))
    lemma = html.escape(str(row.get("lemma", "")))
    raw_title = json.dumps(row, ensure_ascii=False, indent=2)
    title = html.escape(f"lemma: {lemma}\n\n{raw_title}")
    return f"""
    <div class="anchor-row" title="{title}">
      <div class="ref">{html.escape(ref)}</div>
      <div class="markers">{mk}</div>
      <div class="connectors">{connector_badges(row)}</div>
      <div class="subject {subject_class(row)}">{subj}</div>
      <div class="verb">{verb}</div>
      <div class="rmac {rmac_class(code)}">{code}</div>
    </div>
    """


def verse_blocks(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['chapter']}:{row['verse']}"].append(row)
    parts = []
    for ref, verse_rows in grouped.items():
        parts.append(f'<section class="verse-block"><h3>{html.escape(ref)}</h3>')
        for row in verse_rows:
            parts.append(row_to_html(row))
        parts.append("</section>")
    return "\n".join(parts)


def count_run(values: list[str]) -> list[tuple[str, int]]:
    if not values:
        return []
    runs = []
    current = values[0]
    count = 1
    for v in values[1:]:
        if v == current:
            count += 1
        else:
            runs.append((current, count))
            current = v
            count = 1
    runs.append((current, count))
    return runs


def phenomena(rows: list[dict[str, Any]]) -> list[str]:
    notes = []
    subjects = [compact_person_number(r) for r in rows]
    subject_counts = Counter(subjects)
    if subject_counts:
        dominant, n = subject_counts.most_common(1)[0]
        notes.append(f"Dominant subject signal: {dominant} appears {n}/{len(rows)} anchors.")

    subject_runs = [(v, n) for v, n in count_run(subjects) if n >= 3 and v != "—"]
    for v, n in subject_runs:
        notes.append(f"Subject continuity run: {v} repeats across {n} adjacent anchors.")

    rmacs = [rmac(r) for r in rows]
    rmac_counts = Counter(rmacs)
    for code, n in rmac_counts.most_common(5):
        if n >= 3 and code != "—":
            notes.append(f"RMAC recurrence: {code} appears {n} times.")

    conn_counter = Counter()
    for row in rows:
        conn_counter.update(connector_forms(row))
    for conn, n in conn_counter.most_common(8):
        if n >= 2:
            notes.append(f"Connector recurrence: {conn} appears {n} times in the selected range.")

    seq_forms = {"ἔπειτα", "εἶτα", "τότε"}
    seq_seen = []
    for row in rows:
        for conn in connector_forms(row):
            if conn in seq_forms:
                seq_seen.append(f"{conn} at {row['chapter']}:{row['verse']}")
    if seq_seen:
        notes.append("Sequence connector movement: " + "; ".join(seq_seen) + ".")

    temporal_forms = {"ὅταν"}
    temporal_seen = []
    for row in rows:
        for conn in connector_forms(row):
            if conn in temporal_forms:
                temporal_seen.append(f"{conn} at {row['chapter']}:{row['verse']}")
    if temporal_seen:
        notes.append("Temporal connector environment: " + "; ".join(temporal_seen) + ".")

    if not notes:
        notes.append("No repeated observable phenomena met the current simple thresholds.")
    return notes


def phenomena_html(rows: list[dict[str, Any]]) -> str:
    notes = phenomena(rows)
    return "\n".join(f"<li>{html.escape(note)}</li>" for note in notes)


def css() -> str:
    return """
    :root {
      --bg: #111318;
      --panel: #181b22;
      --panel2: #20242d;
      --text: #e8eaf0;
      --muted: #8f96a3;
      --line: #313744;
      --blue: #6aa9ff;
      --green: #76d88a;
      --yellow: #ffd166;
      --magenta: #d68cff;
      --cyan: #67e8f9;
      --orange: #ffae57;
      --red: #ff7b7b;
    }
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
    header { padding: 20px 28px; border-bottom: 1px solid var(--line); background: #0d0f14; position: sticky; top: 0; z-index: 5; }
    h1 { margin: 0 0 6px; font-size: 20px; }
    .subtitle { color: var(--muted); font-size: 13px; }
    main { display: grid; grid-template-columns: minmax(680px, 1fr) 360px; gap: 18px; padding: 18px; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
    .panel h2 { margin: 0; padding: 14px 16px; background: var(--panel2); font-size: 15px; border-bottom: 1px solid var(--line); }
    .verse-block { border-bottom: 1px solid var(--line); padding: 10px 12px 12px; }
    .verse-block h3 { margin: 0 0 8px; font-size: 13px; color: var(--muted); letter-spacing: .08em; }
    .anchor-row { display: grid; grid-template-columns: 58px 70px 180px 130px minmax(160px,1fr) 110px; gap: 8px; align-items: center; min-height: 30px; padding: 4px 6px; border-radius: 8px; }
    .anchor-row:hover { background: rgba(255,255,255,.06); }
    .ref { color: var(--muted); font-variant-numeric: tabular-nums; }
    .markers { color: #f3b6ff; font-size: 12px; }
    .connectors { display: flex; gap: 5px; flex-wrap: wrap; }
    .conn { display: inline-block; padding: 2px 7px; border-radius: 999px; font-size: 12px; font-weight: 700; color: #111; }
    .conn-gar { background: var(--cyan); }
    .conn-ei { background: var(--yellow); }
    .conn-de { background: var(--orange); }
    .conn-hoti, .conn-hotan { background: var(--magenta); }
    .conn-kai { background: #c7f9cc; }
    .conn-ara { background: #ff7b7b; }
    .conn-hina { background: #b8f7d4; }
    .conn-compare { background: #a0c4ff; }
    .conn-seq { background: #fdffb6; }
    .conn-other { background: #d1d5db; }
    .subject { padding: 4px 8px; border-radius: 8px; font-weight: 800; color: #0d0f14; text-align: center; }
    .subject-3s { background: var(--blue); }
    .subject-3p { background: var(--green); }
    .subject-1p { background: var(--yellow); }
    .subject-2p { background: var(--magenta); }
    .subject-1s, .subject-2s, .subject-other { background: #cbd5e1; }
    .verb { font-family: ui-serif, Georgia, serif; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .rmac { padding: 4px 6px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; text-align: center; }
    .rmac-subjunctive { background: rgba(214,140,255,.22); color: var(--magenta); border: 1px solid rgba(214,140,255,.35); }
    .rmac-perfect { background: rgba(103,232,249,.18); color: var(--cyan); border: 1px solid rgba(103,232,249,.3); }
    .rmac-future { background: rgba(118,216,138,.18); color: var(--green); border: 1px solid rgba(118,216,138,.3); }
    .rmac-aorist { background: rgba(255,209,102,.15); color: var(--yellow); border: 1px solid rgba(255,209,102,.25); }
    .rmac-present { background: rgba(255,255,255,.08); color: var(--text); border: 1px solid rgba(255,255,255,.12); }
    .rmac-other { background: rgba(255,255,255,.08); color: var(--muted); }
    aside { position: sticky; top: 82px; align-self: start; }
    .phenomena { padding: 14px 18px; }
    .phenomena li { margin: 0 0 10px; line-height: 1.35; }
    .muted { color: var(--muted); }
    .legend { padding: 14px 18px; border-top: 1px solid var(--line); font-size: 13px; color: var(--muted); }
    .warning { color: var(--yellow); }
    """


def html_doc(book: str, from_ref: str, to_ref: str, rows: list[dict[str, Any]]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MNA Stage 4 HTML TEST — {html.escape(book)} {html.escape(from_ref)}–{html.escape(to_ref)}</title>
  <style>{css()}</style>
</head>
<body>
  <header>
    <h1>MNA Stage 4 HTML TEST — {html.escape(book)} {html.escape(from_ref)}–{html.escape(to_ref)}</h1>
    <div class="subtitle">Temporary observation workspace. Not canonical. No H2/H1/H0 decisions are made here.</div>
  </header>
  <main>
    <section class="panel">
      <h2>Anchor Map</h2>
      {verse_blocks(rows)}
    </section>
    <aside class="panel">
      <h2>Detected Observable Phenomena</h2>
      <div class="phenomena">
        <ul>{phenomena_html(rows)}</ul>
      </div>
      <div class="legend">
        <p><strong>Display note:</strong> repeated Greek forms may be real repetition in the text. Lemma is hidden from the row and available on hover to avoid false visual duplication.</p>
        <p><strong>What to look for:</strong> continuity pressure, restoration, interruption, clustering, connector environments, lexical gravity, sequence movement, closure pressure, development pressure.</p>
        <p><span class="warning">Important:</span> observations are evidence prompts only, not structural decisions.</p>
      </div>
    </aside>
  </main>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="TEMP Stage 4: render HTML observation workspace.")
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
    out_path = out_dir / f"signal-workspace-{args.from_ref.replace(':','-')}-{args.to_ref.replace(':','-')}.html"

    rows = [r for r in load_jsonl(in_path) if in_range(r, start, end)]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc(book, args.from_ref, args.to_ref, rows), encoding="utf-8")

    print("MNA Stage 4 TEST — HTML Observation Workspace")
    print(f"BOOK: {book}")
    print(f"RANGE: {args.from_ref}-{args.to_ref}")
    print(f"ROWS: {len(rows)}")
    print(f"OUTPUT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
