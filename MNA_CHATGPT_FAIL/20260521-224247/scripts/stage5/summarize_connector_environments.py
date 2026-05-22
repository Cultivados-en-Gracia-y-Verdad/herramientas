#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict, Counter
from pathlib import Path

from connector_normalization import normalize_connector


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_jsonl", type=Path)
    args = p.parse_args()

    by_connector = defaultdict(list)

    for r in load_jsonl(args.input_jsonl):
        if r.get("record_type") == "metadata":
            continue

        connector = normalize_connector(
            r.get("subordinator_greek_surface")
        )

        if not connector:
            continue

        by_connector[connector].append(r)

    print("connector\trows\tdominant_mood\tdominant_count\tother_count\tstatus")

    for connector, rows in sorted(by_connector.items(), key=lambda kv: (-len(kv[1]), kv[0])):

        moods = Counter(
            r.get("anchor_mood")
            for r in rows
        )

        dominant_mood, dominant_count = moods.most_common(1)[0]

        other_count = len(rows) - dominant_count

        if other_count == 0:
            status = "UNIFORM"
        else:
            status = "MIXED"

        print(
            f"{connector}\t{len(rows)}\t{dominant_mood}\t"
            f"{dominant_count}\t{other_count}\t{status}"
        )


if __name__ == "__main__":
    main()
