#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-test-signal-pattern-renderer-v7-color"

RESET = "\033[0m"
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
DIM = "\033[2m"
BOLD = "\033[1m"


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


def colorize(value: str, color: str, enabled: bool) -> str:
    if not enabled:
        return value
    return f"{color}{value}{RESET}"


def subject_color(subject: str) -> str:
    if "3S" in subject:
        return BLUE
    if "3P" in subject:
        return GREEN
    if "1P" in subject:
        return YELLOW
    if "2P" in subject:
        return MAGENTA
    return WHITE


def connector_color(conn: str) -> str:
    if conn == "—":
        return DIM
    if "γ" in conn:
        return CYAN
    if "εἰ" in conn or "Εἰ" in conn:
        return YELLOW
    if "ὅτι" in conn or "ὅταν" in conn:
        return MAGENTA
    return WHITE


def rmac_color(rmac: str) -> str:
    if "S" in rmac[4:6] if len(rmac) > 5 else False:
        return MAGENTA
    if "V-X" in rmac:
        return CYAN
    return WHITE


def seen_flag(value, seen):
    return "↩" if value and value in seen else "—"


def render_map(rows, color: bool) -> list[str]:
    out = []
    out.append("REF     MK      CONN             SUBJ       VERB                 RMAC")
    out.append("──────  ─────── ──────────────── ────────── ─────────────────── ─────────")
    prev_ref = None
    for r in rows:
        ref = f"{r['chapter']}:{r['verse']}"
        if prev_ref and ref != prev_ref:
            out.append("")
        subj = compact_subject(r)
        conn = connector_display(r)
        rmac = verbal_profile(r)
        out.append(
            f"{ref:<6}  {marker(r):<7} "
            f"{colorize(f'{conn:<16}', connector_color(conn), color)} "
            f"{colorize(f'{subj:<10}', subject_color(subj), color)} "
            f"{str(r.get('greek_form','')):<19} "
            f"{colorize(rmac, rmac_color(rmac), color)}"
        )
        prev_ref = ref
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TEMP Stage 4: render Stage 3 signals for visible pattern review.")
    ap.add_argument("book")
    ap.add_argument("--from", dest="from_ref", required=True)
    ap.add_argument("--to", dest="to_ref", required=True)
    ap.add_argument("--color", action="store_true", help="Print ANSI-colored structural map to terminal.")
    args = ap.parse_args()

    book = args.book.strip().lower()
    start = parse_ref(args.from_ref)
    end = parse_ref(args.to_ref)
    mna = root()

    in_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    out_dir = mna / "datasets" / "stage4-test" / book
    out_path = out_dir / f"signal-patterns-{args.from_ref.replace(':','-')}-{args.to_ref.replace(':','-')}.md"

    rows = [r for r in load_jsonl(in_path) if in_range(r, start, end)]

    if args.color:
        print(f"MNA Stage 4 TEST — Colored Signal Map: {book} {args.from_ref}-{args.to_ref}")
        print("TEMPORARY TEST OUTPUT — NOT CANONICAL")
        print()
        print("\n".join(render_map(rows, True)))
        return 0

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
    out.extend(render_map(rows, False))
    out.append("```")
    out.append("")

    out.append("## Legend")
    out.append("")
    out.append("- `Conn` renders raw connectors as `connector(distance-to-anchor)`, e.g. `γάρ(2)`.")
    out.append("- `[S]` and `[M]` are raw Stage 3 signals, not break decisions.")
    out.append("- Use `--color` to print an ANSI-colored terminal view.")

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
