#!/usr/bin/env python3

from pathlib import Path
import re

G_DIR = Path("data/g-tokens")
OUT_DIR = Path("data/alignments")

HEADER = "BOOK\tCH\tVS\tG_IDX\tGREEK\tNBLA_IDX\tNBLA_TEXT\tALIGNMENT\n"


def read_tokens(path):
    tokens = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, token = line.split(maxsplit=1)
            tokens.append((idx, token))
    return tokens


OUT_DIR.mkdir(parents=True, exist_ok=True)

pattern = re.compile(r"^(1corintios)-(\d+)-(\d+)\.txt$")

for g_file in sorted(G_DIR.glob("1corintios-*-*.txt")):
    m = pattern.match(g_file.name)
    if not m:
        continue

    book = "1cor"
    chapter = m.group(2)
    verse = m.group(3)

    out_file = OUT_DIR / f"{g_file.stem}.tsv"

    if out_file.exists():
        print(f"SKIP existing {out_file}")
        continue

    tokens = read_tokens(g_file)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for idx, greek in tokens:
            f.write(f"{book}\t{chapter}\t{verse}\t{idx}\t{greek}\t-\t-\tmissing\n")

    print(f"WROTE {out_file}")