#!/usr/bin/env python3

import yaml
from pathlib import Path

RULES_PATH = Path("data/rules/alignment_rules.yaml")

NEW_RULES = [
    {
        "match": {
            "greek": ["κἀγὼ"],
            "ref": "1corintios 11:1",
        },
        "action": {
            "nbla": ["mí"],
            "type": "direct",
            "consume": 1,
        },
    },

    {
        "match": {
            "greek": ["πλὴν", "οὔτε"],
            "ref": "1corintios 11:11",
        },
        "action": {
            "nbla": ["en", "el", "señor", "ni"],
            "type": "expanded",
            "consume": 4,
        },
    },

    {
        "match": {
            "greek": ["ἀτιμία"],
            "ref": "1corintios 11:14",
        },
        "action": {
            "nbla": ["deshonra"],
            "type": "direct",
            "consume": 1,
        },
    },

    {
        "match": {
            "greek": ["τί", "εἴπω"],
            "ref": "1corintios 11:22",
        },
        "action": {
            "nbla": ["diré"],
            "type": "expanded",
            "consume": 1,
        },
    },

    {
        "match": {
            "greek": ["δὲ", "ἑαυτοὺς"],
            "ref": "1corintios 11:31",
        },
        "action": {
            "nbla": ["nosotros", "mismos"],
            "type": "expanded",
            "consume": 2,
        },
    },
]

data = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))

if "rules" not in data:
    data["rules"] = []

existing = set()

for rule in data["rules"]:

    match = rule.get("match", {})

    existing.add((
        tuple(match.get("greek", [])),
        match.get("ref"),
    ))

added = 0

for rule in NEW_RULES:

    match = rule["match"]

    key = (
        tuple(match["greek"]),
        match.get("ref"),
    )

    if key not in existing:
        data["rules"].append(rule)
        added += 1

RULES_PATH.write_text(
    yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
    ),
    encoding="utf-8",
)

print(f"Added rules: {added}")
print(f"Total rules: {len(data['rules'])}")
print("YAML OK")