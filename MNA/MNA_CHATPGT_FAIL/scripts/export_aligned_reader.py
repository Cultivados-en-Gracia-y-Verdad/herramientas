#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


def read_tokens(path: Path) -> dict[str, str]:
    tokens = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            idx, text = line.split("\t", 1)
            tokens[idx] = text
    return tokens


def read_alignment(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def sort_key(path: Path):
    # filemon-1-12.tsv -> (1, 12)
    stem = path.stem
    parts = stem.split("-")
    return int(parts[-2]), int(parts[-1])


def export_book(book: str):
    g_root = Path("data/g-tokens") / book
    s_root = Path("data/s-tokens") / book
    a_root = Path("data/alignments") / book
    out_root = Path("data/exports")
    out_root.mkdir(parents=True, exist_ok=True)

    out_path = out_root / f"{book}-aligned-reader.md"

    lines: list[str] = []
    lines.append(f"# {book.title()} Aligned Reader")
    lines.append("")
    lines.append("Generated from validated MNA TSV alignments.")
    lines.append("")

    tsv_files = sorted(
    [p for p in a_root.glob(f"{book}-*.tsv") if not p.name.endswith(".original.tsv")],
    key=sort_key,
    )

    for tsv in tsv_files:
        stem = tsv.stem
        g_path = g_root / f"{stem}.txt"
        s_path = s_root / f"{stem}.txt"

        if not g_path.exists() or not s_path.exists():
            print(f"SKIP missing token file for {stem}")
            continue

        rows = read_alignment(tsv)

        if not rows:
            continue

        ch = rows[0]["CH"]
        vs = rows[0]["VS"]

        greek_tokens = read_tokens(g_path)
        spanish_tokens = read_tokens(s_path)

        greek_line = " ".join(greek_tokens[k] for k in sorted(greek_tokens, key=lambda x: int(x)))
        spanish_line = " ".join(spanish_tokens[k] for k in sorted(spanish_tokens, key=lambda x: int(x)))

        lines.append(f"## {book.title()} {ch}:{vs}")
        lines.append("")
        lines.append(f"**Greek:** {greek_line}")
        lines.append("")
        lines.append(f"**NBLA:** {spanish_line}")
        lines.append("")
        lines.append("| G_IDX | Greek | NBLA_IDX | NBLA Text | Type |")
        lines.append("|---:|---|---|---|---|")

        for r in rows:
            lines.append(
                f"| {r['G_IDX']} | {r['GREEK']} | {r['NBLA_IDX']} | {r['NBLA_TEXT']} | {r['ALIGNMENT']} |"
            )

        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"DONE")
    print(f"Book: {book}")
    print(f"Verses exported: {len(tsv_files)}")
    print(f"Output: {out_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/export_aligned_reader.py <book>")
        raise SystemExit(1)

    export_book(sys.argv[1])


if __name__ == "__main__":
    main()