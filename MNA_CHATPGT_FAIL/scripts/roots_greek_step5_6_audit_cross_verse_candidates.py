#!/usr/bin/env python3

"""
ROOTS Greek Step 5.6
Audit cross-verse ownership candidates.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

STRONG_RELATIONS = {
    "cause/ground",
    "inference",
    "contrast",
    "contrast/exception",
    "result/inference",
}

WEAK_RELATIONS = {
    "coordination",
    "negative coordination",
    "alternative",
    "alternative/comparison",
}

SUBORDINATE_RELATIONS = {
    "purpose/result",
    "purpose",
    "condition",
    "content/cause",
    "comparison/manner",
    "temporal/condition",
    "cause/temporal",
    "temporal",
}


def read_tsv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def classify_candidate(row):
    relation = row.get("CONNECTOR_RELATION", "")
    confidence = row.get("CANDIDATE_CONFIDENCE", "")
    status = row.get("STATUS", "")

    if status == "no-candidate":
        return "no-candidate"

    if relation in STRONG_RELATIONS and confidence == "medium":
        return "strong-discourse-continuation"

    if relation in SUBORDINATE_RELATIONS:
        return "possible-subordinate-continuation"

    if relation in WEAK_RELATIONS:
        return "weak-coordinate-continuation"

    return "general-cross-verse-candidate"


def build_findings(rows):
    findings = []

    for row in rows:
        classification = classify_candidate(row)

        notes = []

        if classification == "strong-discourse-continuation":
            notes.append("connector relation naturally looks backward")
            notes.append("previous verse final clause available")

        elif classification == "possible-subordinate-continuation":
            notes.append("subordinate connector may rely on previous discourse context")

        elif classification == "weak-coordinate-continuation":
            notes.append("coordinating connector continuation is structurally weaker")

        elif classification == "no-candidate":
            notes.append("no previous verse candidate identified")

        else:
            notes.append("cross-verse relationship requires review")

        findings.append({
            "classification": classification,
            "notes": "; ".join(notes),
            **row,
        })

    return findings


def render_counter(title, counter):
    lines = [f"## {title}", ""]

    if not counter:
        lines.append("- none")
        lines.append("")
        return lines

    for key, value in counter.most_common():
        lines.append(f"- {key}: {value}")

    lines.append("")
    return lines


def render_findings(title, rows, limit=40):
    lines = [f"## {title}", ""]

    if not rows:
        lines.append("- none")
        lines.append("")
        return lines

    for row in rows[:limit]:
        ref = f"{row.get('BOOK')} {row.get('CH')}:{row.get('VS')}"
        connector = row.get("CONNECTOR_GREEK", "")
        relation = row.get("CONNECTOR_RELATION", "")
        target = row.get("CURRENT_TARGET_CLAUSE", "")
        candidate_ref = row.get("CANDIDATE_SOURCE_REF", "")
        candidate_clause = row.get("CANDIDATE_SOURCE_CLAUSE", "")
        confidence = row.get("CANDIDATE_CONFIDENCE", "")
        notes = row.get("notes", "")

        lines.append(
            f"- {ref} | {connector} | {relation} | {candidate_ref} {candidate_clause} → {target} | confidence: {confidence}"
        )
        lines.append(f"  - {notes}")

    if len(rows) > limit:
        lines.append(f"- ... {len(rows) - limit} more")

    lines.append("")
    return lines


def render_report(book, findings):
    lines = []

    classification_counts = Counter(f["classification"] for f in findings)
    relation_counts = Counter(f["CONNECTOR_RELATION"] for f in findings)
    confidence_counts = Counter(f["CANDIDATE_CONFIDENCE"] for f in findings)

    lines.append(f"# ROOTS-GREEK Cross-Verse Audit: {book}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- candidate rows: {len(findings)}")
    lines.append(f"- strong discourse continuations: {classification_counts.get('strong-discourse-continuation', 0)}")
    lines.append(f"- possible subordinate continuations: {classification_counts.get('possible-subordinate-continuation', 0)}")
    lines.append(f"- weak coordinate continuations: {classification_counts.get('weak-coordinate-continuation', 0)}")
    lines.append(f"- no candidate rows: {classification_counts.get('no-candidate', 0)}")
    lines.append("")

    lines.append("## Certainty Boundary")
    lines.append("")
    lines.append("- Confirmed: connector existence and current target clause.")
    lines.append("- Suggested: previous verse final clause as possible source.")
    lines.append("- Not confirmed: discourse continuity, hierarchy, paragraph boundaries, PASO 6-8 structure.")
    lines.append("")

    lines.extend(render_counter("Classification Counts", classification_counts))
    lines.extend(render_counter("Connector Relation Counts", relation_counts))
    lines.extend(render_counter("Candidate Confidence Counts", confidence_counts))

    strong = [f for f in findings if f["classification"] == "strong-discourse-continuation"]
    subordinate = [f for f in findings if f["classification"] == "possible-subordinate-continuation"]
    weak = [f for f in findings if f["classification"] == "weak-coordinate-continuation"]
    none = [f for f in findings if f["classification"] == "no-candidate"]

    lines.extend(render_findings("Strong Discourse Continuation Candidates", strong))
    lines.extend(render_findings("Possible Subordinate Continuation Candidates", subordinate))
    lines.extend(render_findings("Weak Coordinate Continuation Candidates", weak))
    lines.extend(render_findings("Rows Without Previous-Verse Candidates", none))

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 5.6 cross-verse candidate auditor")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/reports")
    args = parser.parse_args()

    in_path = Path(args.dataset_dir) / f"{args.book}-cross-verse-candidates.tsv"
    out_path = Path(args.out_dir) / f"{args.book}-cross-verse-audit.md"

    rows = read_tsv(in_path)
    findings = build_findings(rows)
    report = render_report(args.book, findings)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    counts = Counter(f["classification"] for f in findings)

    print(f"Wrote {out_path}")
    print({
        "rows": len(findings),
        "strong_discourse_continuation": counts.get("strong-discourse-continuation", 0),
        "possible_subordinate_continuation": counts.get("possible-subordinate-continuation", 0),
        "weak_coordinate_continuation": counts.get("weak-coordinate-continuation", 0),
        "no_candidate": counts.get("no-candidate", 0),
    })


if __name__ == "__main__":
    main()
