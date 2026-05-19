#!/usr/bin/env python3
"""
MNA Stage 4 — ROOTS Constraint Audit

Purpose:
- Audit reviewed trunk rows against ROOTS governing constraints.
- Detect methodological drift before export.
- Do not modify data.

Connector behavior is rule-governed.
The audit reads authoritative connector behavior from:

    data/rules/roots_dependency_rules.yaml

ROOTS removes subordinate clauses mechanically.
ROOTS does not remove every token containing subordinating vocabulary.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import yaml


INTERPRETIVE_LANGUAGE = [
    "governing force",
    "governing",
    "central idea",
    "central",
    "main point",
    "dominant movement",
    "rhetorical prominence",
    "rhetorically",
    "rhetorical",
    "exhortational force",
    "exhortational content",
    "exhortational target",
    "thematic",
    "discourse",
    "importance",
    "important",
    "prominence",
    "primary force",
]

ELEVATED_CONFIDENCE = {"HIGH", "MEDIUM-HIGH"}
CLAUSE_BOUNDARY_CHARS = "·.;·:—"


class Violation:
    def __init__(self, reference: str, code: str, detail: str, severity: str = "WARN") -> None:
        self.reference = reference
        self.code = code
        self.detail = detail
        self.severity = severity

    def to_json(self) -> dict:
        return {
            "reference": self.reference,
            "code": self.code,
            "severity": self.severity,
            "detail": self.detail,
        }


class ConnectorRule:
    def __init__(self, data: dict) -> None:
        self.connector = data["connector"]
        self.normalized_forms = data.get("normalized_forms", [self.connector])
        self.connector_type = data.get("connector_type")
        self.dependency_type = data.get("dependency_type")
        self.audit = data.get("audit", {})


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> tuple[Optional[dict], list[dict]]:
    metadata = None
    rows: list[dict] = []

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def load_connector_rules(root: Path) -> list[ConnectorRule]:
    rule_path = root / "data" / "rules" / "roots_dependency_rules.yaml"

    if not rule_path.is_file():
        raise FileNotFoundError(f"Dependency rule file not found: {rule_path}")

    with rule_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    connectors = data.get("connectors", [])
    return [ConnectorRule(entry) for entry in connectors]


def token_present(text: str, token: str) -> bool:
    pattern = rf"(^|[\s·,.;·:—]){re.escape(token)}($|[\s·,.;·:—])"
    return re.search(pattern, text) is not None


def connector_at_trunk_start(text: str, token: str) -> bool:
    stripped = text.strip()
    pattern = rf"^{re.escape(token)}($|[\s·,.;·:—])"
    return re.search(pattern, stripped) is not None


def connector_after_clause_boundary(text: str, token: str) -> bool:
    pattern = rf"[{re.escape(CLAUSE_BOUNDARY_CHARS)}]\s*{re.escape(token)}($|[\s·,.;·:—])"
    return re.search(pattern, text) is not None


def find_connector_presence(trunk: str, rules: list[ConnectorRule]) -> list[tuple[ConnectorRule, str]]:
    found: list[tuple[ConnectorRule, str]] = []

    for rule in rules:
        for form in rule.normalized_forms:
            if token_present(trunk, form):
                found.append((rule, form))

    return found


def find_likely_retained_subordinate_clause(trunk: str, rules: list[ConnectorRule]) -> list[tuple[ConnectorRule, str]]:
    found: list[tuple[ConnectorRule, str]] = []

    for rule in rules:
        for form in rule.normalized_forms:
            if connector_at_trunk_start(trunk, form) or connector_after_clause_boundary(trunk, form):
                found.append((rule, form))

    return found


def find_interpretive_terms(notes: str) -> list[str]:
    lower = notes.lower()
    return [term for term in INTERPRETIVE_LANGUAGE if term in lower]


def audit_row(row: dict, rules: list[ConnectorRule]) -> list[Violation]:
    violations: list[Violation] = []

    reference = str(row.get("reference", "UNKNOWN"))
    trunk = str(row.get("trunk_greek") or "")
    notes = str(row.get("review_notes") or row.get("notes") or "")
    confidence = str(row.get("confidence") or "")

    likely_scope = find_likely_retained_subordinate_clause(trunk, rules)
    token_presence = find_connector_presence(trunk, rules)

    likely_forms = {form for _, form in likely_scope}

    unresolved = [
        (rule, form)
        for rule, form in token_presence
        if form not in likely_forms
    ]

    if likely_scope:
        forms = sorted({form for _, form in likely_scope})
        violations.append(
            Violation(
                reference,
                "LIKELY_SUBORDINATE_CLAUSE_RETAINED",
                "Likely subordinate clause retained in trunk: " + ", ".join(forms),
                "FAIL",
            )
        )

    if unresolved:
        forms = sorted({form for _, form in unresolved})
        violations.append(
            Violation(
                reference,
                "SUBORDINATING_CONNECTOR_TOKEN_PRESENT",
                "Subordinating connector token present; clause scope requires review: " + ", ".join(forms),
                "WARN",
            )
        )

    interpretive_terms = find_interpretive_terms(notes)

    if interpretive_terms:
        violations.append(
            Violation(
                reference,
                "INTERPRETIVE_RETENTION_LANGUAGE",
                "Review note contains interpretive-retention language: " + ", ".join(interpretive_terms),
                "FLAG",
            )
        )

    if confidence in ELEVATED_CONFIDENCE and interpretive_terms:
        violations.append(
            Violation(
                reference,
                "CONFIDENCE_EXCEEDS_MECHANICAL_CERTAINTY",
                f"Elevated confidence {confidence} paired with interpretive-retention language.",
                "FLAG",
            )
        )

    if confidence in ELEVATED_CONFIDENCE and likely_scope:
        violations.append(
            Violation(
                reference,
                "CONFIDENCE_WITH_LIKELY_SUBORDINATE_RETENTION",
                f"Elevated confidence {confidence} paired with likely subordinate clause retention.",
                "FAIL",
            )
        )

    if confidence in ELEVATED_CONFIDENCE and unresolved:
        violations.append(
            Violation(
                reference,
                "CONFIDENCE_WITH_UNVERIFIED_SUBORDINATING_TOKEN",
                f"Elevated confidence {confidence} paired with unresolved subordinating connector scope.",
                "WARN",
            )
        )

    return violations


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0))))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Stage 4 reviewed trunk rows against ROOTS constraints.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--fail-on-warn", action="store_true", help="Return nonzero if warnings exist")
    parser.add_argument("--jsonl", action="store_true", help="Write machine-readable audit JSONL")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        rules = load_connector_rules(root)

        book = args.book.strip().lower()
        dataset_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        output_path = root / "exports" / "audits" / f"{book}-stage4-roots-constraint-audit.jsonl"

        _metadata, rows = load_jsonl(dataset_path)
        rows = sort_rows(rows)

        all_violations: list[Violation] = []

        for row in rows:
            all_violations.extend(audit_row(row, rules))

        counts = Counter(v.code for v in all_violations)

        fail_count = sum(1 for v in all_violations if v.severity == "FAIL")
        warn_count = sum(1 for v in all_violations if v.severity == "WARN")
        flag_count = sum(1 for v in all_violations if v.severity == "FLAG")

        print("MNA Stage 4 — ROOTS Constraint Audit")
        print(f"BOOK: {book}")
        print(f"DATASET: {dataset_path}")
        print(f"RULES LOADED: {len(rules)}")
        print(f"ROWS AUDITED: {len(rows)}")
        print(f"FAILURES: {fail_count}")
        print(f"WARNINGS: {warn_count}")
        print(f"FLAGS: {flag_count}")
        print()

        if counts:
            print("VIOLATION COUNTS:")
            for code, count in sorted(counts.items()):
                print(f"  - {code}: {count}")
            print()

        if all_violations:
            print("VIOLATIONS:")
            for violation in all_violations:
                print(f"  - {violation.severity} | {violation.reference} | {violation.code} | {violation.detail}")
            print()

        if args.jsonl:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with output_path.open("w", encoding="utf-8") as out:
                out.write(json.dumps({
                    "record_type": "metadata",
                    "book": book,
                    "rows_audited": len(rows),
                    "rules_loaded": len(rules),
                    "failures": fail_count,
                    "warnings": warn_count,
                    "flags": flag_count,
                    "violation_counts": dict(counts),
                }, ensure_ascii=False) + "\n")

                for violation in all_violations:
                    out.write(json.dumps(violation.to_json(), ensure_ascii=False) + "\n")

            print(f"AUDIT JSONL: {output_path}")
            print()

        if fail_count:
            print("STATUS: FAIL")
            return 1

        if warn_count and args.fail_on_warn:
            print("STATUS: FAIL")
            return 1

        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("MNA Stage 4 ROOTS constraint audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
