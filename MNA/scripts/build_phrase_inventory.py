#!/usr/bin/env python3

from pathlib import Path
import csv
from collections import defaultdict

SCRIPT_VERSION = "v3.1-phrase-inventory-2026-05-06"

ALIGN_DIR = Path("data/alignments/1corintios")
OUT_DIR = Path("data/review")
OUT_FILE = OUT_DIR / "phrase_inventory.tsv"

IGNORE_ALIGNMENTS = {
    "missing",
    "shared",
}

inventory = defaultdict(lambda: {
    "count": 0,
    "refs": set(),
    "types": set(),
})

def load_tsv(path):
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)

def normalize(text):
    return " ".join(text.strip().split())

def process_file(path):
    rows = load_tsv(path)

    groups = defaultdict(list)

    for row in rows:
        align = row["ALIGNMENT"].strip()

        if align in IGNORE_ALIGNMENTS:
            continue

        nbla = normalize(row["NBLA_TEXT"])

        if not nbla or nbla == "-":
            continue

        key = (
            row["NBLA_IDX"],
            nbla,
            align,
        )

        groups[key].append(row)

    for (nbla_idx, nbla_text, align), group_rows in groups.items():

        greek_span = " ".join(
            r["GREEK"] for r in group_rows
        )

        greek_span = normalize(greek_span)

        if not greek_span:
            continue

        phrase_key = (
            greek_span,
            nbla_text,
        )

        inventory[phrase_key]["count"] += 1
        inventory[phrase_key]["refs"].add(
            f'{group_rows[0]["BOOK"]} {group_rows[0]["CH"]}:{group_rows[0]["VS"]}'
        )
        inventory[phrase_key]["types"].add(align)

def write_inventory():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for (greek_span, nbla_span), data in inventory.items():

        refs = sorted(data["refs"])

        rows.append({
            "greek_span": greek_span,
            "nbla_span": nbla_span,
            "count": data["count"],
            "first_seen": refs[0],
            "last_seen": refs[-1],
            "alignment_types": ",".join(sorted(data["types"])),
        })

    rows.sort(
        key=lambda r: (
            -r["count"],
            r["greek_span"],
        )
    )

    with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "greek_span",
                "nbla_span",
                "count",
                "first_seen",
                "last_seen",
                "alignment_types",
            ],
            delimiter="\t",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)

def main():

    print(f"build_phrase_inventory.py {SCRIPT_VERSION}")

    files = sorted(
        p for p in ALIGN_DIR.glob("*.tsv")
        if not p.name.endswith(".original.tsv")
    )

    print(f"TSV files found: {len(files)}")

    for path in files:
        process_file(path)

    write_inventory()

    print(f"Phrases collected: {len(inventory)}")
    print(f"Output: {OUT_FILE}")

if __name__ == "__main__":
    main()