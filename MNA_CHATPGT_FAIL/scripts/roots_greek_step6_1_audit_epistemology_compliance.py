#!/usr/bin/env python3

"""
ROOTS Greek Step 6.1
Audit epistemology compliance for rendered and structural outputs.
"""

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

EXPECTED_CLASSIFICATIONS = {"FACT", "SUGGESTION", "REVIEW", "BLOCKED"}


def read_tsv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_text(path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def add_issue(issues, level, code, location, message):
    issues.append({
        "level": level,
        "code": code,
        "location": location,
        "message": message,
    })


def audit_paso6_output(text, path, issues):
    if not text:
        add_issue(issues, "FAIL", "MISSING_PASO6_OUTPUT", str(path), "PASO 6 output missing.")
        return

    if "[DISCLOSURE]" not in text:
        add_issue(issues, "FAIL", "PASO6_MISSING_DISCLOSURE", str(path), "Disclosure missing.")

    if "[BLOCKED-TOPOLOGY]" not in text:
        add_issue(issues, "FAIL", "PASO6_MISSING_BLOCKED_TOPOLOGY", str(path), "Blocked topology disclosure missing.")

    bare_clause_pattern = re.compile(r"^\s*C\d+\b", re.MULTILINE)
    if bare_clause_pattern.findall(text):
        add_issue(issues, "FAIL", "BARE_CLAUSE_HEADER", str(path), "Bare clause header detected.")


def render_report(book, issues, certainty_rows, paso6_text):
    lines = []

    issue_counts = Counter(issue["level"] for issue in issues)
    certainty_counts = Counter(row.get("CLASSIFICATION", "") for row in certainty_rows)

    lines.append(f"# ROOTS-GREEK Epistemology Compliance Audit: {book}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- FAIL issues: {issue_counts.get('FAIL', 0)}")
    lines.append(f"- WARN issues: {issue_counts.get('WARN', 0)}")
    lines.append(f"- certainty rows: {len(certainty_rows)}")
    lines.append(f"- PASO 6 disclosures: {paso6_text.count('[DISCLOSURE]')}")
    lines.append("")

    lines.append("## Certainty Counts")
    lines.append("")
    for key, value in certainty_counts.most_common():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Issues")
    lines.append("")

    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- {issue['level']} | {issue['code']} | {issue['location']}")
            lines.append(f"  - {issue['message']}")

    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ROOTS Greek epistemology compliance audit")
    parser.add_argument("book")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--output-dir", default="MNA/roots-greek/output")
    parser.add_argument("--reports-dir", default="MNA/roots-greek/reports")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    reports_dir = Path(args.reports_dir)

    certainty_rows = read_tsv(dataset_dir / f"{args.book}-certainty-gate.tsv")
    paso6_text = read_text(output_dir / f"{args.book}-paso6.md")

    issues = []

    for row in certainty_rows:
        classification = row.get("CLASSIFICATION", "")

        if classification not in EXPECTED_CLASSIFICATIONS:
            add_issue(
                issues,
                "FAIL",
                "UNKNOWN_CLASSIFICATION",
                row.get("ITEM_ID", ""),
                f"Unknown classification: {classification}",
            )

    audit_paso6_output(
        paso6_text,
        output_dir / f"{args.book}-paso6.md",
        issues,
    )

    report = render_report(args.book, issues, certainty_rows, paso6_text)

    out_path = reports_dir / f"{args.book}-epistemology-compliance-audit.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    issue_counts = Counter(issue["level"] for issue in issues)

    print(f"Wrote {out_path}")
    print({
        "FAIL": issue_counts.get("FAIL", 0),
        "WARN": issue_counts.get("WARN", 0),
        "issues": len(issues),
    })


if __name__ == "__main__":
    main()