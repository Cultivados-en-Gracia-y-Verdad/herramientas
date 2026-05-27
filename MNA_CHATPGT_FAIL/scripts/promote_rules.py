#!/usr/bin/env python3

import csv
import re
import unicodedata
from pathlib import Path

import yaml

SCRIPT_VERSION = "promote_rules.py v0.1-conservative-2026-05-08"

INVENTORY_PATH = Path("data/review/phrase_inventory.tsv")
RULES_PATH = Path("data/rules/alignment_rules.yaml")
REVIEW_PATH = Path("data/review/promoted_rules.tsv")

MIN_COUNT = 5
MAX_GREEK_WORDS = 2
MAX_NBLA_WORDS = 4

EXCLUDED_GREEK = {
    "δὲ",
    "δέ",
    "γὰρ",
    "γάρ",
    "καὶ",
    "ὁ",
}

ALLOWED_TYPES = {"direct", "expanded"}


def norm_text(s: str) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s


def split_words(s: str):
    return [w for w in str(s or "").strip().split() if w]


def load_yaml_rules(path: Path):
    if not path.exists():
        return {"rules": []}

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if data is None:
        data = {}

    if isinstance(data, list):
        data = {"rules": data}

    if "rules" not in data or data["rules"] is None:
        data["rules"] = []

    return data


def existing_keys(rules):
    keys = set()

    for rule in rules:
        if not isinstance(rule, dict):
            continue

        match = rule.get("match", {})
        action = rule.get("action", {})

        greek = match.get("greek", [])
        nbla = action.get("nbla", [])

        if isinstance(greek, str):
            greek = [greek]
        if isinstance(nbla, str):
            nbla = split_words(nbla)

        keys.add((tuple(norm_text(x) for x in greek), tuple(norm_text(x) for x in nbla)))

    return keys


def main():
    print(SCRIPT_VERSION)

    if not INVENTORY_PATH.exists():
        raise SystemExit(f"Missing inventory: {INVENTORY_PATH}")

    data = load_yaml_rules(RULES_PATH)
    rules = data["rules"]
    existing = existing_keys(rules)

    promoted = []
    skipped = []

    with INVENTORY_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            greek_span = row.get("greek_span", "").strip()
            nbla_span = row.get("nbla_span", "").strip()
            count = int(row.get("count", "0") or 0)
            alignment_types_raw = row.get("alignment_types", "").strip()

            greek_words = split_words(greek_span)
            nbla_words = split_words(nbla_span)
            alignment_types = {x.strip() for x in alignment_types_raw.split(",") if x.strip()}

            reason = None

            if count < MIN_COUNT:
                reason = "count too low"
            elif not greek_words or not nbla_words:
                reason = "empty span"
            elif len(greek_words) > MAX_GREEK_WORDS:
                reason = "greek span too long"
            elif len(nbla_words) > MAX_NBLA_WORDS:
                reason = "nbla span too long"
            elif any(g in EXCLUDED_GREEK for g in greek_words):
                reason = "excluded discourse token"
            elif not alignment_types.issubset(ALLOWED_TYPES):
                reason = f"unsupported types: {alignment_types_raw}"
            elif len(alignment_types) != 1:
                reason = f"mixed types: {alignment_types_raw}"
            elif (tuple(norm_text(x) for x in greek_words), tuple(norm_text(x) for x in nbla_words)) in existing:
                reason = "already exists"

            if reason:
                skipped.append({**row, "decision": "skip", "reason": reason})
                continue

            alignment_type = next(iter(alignment_types))

            new_rule = {
                "match": {
                    "greek": greek_words,
                },
                "action": {
                    "nbla": nbla_words,
                    "type": alignment_type,
                    "consume": len(nbla_words),
                },
                "meta": {
                    "source": "promoted_from_phrase_inventory",
                    "count": count,
                    "first_seen": row.get("first_seen", ""),
                    "last_seen": row.get("last_seen", ""),
                    "confidence": 0.98 if count >= 10 else 0.95,
                },
            }

            rules.append(new_rule)
            existing.add((tuple(norm_text(x) for x in greek_words), tuple(norm_text(x) for x in nbla_words)))

            promoted.append({**row, "decision": "promote", "reason": "accepted"})

    RULES_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "decision",
        "reason",
        "greek_span",
        "nbla_span",
        "count",
        "first_seen",
        "last_seen",
        "alignment_types",
    ]

    with REVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()

        for row in promoted + skipped:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"Promoted: {len(promoted)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Rules total: {len(rules)}")
    print(f"Review: {REVIEW_PATH}")
    print("YAML OK")


if __name__ == "__main__":
    main()