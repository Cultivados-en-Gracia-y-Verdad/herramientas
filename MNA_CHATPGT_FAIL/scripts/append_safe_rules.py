#!/usr/bin/env python3

import yaml
from pathlib import Path

RULES_PATH = Path("data/rules/alignment_rules.yaml")

NEW_RULES = [
    {
        "match": {"greek": ["ἵνα"]},
        "action": {"nbla": ["para", "que"], "type": "expanded", "consume": 2},
    },
    {
        "match": {"greek": ["θεοῦ"]},
        "action": {"nbla": ["de", "dios"], "type": "expanded", "consume": 2},
    },
    {
        "match": {"greek": ["χριστοῦ"]},
        "action": {"nbla": ["de", "cristo"], "type": "expanded", "consume": 2},
    },
    {
        "match": {"greek": ["ὑμῶν"]},
        "action": {"nbla": ["de", "ustedes"], "type": "expanded", "consume": 2},
    },
    {
        "match": {"greek": ["κυρίου"]},
        "action": {"nbla": ["del", "señor"], "type": "expanded", "consume": 2},
    },
    {
        "match": {"greek": ["περὶ"]},
        "action": {"nbla": ["en", "cuanto", "a"], "type": "expanded", "consume": 3},
    },
    {
        "match": {"greek": ["κεφαλὴν"]},
        "action": {"nbla": ["cabeza"], "type": "direct", "consume": 1},
    },
    {
        "match": {"greek": ["ἄνδρα"]},
        "action": {"nbla": ["hombre"], "type": "direct", "consume": 1},
    },
    {
        "match": {"greek": ["ἀτιμία"]},
        "action": {"nbla": ["deshonra"], "type": "direct", "consume": 1},
    },
    {
        "match": {"greek": ["ἀλλήλους"]},
        "action": {"nbla": ["otros"], "type": "direct", "consume": 1},
    },
    {
        "match": {"greek": ["ποτήριον"]},
        "action": {"nbla": ["copa"], "type": "direct", "consume": 1},
    },
    {
        "match": {"greek": ["δὲ", "ἑαυτοὺς"]},
        "action": {"nbla": ["nosotros", "mismos"], "type": "expanded", "consume": 2},
    },
]

data = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))

if "rules" not in data:
    data["rules"] = []

existing = {
    tuple(rule.get("match", {}).get("greek", []))
    for rule in data["rules"]
}

added = 0

for rule in NEW_RULES:
    key = tuple(rule["match"]["greek"])

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