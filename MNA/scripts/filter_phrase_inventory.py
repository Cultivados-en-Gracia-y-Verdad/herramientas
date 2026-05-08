#!/usr/bin/env python3

import csv
from pathlib import Path

IN_FILE = Path("data/review/phrase_inventory.tsv")
OUT_FILE = Path("data/review/promotable_phrases.tsv")

MIN_COUNT = 3

BAD_SINGLETONS = {
    "ὁ", "ἡ", "το", "τὸ", "τοῦ", "τῷ", "τὴν", "τὸν",
    "καὶ", "δὲ", "γὰρ", "γάρ", "οὐ", "οὐκ", "μὴ", "ἐν"
}

rows_out = []

with IN_FILE.open(encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")

    for row in reader:

        count = int(row["count"])

        greek_span = row["greek_span"].strip()
        nbla_span = row["nbla_span"].strip()

        greek_words = greek_span.split()
        nbla_words = nbla_span.split()

        if count < MIN_COUNT:
            continue

        if len(greek_words) == 1 and greek_span in BAD_SINGLETONS:
            continue

        if len(nbla_words) > 4 and count < 5:
            continue

        if not nbla_span:
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