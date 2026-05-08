#!/usr/bin/env python3

import csv
from pathlib import Path

IN_FILE = Path("data/review/phrase_inventory.tsv")
OUT_FILE = Path("data/review/real_rule_candidates.tsv")

MIN_COUNT = 2

rows_out = []

with IN_FILE.open(encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")

    for row in reader:
        count = int(row["count"])
        types = row["alignment_types"]

        if count < MIN_COUNT:
            continue

        if "expanded" not in types and "merged" not in types:
            continue

        rows_out.append(row)

rows_out.sort(
    key=lambda r: (
        -int(r["count"]),
        r["greek_span"],
        r["nbla_span"]
    )
)

with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
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
    writer.writerows(rows_out)

print(f"Wrote: {OUT_FILE}")
print(f"Rows: {len(rows_out)}")