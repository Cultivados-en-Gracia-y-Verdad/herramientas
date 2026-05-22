#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from connector_normalization import normalize_connector


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def classify_state(total, dominant_count, other_count):
    if total <= 2:
        return "UNRESOLVED_LOW_DATA"

    if other_count == 0:
        return "UNIFORM"

    ratio = dominant_count / total

    if ratio >= 0.90:
        return "DOMINANT_WITH_SPARSE_ANOMALIES"

    return "MIXED_SUBCLASS"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_jsonl", type=Path)
    p.add_argument("--jsonl", action="store_true")
    args = p.parse_args()

    by_connector = defaultdict(list)

    for r in load_jsonl(args.input_jsonl):
        if r.get("record_type") == "metadata":
            continue

        connector = normalize_connector(r.get("subordinator_greek_surface"))
        if not connector:
            continue

        by_connector[connector].append(r)

    rows = []

    for connector, records in sorted(by_connector.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        moods = Counter(r.get("anchor_mood") for r in records)
        dominant_mood, dominant_count = moods.most_common(1)[0]
        total = len(records)
        other_count = total - dominant_count
        state = classify_state(total, dominant_count, other_count)

        rows.append({
            "connector": connector,
            "rows": total,
            "dominant_mood": dominant_mood,
            "dominant_count": dominant_count,
            "other_count": other_count,
            "structural_state": state,
            "mood_distribution": dict(moods),
        })

    if args.jsonl:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    else:
        print("connector\trows\tdominant_mood\tdominant_count\tother_count\tstructural_state")
        for row in rows:
            print(
                f"{row['connector']}\t{row['rows']}\t{row['dominant_mood']}\t"
                f"{row['dominant_count']}\t{row['other_count']}\t{row['structural_state']}"
            )


if __name__ == "__main__":
    main()
