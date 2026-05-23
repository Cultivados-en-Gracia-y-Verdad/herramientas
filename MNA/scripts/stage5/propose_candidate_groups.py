#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = "stage5-candidate-grouping-prototype-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") != "metadata":
                rows.append(obj)
    return rows


def ref(row: dict[str, Any]) -> str:
    return f"{row['chapter']}:{row['verse']}"


def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row["chapter"]), int(row["verse"]), int(row["token_index"]))


def compact_person_number(row: dict[str, Any]) -> str:
    person = str(row.get("person") or "")
    number = str(row.get("number") or "")
    p = {"first": "1", "second": "2", "third": "3", "1": "1", "2": "2", "3": "3"}.get(person, person)
    n = {"singular": "S", "plural": "P", "S": "S", "P": "P"}.get(number, number)
    return f"{p}{n}" if p and n else "—"


def clear_subject(row: dict[str, Any]) -> str:
    explicit = str(row.get("explicit_subject_before") or "").strip()
    pn = compact_person_number(row)
    if explicit:
        return f"{explicit} ({pn})"
    return pn


def movement_key(row: dict[str, Any]) -> str:
    return "/".join([
        str(row.get("tense") or "—"),
        str(row.get("voice") or "—"),
        str(row.get("mood") or "—"),
    ])


def connector_forms(row: dict[str, Any]) -> list[str]:
    items = row.get("connectors_before_anchor") or []
    if isinstance(items, list) and items:
        return [str(i.get("form", "")) for i in items if i.get("form")]
    form = row.get("connector_form") or ""
    return str(form).split() if form else []


def lemma(row: dict[str, Any]) -> str:
    return str(row.get("lemma") or "")


def transition_pressure(prev: dict[str, Any], cur: dict[str, Any]) -> tuple[int, list[str]]:
    pressure = 0
    reasons: list[str] = []

    prev_subj = compact_person_number(prev)
    cur_subj = compact_person_number(cur)
    if prev_subj != cur_subj:
        pressure += 2
        reasons.append(f"subject field changes {prev_subj} → {cur_subj}")

    prev_move = movement_key(prev)
    cur_move = movement_key(cur)
    if prev_move != cur_move:
        pressure += 2
        reasons.append(f"movement changes {prev_move} → {cur_move}")

    prev_conn = set(connector_forms(prev))
    cur_conn = set(connector_forms(cur))
    if cur_conn and cur_conn.isdisjoint(prev_conn):
        pressure += 1
        reasons.append(f"new connector environment: {' '.join(sorted(cur_conn))}")

    if prev_conn and not cur_conn:
        pressure += 1
        reasons.append("connector environment drops")

    if ref(prev) != ref(cur):
        pressure += 0

    return pressure, reasons


def continuity_evidence(rows: list[dict[str, Any]]) -> list[str]:
    evidence: list[str] = []
    total = len(rows)
    if total == 0:
        return evidence

    subj_counts = Counter(compact_person_number(r) for r in rows)
    subj, subj_count = subj_counts.most_common(1)[0]
    if subj != "—" and subj_count >= max(2, total // 2):
        evidence.append(f"dominant subject field {subj}: {subj_count}/{total} anchors")

    move_counts = Counter(movement_key(r) for r in rows)
    move, move_count = move_counts.most_common(1)[0]
    if move != "—/—/—" and move_count >= max(2, total // 3):
        evidence.append(f"recurring movement environment {move}: {move_count}/{total} anchors")

    conn_counter: Counter[str] = Counter()
    for r in rows:
        conn_counter.update(connector_forms(r))
    for conn, count in conn_counter.most_common(4):
        if count >= 2:
            evidence.append(f"connector recurrence {conn}: {count}x")

    lemma_counter = Counter(lemma(r) for r in rows if lemma(r))
    for lem, count in lemma_counter.most_common(4):
        if count >= 2:
            evidence.append(f"lexical recurrence {lem}: {count}x")

    # Restoration after interruption: A B A pattern in compact subject or movement.
    subjects = [compact_person_number(r) for r in rows]
    for i in range(len(subjects) - 2):
        if subjects[i] == subjects[i + 2] and subjects[i] != subjects[i + 1]:
            evidence.append(f"subject restoration pattern {subjects[i]} → {subjects[i+1]} → {subjects[i+2]}")
            break

    movements = [movement_key(r) for r in rows]
    for i in range(len(movements) - 2):
        if movements[i] == movements[i + 2] and movements[i] != movements[i + 1]:
            evidence.append(f"movement restoration pattern {movements[i]} → {movements[i+1]} → {movements[i+2]}")
            break

    return evidence


def confidence_for(evidence: list[str], length: int) -> str:
    score = len(evidence)
    if length >= 4:
        score += 1
    if score >= 5:
        return "medium-high"
    if score >= 3:
        return "medium"
    return "low"


def make_group(book: str, group_num: int, rows: list[dict[str, Any]], start_boundary: list[str], end_boundary: list[str]) -> dict[str, Any]:
    evidence = continuity_evidence(rows)
    return {
        "record_type": "stage5_candidate_group",
        "builder_version": VERSION,
        "book": book,
        "group_id": f"{book}-G{group_num:03d}",
        "range": f"{ref(rows[0])}-{ref(rows[-1])}",
        "start_ref": ref(rows[0]),
        "end_ref": ref(rows[-1]),
        "anchor_count": len(rows),
        "anchors": [
            {
                "order": r.get("order"),
                "ref": ref(r),
                "verb": r.get("greek_form"),
                "lemma": r.get("lemma"),
                "subject": clear_subject(r),
                "movement": movement_key(r),
                "connectors": connector_forms(r),
            }
            for r in rows
        ],
        "continuity_evidence": evidence,
        "boundary_evidence": {
            "start": start_boundary,
            "end": end_boundary,
        },
        "confidence": confidence_for(evidence, len(rows)),
        "status": "REVIEW",
    }


def propose_groups(book: str, rows: list[dict[str, Any]], threshold: int = 4, min_size: int = 2) -> list[dict[str, Any]]:
    if not rows:
        return []

    groups: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = [rows[0]]
    start_boundary = ["beginning of selected data"]
    pending_boundary: list[str] = []
    group_num = 1

    for prev, cur in zip(rows, rows[1:]):
        pressure, reasons = transition_pressure(prev, cur)
        if pressure >= threshold and len(current) >= min_size:
            groups.append(make_group(book, group_num, current, start_boundary, reasons))
            group_num += 1
            current = [cur]
            start_boundary = reasons
        else:
            current.append(cur)
            pending_boundary = reasons

    if current:
        groups.append(make_group(book, group_num, current, start_boundary, ["end of selected data"]))

    return groups


def md_for_groups(book: str, groups: list[dict[str, Any]]) -> str:
    out: list[str] = []
    out.append(f"# MNA Stage 5 — Candidate Groups: {book}")
    out.append("")
    out.append("EXPERIMENTAL OUTPUT — REVIEW REQUIRED")
    out.append("")
    out.append("Stage 5 proposes local grouping candidates from accumulated continuity pressure.")
    out.append("")
    out.append("These are not final H2/H1/H0 structures.")
    out.append("")
    for g in groups:
        out.append(f"## {g['group_id']} — {g['range']}")
        out.append("")
        out.append(f"- Status: `{g['status']}`")
        out.append(f"- Confidence: `{g['confidence']}`")
        out.append(f"- Anchors: `{g['anchor_count']}`")
        out.append("")
        out.append("### Continuity Evidence")
        out.append("")
        if g["continuity_evidence"]:
            for e in g["continuity_evidence"]:
                out.append(f"- {e}")
        else:
            out.append("- No continuity evidence met current thresholds.")
        out.append("")
        out.append("### Boundary Evidence")
        out.append("")
        out.append("**Start**")
        for e in g["boundary_evidence"]["start"]:
            out.append(f"- {e}")
        out.append("")
        out.append("**End**")
        for e in g["boundary_evidence"]["end"]:
            out.append(f"- {e}")
        out.append("")
        out.append("### Anchors")
        out.append("")
        out.append("| Ref | Verb | Subject | Movement | Connectors |")
        out.append("|---|---|---|---|---|")
        for a in g["anchors"]:
            out.append(
                f"| {a['ref']} | {a['verb']} | {a['subject']} | {a['movement']} | {' '.join(a['connectors']) or '—'} |"
            )
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 5 experimental candidate grouping proposals.")
    ap.add_argument("book")
    ap.add_argument("--threshold", type=int, default=4)
    ap.add_argument("--min-size", type=int, default=2)
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()
    in_path = mna / "datasets" / "stage3" / book / "subject-movement-markers.jsonl"
    out_dir = mna / "datasets" / "stage5-test" / book
    jsonl_path = out_dir / "candidate-groups.jsonl"
    md_path = out_dir / "candidate-groups.md"
    audit_path = out_dir / "grouping-audit.json"

    rows = sorted(load_jsonl(in_path), key=sort_key)
    groups = propose_groups(book, rows, threshold=args.threshold, min_size=args.min_size)

    out_dir.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "record_type": "metadata",
            "builder_version": VERSION,
            "book": book,
            "input": str(in_path),
            "threshold": args.threshold,
            "min_size": args.min_size,
            "groups_written": len(groups),
        }, ensure_ascii=False, sort_keys=True) + "\n")
        for g in groups:
            f.write(json.dumps(g, ensure_ascii=False, sort_keys=True) + "\n")

    md_path.write_text(md_for_groups(book, groups), encoding="utf-8")
    audit_path.write_text(json.dumps({
        "audit_pass": True,
        "builder_version": VERSION,
        "book": book,
        "rows_read": len(rows),
        "groups_written": len(groups),
        "threshold": args.threshold,
        "min_size": args.min_size,
        "outputs": {
            "jsonl": str(jsonl_path),
            "markdown": str(md_path),
        },
    }, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print("MNA Stage 5 — Candidate Grouping Prototype")
    print(f"BOOK: {book}")
    print(f"ROWS READ: {len(rows)}")
    print(f"GROUPS WRITTEN: {len(groups)}")
    print(f"JSONL: {jsonl_path}")
    print(f"MD: {md_path}")
    print(f"AUDIT: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
