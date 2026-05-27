#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd, root):
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=str(root)).returncode


def run_to_file(cmd, root, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("$ " + " ".join(cmd) + f" > {output_path}")
    with output_path.open("w", encoding="utf-8") as f:
        return subprocess.run(cmd, cwd=str(root), stdout=f).returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("book")
    args = p.parse_args()

    root = Path(__file__).resolve().parents[2]
    book = args.book.strip().lower()
    stage5_dir = root / "datasets" / "stage5" / book
    stage5_audit_dir = root / "audits" / "stage5" / book
    stage5_dir.mkdir(parents=True, exist_ok=True)
    stage5_audit_dir.mkdir(parents=True, exist_ok=True)

    steps = [
        [sys.executable, "scripts/stage4/build_predicate_completeness.py", book],
        [sys.executable, "scripts/stage4/validate_predicate_completeness.py", book],
        [sys.executable, "scripts/stage4/build_independent_clause_candidates.py", book],
        [sys.executable, "scripts/stage4/validate_independent_clause_candidates.py", book],
        [sys.executable, "scripts/stage4/audit_clause_survivability.py", book],
        [sys.executable, "scripts/stage4/detect_subordinator_dependency_candidates.py", book],
        [
            sys.executable,
            "scripts/stage5/export_stage4_for_stage5.py",
            f"audits/stage4/clause-survivability-audit/{book}.jsonl",
            f"datasets/stage5/{book}/{book}-stage5-input.jsonl",
            "--subordinator-candidates",
            f"audits/stage4/subordinator-dependency-candidates/{book}.jsonl",
        ],
    ]

    for cmd in steps:
        code = run(cmd, root)
        if code != 0:
            return code

    redirected_steps = [
        (
            [
                sys.executable,
                "scripts/stage5/classify_connector_structural_states.py",
                f"audits/stage4/subordinator-dependency-candidates/{book}.jsonl",
                "--jsonl",
            ],
            stage5_dir / "connector-structural-states.jsonl",
        ),
        (
            [
                sys.executable,
                "scripts/stage5/classify_connector_policy_states.py",
                f"datasets/stage5/{book}/connector-structural-states.jsonl",
            ],
            stage5_dir / "connector-policy-states.jsonl",
        ),
    ]

    for cmd, output_path in redirected_steps:
        code = run_to_file(cmd, root, output_path)
        if code != 0:
            return code

    steps2 = [
        [
            sys.executable,
            "scripts/stage5/extract_trunk_survival_v2.py",
            f"datasets/stage5/{book}/{book}-stage5-input.jsonl",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            "--rules",
            "data/rules/roots_survival_rules.yaml",
            "--policy",
            f"datasets/stage5/{book}/connector-policy-states.jsonl",
        ],
    ]

    for cmd in steps2:
        code = run(cmd, root)
        if code != 0:
            return code

    code = run_to_file(
        [
            sys.executable,
            "scripts/stage5/audit_survival_against_policy.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            f"datasets/stage5/{book}/connector-policy-states.jsonl",
            "--jsonl",
        ],
        root,
        stage5_dir / "survival-policy-audit-v2.jsonl",
    )
    if code != 0:
        return code

    steps3 = [
        [
            sys.executable,
            "scripts/stage5/enrich_survival_with_anchor_skeleton.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2.jsonl",
            f"datasets/anchor-skeleton/{book}.jsonl",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl",
        ],
    ]

    for cmd in steps3:
        code = run(cmd, root)
        if code != 0:
            return code

    final_redirected_steps = [
        (
            [
                sys.executable,
                "scripts/stage5/classify_inherited_survival_environments.py",
                f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl",
                "--jsonl",
            ],
            stage5_dir / "inherited-survival-environments.jsonl",
        ),
    ]

    for cmd, output_path in final_redirected_steps:
        code = run_to_file(cmd, root, output_path)
        if code != 0:
            return code

    steps4 = [
        [
            sys.executable,
            "scripts/stage5/build_positive_independence_signals.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl",
            f"datasets/stage5/{book}/positive-independence-signals.jsonl",
        ],
        [
            sys.executable,
            "scripts/stage5/build_negative_independence_pressure.py",
            f"datasets/stage5/{book}/{book}-trunk-survival-v2-enriched.jsonl",
            f"datasets/stage5/{book}/negative-independence-pressure.jsonl",
        ],
        [
            sys.executable,
            "scripts/stage5/classify_trunk_candidacy_environments.py",
            f"datasets/stage5/{book}/positive-independence-signals.jsonl",
            f"datasets/stage5/{book}/negative-independence-pressure.jsonl",
            f"datasets/stage5/{book}/trunk-candidacy-environments.jsonl",
        ],
        [
            sys.executable,
            "scripts/stage5/build_trunk_candidacy_assertions.py",
            f"datasets/stage5/{book}/trunk-candidacy-environments.jsonl",
            f"datasets/stage5/{book}/trunk-candidacy-assertions.jsonl",
        ],
        [
            sys.executable,
            "scripts/stage5/audit_trunk_candidacy_assertions.py",
            f"datasets/stage5/{book}/trunk-candidacy-assertions.jsonl",
            f"audits/stage5/{book}/trunk-candidacy-assertion-audit.jsonl",
        ],
        [
            sys.executable,
            "scripts/stage5/export_stage5_baseline_snapshot.py",
            book,
            f"datasets/stage5/{book}/trunk-candidacy-assertions.jsonl",
            f"audits/stage5/{book}/trunk-candidacy-assertion-audit.jsonl",
            f"audits/stage5/{book}/stage5-baseline-snapshot.json",
        ],
        [
            sys.executable,
            "scripts/stage5/audit_dependency_pressure_subclasses.py",
            f"datasets/stage5/{book}/trunk-candidacy-assertions.jsonl",
            f"audits/stage5/{book}/dependency-pressure-subclasses.json",
        ],
        [
            sys.executable,
            "scripts/stage5/audit_connector_mood_pairs.py",
            f"datasets/stage5/{book}/trunk-candidacy-assertions.jsonl",
            f"audits/stage5/{book}/connector-mood-pairs.json",
        ],
    ]

    for cmd in steps4:
        code = run(cmd, root)
        if code != 0:
            return code

    print(f"STAGE 5 COMPLETE: {book}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
