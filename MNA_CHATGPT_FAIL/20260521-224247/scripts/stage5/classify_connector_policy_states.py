#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

POLICY_BY_STRUCTURAL_STATE = {
    "UNIFORM": "PRESERVE_SAFE",
    "DOMINANT_WITH_SPARSE_ANOMALIES": "PRESERVE_WITH_ANOMALY_MONITORING",
    "MIXED_SUBCLASS": "SUBCLASS_REQUIRED",
    "UNRESOLVED_LOW_DATA": "INSUFFICIENT_DATA",
}


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def classify_policy(structural_state):
    return POLICY_BY_STRUCTURAL_STATE.get(
        structural_state,
        "UNKNOWN_STRUCTURAL_STATE",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("structural_states_jsonl", type=Path)
    args = p.parse_args()

    for row in load_jsonl(args.structural_states_jsonl):
        structural_state = row.get("structural_state")
        row["policy_state"] = classify_policy(structural_state)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
