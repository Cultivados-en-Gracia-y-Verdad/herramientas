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

    for r in inherited:
        by_chapter[r.get("chapter")] += 1
        by_connector[r.get("connector_greek")] += 1
        by_dependency_status[r.get("dependency_status")] += 1
        by_warning_count[len(r.get("warnings") or [])] += 1

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

    print()
    print("BY CONNECTOR")
    print("------------")
    for k, v in by_connector.most_common():
        print(f"{v:5}  {k}")

    print()
    print("BY DEPENDENCY STATUS")
    print("--------------------")
    for k, v in by_dependency_status.most_common():
        print(f"{v:5}  {k}")

    print()
    print("BY WARNING COUNT")
    print("----------------")
    for k, v in sorted(by_warning_count.items()):
        print(f"{v:5}  {k}")


if __name__ == "__main__":
    main()
