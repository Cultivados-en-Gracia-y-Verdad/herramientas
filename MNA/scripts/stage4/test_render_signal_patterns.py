#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage4-test-signal-pattern-renderer-v8-color-modes"

RESET = "\033[0m"
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
DIM = "\033[2m"


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
    return f"{color}{value}{RESET}" if enabled else value


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
    if "-S" in rmac:
        return MAGENTA
    if "V-X" in rmac:
        return CYAN
    if "V-F" in rmac:
        return GREEN
    return WHITE


def apply_color(value: str, signal: str, color_mode: str) -> str:
    if color_mode == "none":
        return value
    if color_mode == "all":
        return value
    # handled column-by-column in render_map
    return value


def render_map(rows, color_mode: str) -> list[str]:
    color_all = color_mode == "all"
    color_subject = color_mode in {"all", "subject"}
    color_rmac = color_mode in {"all", "rmac"}
    color_connector = color_mode in {"all", "connector"}

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
        conn_text = colorize(f"{conn:<16}", connector_color(conn), color_connector)
        subj_text = colorize(f"{subj:<10}", subject_color(subj), color_subject)
        rmac_text = colorize(rmac, rmac_color(rmac), color_rmac)
        out.append(
            f"{ref:<6}  {marker(r):<7} "
            f"{conn_text} "
            f"{subj_text} "
            f"{str(r.get('greek_form','')):<19} "
            f"{rmac_text}"
        )
        prev_ref = ref
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TEMP Stage 4: render Stage 3 signals for visible pattern review.")
    ap.add_argument("book")
    ap.add_argument("--from", dest="from_ref", required=True)
    ap.add_argument("--to", dest="to_ref", required=True)
    ap.add_argument("--color", action="store_true", help="Alias for --color-mode all.")
    ap.add_argument("--color-mode", choices=["none", "all", "subject", "rmac", "connector"], default="none")
    args = ap.parse_args()

    book = args.book.strip().lower()
    start = parse_ref(args.from_ref)
    end = parse_ref(args.to_ref)
    mna = root()

    in_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    out_dir = mna / "datasets" / "stage4-test" / book
    out_path = out_dir / f"signal-patterns-{args.from_ref.replace(':','-')}-{args.to_ref.replace(':','-')}.md"

    rows = [r for r in load_jsonl(in_path) if in_range(r, start, end)]
    color_mode = "all" if args.color else args.color_mode

    if color_mode != "none":
        print(f"MNA Stage 4 TEST — Colored Signal Map: {book} {args.from_ref}-{args.to_ref}")
        print(f"COLOR MODE: {color_mode}")
        print("TEMPORARY TEST OUTPUT — NOT CANONICAL")
        print()
        print("\n".join(render_map(rows, color_mode)))
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
    out.extend(render_map(rows, "none"))
    out.append("```")
    out.append("")
    out.append("## Legend")
    out.append("")
    out.append("- `Conn` renders raw connectors as `connector(distance-to-anchor)`, e.g. `γάρ(2)`.")
    out.append("- `[S]` and `[M]` are raw Stage 3 signals, not break decisions.")
    out.append("- Color modes: `--color-mode subject`, `--color-mode rmac`, `--color-mode connector`, or `--color-mode all`.")

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
