#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from connector_normalization import normalize_connector

RULE_WARN="S5-PRESERVE-WARN-UNKNOWN-001"
RULE_COND="S5-PRESERVE-CONDITIONAL-UNIT-001"
RULE_STAGE4="S5-PRESERVE-STAGE4-SURVIVES-001"
RULE_COORD="S5-COORDINATING-SURVIVE-001"
RULE_TEMP="S5-TEMPORAL-CONDITION-SURVIVE-001"

COND={"εἰ","ἐὰν"}
TEMP={"ὅταν"}
COORD={"εἴτε"}
WARN={"ὅτι","ἵνα","ὡς","καθὼς"}
BLOCK={"SUBCLASS_REQUIRED","INSUFFICIENT_DATA"}
MONITOR={"PRESERVE_WITH_ANOMALY_MONITORING"}

def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def load_policy(path):
    if not path:
        return {}
    d={}
    for r in load_jsonl(path):
        c=normalize_connector(r.get("connector"))
        if c:
            d[c]=r
    return d

def base(r, conn):
    return {
        "book":r.get("book"),"chapter":r.get("chapter"),"verse":r.get("verse"),
        "unit_id":r.get("unit_id"),"clause_id":r.get("clause_id"),
        "finite_verb":r.get("finite_verb"),"connector_greek":conn,
        "dependency_status":r.get("dependency_status"),
        "source_stage4_decision":r.get("stage4_decision"),
        "warnings":list(r.get("warnings") or []),"flags":list(r.get("flags") or []),
    }

def survive(out, conn, policy, rule, reason):
    p=policy.get(conn)
    if p and p.get("policy_state") in BLOCK:
        out.update(
            survival_decision="PRESERVE_WARN",
            survival_rule_id=RULE_WARN,
            survival_reason="Connector policy forbids global survival; subclassing or more data required.",
            policy_state=p.get("policy_state"),
            structural_state=p.get("structural_state"),
        )
        out["warnings"].append({"code":"S5_POLICY_BLOCKED_GLOBAL_SURVIVE","connector":conn,"policy_state":p.get("policy_state")})
        return out
    out.update(survival_decision="SURVIVE",survival_rule_id=rule,survival_reason=reason)
    if p and p.get("policy_state") in MONITOR:
        out["policy_state"]=p.get("policy_state")
        out["structural_state"]=p.get("structural_state")
        out["warnings"].append({"code":"S5_ANOMALY_MONITORING_REQUIRED","connector":conn,"policy_state":p.get("policy_state")})
    return out

def decide(r, policy):
    conn=normalize_connector(r.get("connector_greek") or r.get("connector"))
    out=base(r,conn)
    dep=r.get("dependency_status")
    stage4=r.get("stage4_decision")

    if conn in COND:
        return survive(out,conn,policy,RULE_COND,"Conditional logical unit preserved.")
    if conn in TEMP:
        return survive(out,conn,policy,RULE_TEMP,"Temporal-condition connector preserved.")
    if conn in COORD:
        return survive(out,conn,policy,RULE_COORD,"Coordinating/disjunctive connector preserved.")
    if conn in WARN:
        out.update(survival_decision="PRESERVE_WARN",survival_rule_id=RULE_WARN,survival_reason="Warning-sensitive subordinator dependency candidate.")
        out["warnings"].append({"code":"S5_WARNING_SENSITIVE_CONNECTOR","connector":conn})
        return out
    if dep=="DEPENDENCY_CANDIDATE_FOR_MANUAL_AUDIT":
        out.update(survival_decision="PRESERVE_WARN",survival_rule_id=RULE_WARN,survival_reason="Unresolved dependency candidate.")
        out["warnings"].append({"code":"S5_DEPENDENCY_CANDIDATE_UNRESOLVED"})
        return out
    if stage4=="STRUCTURALLY_SURVIVES":
        return survive(out,conn,policy,RULE_STAGE4,"Stage 4 classified this record as structurally surviving.")
    out.update(survival_decision="PRESERVE_WARN",survival_rule_id=RULE_WARN,survival_reason="Preserved pending further survivability refinement.")
    out["warnings"].append({"code":"S5_DEFAULT_WARN"})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input_jsonl",type=Path)
    p.add_argument("output_jsonl",type=Path)
    p.add_argument("--rules",type=Path,required=True)
    p.add_argument("--policy",type=Path)
    a=p.parse_args()
    policy=load_policy(a.policy)
    a.output_jsonl.parent.mkdir(parents=True,exist_ok=True)
    n=0
    with a.output_jsonl.open("w",encoding="utf-8") as f:
        for r in load_jsonl(a.input_jsonl):
            f.write(json.dumps(decide(r,policy),ensure_ascii=False,sort_keys=True)+"\n")
            n+=1
    print(f"WROTE {n} records -> {a.output_jsonl}")

if __name__=="__main__":
    main()
