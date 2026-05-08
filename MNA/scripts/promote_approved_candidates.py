#!/usr/bin/env python3
"""
promote_approved_candidates.py

Promote manually approved validator-guided candidates
from:

    data/review/rule_candidates.tsv

into:

    data/rules/alignment_rules.yaml
"""

from __future__ import annotations

import csv
from pathlib import Path
import yaml

SCRIPT_VERSION = "v0.1-validator-promotion-2026-05-08"

CANDIDATES = Path("data/review/rule_candidates.tsv")
RULES_YAML = Path("data/rules/alignment_rules.yaml")


def load_rules(path):
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("rules", [])

    raise ValueError(f"Unsupported rules YAML structure: {type(data)}")


def existing_keys(rules):
    keys = set()

    for r in rules:
        try:
            greek = tuple(r["match"]["greek"])
            nbla = tuple(r["action"]["nbla"])
            keys.add((greek, nbla))
        except Exception:
            continue

    return keys


def build_rule(row):
    greek = row["greek_span"].split()
    nbla = row["nbla_span"].split()

    return {
        "match": {
            "greek": greek
        },
        "action": {
            "nbla": nbla,
            "type": row["suggested_type"],
            "consume": len(nbla)
        },
        "meta": {
            "source": "validator_guided_candidate",
            "ref": row["ref"],
            "confidence": row["confidence"],
        }
    }


def main():
    print(f"promote_approved_candidates.py {SCRIPT_VERSION}")

    rules = load_yaml_rules(RULES_YAML)
    keys = existing_keys(rules)

    promoted = 0
    skipped = 0

    with CANDIDATES.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            approved = row.get("approved", "").strip().lower()

            if approved != "yes":
                skipped += 1
                continue

            greek = tuple(row["greek_span"].split())
            nbla = tuple(row["nbla_span"].split())

            key = (greek, nbla)

            if key in keys:
                skipped += 1
                continue

            rule = build_rule(row)

            rules.append(rule)
            keys.add(key)
            promoted += 1

    with RULES_YAML.open("w", encoding="utf-8") as f:
        yaml.dump(
            rules,
            f,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )

    print(f"Promoted: {promoted}")
    print(f"Skipped: {skipped}")
    print(f"Rules total: {len(rules)}")
    print("YAML OK")


if __name__ == "__main__":
    main()