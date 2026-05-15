#!/usr/bin/env python3

import csv
import sys
import os
import yaml
from pathlib import Path


DEFAULT_RULES_PATH = "data/rules/alignment_rules.yaml"
LEARNED_PRIORITY = 80


def load_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)
    return rows


def load_rules(path):
    path = Path(path)

    if not path.exists():
        return {"rules": []}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        data = {}

    if "rules" not in data or data["rules"] is None:
        data["rules"] = []

    return data


def save_rules(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def nbla_words(nbla_text):
    if not nbla_text or nbla_text == "-":
        return []
    return nbla_text.split()


def existing_rule_keys(rules):
    keys = set()

    for rule in rules:
        greek = tuple(rule.get("match", {}).get("greek", []))
        nbla = tuple(rule.get("action", {}).get("nbla", []))
        action_type = rule.get("action", {}).get("type", "")
        keys.add((greek, nbla, action_type))

    return keys


def is_learnable_single_row(row):
    if row["ALIGNMENT"] in ("missing", "shared"):
        return False

    if row["NBLA_IDX"] == "-" or row["NBLA_TEXT"] == "-":
        return False

    if not row["GREEK"]:
        return False

    return True


def make_rule(row):
    words = nbla_words(row["NBLA_TEXT"])

    if not words:
        return None

    return {
        "match": {
            "greek": [row["GREEK"]],
        },
        "action": {
            "nbla": words,
            "type": row["ALIGNMENT"],
            "consume": len(words),
        },
        "priority": LEARNED_PRIORITY,
    }


def compare_and_learn(old_rows, new_rows, rules_data):
    print("\n=== LEARNING REPORT ===\n")

    found_changes = False
    learned_count = 0
    skipped_count = 0

    rules = rules_data["rules"]
    known = existing_rule_keys(rules)

    for old, new in zip(old_rows, new_rows):
        changes = []

        if old["NBLA_IDX"] != new["NBLA_IDX"]:
            changes.append("NBLA_IDX")

        if old["NBLA_TEXT"] != new["NBLA_TEXT"]:
            changes.append("NBLA_TEXT")

        if old["ALIGNMENT"] != new["ALIGNMENT"]:
            changes.append("ALIGNMENT")

        if not changes:
            continue

        found_changes = True

        print(f"G_IDX {new['G_IDX']} | {new['GREEK']}")
        print(f"  CHANGE: {', '.join(changes)}")
        print(f"  OLD: {old['NBLA_IDX']} | {old['NBLA_TEXT']} | {old['ALIGNMENT']}")
        print(f"  NEW: {new['NBLA_IDX']} | {new['NBLA_TEXT']} | {new['ALIGNMENT']}")

        if is_learnable_single_row(new):
            rule = make_rule(new)

            greek_key = tuple(rule["match"]["greek"])
            nbla_key = tuple(rule["action"]["nbla"])
            type_key = rule["action"]["type"]
            key = (greek_key, nbla_key, type_key)

            if key not in known:
                rules.append(rule)
                known.add(key)
                learned_count += 1
                print("  LEARNED: yes")
            else:
                skipped_count += 1
                print("  LEARNED: already exists")
        else:
            skipped_count += 1
            print("  LEARNED: skipped")

        print("-" * 50)

    return found_changes, learned_count, skipped_count


def main():
    if len(sys.argv) not in (3, 4):
        print(
            "Usage:\n"
            "  python3 scripts/learn_from_fix.py original.tsv corrected.tsv\n"
            "  python3 scripts/learn_from_fix.py original.tsv corrected.tsv data/rules/alignment_rules.yaml"
        )
        sys.exit(2)

    old_path = sys.argv[1]
    new_path = sys.argv[2]
    rules_path = sys.argv[3] if len(sys.argv) == 4 else DEFAULT_RULES_PATH

    old_rows = load_tsv(old_path)
    new_rows = load_tsv(new_path)

    if len(old_rows) != len(new_rows):
        print("ERROR: original and corrected TSV files have different row counts")
        sys.exit(1)

    rules_data = load_rules(rules_path)

    found_changes, learned_count, skipped_count = compare_and_learn(
        old_rows,
        new_rows,
        rules_data,
    )

    if learned_count:
        save_rules(rules_path, rules_data)
        print(f"\n✔ Rules updated: {rules_path}")
        print(f"✔ New rules learned: {learned_count}")

    print(f"ℹ Skipped/already present: {skipped_count}")

    if found_changes:
        os.remove(old_path)
        print(f"✔ Original snapshot removed: {old_path}")
    else:
        print("\n⚠ No changes detected — original retained")


if __name__ == "__main__":
    main()