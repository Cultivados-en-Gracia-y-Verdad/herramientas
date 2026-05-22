#!/usr/bin/env python3
"""
MNA Stage 5 — Baseline Snapshot Exporter

Purpose:
Export a mechanical baseline snapshot of the current Stage 5 state for drift detection.

This script does not interpret, score, rank, or claim final trunk status.
It only summarizes counts from Stage 5 output artifacts.
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def counter_to_sorted_dict(counter):
    return {str(k): v for k, v in sorted(counter.items(), key=lambda kv: str(kv[0]))}


def summarize_assertions(path):
    total = 0
    environments = Counter()
    assertions = Counter()
    signals = Counter()
    pressure = Counter()
    signal_count = Counter()
    pressure_count = Counter()

    for row in load_jsonl(path):
        total += 1
        environments[row.get("candidacy_environment")] += 1
        signal_count[row.get("signal_count")] += 1
        pressure_count[row.get("negative_pressure_count")] += 1

        for item in row.get("assertions") or []:
            assertions[item] += 1
        for item in row.get("signals") or []:
            signals[item] += 1
        for item in row.get("negative_pressure") or []:
            pressure[item] += 1

    return {
        "total_rows": total,
        "environment_counts": counter_to_sorted_dict(environments),
        "assertion_counts": counter_to_sorted_dict(assertions),
        "signal_counts": counter_to_sorted_dict(signals),
        "negative_pressure_counts": counter_to_sorted_dict(pressure),
        "signal_count_distribution": counter_to_sorted_dict(signal_count),
        "negative_pressure_count_distribution": counter_to_sorted_dict(pressure_count),
    }


def summarize_audit(path):
    total_failures = 0
    rules = {}

    for row in load_jsonl(path):
        if row.get("record_type") != "audit_summary":
            continue
        rule_id = row.get("rule_id")
        failures = int(row.get("failures") or 0)
        total_failures += failures
        rules[rule_id] = {
            "status": row.get("status"),
            "failures": failures,
        }

    return {
        "audit_pass": total_failures == 0,
        "audit_failures": total_failures,
        "rules": rules,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("book")
    p.add_argument("assertions_jsonl", type=Path)
    p.add_argument("assertion_audit_jsonl", type=Path)
    p.add_argument("output_json", type=Path)
    args = p.parse_args()

    snapshot = {
        "record_type": "stage5_baseline_snapshot",
        "book": args.book.strip().lower(),
        "purpose": "future structural drift detection",
        "final_trunk_status_claimed": False,
        "assertions_source": str(args.assertions_jsonl),
        "assertion_audit_source": str(args.assertion_audit_jsonl),
        "assertion_summary": summarize_assertions(args.assertions_jsonl),
        "assertion_audit_summary": summarize_audit(args.assertion_audit_jsonl),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"WROTE -> {args.output_json}")
    print(f"AUDIT_PASS: {snapshot['assertion_audit_summary']['audit_pass']}")
    print(f"TOTAL_ROWS: {snapshot['assertion_summary']['total_rows']}")


if __name__ == "__main__":
    main()
