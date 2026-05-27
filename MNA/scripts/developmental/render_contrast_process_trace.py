#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "developmental-contrast-process-trace-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize(text: str) -> str:
    text = text.lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text


def read_seed(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ref_line(raw: str) -> tuple[str, str] | None:
    line = raw.strip()
    if not line:
        return None

    patterns = [
        r"^#+\s*Santiago\s+(\d+):(\d+)\s+(.+)$",
        r"^Santiago\s+(\d+):(\d+)\s+(.+)$",
        r"^(\d+):(\d+)\s+(.+)$",
        r"^(\d+)\s+(\d+)\s+(.+)$",
    ]

    for pat in patterns:
        m = re.match(pat, line, flags=re.IGNORECASE)
        if m:
            ch, vs, text = m.groups()
            return f"{int(ch)}:{int(vs)}", text.strip()

    return None


def read_nbla(book: str, mna: Path) -> list[dict[str, str]]:
    candidates = [
        mna / "SOURCES" / "NBLA" / f"{book}.nbla.md",
        mna / "data" / "NBLA" / f"{book}.nbla.md",
        mna / "data" / "NBLA" / f"{book}.md",
    ]

    path = next((p.resolve() for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError("Could not find NBLA file for book: " + book)

    rows: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_ref_line(raw)
        if parsed:
            ref, text = parsed
            rows.append({"ref": ref, "text": text})
    return rows


def term_hit(term: str, text_norm: str) -> bool:
    term_norm = normalize(term)
    if " " in term_norm:
        return term_norm in text_norm
    return re.search(rf"\b{re.escape(term_norm)}\b", text_norm) is not None


def find_hits(signal: dict[str, Any], verses: list[dict[str, str]], chapter: int) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    terms = signal.get("terms", {})
    side_a = terms.get("side_a", [])
    side_b = terms.get("side_b", [])

    for row in verses:
        ref = row["ref"]
        ch = int(ref.split(":", 1)[0])
        if ch != chapter:
            continue

        text_norm = normalize(row["text"])
        a_hits = [t for t in side_a if term_hit(t, text_norm)]
        b_hits = [t for t in side_b if term_hit(t, text_norm)]

        if a_hits or b_hits:
            hits.append({
                "ref": ref,
                "text": row["text"],
                "side_a_hits": a_hits,
                "side_b_hits": b_hits,
            })
    return hits


def status_for(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "no visible hits / review"
    if len(hits) == 1:
        return "single appearance / review"
    return "recurring signal / unresolved-review"


def render_signal(signal: dict[str, Any], hits: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    label = signal.get("label", signal.get("signal_id", "signal"))

    lines.append(f"## SIGNAL: {label}")
    lines.append("")
    lines.append(f"- Type: `{signal.get('signal_type')}`")
    lines.append(f"- Review status: `{signal.get('status', 'REVIEW')}`")
    lines.append(f"- Observation question: {signal.get('observation_question', '')}")
    lines.append(f"- Trace status: `{status_for(hits)}`")
    lines.append("")
    lines.append("### Process Trace")
    lines.append("")

    if not hits:
        lines.append("No matching textual hits found. Review seed terms or source text.")
        lines.append("")
        return lines

    start_ref = hits[0]["ref"]
    end_ref = hits[-1]["ref"]
    lines.append(f"Open span for review: `{start_ref} → {end_ref}`")
    lines.append("")

    for idx, hit in enumerate(hits, start=1):
        marker = "first appearance" if idx == 1 else "recurrence"
        if idx == len(hits) and len(hits) > 1:
            marker = "latest visible recurrence"

        lines.append(f"#### {hit['ref']} — {marker}")
        lines.append("")
        lines.append(f"> {hit['text']}")
        lines.append("")
        if hit["side_a_hits"]:
            lines.append("- Side A hits: " + ", ".join(f"`{x}`" for x in hit["side_a_hits"]))
        if hit["side_b_hits"]:
            lines.append("- Side B hits: " + ", ".join(f"`{x}`" for x in hit["side_b_hits"]))
        lines.append("")

    lines.append("### Review Question")
    lines.append("")
    lines.append("Does the trace show the same developmental pressure continuing, or only repeated vocabulary?")
    lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Render developmental contrast process traces.")
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    args = parser.parse_args()

    book = args.book.strip().lower()
    mna = root()
    seed_path = mna / "data" / "developmental-signals" / book / "contrast-signals.json"
    out_dir = mna / "datasets" / "developmental" / book
    out_dir.mkdir(parents=True, exist_ok=True)

    seed = read_seed(seed_path)
    verses = read_nbla(book, mna)

    output: dict[str, Any] = {
        "record_type": "developmental_contrast_process_trace",
        "version": VERSION,
        "book": book,
        "chapter": args.chapter,
        "signals": [],
    }

    md: list[str] = []
    md.append(f"# Developmental Contrast Process Trace — {book} {args.chapter}")
    md.append("")
    md.append("This output exposes process traces only. It does not create sections or conclusions.")
    md.append("")

    for signal in seed.get("signals", []):
        hits = find_hits(signal, verses, args.chapter)
        output["signals"].append({
            "signal_id": signal.get("signal_id"),
            "label": signal.get("label"),
            "observation_question": signal.get("observation_question"),
            "status": status_for(hits),
            "hits": hits,
        })
        md.extend(render_signal(signal, hits))

    json_path = out_dir / f"chapter-{args.chapter}-contrast-process-trace.json"
    md_path = out_dir / f"chapter-{args.chapter}-contrast-process-trace.md"

    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(md), encoding="utf-8")

    print("Developmental contrast process trace")
    print(f"BOOK: {book}")
    print(f"CHAPTER: {args.chapter}")
    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
