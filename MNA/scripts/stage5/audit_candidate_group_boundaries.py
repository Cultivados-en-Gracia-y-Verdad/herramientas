#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERSION = "stage5-candidate-boundary-audit-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_candidate_groups(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required Stage 5 candidate groups file not found: {path}")

    metadata: dict[str, Any] = {}
    groups: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") == "metadata":
                metadata = obj
            elif obj.get("record_type") == "stage5_candidate_group":
                groups.append(obj)

    return metadata, groups


def classify_boundary_reason(reason: str) -> str:
    text = reason.lower()

    if "subject field changes" in text:
        return "subject_change"
    if "movement changes" in text:
        return "movement_change"
    if "new connector environment" in text:
        return "new_connector_environment"
    if "connector environment drops" in text:
        return "connector_environment_drops"
    if "beginning of selected data" in text:
        return "beginning"
    if "end of selected data" in text:
        return "end"
    return "other"


def summarize_boundary_reasons(groups: list[dict[str, Any]]) -> dict[str, Any]:
    start_counter: Counter[str] = Counter()
    end_counter: Counter[str] = Counter()
    raw_start: Counter[str] = Counter()
    raw_end: Counter[str] = Counter()

    for group in groups:
        boundary = group.get("boundary_evidence", {})
        for reason in boundary.get("start", []):
            raw_start[reason] += 1
            start_counter[classify_boundary_reason(reason)] += 1
        for reason in boundary.get("end", []):
            raw_end[reason] += 1
            end_counter[classify_boundary_reason(reason)] += 1

    return {
        "start_reason_classes": dict(start_counter.most_common()),
        "end_reason_classes": dict(end_counter.most_common()),
        "top_raw_start_reasons": dict(raw_start.most_common(25)),
        "top_raw_end_reasons": dict(raw_end.most_common(25)),
    }


def summarize_confidence(groups: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(g.get("confidence", "unknown")) for g in groups).most_common())


def summarize_sizes(groups: list[dict[str, Any]]) -> dict[str, Any]:
    sizes = [int(g.get("anchor_count", 0)) for g in groups]
    if not sizes:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "avg": 0,
            "single_anchor_groups": 0,
            "two_anchor_groups": 0,
            "small_groups_1_to_2": 0,
        }

    return {
        "count": len(sizes),
        "min": min(sizes),
        "max": max(sizes),
        "avg": round(sum(sizes) / len(sizes), 2),
        "single_anchor_groups": sum(1 for s in sizes if s == 1),
        "two_anchor_groups": sum(1 for s in sizes if s == 2),
        "small_groups_1_to_2": sum(1 for s in sizes if s <= 2),
        "small_groups_1_to_3": sum(1 for s in sizes if s <= 3),
        "large_groups_10_plus": sum(1 for s in sizes if s >= 10),
    }


def summarize_evidence(groups: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_class_counter: Counter[str] = Counter()
    raw_evidence_counter: Counter[str] = Counter()

    for group in groups:
        for evidence in group.get("continuity_evidence", []):
            raw_evidence_counter[evidence] += 1
            low = evidence.lower()
            if "dominant subject field" in low:
                evidence_class_counter["dominant_subject_field"] += 1
            elif "recurring movement environment" in low:
                evidence_class_counter["recurring_movement_environment"] += 1
            elif "movement restoration pattern" in low:
                evidence_class_counter["movement_restoration_pattern"] += 1
            elif "subject restoration pattern" in low:
                evidence_class_counter["subject_restoration_pattern"] += 1
            elif "connector recurrence" in low:
                evidence_class_counter["connector_recurrence"] += 1
            elif "lexical recurrence" in low:
                evidence_class_counter["lexical_recurrence"] += 1
            else:
                evidence_class_counter["other"] += 1

    return {
        "evidence_classes": dict(evidence_class_counter.most_common()),
        "top_raw_evidence": dict(raw_evidence_counter.most_common(40)),
    }


def parse_start_chapter(group: dict[str, Any]) -> int:
    start_ref = str(group.get("start_ref") or group.get("range", "0:0").split("-", 1)[0])
    return int(start_ref.split(":", 1)[0])


def summarize_by_chapter(groups: list[dict[str, Any]]) -> dict[str, Any]:
    chapter_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        chapter_groups[parse_start_chapter(group)].append(group)

    out: dict[str, Any] = {}
    for ch in sorted(chapter_groups):
        ch_groups = chapter_groups[ch]
        sizes = [int(g.get("anchor_count", 0)) for g in ch_groups]
        out[str(ch)] = {
            "groups": len(ch_groups),
            "anchors": sum(sizes),
            "avg_group_size": round(sum(sizes) / len(sizes), 2) if sizes else 0,
            "small_groups_1_to_2": sum(1 for s in sizes if s <= 2),
            "medium_high_or_higher": sum(1 for g in ch_groups if str(g.get("confidence")) in {"medium-high", "high"}),
        }
    return out


def suspect_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suspects: list[dict[str, Any]] = []
    for group in groups:
        anchor_count = int(group.get("anchor_count", 0))
        confidence = str(group.get("confidence", ""))
        continuity_evidence = group.get("continuity_evidence", [])
        boundary = group.get("boundary_evidence", {})
        start_count = len(boundary.get("start", []))
        end_count = len(boundary.get("end", []))

        reasons: list[str] = []
        if anchor_count <= 2 and confidence == "low":
            reasons.append("low-confidence tiny group")
        if anchor_count <= 2 and not continuity_evidence:
            reasons.append("tiny group with no continuity evidence")
        if start_count >= 3 and end_count >= 3 and anchor_count <= 3:
            reasons.append("high boundary pressure on both sides around tiny group")

        if reasons:
            suspects.append({
                "group_id": group.get("group_id"),
                "range": group.get("range"),
                "anchor_count": anchor_count,
                "confidence": confidence,
                "reasons": reasons,
                "start_boundary": boundary.get("start", []),
                "end_boundary": boundary.get("end", []),
                "continuity_evidence": continuity_evidence,
            })
    return suspects


def markdown_report(book: str, audit: dict[str, Any]) -> str:
    out: list[str] = []
    out.append(f"# MNA Stage 5 Boundary Audit — {book}")
    out.append("")
    out.append("EXPERIMENTAL AUDIT OUTPUT")
    out.append("")
    out.append("This audit does not change grouping. It shows why Stage 5 split the text.")
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append(f"- Rows read: `{audit['rows_read']}`")
    out.append(f"- Groups audited: `{audit['groups_audited']}`")
    out.append(f"- Average group size: `{audit['size_summary']['avg']}` anchors")
    out.append(f"- Small groups, 1–2 anchors: `{audit['size_summary']['small_groups_1_to_2']}`")
    out.append(f"- Large groups, 10+ anchors: `{audit['size_summary']['large_groups_10_plus']}`")
    out.append("")

    out.append("## Confidence Distribution")
    out.append("")
    for key, count in audit["confidence_summary"].items():
        out.append(f"- `{key}`: {count}")
    out.append("")

    out.append("## Boundary Reason Classes")
    out.append("")
    out.append("### Start Boundary Reasons")
    out.append("")
    for key, count in audit["boundary_summary"]["start_reason_classes"].items():
        out.append(f"- `{key}`: {count}")
    out.append("")
    out.append("### End Boundary Reasons")
    out.append("")
    for key, count in audit["boundary_summary"]["end_reason_classes"].items():
        out.append(f"- `{key}`: {count}")
    out.append("")

    out.append("## Continuity Evidence Classes")
    out.append("")
    for key, count in audit["evidence_summary"]["evidence_classes"].items():
        out.append(f"- `{key}`: {count}")
    out.append("")

    out.append("## Chapter Summary")
    out.append("")
    out.append("| Chapter | Groups | Anchors | Avg Size | Small 1–2 | Medium-High+ |")
    out.append("|---:|---:|---:|---:|---:|---:|")
    for ch, data in audit["chapter_summary"].items():
        out.append(
            f"| {ch} | {data['groups']} | {data['anchors']} | {data['avg_group_size']} | {data['small_groups_1_to_2']} | {data['medium_high_or_higher']} |"
        )
    out.append("")

    out.append("## Suspect Tiny Groups")
    out.append("")
    suspects = audit["suspect_groups"][:100]
    if not suspects:
        out.append("No suspect tiny groups detected by current audit rules.")
    else:
        for s in suspects:
            out.append(f"### {s['group_id']} — {s['range']}")
            out.append("")
            out.append(f"- Anchors: `{s['anchor_count']}`")
            out.append(f"- Confidence: `{s['confidence']}`")
            out.append("- Reasons:")
            for reason in s["reasons"]:
                out.append(f"  - {reason}")
            out.append("")
    out.append("")

    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit experimental Stage 5 candidate group boundaries.")
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()
    in_path = mna / "datasets" / "stage5-test" / book / "candidate-groups.jsonl"
    out_dir = mna / "audits" / "stage5-test" / book
    audit_path = out_dir / "candidate-boundary-audit.json"
    md_path = out_dir / "candidate-boundary-audit.md"

    metadata, groups = load_candidate_groups(in_path)

    rows_read = int(metadata.get("groups_written", 0))
    # Preserve original Stage 5 metadata if available; groups_written is not rows_read,
    # so keep both names explicit below.
    audit = {
        "audit_pass": True,
        "audit_version": VERSION,
        "book": book,
        "source": str(in_path),
        "stage5_metadata": metadata,
        "rows_read": metadata.get("rows_read", metadata.get("input_rows", "unknown")),
        "groups_audited": len(groups),
        "size_summary": summarize_sizes(groups),
        "confidence_summary": summarize_confidence(groups),
        "boundary_summary": summarize_boundary_reasons(groups),
        "evidence_summary": summarize_evidence(groups),
        "chapter_summary": summarize_by_chapter(groups),
        "suspect_groups": suspect_groups(groups),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(markdown_report(book, audit), encoding="utf-8")

    print("MNA Stage 5 — Candidate Boundary Audit")
    print(f"BOOK: {book}")
    print(f"GROUPS AUDITED: {len(groups)}")
    print(f"AUDIT: {audit_path}")
    print(f"MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
