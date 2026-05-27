#!/usr/bin/env python3
import argparse
import json
from collections import Counter
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
    p.add_argument("--connector", required=True)
    p.add_argument("--debug-normalization", action="store_true")
    args = p.parse_args()

    target = normalize_connector(args.connector)
    rows = []
    raw_counter = Counter()
    normalized_counter = Counter()

    for r in load_jsonl(args.input_jsonl):
        if r.get("record_type") == "metadata":
            continue

        raw_connector = r.get("subordinator_greek_surface")
        connector = normalize_connector(raw_connector)

        raw_counter[raw_connector] += 1
        normalized_counter[connector] += 1

        if connector != target:
            continue

        rows.append(r)

    if args.debug_normalization:
        print()
        print("NORMALIZATION DEBUG")
        print("-------------------")
        print(f"TARGET: {args.connector} -> {target}")
        print()
        print("RAW FOR TARGET FAMILY")
        for raw, count in raw_counter.most_common():
            if normalize_connector(raw) == target:
                print(f"{count:5}  {raw}")
        print()
        print("NORMALIZED TARGET COUNT")
        print(f"{normalized_counter[target]:5}  {target}")

    print()
    print(f"CONNECTOR: {target}")
    print(f"ROWS: {len(rows)}")
    print()

    mood_counter = Counter()

    for r in rows:
        mood_counter[r.get("anchor_mood")] += 1

    print("MOOD DISTRIBUTION")
    print("-----------------")

    for k, v in mood_counter.most_common():
        print(f"{v:5}  {k}")

    if not rows:
        return

    dominant_mood = mood_counter.most_common(1)[0][0]

    print()
    print(f"DOMINANT MOOD: {dominant_mood}")
    print()

    anomalies = []

    for r in rows:
        if r.get("anchor_mood") != dominant_mood:
            anomalies.append(r)

    print("ANOMALIES")
    print("---------")

    if not anomalies:
        print("NONE")

    for r in anomalies:
        out = {
            "reference": r.get("reference"),
            "connector_surface": r.get("subordinator_greek_surface"),
            "finite_verb": r.get("anchor_greek_surface"),
            "anchor_mood": r.get("anchor_mood"),
            "anchor_morphology": r.get("anchor_morphology"),
            "token_pair": [
                r.get("subordinator_token_index_in_verse"),
                r.get("anchor_token_index_in_verse"),
            ],
        }

        print(json.dumps(out, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
