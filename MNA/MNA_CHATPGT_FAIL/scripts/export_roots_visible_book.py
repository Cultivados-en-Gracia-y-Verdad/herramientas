#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from roots_engine_v2_rewrite import (
    build_connectors,
    is_finite_rmac,
    render_json_file,
)


def verse_sort_key(path: Path):
    try:
        chapter = int(path.parent.name)
    except ValueError:
        chapter = 999999
    try:
        verse = int(path.stem)
    except ValueError:
        verse = 999999
    return chapter, verse


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_verbs(data) -> str:
    rows = []
    for col in sorted(data.get("columns", []), key=lambda c: c.get("column", 999999)):
        rmac = col.get("rmac", "")
        if not rmac.startswith("V-"):
            continue

        status = "F" if is_finite_rmac(rmac) else "NF"
        greek = col.get("greek", "")
        lemma = col.get("lemma", "")
        nbla = col.get("nbla", "")
        alignment = col.get("alignment", "")
        rows.append(f"- {greek} | {lemma} | {rmac} | [{status}] | NBLA: {nbla} | {alignment}")

    return "\n".join(rows) if rows else "- ninguno"


def render_connectors(data) -> str:
    connectors = build_connectors(data)
    if not connectors:
        return "- ninguno"

    rows = []
    for connector in connectors:
        rows.append(
            f"- {connector.greek} | {connector.lemma} | NBLA: {connector.gloss} | "
            f"relación: {connector.relation_type} | alcance: {connector.level}"
        )
    return "\n".join(rows)


def render_verse_report(path: Path) -> str:
    data = load_json(path)
    structure = render_json_file(path).strip()

    parts = []
    parts.append("\n### Verbos detectados\n\n")
    parts.append(render_verbs(data))
    parts.append("\n\n### Conectores detectados\n\n")
    parts.append(render_connectors(data))
    parts.append("\n\n### Vista estructural\n\n")
    parts.append("```text\n")
    parts.append(structure)
    parts.append("\n```\n")
    return "".join(parts)


def export_book(book: str, base_dir: Path, out_path: Path) -> int:
    book_dir = base_dir / book
    if not book_dir.exists():
        raise FileNotFoundError(f"Book directory not found: {book_dir}")

    json_files = sorted(book_dir.glob("*/*.json"), key=verse_sort_key)
    if not json_files:
        raise FileNotFoundError(f"No verse JSON files found under: {book_dir}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    parts = [f"# ROOTS Vista Estructural — {book}\n"]
    count = 0

    for path in json_files:
        chapter, verse = verse_sort_key(path)
        parts.append(f"\n## {book} {chapter}:{verse}\n")
        parts.append(render_verse_report(path))
        count += 1

    out_path.write_text("".join(parts), encoding="utf-8")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Export all available verse-level ROOTS visible structures for one book."
    )
    parser.add_argument("book", help="Book folder name under MNA/data/interlinear, e.g. 1corintios")
    parser.add_argument(
        "--base-dir",
        default="MNA/data/interlinear",
        help="Base interlinear JSON directory. Default: MNA/data/interlinear",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output Markdown path. Default: MNA/outputs/roots-visible/{book}.md",
    )
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("MNA/outputs/roots-visible") / f"{args.book}.md"
    count = export_book(args.book, Path(args.base_dir), out_path)
    print(f"Exported {count} verses to {out_path}")


if __name__ == "__main__":
    main()
