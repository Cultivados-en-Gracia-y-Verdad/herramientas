#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

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

    args = p.parse_args()

    connector = args.connector

    rows = []

    for r in load_jsonl(args.input_jsonl):

        if r.get("connector_greek") != connector:
            continue

        rows.append({
            "clause_id": r.get("clause_id"),
            "finite_verb": r.get("finite_verb"),
            "dependency_status": r.get("dependency_status"),
            "source_stage4_decision": r.get("source_stage4_decision"),
            "chapter": r.get("chapter"),
            "verse": r.get("verse"),
        })

    print()
    print(f"CONNECTOR: {connector}")
    print(f"ROWS: {len(rows)}")
    print()

    dep_counter = Counter()
    decision_counter = Counter()

    for r in rows:
        dep_counter[r["dependency_status"]] += 1
        decision_counter[r["source_stage4_decision"]] += 1

    print("DEPENDENCY STATUS")
    print("-----------------")

    for k,v in dep_counter.most_common():
        print(f"{v:5}  {k}")

    print()
    print("STAGE4 DECISIONS")
    print("----------------")

    for k,v in decision_counter.most_common():
        print(f"{v:5}  {k}")

    print()
    print("SAMPLE ROWS")
    print("-----------")

    for r in rows[:15]:
        print(json.dumps(r, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
