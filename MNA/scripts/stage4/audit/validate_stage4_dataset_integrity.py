#!/usr/bin/env python3
"""
MNA Stage 4 Audit — dataset integrity.

PURPOSE
- Audit Stage 4 dataset integrity across the approved candidate layer.
- Verify Stage 4 does not mutate predicate identity inherited from predicate-completeness.
- Verify approved/quarantined audit source wiring.
- Verify anti-drift fields remain NONE.

IMPORTANT
This script is diagnostic only.
It does NOT modify datasets.
It does NOT create trunk, [S], [M], labels, units, or titles.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

VERSION = "stage4-dataset-integrity-audit-v2-quarantine-aware"

ALLOWED_STATUSES = {"NO", "UNRESOLVED_CANDIDATE"}

APPROVED_AUDIT_DATASETS = {
    "absolute-dependency-candidates": "audits/stage4/absolute-dependency-candidates/{book}.jsonl",
    "relative-dependency-candidates": "audits/stage4/relative-dependency-candidates/{book}.jsonl",
    "content-clause-dependency-candidates": "audits/stage4/content-clause-dependency-candidates/{book}.jsonl",
}

QUARANTINED_AUDIT_DATASETS = {
    "subordinator-dependency-candidates": "audits/stage4/subordinator-dependency-candidates/{book}.jsonl",
}

ANTI_DRIFT_FIELDS = {
    "trunk_claim": "NONE",
    "subject_marker_claim": "NONE",
    "movement_marker_claim": "NONE",
    "connector_relationship_claim": "NONE",
    "label_claim": "NONE",
    "unit_claim": "NONE",
    "title_claim": "NONE",
}

INHERITED_FIELDS = [
    "predicate_anchor_id",
    "book",
    "chapter",
    "verse",
    "reference",
    "anchor_order",
    "greek_surface",
    "greek_clean",
    "lemma",
    "morphology",
    "mood",
    "person",
    "number",
]


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def load_jsonl(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    metadata = None
    rows = []

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
                if metadata is not None:
                    raise ValueError(f"Multiple metadata rows in {path}")
                metadata = obj
            else:
                rows.append(obj)

    if metadata is None:
        raise ValueError(f"Missing metadata row: {path}")

    return metadata, rows


def path_from_template(root: Path, template: str, book: str) -> Path:
    return root / template.format(book=book)


def collect_audit_sources(root: Path, book: str, templates: dict[str, str]) -> tuple[dict[str, set[str]], dict[str, int], list[Path]]:
    anchor_sources: dict[str, set[str]] = defaultdict(set)
    source_counts: dict[str, int] = {}
    present_paths: list[Path] = []

    for source_name, template in templates.items():
        path = path_from_template(root, template, book)
        if not path.is_file():
            source_counts[source_name] = 0
            continue

        present_paths.append(path)
        _metadata, rows = load_jsonl(path)
        count = 0

        for row in rows:
            anchor_id = row.get("predicate_anchor_id")
            if not anchor_id:
                continue
            anchor_sources[str(anchor_id)].add(source_name)
            count += 1

        source_counts[source_name] = count

    return anchor_sources, source_counts, present_paths


def audit(book: str, root: Path) -> dict[str, object]:
    predicate_path = root / "datasets" / "predicate-completeness" / f"{book}.jsonl"
    candidate_path = root / "datasets" / "independent-clause-candidates" / f"{book}.jsonl"

    predicate_metadata, predicate_rows = load_jsonl(predicate_path)
    candidate_metadata, candidate_rows = load_jsonl(candidate_path)

    approved_sources, approved_counts, approved_paths = collect_audit_sources(root, book, APPROVED_AUDIT_DATASETS)
    quarantined_sources, quarantined_counts, quarantined_paths = collect_audit_sources(root, book, QUARANTINED_AUDIT_DATASETS)

    errors = Counter()
    warnings = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    def add_example(key: str, value: str, limit: int = 10) -> None:
        if len(examples[key]) < limit:
            examples[key].append(value)

    if predicate_metadata.get("book") != book:
        errors["predicate_metadata_book_mismatch"] += 1
    if candidate_metadata.get("book") != book:
        errors["candidate_metadata_book_mismatch"] += 1

    if len(predicate_rows) != len(candidate_rows):
        errors["row_count_mismatch"] += 1

    predicate_ids = [str(row.get("predicate_anchor_id")) for row in predicate_rows]
    candidate_ids = [str(row.get("predicate_anchor_id")) for row in candidate_rows]

    if predicate_ids != candidate_ids:
        errors["anchor_sequence_mismatch"] += 1

    duplicate_predicate_ids = [anchor_id for anchor_id, count in Counter(predicate_ids).items() if count > 1]
    duplicate_candidate_ids = [anchor_id for anchor_id, count in Counter(candidate_ids).items() if count > 1]

    if duplicate_predicate_ids:
        errors["duplicate_predicate_anchor_ids"] += len(duplicate_predicate_ids)
        for anchor_id in duplicate_predicate_ids[:10]:
            add_example("duplicate_predicate_anchor_ids", anchor_id)

    if duplicate_candidate_ids:
        errors["duplicate_candidate_anchor_ids"] += len(duplicate_candidate_ids)
        for anchor_id in duplicate_candidate_ids[:10]:
            add_example("duplicate_candidate_anchor_ids", anchor_id)

    status_counts = Counter()
    no_rows = 0
    unresolved_rows = 0
    previous_order = 0

    predicate_by_id = {str(row.get("predicate_anchor_id")): row for row in predicate_rows}

    for row in candidate_rows:
        anchor_id = str(row.get("predicate_anchor_id"))
        predicate_row = predicate_by_id.get(anchor_id)

        if row.get("record_type") != "independent_clause_candidate_row":
            errors["candidate_record_type_error"] += 1
            add_example("candidate_record_type_error", anchor_id)

        try:
            order = int(row.get("anchor_order"))
            if order <= previous_order:
                errors["ordering_error"] += 1
                add_example("ordering_error", anchor_id)
            previous_order = order
        except Exception:
            errors["ordering_error"] += 1
            add_example("ordering_error", anchor_id)

        status = row.get("independent_clause_candidate")
        stage4_status = row.get("stage4_status")
        status_counts[str(status)] += 1

        if status not in ALLOWED_STATUSES:
            errors["invalid_status"] += 1
            add_example("invalid_status", f"{anchor_id}: {status}")

        if status != stage4_status:
            errors["stage4_status_mismatch"] += 1
            add_example("stage4_status_mismatch", anchor_id)

        if status == "NO":
            no_rows += 1
        elif status == "UNRESOLVED_CANDIDATE":
            unresolved_rows += 1

        if predicate_row is None:
            errors["candidate_anchor_not_in_predicate_dataset"] += 1
            add_example("candidate_anchor_not_in_predicate_dataset", anchor_id)
        else:
            for field in INHERITED_FIELDS:
                if str(row.get(field)) != str(predicate_row.get(field)):
                    errors["inheritance_field_mismatch"] += 1
                    add_example("inheritance_field_mismatch", f"{anchor_id}: {field}")

        sources = row.get("dependency_candidate_sources")
        if not isinstance(sources, list):
            errors["dependency_sources_not_list"] += 1
            add_example("dependency_sources_not_list", anchor_id)
            sources = []

        source_set = set(str(source) for source in sources)
        approved_for_anchor = approved_sources.get(anchor_id, set())
        quarantined_for_anchor = quarantined_sources.get(anchor_id, set())

        unknown_sources = source_set - set(APPROVED_AUDIT_DATASETS.keys())
        if unknown_sources:
            errors["unknown_dependency_source_in_candidate"] += 1
            add_example("unknown_dependency_source_in_candidate", f"{anchor_id}: {sorted(unknown_sources)}")

        quarantined_in_candidate = source_set & set(QUARANTINED_AUDIT_DATASETS.keys())
        if quarantined_in_candidate:
            errors["quarantined_source_used_for_official_elimination"] += 1
            add_example("quarantined_source_used_for_official_elimination", f"{anchor_id}: {sorted(quarantined_in_candidate)}")

        if source_set != approved_for_anchor:
            errors["approved_source_set_mismatch"] += 1
            add_example(
                "approved_source_set_mismatch",
                f"{anchor_id}: row={sorted(source_set)} approved={sorted(approved_for_anchor)} quarantined={sorted(quarantined_for_anchor)}",
            )

        if status == "NO" and not approved_for_anchor:
            errors["no_without_approved_source"] += 1
            add_example("no_without_approved_source", anchor_id)

        if status == "UNRESOLVED_CANDIDATE" and approved_for_anchor:
            errors["unresolved_with_approved_source"] += 1
            add_example("unresolved_with_approved_source", anchor_id)

        for field, expected_value in ANTI_DRIFT_FIELDS.items():
            if row.get(field) != expected_value:
                errors["anti_drift_field_error"] += 1
                add_example("anti_drift_field_error", f"{anchor_id}: {field}={row.get(field)}")

    if int(candidate_metadata.get("rows", -1)) != len(candidate_rows):
        errors["metadata_rows_count_error"] += 1

    if int(candidate_metadata.get("independent_clause_candidate_NO", -1)) != no_rows:
        errors["metadata_no_count_error"] += 1

    if int(candidate_metadata.get("independent_clause_candidate_UNRESOLVED", -1)) != unresolved_rows:
        errors["metadata_unresolved_count_error"] += 1

    approved_metadata_sources = candidate_metadata.get("approved_audit_sources_used", [])
    if sorted(approved_metadata_sources) != sorted(APPROVED_AUDIT_DATASETS.keys()):
        errors["metadata_approved_audit_sources_error"] += 1
        add_example(
            "metadata_approved_audit_sources_error",
            f"metadata={approved_metadata_sources} approved={sorted(APPROVED_AUDIT_DATASETS.keys())}",
        )

    quarantined_metadata_sources = candidate_metadata.get("quarantined_audit_sources_present_but_excluded", [])
    expected_quarantined_present = [name for name, template in QUARANTINED_AUDIT_DATASETS.items() if path_from_template(root, template, book).is_file()]
    if sorted(quarantined_metadata_sources) != sorted(expected_quarantined_present):
        errors["metadata_quarantined_audit_sources_error"] += 1
        add_example(
            "metadata_quarantined_audit_sources_error",
            f"metadata={quarantined_metadata_sources} expected={sorted(expected_quarantined_present)}",
        )

    if "audit_sources_used" in candidate_metadata:
        errors["legacy_metadata_audit_sources_field_present"] += 1
        add_example("legacy_metadata_audit_sources_field_present", str(candidate_metadata.get("audit_sources_used")))

    if quarantined_paths:
        warnings["quarantined_datasets_present"] += len(quarantined_paths)

    status = "PASS" if not errors else "FAIL"

    return {
        "version": VERSION,
        "book": book,
        "predicate_path": str(predicate_path),
        "candidate_path": str(candidate_path),
        "predicate_rows": len(predicate_rows),
        "candidate_rows": len(candidate_rows),
        "no_rows": no_rows,
        "unresolved_rows": unresolved_rows,
        "status_counts": dict(status_counts),
        "approved_source_counts": approved_counts,
        "quarantined_source_counts": quarantined_counts,
        "approved_paths": [str(path) for path in approved_paths],
        "quarantined_paths": [str(path) for path in quarantined_paths],
        "errors": dict(errors),
        "warnings": dict(warnings),
        "examples": dict(examples),
        "status": status,
    }


def print_result(result: dict[str, object]) -> None:
    print("MNA Stage 4 Audit — Dataset Integrity")
    print(f"BOOK: {result['book']}")
    print(f"VERSION: {result['version']}")
    print(f"PREDICATE_COMPLETENESS: {result['predicate_path']}")
    print(f"INDEPENDENT_CLAUSE_CANDIDATES: {result['candidate_path']}")
    print(f"PREDICATE_ROWS: {result['predicate_rows']}")
    print(f"CANDIDATE_ROWS: {result['candidate_rows']}")
    print(f"NO_ROWS: {result['no_rows']}")
    print(f"UNRESOLVED_ROWS: {result['unresolved_rows']}")
    print()

    print("APPROVED AUDIT SOURCE COUNTS:")
    for name, count in sorted(result["approved_source_counts"].items()):
        print(f"  - {name}: {count}")

    print()
    print("QUARANTINED AUDIT SOURCE COUNTS:")
    for name, count in sorted(result["quarantined_source_counts"].items()):
        print(f"  - {name}: {count}")

    print()
    print("WARNINGS:")
    warnings = result["warnings"]
    if warnings:
        for key, count in sorted(warnings.items()):
            print(f"  - {key}: {count}")
    else:
        print("  - none")

    print()
    print("ERRORS:")
    errors = result["errors"]
    if errors:
        for key, count in sorted(errors.items()):
            print(f"  - {key}: {count}")
    else:
        print("  - none")

    examples = result["examples"]
    if examples:
        print()
        print("ERROR EXAMPLES:")
        for key, values in sorted(examples.items()):
            print(f"  {key}:")
            for value in values:
                print(f"    - {value}")

    print()
    print(f"STATUS: {result['status']}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Stage 4 dataset integrity.")
    parser.add_argument("book", help="Book slug, e.g. 1corintios")
    parser.add_argument("--json", action="store_true", help="Print JSON result instead of text")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        result = audit(args.book.strip().lower(), root)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print_result(result)
        return 0 if result["status"] == "PASS" else 2
    except Exception as exc:
        print("MNA Stage 4 dataset integrity audit FAILED", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
