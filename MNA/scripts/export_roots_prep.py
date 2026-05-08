#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


FINITE_RE = re.compile(r"V-...[ISMOPN].*")
NONFINITE_RE = re.compile(r"V-...(N|P).*")


CONNECTORS = {
    "καὶ",
    "δὲ",
    "ἀλλὰ",
    "γὰρ",
    "οὖν",
    "ἵνα",
    "ὅτι",
    "εἰ",
    "ἐὰν",
    "διό",
    "ὡς",
    "μή",
    "μὴ",
    "οὐ",
    "οὐκ",
    "ἀλλά",
}


def read_tokens(path: Path) -> list[tuple[str, str]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            idx, text = line.split("\t", 1)
            rows.append((idx, text))
    return rows


def read_morph(path: Path) -> list[dict]:
    rows = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue

            parts = line.split("\t")

            if len(parts) < 6:
                continue

            rows.append({
                "book": parts[0],
                "ref": parts[1],
                "idx": parts[2],
                "greek": parts[3],
                "lemma": parts[4],
                "morph": parts[5],
            })

    return rows


def read_alignment(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def sort_key(path: Path):
    stem = path.stem
    parts = stem.split("-")
    return int(parts[-2]), int(parts[-1])


def is_finite(morph: str) -> bool:
    return bool(FINITE_RE.match(morph))


def is_nonfinite(morph: str) -> bool:
    return bool(NONFINITE_RE.match(morph))


def export_book(book: str):
    g_root = Path("data/g-tokens") / book
    s_root = Path("data/s-tokens") / book
    a_root = Path("data/alignments") / book

    morph_path = Path("data/morph") / f"{book}.tsv"

    out_root = Path("data/exports")
    out_root.mkdir(parents=True, exist_ok=True)

    out_path = out_root / f"{book}-roots-prep.md"

    morph_rows = read_morph(morph_path)

    morph_lookup = {}

    for row in morph_rows:
        key = (row["ref"], row["idx"])
        morph_lookup[key] = row

    tsv_files = sorted(
        [p for p in a_root.glob(f"{book}-*.tsv") if not p.name.endswith(".original.tsv")],
        key=sort_key,
    )

    lines = []

    lines.append(f"# {book.title()} ROOTS Prep")
    lines.append("")

    for tsv in tsv_files:
        rows = read_alignment(tsv)

        if not rows:
            continue

        ch = rows[0]["CH"]
        vs = rows[0]["VS"]

        ref = f"{ch}:{vs}"

        g_path = g_root / f"{tsv.stem}.txt"
        s_path = s_root / f"{tsv.stem}.txt"

        greek_tokens = read_tokens(g_path)
        spanish_tokens = read_tokens(s_path)

        greek_line = " ".join(t for _, t in greek_tokens)
        spanish_line = " ".join(t for _, t in spanish_tokens)

        lines.append(f"## {book.title()} {ref}")
        lines.append("")

        lines.append(f"### Greek")
        lines.append("")
        lines.append(greek_line)
        lines.append("")

        lines.append(f"### NBLA")
        lines.append("")
        lines.append(spanish_line)
        lines.append("")

        finite = []
        nonfinite = []
        connectors = []

        for idx, greek in greek_tokens:
            key = (ref, idx)

            if key not in morph_lookup:
                continue

            m = morph_lookup[key]

            morph = m["morph"]
            lemma = m["lemma"]

            item = f"- {greek} ({morph}) → {lemma}"

            if is_finite(morph):
                finite.append(item)

            elif is_nonfinite(morph):
                nonfinite.append(item)

            if greek.strip("·.,;—⸀⸂⸃") in CONNECTORS:
                connectors.append(f"- {greek}")

        lines.append("### Finite Verbs")
        lines.append("")

        if finite:
            lines.extend(finite)
        else:
            lines.append("- none")

        lines.append("")

        lines.append("### Non-Finite Verbs")
        lines.append("")

        if nonfinite:
            lines.extend(nonfinite)
        else:
            lines.append("- none")

        lines.append("")

        lines.append("### Connectors")
        lines.append("")

        if connectors:
            lines.extend(connectors)
        else:
            lines.append("- none")

        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("DONE")
    print(f"Book: {book}")
    print(f"Output: {out_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/export_roots_prep.py <book>")
        raise SystemExit(1)

    export_book(sys.argv[1])


if __name__ == "__main__":
    main()