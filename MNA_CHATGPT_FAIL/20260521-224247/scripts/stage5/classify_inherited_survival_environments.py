#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

INHERITED_RULE_ID = "S5-PRESERVE-STAGE4-SURVIVES-001"


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def environment_key(row):
    return {
        "anchor_mood": row.get("anchor_mood"),
        "anchor_person": row.get("anchor_person"),
        "anchor_number": row.get("anchor_number"),
        "anchor_morphology": row.get("anchor_morphology"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("enriched_survival_jsonl", type=Path)
    p.add_argument("--jsonl", action="store_true")
    args = p.parse_args()

    inherited = []

    for row in load_jsonl(args.enriched_survival_jsonl):
        if row.get("survival_rule_id") == INHERITED_RULE_ID:
            inherited.append(row)

    by_mood = defaultdict(list)
    by_environment = Counter()

    for row in inherited:
        mood = row.get("anchor_mood")
        by_mood[mood].append(row)
        key = (
            row.get("anchor_mood"),
            row.get("anchor_person"),
            row.get("anchor_number"),
            row.get("anchor_morphology"),
        )
        by_environment[key] += 1

    if args.jsonl:
        for key, count in by_environment.most_common():
            mood, person, number, morphology = key
            print(json.dumps({
                "anchor_mood": mood,
                "anchor_person": person,
                "anchor_number": number,
                "anchor_morphology": morphology,
                "count": count,
            }, ensure_ascii=False, sort_keys=True))
        return

    print(f"INHERITED_STAGE4_SURVIVALS: {len(inherited)}")
    print()

    print("BY MOOD")
    print("-------")
    for mood, rows in sorted(by_mood.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
        print(f"{len(rows):5}  {mood}")

    print()
    print("TOP ENVIRONMENTS")
    print("----------------")
    for key, count in by_environment.most_common(40):
        mood, person, number, morphology = key
        print(
            f"{count:5}  mood={mood} person={person} "
            f"number={number} morphology={morphology}"
        )


if __name__ == "__main__":
    main()
