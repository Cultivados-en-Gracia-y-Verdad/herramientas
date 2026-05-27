#!/usr/bin/env python3

"""
ROOTS Greek Step 3.6
Audit Greek clause spans produced by Step 3.5.

INPUT
-----
MNA/roots-greek/dataset/{book}-clause-spans.tsv

OUTPUT
------
MNA/roots-greek/reports/{book}-clause-spans-audit.md

This audit does not modify data.
It reports structural risks before hierarchy / PASO 6-8 rendering.

Checks include:
- duplicate clause IDs
- invalid span ranges
- non-contiguous token indexes
- finite anchor outside span
- finite anchor missing from span text
- spans with multiple finite markings
- suspiciously short spans
- suspiciously long spans
- likely orphan connectors at span edges
- empty span text
"""

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

EDGE_CONNECTORS = {
    "δέ", "δὲ", "καί", "καὶ", "τε", "ἀλλά", "ἀλλὰ", "ἀλλʼ", "γάρ", "γὰρ", "οὖν", "ἄρα",
    "ὥστε", "διό", "διὸ", "διόπερ", "ἵνα", "ὅπως", "ὅτι", "ἐάν", "ἐὰν", "εἰ", "εἴ", "εἴπερ",
    "ἐπεί", "ἐπεὶ", "ἐπειδή", "ἐπειδὴ", "ὅταν", "ἕως", "καθώς", "καθὼς", "ὡς", "ὥσπερ",
    "ἤ", "ἢ", "εἴτε", "μή", "μὴ", "οὐ", "οὐκ", "οὐχ", "οὔτε", "μηδέ", "μηδὲ", "οὐδέ", "οὐδὲ",
}

FINITE_MARK_RE = re.compile(r"==[^=]+==")


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def row_ref(row: Dict[str, str]) -> str:
    return f"{row.get('BOOK')} {row.get('CH')}:{row.get('VS')} {row.get('CLAUSE_ID')}"


def parse_int(value: str, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def parse_gidx_list(value: str) -> List[int]:
    out: List[int] = []
    for part in str(value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            pass
    return out


def clean_token(token: str) -> str:
    return str(token or "").strip().strip(".,;:·—⸁⸃[]();?·")


def span_tokens(row: Dict[str, str]) -> List[str]:
    text = row.get("SPAN_TEXT", "")
    cleaned = text.replace("==", "")
    return [tok for tok in cleaned.split() if tok]


def first_token(row: Dict[str, str]) -> str:
    toks = span_tokens(row)
    return clean_token(toks[0]) if toks else ""


def last_token(row: Dict[str, str]) -> str:
    toks = span_tokens(row)
    return clean_token(toks[-1]) if toks else ""


def finite_mark_count(row: Dict[str, str]) -> int:
    return len(FINITE_MARK_RE.findall(row.get("SPAN_TEXT", "")))


def issue(level: str, code: str, row: Dict[str, str], message: str) -> Dict[str, str]:
    return {
        "level": level,
        "code": code,
        "ref": row_ref(row),
        "message": message,
        "span": row.get("SPAN_TEXT", ""),
    }


def audit_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []

    seen_clause_keys = Counter(
        (row.get("BOOK"), row.get("CH"), row.get("VS"), row.get("CLAUSE_ID"))
        for row in rows
    )

    for row in rows:
        key = (row.get("BOOK"), row.get("CH"), row.get("VS"), row.get("CLAUSE_ID"))

        if seen_clause_keys[key] > 1:
            issues.append(issue("FAIL", "DUPLICATE_CLAUSE_ID", row, "duplicate clause ID within verse"))

        start = parse_int(row.get("SPAN_START"))
        end = parse_int(row.get("SPAN_END"))
        finite_idx = parse_int(row.get("FINITE_G_IDX"))
        gidxs = parse_gidx_list(row.get("SPAN_GIDX", ""))
        text = row.get("SPAN_TEXT", "")

        if not text.strip():
            issues.append(issue("FAIL", "EMPTY_SPAN_TEXT", row, "span text is empty"))

        if start < 0 or end < 0:
            issues.append(issue("FAIL", "INVALID_SPAN_INDEX", row, "span start/end could not be parsed"))
        elif start > end:
            issues.append(issue("FAIL", "REVERSED_SPAN", row, f"span start {start} is after span end {end}"))

        if not gidxs:
            issues.append(issue("FAIL", "EMPTY_SPAN_GIDX", row, "SPAN_GIDX is empty or unparsable"))
        else:
            if start >= 0 and gidxs[0] != start:
                issues.append(issue("WARN", "SPAN_START_MISMATCH", row, f"SPAN_START={start:02d} but first SPAN_GIDX={gidxs[0]:02d}"))
            if end >= 0 and gidxs[-1] != end:
                issues.append(issue("WARN", "SPAN_END_MISMATCH", row, f"SPAN_END={end:02d} but last SPAN_GIDX={gidxs[-1]:02d}"))

            expected = list(range(gidxs[0], gidxs[-1] + 1))
            if gidxs != expected:
                issues.append(issue("WARN", "NON_CONTIGUOUS_GIDX", row, "SPAN_GIDX is not a contiguous token sequence"))

            if finite_idx not in gidxs:
                issues.append(issue("FAIL", "FINITE_OUTSIDE_SPAN", row, f"finite anchor {finite_idx:02d} is not inside SPAN_GIDX"))

        marks = finite_mark_count(row)
        if marks == 0:
            issues.append(issue("FAIL", "NO_FINITE_MARK", row, "span has no ==finite== marking"))
        elif marks > 1:
            issues.append(issue("WARN", "MULTIPLE_FINITE_MARKS", row, f"span has {marks} finite markings"))

        token_count = len(span_tokens(row))
        if token_count <= 1:
            issues.append(issue("WARN", "VERY_SHORT_SPAN", row, f"span has only {token_count} token(s)"))
        elif token_count >= 30:
            issues.append(issue("WARN", "VERY_LONG_SPAN", row, f"span has {token_count} tokens"))

        first = first_token(row)
        last = last_token(row)

        if last in EDGE_CONNECTORS:
            issues.append(issue("WARN", "TRAILING_CONNECTOR", row, f"span ends with connector-like token: {last}"))

        # A leading connector is often normal, especially for subordinate clauses, so INFO only.
        if first in EDGE_CONNECTORS:
            issues.append(issue("INFO", "LEADING_CONNECTOR", row, f"span begins with connector-like token: {first}"))

    return issues


def group_by_level(issues: List[Dict[str, str]]) -> Counter:
    return Counter(i["level"] for i in issues)


def group_by_code(issues: List[Dict[str, str]]) -> Counter:
    return Counter(i["code"] for i in issues)


def render_issue_list(title: str, issues: List[Dict[str, str]], limit: int = 50) -> List[str]:
    lines = [f"## {title}", ""]
    if not issues:
        lines.append("- none")
        lines.append("")
        return lines

    for item in issues[:limit]:
        lines.append(f"- {item['level']} | {item['code']} | {item['ref']} | {item['message']}")
        lines.append(f"  - `{item['span']}`")
    if len(issues) > limit:
        lines.append(f"- ... {len(issues) - limit} more")
    lines.append("")
    return lines


def render_report(book: str, rows: List[Dict[str, str]], issues: List[Dict[str, str]]) -> str:
    level_counts = group_by_level(issues)
    code_counts = group_by_code(issues)

    lines: List[str] = []
    lines.append(f"# ROOTS-GREEK Clause Span Audit: {book}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- clause spans: {len(rows)}")
    lines.append(f"- issues: {len(issues)}")
    lines.append(f"- FAIL: {level_counts.get('FAIL', 0)}")
    lines.append(f"- WARN: {level_counts.get('WARN', 0)}")
    lines.append(f"- INFO: {level_counts.get('INFO', 0)}")
    lines.append("")

    lines.append("## Issue Counts by Code")
    lines.append("")
    if not code_counts:
        lines.append("- none")
    else:
        for code, count in code_counts.most_common():
            lines.append(f"- {code}: {count}")
    lines.append("")

    lines.append("## Certainty Boundary")
    lines.append("")
    lines.append("- Confirmed: finite anchor exists inside each span when no FAIL is present.")
    lines.append("- Suggested: span boundaries and carried particles.")
    lines.append("- Not confirmed: hierarchy, indentation, connector ownership, PASO 6-8 final structure.")
    lines.append("")

    fails = [i for i in issues if i["level"] == "FAIL"]
    warns = [i for i in issues if i["level"] == "WARN"]
    infos = [i for i in issues if i["level"] == "INFO"]

    lines.extend(render_issue_list("FAIL Issues", fails))
    lines.extend(render_issue_list("WARN Issues", warns))
    lines.extend(render_issue_list("INFO Issues", infos, limit=25))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="ROOTS Greek Step 3.6: audit clause spans.")
    parser.add_argument("book", help="Book name, e.g. 1corintios")
    parser.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    parser.add_argument("--out-dir", default="MNA/roots-greek/reports")
    args = parser.parse_args()

    in_path = Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv"
    out_path = Path(args.out_dir) / f"{args.book}-clause-spans-audit.md"

    rows = read_tsv(in_path)
    issues = audit_rows(rows)
    report = render_report(args.book, rows, issues)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    level_counts = group_by_level(issues)
    print(f"Wrote {out_path}")
    print({
        "clause_spans": len(rows),
        "issues": len(issues),
        "FAIL": level_counts.get("FAIL", 0),
        "WARN": level_counts.get("WARN", 0),
        "INFO": level_counts.get("INFO", 0),
    })


if __name__ == "__main__":
    main()
