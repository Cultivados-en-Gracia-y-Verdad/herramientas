#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path

INHERITED_RULE_ID = "S5-PRESERVE-STAGE4-SURVIVES-001"


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def print_counter(title, counter, limit=None):
    print()
    print(title)
    print("-" * len(title))
    items = counter.most_common(limit)
    for k, v in items:
        print(f"{v:5}  {k}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("survival_jsonl", type=Path)
    p.add_argument("--jsonl", action="store_true")
    args = p.parse_args()

    inherited = []

    for r in load_jsonl(args.survival_jsonl):
        if r.get("survival_rule_id") == INHERITED_RULE_ID:
            inherited.append(r)

    by_chapter = Counter()
    by_connector = Counter()
    by_dependency_status = Counter()
    by_warning_count = Counter()
    by_anchor_mood = Counter()
    by_anchor_morphology = Counter()
    by_anchor_person = Counter()
    by_anchor_number = Counter()
    by_anchor_enrichment_status = Counter()

    for r in inherited:
        by_chapter[r.get("chapter")] += 1
        by_connector[r.get("connector_greek")] += 1
        by_dependency_status[r.get("dependency_status")] += 1
        by_warning_count[len(r.get("warnings") or [])] += 1
        by_anchor_mood[r.get("anchor_mood")] += 1
        by_anchor_morphology[r.get("anchor_morphology")] += 1
        by_anchor_person[r.get("anchor_person")] += 1
        by_anchor_number[r.get("anchor_number")] += 1
        by_anchor_enrichment_status[r.get("anchor_enrichment_status")] += 1

    if args.jsonl:
        for r in inherited:
            print(json.dumps(r, ensure_ascii=False, sort_keys=True))
        return

    print(f"INHERITED_STAGE4_SURVIVALS: {len(inherited)}")

    print()
    print("BY CHAPTER")
    print("----------")
    for k, v in sorted(by_chapter.items(), key=lambda kv: kv[0] or 0):
        print(f"{v:5}  {k}")

    print_counter("BY CONNECTOR", by_connector)
    print_counter("BY DEPENDENCY STATUS", by_dependency_status)
    print_counter("BY WARNING COUNT", by_warning_count)
    print_counter("BY ANCHOR ENRICHMENT STATUS", by_anchor_enrichment_status)
    print_counter("BY ANCHOR MOOD", by_anchor_mood)
    print_counter("BY ANCHOR PERSON", by_anchor_person)
    print_counter("BY ANCHOR NUMBER", by_anchor_number)
    print_counter("TOP ANCHOR MORPHOLOGIES", by_anchor_morphology, limit=25)


if __name__ == "__main__":
    main()
