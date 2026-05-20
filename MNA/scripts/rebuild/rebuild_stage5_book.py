#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd, root):
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(root)).returncode

def main():
    p = argparse.ArgumentParser()
    p.add_argument("book")
    args = p.parse_args()

    root = Path(__file__).resolve().parents[2]
    book = args.book.strip().lower()

    steps = [
        [sys.executable, "scripts/stage4/build_predicate_completeness.py", book],
        [sys.executable, "scripts/stage4/validate_predicate_completeness.py", book],
        [sys.executable, "scripts/stage4/build_independent_clause_candidates.py", book],
        [sys.executable, "scripts/stage4/validate_independent_clause_candidates.py", book],
        [sys.executable, "scripts/stage4/audit_clause_survivability.py", book],
        [sys.executable, "scripts/stage4/detect_subordinator_dependency_candidates.py", book],
        [sys.executable, "scripts/stage5/export_stage4_for_stage5.py",
            f"audits/stage4/clause-survivability-audit/{book}.jsonl",
            f"datasets/stage5/{book}/{book}-stage5-input.jsonl",
            "--subordinator-candidates",
            f"audits/stage4/subordinator-dependency-candidates/{book}.jsonl"],
    ]

    for cmd in steps:
        code = run(cmd, root)
        if code != 0:
            return code

    stage5_dir = root / "datasets" / "stage5" / book
    stage5_dir.mkdir(parents=True, exist_ok=True)

    with (stage5_dir / "connector-structural-states.jsonl").open("w", encoding="utf-8") as f:
        code = subprocess.run([
            sys.executable, "scripts/stage5/classify_connector_structural_states.py",
            f"audits/stage4/subordinator-dependency-candidates/{book}.jsonl",
            "--jsonl"
        ], cwd=str(root), stdout=f).returncode
    if code != 0:
        return code

    with (stage5_dir / "connector-policy-states.jsonl").open("w", encoding="utf-8") as f:
        code = subprocess.run([
            sys.executable, "scripts/stage5/classify_connector_policy_states.py",
            f"datasets/stage5/{book}/connector-structural-states.jsonl"
        ], cwd=str(root), stdout=f).returncode
    if code != 0:
        return code

    steps2 = [
        [sys.executable, "scripts/stage5/extract_trunk_survival_v2.py",
            f"datasets/stage5/{book}/{book}-stage5-input.jsonl",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            "--rules", "data/rules/roots_survival_rules.yaml",
            "--policy", f"datasets/stage5/{book}/connector-policy-states.jsonl"],
    ]

    for cmd in steps2:
        code = run(cmd, root)
        if code != 0:
            return code

    with (stage5_dir / "survival-policy-audit-v2.jsonl").open("w", encoding="utf-8") as f:
        code = subprocess.run([
            sys.executable, "scripts/stage5/audit_survival_against_policy.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            f"datasets/stage5/{book}/connector-policy-states.jsonl",
            "--jsonl"
        ], cwd=str(root), stdout=f).returncode
    if code != 0:
        return code

    steps3 = [
        [sys.executable, "scripts/stage5/enrich_survival_with_anchor_skeleton.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            f"datasets/anchor-skeleton/{book}.jsonl",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl"],
    ]

    for cmd in steps3:
        code = run(cmd, root)
        if code != 0:
            return code

    with (stage5_dir / "inherited-survival-environments.jsonl").open("w", encoding="utf-8") as f:
        code = subprocess.run([
            sys.executable, "scripts/stage5/classify_inherited_survival_environments.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl",
            "--jsonl"
        ], cwd=str(root), stdout=f).returncode
    if code != 0:
        return code

    print(f"STAGE 5 COMPLETE: {book}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
