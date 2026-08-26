#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import yaml

PRODUCER = [
    "verse_completeness","verse_order","duplicate_source_segments",
    "missing_source_segments","token_accounting","span_integrity","reproducibility"
]
INDEPENDENT = [
    "source_identity","source_text_integrity","alignment_integrity",
    "span_boundary_review","suspicious_omission_review","suspicious_duplication_review"
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attestation", required=True)
    ap.add_argument("--book", required=True)
    args = ap.parse_args()

    data = yaml.safe_load(Path(args.attestation).read_text(encoding="utf-8"))
    errors = []

    if data.get("schema_version") != "0.1":
        errors.append("unsupported schema version")

    project = data.get("project", {})
    if project.get("book") != args.book:
        errors.append("book/project mismatch")
    if project.get("producer_project") != "cgv-translator":
        errors.append("unexpected producer project")

    source = data.get("source", {})
    alignment = data.get("alignment", {})
    if source.get("name") != "LBF":
        errors.append("source is not LBF")

    for name, obj in [("source", source), ("alignment", alignment)]:
        if not obj.get("revision"):
            errors.append(f"{name} revision missing")
        if not obj.get("path"):
            errors.append(f"{name} path missing")
        if not obj.get("checksum_sha256"):
            errors.append(f"{name} checksum missing")

    producer = data.get("producer", {})
    if producer.get("status") != "PASS":
        errors.append("producer checks not PASS")
    for check in PRODUCER:
        if producer.get("checks", {}).get(check) != "PASS":
            errors.append(f"producer check not PASS: {check}")

    independent = data.get("independent_verification", {})
    if independent.get("status") != "PASS":
        errors.append("independent verification not PASS")
    for check in INDEPENDENT:
        if independent.get("checks", {}).get(check) != "PASS":
            errors.append(f"independent check not PASS: {check}")

    human = data.get("human_linguistic_review", {})
    if human.get("required", True) and human.get("status") != "PASS":
        errors.append("required human linguistic review not PASS")

    att = data.get("attestation", {})
    if att.get("status") != "VERIFIED":
        errors.append("attestation is not VERIFIED")
    if att.get("blockers"):
        errors.append("attestation has blockers")

    for name, obj in [("source", source), ("alignment", alignment)]:
        path = Path(obj.get("path", ""))
        if path.exists() and sha256(path) != obj.get("checksum_sha256"):
            errors.append(f"{name} checksum mismatch")

    if errors:
        print("REJECTED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("ACCEPTED")
    print(f"Book: {project.get('book')}")
    print(f"Source revision: {source.get('revision')}")
    print(f"Alignment revision: {alignment.get('revision')}")
    print("Gate 0 evidence satisfies contract v0.1.")

if __name__ == "__main__":
    main()
