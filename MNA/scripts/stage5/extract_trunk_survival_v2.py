#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

RULE_WARN = "S5-PRESERVE-WARN-UNKNOWN-001"
RULE_COND = "S5-PRESERVE-CONDITIONAL-UNIT-001"
RULE_STAGE4 = "S5-PRESERVE-STAGE4-SURVIVES-001"
RULE_COORD = "S5-COORDINATING-SURVIVE-001"
RULE_CONSEQ = "S5-CONSEQUENCE-SURVIVE-001"
RULE_TEMP_COND = "S5-TEMPORAL-CONDITION-SURVIVE-001"

EI = "\u03b5\u1f30"
EAN = "\u1f10\u1f70\u03bd"
EITE = "\u03b5\u1f34\u03c4\u03b5"
HOSTE = "\u1f65\u03c3\u03c4\u03b5"
HOTAN = "\u1f45\u03c4\u03b1\u03bd"
HOTI = "\u1f45\u03c4\u03b9"
HINA = "\u1f35\u03bd\u03b1"
HOS = "\u1f61\u03c2"
KATHOS = "\u03ba\u03b1\u03b8\u1f7c\u03c2"

COND = {EI, EAN}
COORD = {EITE}
CONSEQ = {HOSTE}
TEMP_COND = {HOTAN}
WARN = {HOTI, HINA, HOS, KATHOS}

MAP = {
    "\u0395\u1f30": EI,
    "\u03b5\u1f34": EI,
    "\u0395\u1f34": EI,
    "\u2e00\u03b5\u1f34": EI,
    "\u2e02\u03b5\u1f34": EI,
    "\u2e00\u0395\u1f30": EI,
    "\u1f18\u1f70\u03bd": EAN,
    "\u1f10\u03ac\u03bd": EAN,
    "\u2e00\u1f10\u1f70\u03bd": EAN,
    "\u1f10\u1f70\u03bd\u2e03": EAN,
    "\u1f10\u1f70\u03bd\u2e05": EAN,
    "\u0395\u1f34\u03c4\u03b5": EITE,
    "\u2e00\u03b5\u1f34\u03c4\u03b5": EITE,
    "\u1f6d\u03c3\u03c4\u03b5": HOSTE,
    "\u1f6d\u03c3\u03c4\u03b5,": HOSTE,
    "\u1f65\u03c3\u03c4\u03b5,": HOSTE,
    "\u1f4d\u03c4\u03b9": HOTI,
    "\u2e00\u1f45\u03c4\u03b5": "\u1f45\u03c4\u03b5",
    "\u039a\u03b1\u03b8\u03ac\u03c0\u03b5\u03c1": "\u03ba\u03b1\u03b8\u03ac\u03c0\u03b5\u03c1",
    "\u2e00\u03ba\u03b1\u03b8\u03ac\u03c0\u03b5\u03c1": "\u03ba\u03b1\u03b8\u03ac\u03c0\u03b5\u03c1",
    "\u1f18\u03c0\u03b5\u1f76": "\u1f10\u03c0\u03b5\u1f76",
    "\u03ba\u03b1\u03b8\u03ce\u03c2": KATHOS,
    "\u2e00\u03ba\u03b1\u03b8\u03ce\u03c2": KATHOS,
}

def norm(x):
    if x is None:
        return None
    x = str(x).strip()
    return MAP.get(x, x)

def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)

def decide(r):
    conn = norm(r.get("connector_greek") or r.get("connector"))
    dep = r.get("dependency_status")
    stage4 = r.get("stage4_decision")
    out = {
        "book": r.get("book"),
        "chapter": r.get("chapter"),
        "verse": r.get("verse"),
        "unit_id": r.get("unit_id"),
        "clause_id": r.get("clause_id"),
        "finite_verb": r.get("finite_verb"),
        "connector_greek": conn,
        "dependency_status": dep,
        "source_stage4_decision": stage4,
        "warnings": list(r.get("warnings") or []),
        "flags": list(r.get("flags") or []),
    }
    if conn in COND:
        out.update(survival_decision="SURVIVE", survival_rule_id=RULE_COND, survival_reason="Conditional logical unit preserved.")
        return out
    if conn in TEMP_COND:
        out.update(survival_decision="SURVIVE", survival_rule_id=RULE_TEMP_COND, survival_reason="Temporal-condition connector preserved.")
        return out
    if conn in COORD:
        out.update(survival_decision="SURVIVE", survival_rule_id=RULE_COORD, survival_reason="Coordinating/disjunctive connector preserved.")
        return out
    if conn in CONSEQ:
        out.update(survival_decision="SURVIVE", survival_rule_id=RULE_CONSEQ, survival_reason="Consequence/inference connector preserved.")
        return out
    if conn in WARN:
        out.update(survival_decision="PRESERVE_WARN", survival_rule_id=RULE_WARN, survival_reason="Warning-sensitive subordinator dependency candidate.")
        out["warnings"].append({"code": "S5_WARNING_SENSITIVE_CONNECTOR", "connector": conn})
        return out
    if dep == "DEPENDENCY_CANDIDATE_FOR_MANUAL_AUDIT":
        out.update(survival_decision="PRESERVE_WARN", survival_rule_id=RULE_WARN, survival_reason="Unresolved dependency candidate.")
        out["warnings"].append({"code": "S5_DEPENDENCY_CANDIDATE_UNRESOLVED"})
        return out
    if stage4 == "STRUCTURALLY_SURVIVES":
        out.update(survival_decision="SURVIVE", survival_rule_id=RULE_STAGE4, survival_reason="Stage 4 classified this record as structurally surviving.")
        return out
    out.update(survival_decision="PRESERVE_WARN", survival_rule_id=RULE_WARN, survival_reason="Preserved pending further survivability refinement.")
    out["warnings"].append({"code": "S5_DEFAULT_WARN"})
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    p.add_argument("--rules", type=Path, required=True)
    a = p.parse_args()
    a.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with a.output_jsonl.open("w", encoding="utf-8") as f:
        for r in load_jsonl(a.input_jsonl):
            f.write(json.dumps(decide(r), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    print(f"WROTE {count} records -> {a.output_jsonl}")

if __name__ == "__main__":
    main()
