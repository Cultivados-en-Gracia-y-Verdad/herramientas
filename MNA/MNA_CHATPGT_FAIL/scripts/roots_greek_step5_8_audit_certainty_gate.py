#!/usr/bin/env python3

"""
ROOTS Greek Step 5.8
Audit the certainty gate produced by Step 5.7.

INPUT
-----
MNA/roots-greek/dataset/{book}-certainty-gate.tsv

OUTPUT
------
MNA/roots-greek/reports/{book}-certainty-gate-audit.md

CORE PRINCIPLE
--------------
This audit verifies that the pipeline is preserving the certainty boundary.

It does NOT:
- promote suggestions
- confirm relationships
- create hierarchy
- render PASO output

It reports:
- classification counts
- layer counts
- downstream-use permissions
- PASO-rendering blockers
- any suspicious rows marked FACT but blocking rendering
- any non-FACT rows allowed too broadly downstream

Greek-only.
No Spanish.
No interpretation.
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

EXPECTED_CLASSIFICATIONS = {"FACT", "SUGGESTION", "REVIEW", "BLOCKED"}


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def row_ref(row: Dict[str, str]) -> str:
    return f"{row.get('BOOK')} {row.get('CH')}:{row.get('VS')} | {row.get('LAYER')} | {row.get('ITEM_ID')} | {row.get('ITEM_TYPE')}"


def audit_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []

    for row in rows:
        classification = row.get("CLASSIFICATION", "")
        allowed = row.get("ALLOWED_DOWNSTREAM_USE", "")
        blocks = row.get("BLOCKS_PASO_RENDERING", "")
        layer = row.get("LAYER", "")

        if classification not in EXPECTED_CLASSIFICATIONS:
            issues.append({
                "level": "FAIL",
                "code": "UNKNOWN_CLASSIFICATION",
                "ref": row_ref(row),
                "message": f"Unknown classification: {classification}",
            })

        if classification == "FACT" and blocks == "yes":
            issues.append({
                "level": "WARN",
                "code": "FACT_BLOCKS_RENDERING",
                "ref": row_ref(row),
                "message": "FACT row blocks PASO rendering; verify reason",
            })

        if classification in {"SUGGESTION", "REVIEW", "BLOCKED"} and blocks != "yes":
            issues.append({
                "level": "WARN",
                "code": "NONFACT_DOES_NOT_BLOCK_RENDERING",
                "ref": row_ref(row),
                "message": "Non-FACT row does not block PASO rendering",
            })

        if classification == "BLOCKED" and allowed not in {"none", "audit-only; cannot-render-final-structure"}:
            issues.append({
                "level": "WARN",
                "code": "BLOCKED_HAS_DOWNSTREAM_USE",
                "ref": row_ref(row),
                "message": f"BLOCKED row still allows downstream use: {allowed}",
            })

        if classification in {"SUGGESTION", "REVIEW"} and "render" in allowed and "provisional" not in allowed:
            issues.append({
                "level": "WARN",
                "code": "NONFACT_RENDER_ALLOWED",
                "ref": row_ref(row),
                "message": f"Non-FACT row appears render-allowed without provisional language: {allowed}",
            })

        if layer == "step5-structure-tree" and classification != "BLOCKED":
            issues.append({
                "level": "FAIL",
                "code": "TREE_NOT_BLOCKED",
                "ref": row_ref(row),
                "message": "Structure tree must remain BLOCKED until explicit promotion rules exist",
            })

        if layer == "step5.5-cross-verse-candidates" and classification not in {"REVIEW", "BLOCKED"}:
            issues.append({
                "level": "FAIL",
                "code": "CROSS_VERSE_NOT_REVIEW",
                "ref": row_ref(row),
                "message": "Cross-verse candidates must remain REVIEW or BLOCKED",
            })

    return issues


def render_counter(title: str, counter: Counter) -> List[str]:
    lines = [f"## {title}", ""]
    if not counter:
        lines.append("- none")
        lines.append("")
        return lines

    for key, value in counter.most_common():
        lines.append(f"- {key}: {value}")

    lines.append("")
    return lines


def render_issues(title: str, issues: List[Dict[str, str]], limit: int = 50) -> List[str]:
    lines = [f"## {title}", ""]
    if not issues:
        lines.append("- none")
        lines.append("")
        return lines

    for issue in issues[:limit]:
        lines.append(f"- {issue['level']} | {issue['code']} | {issue['ref']}")
        lines.append(f"  - {issue['message']}")

    if len(issues) > limit:
        lines.append(f"- ... {len(issues) - limit} more")

    lines.append("")
    return lines


def render_report(book: str, rows: List[Dict[str, str]], issues: List[Dict[str, str]]) -> str:
    lines: List[str] = []

    classification_counts = Counter(row.get("CLASSIFICATION", "") for row in rows)
    layer_counts = Counter(row.get("LAYER", "") for row in rows)
    blocks_counts = Counter(row.get("BLOCKS_PASO_RENDERING", "") for row in rows)
    allowed_counts = Counter(row.get("ALLOWED_DOWNSTREAM_USE", "") for row in rows)
    issue_counts = Counter(issue["level"] for issue in issues)
    issue_code_counts = Counter(issue["code"] for issue in issues)

    lines.append(f"# ROOTS-GREEK Certainty Gate Audit: {book}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- certainty rows: {len(rows)}")
    lines.append(f"- FACT: {classification_counts.get('FACT', 0)}")
    lines.append(f"- SUGGESTION: {classification_counts.get('SUGGESTION', 0)}")
    lines.append(f"- REVIEW: {classification_counts.get('REVIEW', 0)}")
    lines.append(f"- BLOCKED: {classification_counts.get('BLOCKED', 0)}")
    lines.append(f"- FAIL issues: {issue_counts.get('FAIL', 0)}")
    lines.append(f"- WARN issues: {issue_counts.get('WARN', 0)}")
    lines.append("")

    lines.append("## Certainty Boundary")
    lines.append("")
    lines.append("- FACT rows may feed lexical displays and finite-anchor detection.")
    lines.append("- SUGGESTION rows may be displayed only as provisional evidence.")
    lines.append("- REVIEW rows require audit before any structural use.")
    lines.append("- BLOCKED rows cannot render final PASO structure.")
    lines.append("")

    lines.extend(render_counter("Classification Counts", classification_counts))
    lines.extend(render_counter("Layer Counts", layer_counts))
    lines.extend(render_counter("Blocks PASO Rendering Counts", blocks_counts))
    lines.extend(render_counter("Allowed Downstream Use Counts", allowed_counts))
    lines.extend(render_counter("Issue Counts by Code", issue_code_counts))

    fails = [issue for issue in issues if issue["level"] == "FAIL"]
    warns = [issue for issue in issues if issue["level"] == "WARN"]

    lines.extend(render_issues("FAIL Issues", fails))
    lines.extend(render_issues("WARN Issues", warns))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5.8 certainty gate auditor")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/reports")
    args = parser.parse_args()

    in_path = Path(args.dataset_dir) / f"{args.book}-certainty-gate.tsv"
    out_path = Path(args.out_dir) / f"{args.book}-certainty-gate-audit.md"

    rows = read_tsv(in_path)
    issues = audit_rows(rows)
    report = render_report(args.book, rows, issues)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    classification_counts = Counter(row.get("CLASSIFICATION", "") for row in rows)
    issue_counts = Counter(issue["level"] for issue in issues)

    print(f"Wrote {out_path}")
    print({
        "rows": len(rows),
        "FACT": classification_counts.get("FACT", 0),
        "SUGGESTION": classification_counts.get("SUGGESTION", 0),
        "REVIEW": classification_counts.get("REVIEW", 0),
        "BLOCKED": classification_counts.get("BLOCKED", 0),
        "FAIL": issue_counts.get("FAIL", 0),
        "WARN": issue_counts.get("WARN", 0),
    })


if __name__ == "__main__":
    main()
