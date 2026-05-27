#!/usr/bin/env python3
import argparse, json
from pathlib import Path

CONDITIONALS = {"εἰ", "ἐὰν"}

ENV_STRONG_POSITIVE = "ENV-001-STRONG_POSITIVE_INDEPENDENCE_SIGNAL_SET"
ENV_CONDITIONAL_PRESSURE = "ENV-002-CONDITIONAL_SURVIVAL_UNDER_DEPENDENCY_PRESSURE"
ENV_DEPENDENCY_PRESSURE_WARN = "ENV-003-DEPENDENCY_PRESSURE_PRESERVE_WARN"
ENV_UNCLASSIFIED = "ENV-999-UNCLASSIFIED_CANDIDACY_ENVIRONMENT"

def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def load_by_clause_id(path):
    d = {}
    for r in load_jsonl(path):
        cid = r.get("clause_id")
        if cid:
            d[cid] = r
    return d

def classify(pos, neg):
    connector = pos.get("connector_greek")
    rule = pos.get("survival_rule_id")
    decision = pos.get("survival_decision")
    dep = pos.get("dependency_status")
    sig_count = pos.get("signal_count")
    neg_count = neg.get("negative_pressure_count")

    if sig_count == 4 and neg_count == 0:
        return ENV_STRONG_POSITIVE

    if (
        neg_count == 2
        and connector in CONDITIONALS
        and rule == "S5-PRESERVE-CONDITIONAL-UNIT-001"
        and dep == "DEPENDENCY_CANDIDATE_FOR_MANUAL_AUDIT"
        and decision == "SURVIVE"
    ):
        return ENV_CONDITIONAL_PRESSURE

    if neg_count and decision == "PRESERVE_WARN":
        return ENV_DEPENDENCY_PRESSURE_WARN

    return ENV_UNCLASSIFIED

def main():
    p = argparse.ArgumentParser()
    p.add_argument("positive_signals_jsonl", type=Path)
    p.add_argument("negative_pressure_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    a = p.parse_args()

    neg_by_clause = load_by_clause_id(a.negative_pressure_jsonl)
    a.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    missing = 0

    with a.output_jsonl.open("w", encoding="utf-8") as f:
        for pos in load_jsonl(a.positive_signals_jsonl):
            cid = pos.get("clause_id")
            neg = neg_by_clause.get(cid)

            if neg is None:
                missing += 1
                neg = {"negative_pressure": [], "negative_pressure_count": None}

            out = {
                "book": pos.get("book"),
                "chapter": pos.get("chapter"),
                "verse": pos.get("verse"),
                "unit_id": pos.get("unit_id"),
                "clause_id": cid,
                "finite_verb": pos.get("finite_verb"),
                "connector_greek": pos.get("connector_greek"),
                "dependency_status": pos.get("dependency_status"),
                "survival_decision": pos.get("survival_decision"),
                "survival_rule_id": pos.get("survival_rule_id"),
                "anchor_mood": pos.get("anchor_mood"),
                "anchor_morphology": pos.get("anchor_morphology"),
                "anchor_person": pos.get("anchor_person"),
                "anchor_number": pos.get("anchor_number"),
                "signals": pos.get("signals", []),
                "signal_count": pos.get("signal_count"),
                "negative_pressure": neg.get("negative_pressure", []),
                "negative_pressure_count": neg.get("negative_pressure_count"),
            }
            out["candidacy_environment"] = classify(pos, neg)

            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    print(f"WROTE {count} records -> {a.output_jsonl}")
    print(f"MISSING_NEGATIVE_ROWS: {missing}")

if __name__ == "__main__":
    main()
