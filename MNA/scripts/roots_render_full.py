#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    return rows


def load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    out = {}

    for row in rows:
        key = str(
            row.get("predication_id")
            or row.get("stream_index")
            or row.get("id")
            or ""
        )

        if key:
            out[key] = row

    return out


def load_all(book: str) -> dict[str, dict[str, dict[str, Any]]]:
    root = mna_root() / "data"

    datasets = {
        "predications": root / "predications" / f"{book}-predications.jsonl",
        "connectors": root / "connectors" / f"{book}-connectors.jsonl",
        "paso8": root / "paso8-trunk" / f"{book}-paso8-trunk.jsonl",
        "paso9": root / "paso9-support" / f"{book}-paso9-support.jsonl",
        "movement": root / "movement" / f"{book}-movement.jsonl",
    }

    loaded = {}

    for name, path in datasets.items():
        loaded[name] = load_dataset(path)

    return loaded


def parse_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]

    if not value:
        return []

    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
    except Exception:
        pass

    return []


def ref(row: dict[str, Any]) -> str:
    return f"{row.get('chapter')}:{row.get('verse')}"


def render_predication(row: dict[str, Any], datasets: dict[str, dict[str, dict[str, Any]]]) -> str:
    key = str(row.get("predication_id") or row.get("stream_index") or "")

    connector_row = datasets["connectors"].get(key, {})
    paso8_row = datasets["paso8"].get(key, {})
    paso9_row = datasets["paso9"].get(key, {})
    movement_row = datasets["movement"].get(key, {})

    connectors = parse_list(connector_row.get("connectors"))
    labels = parse_list(paso9_row.get("candidate_labels"))
    movements = parse_list(movement_row.get("movement_markers"))

    text = row.get("surface_text") or row.get("clause_text") or ""
    verb = row.get("finite_verb") or "—"
    morph = row.get("verb_morphology") or "—"
    trunk = paso8_row.get("trunk") or paso8_row.get("trunk_text") or ""
    structure = row.get("structure") or row.get("visible_structure") or ""
    action = movement_row.get("trunk_action") or movement_row.get("action") or "—"

    out = []

    out.append(f"# {ref(row)}")
    out.append("")

    out.append("## PASO 1 — COPIAR TEXTO")
    out.append("")
    out.append(text)
    out.append("")

    out.append("## PASO 2 — VERBOS FINITOS")
    out.append("")
    out.append(f"- {verb} ({morph})")
    out.append("")

    out.append("## PASO 3 — CLÁUSULAS")
    out.append("")
    out.append(f"- {text}")
    out.append("")

    out.append("## PASO 4 — CONECTORES")
    out.append("")

    if connectors:
        for c in connectors:
            out.append(f"- {c}")
    else:
        out.append("- ninguno")

    out.append("")

    out.append("## PASO 6 — MOSTRAR LA ESTRUCTURA")
    out.append("")
    out.append("```text")
    out.append(structure)
    out.append("```")
    out.append("")

    out.append("## PASO 8 — TRONCO")
    out.append("")
    out.append(trunk)
    out.append("")

    out.append("## PASO 9 — ETIQUETAS")
    out.append("")

    if labels:
        for label in labels:
            out.append(f"- {label}")
    else:
        out.append("- ninguna")

    out.append("")

    out.append("## MOVIMIENTOS OBSERVADOS")
    out.append("")

    if movements:
        for movement in movements:
            out.append(f"- {movement}")
    else:
        out.append("- ninguno")

    out.append("")

    out.append("## PASO 13 — ACCIÓN DEL TRONCO")
    out.append("")
    out.append(action)
    out.append("")

    out.append("---")
    out.append("")

    return "\n".join(out)


def render_book(book: str) -> str:
    datasets = load_all(book)

    predications = list(datasets["predications"].values())

    predications = sorted(
        predications,
        key=lambda row: int(row.get("stream_index") or 0),
    )

    output = [f"# ROOTS RENDER — {book.upper()}", ""]

    for row in predications:
        output.append(render_predication(row, datasets))

    return "\n".join(output)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_render_full.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()

    out_dir = mna_root() / "output" / "roots-render"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{book}-roots-render.md"

    out_path.write_text(render_book(book), encoding="utf-8")

    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
