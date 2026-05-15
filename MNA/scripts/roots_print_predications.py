#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"ERROR {path}:{lineno}: invalid JSON") from exc
    return rows


def find_stream(book: str) -> Path:
    candidates = [
        mna_root() / "data" / "predications" / f"{book}-predications.jsonl",
        mna_root() / "data" / "independent-stream" / f"{book}-independent-stream.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    tried = "\n".join(str(p) for p in candidates)
    raise SystemExit(f"ERROR: no predication stream found for {book}. Tried:\n{tried}")


def subject(row: dict[str, Any]) -> str:
    person = row.get("subject_person")
    number = row.get("subject_number")
    status = row.get("subject_status") or ""
    token = row.get("subject_token")

    if person and number:
        return f"{person}{number} ({status})"
    if token:
        return f"token {token} ({status})"
    return f"— ({status or 'unresolved'})"


def render(book: str) -> str:
    path = find_stream(book)
    rows = read_jsonl(path)
    rows.sort(key=lambda r: int(r.get("stream_index") or 0))

    out: list[str] = []
    out.append(f"# {book} — predicaciones")
    out.append("")
    out.append(f"Fuente: {path}")
    out.append(f"Total: {len(rows)}")
    out.append("")

    current_ref = None
    for row in rows:
        ref = f"{row.get('chapter')}:{row.get('verse')}"
        if ref != current_ref:
            current_ref = ref
            out.append(f"## {ref}")
            out.append("")

        pid = row.get("predication_id") or "—"
        idx = row.get("stream_index") or "—"
        finite = row.get("finite_verb") or "—"
        lemma = row.get("finite_lemma") or "—"
        morph = row.get("finite_compact") or row.get("finite_morphgnt") or "—"
        nbla = row.get("nbla_text") or "—"
        independence = row.get("independence_status") or "—"
        subordination = row.get("subordination_status") or "—"

        out.append(f"- {idx}. {pid}")
        out.append(f"  - verbo: {finite}")
        out.append(f"  - lema: {lemma}")
        out.append(f"  - morfología: {morph}")
        out.append(f"  - sujeto: {subject(row)}")
        out.append(f"  - predicado español: {nbla}")
        out.append(f"  - independencia: {independence}")
        out.append(f"  - subordinación: {subordination}")
        out.append("")

    return "\n".join(out)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 MNA/scripts/roots_print_predications.py <book>")

    book = sys.argv[1].lower()
    out_dir = mna_root() / "output" / "roots-render"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-predications.md"
    out_path.write_text(render(book), encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
