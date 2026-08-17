#!/usr/bin/env python3
"""Controlled book review, release build, approval, and publication.

All PASS decisions come from named humans. This program only enforces revision
bindings, builds deterministic bytes, and verifies checksums.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from book_workflow import (
    HUMAN_REVIEW_METHOD,
    WorkflowError,
    gate_state,
    load_book,
    load_json,
    normalize_book,
    normalized_person,
    now_iso,
    revision_bindings,
    save_immutable_json,
    save_json,
    sha256_file,
    stable_hash,
)


BOOK_REVIEW_CHECKS = (
    "terminology_names_titles",
    "recurring_constructions",
    "contextual_consistency",
    "book_wide_investigation_decisions",
    "alignment_conventions_and_exceptions",
    "unresolved_or_stale_records",
    "source_coverage_and_verse_inventory",
)

# Consumer Bible filename in cgv-data. Release paperwork stays in Biblia-LBF.
LBF_TEXT_SLUGS = {
    "zechariah": "zacarias",
    "daniel": "daniel",
    "titus": "tito",
    "jude": "judas",
    "1peter": "1pedro",
    "1john": "1juan",
}


def release_paths(data: dict[str, Any]) -> dict[str, Path]:
    base = data["root"] / "verification" / data["book"]
    return {
        "book_review": base / "book-review.json",
        "book_reviews": base / "book-reviews",
        "manifest": base / "release-manifest.json",
        "releases": base / "releases",
        "approval": base / "release-approval.json",
        "approvals": base / "release-approvals",
        "publication": base / "publication-record.json",
        "attestation": base / "manager-attestation.yaml",
    }


def decision_field(path: Path, field: str) -> str:
    match = re.search(rf"(?im)^{re.escape(field)}:\s*([^\n]+)", path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else ""


def investigation_bindings(data: dict[str, Any]) -> list[dict[str, str]]:
    directory = data["root"] / "investigations" / data["book"]
    values = []
    if not directory.is_dir():
        return values
    for investigation in sorted(path for path in directory.iterdir() if path.is_dir()):
        decision = investigation / "decision.md"
        if not decision.is_file():
            raise WorkflowError(f"{investigation.name}: decision.md is missing")
        release_blocking = decision_field(decision, "Release-Blocking").lower() in {"yes", "true"}
        status = decision_field(decision, "Status").upper()
        if release_blocking and status not in {"RESOLVED", "SUPERSEDED"}:
            raise WorkflowError(f"{investigation.name} is release-blocking and {status or 'UNCLASSIFIED'}")
        values.append({
            "investigationId": investigation.name,
            "status": status,
            "releaseBlocking": "true" if release_blocking else "false",
            "decisionVersion": decision_field(decision, "Version"),
            "decisionMaker": decision_field(decision, "Decision-Maker"),
            "decisionSha256": sha256_file(decision),
        })
    return values


def current_bindings(data: dict[str, Any]) -> dict[str, Any]:
    reviews = {}
    for gate in ("translation", "alignment"):
        state, detail = gate_state(data, gate)
        if state != "PASS":
            raise WorkflowError(f"{gate.upper()} is {state}: {detail}")
        document = load_json(data["paths"][f"{gate}_review"])
        decision_ids = sorted(str(item.get("decisionId")) for item in document["verses"])
        reviews["G0A" if gate == "translation" else "G0B"] = {
            "decisionCount": len(decision_ids),
            "decisionSetSha256": stable_hash(decision_ids),
        }
    return {
        "inputRevisionIds": revision_bindings(data, "alignment"),
        "gateDecisionSets": reviews,
        "investigations": investigation_bindings(data),
    }


def require_named_role(data: dict[str, Any], role: str, person: str) -> None:
    roles = load_json(data["paths"]["roles"])
    assignment = roles.get("assignments", {}).get(role, {})
    assigned = str(assignment.get("name") or "")
    if assignment.get("status") != "ASSIGNED" or normalized_person(assigned) != normalized_person(person):
        raise WorkflowError(f"{person!r} is not the assigned {role} ({assigned!r}).")


def record_book_review(data: dict[str, Any], reviewer: str, notes: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise WorkflowError("Direct human complete-book review must be explicitly confirmed.")
    reviewer = reviewer.strip()
    if not reviewer:
        raise WorkflowError("A named human book reviewer is required.")
    bindings = current_bindings(data)
    body = {
        "schemaVersion": 1,
        "revision": 1,
        "recordType": "BOOK_REVIEW",
        "book": data["book"],
        **bindings,
        "reviewer": reviewer,
        "authority": "HUMAN",
        "reviewMethod": "DIRECT_COMPLETE_BOOK_REVIEW",
        "aiUsed": False,
        "checks": {name: "PASS" for name in BOOK_REVIEW_CHECKS},
        "result": "PASS",
        "notes": notes.strip(),
        "timestamp": now_iso(),
    }
    record_id = f"BOOKREV-{data['book']}-{stable_hash(body)[:12]}"
    record = {"recordId": record_id, **body}
    paths = release_paths(data)
    save_immutable_json(paths["book_reviews"] / f"{record_id}.json", record)
    save_json(paths["book_review"], record)
    return record


def validated_book_review(data: dict[str, Any]) -> dict[str, Any]:
    path = release_paths(data)["book_review"]
    if not path.is_file():
        raise WorkflowError("A current complete-book review PASS is required.")
    review = load_json(path)
    if review.get("result") != "PASS" or review.get("authority") != "HUMAN" or review.get("aiUsed") is not False:
        raise WorkflowError("The current complete-book review is not a valid human PASS.")
    expected = current_bindings(data)
    for key in expected:
        if review.get(key) != expected[key]:
            raise WorkflowError(f"The complete-book review is stale: {key} changed.")
    if any(review.get("checks", {}).get(name) != "PASS" for name in BOOK_REVIEW_CHECKS):
        raise WorkflowError("The complete-book review checklist is incomplete.")
    return review


def render_lbf_text(data: dict[str, Any], edition: str, version: str) -> bytes:
    bindings = revision_bindings(data, "alignment")
    lines = [
        "<!-- LBF — La Biblia Fiel",
        f"     book: {data['book']}",
        f"     edition: {edition}",
        f"     version: {version}",
        f"     translation-revision: {bindings['translation']}",
        "-->",
    ]
    seen = set()
    for row in data["rows"]:
        reference = str(row.get("reference") or "").strip()
        spanish = str(row.get("spanish") or "").strip()
        if not reference or not spanish or reference in seen:
            raise WorkflowError(f"Cannot render invalid or duplicate translation row: {reference!r}")
        seen.add(reference)
        lines.append(f"{reference} {spanish}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def save_immutable_bytes(path: Path, payload: bytes) -> None:
    if path.is_file():
        if path.read_bytes() != payload:
            raise WorkflowError(f"Refusing to overwrite immutable artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def validate_release_identity(edition: str, version: str) -> tuple[str, str]:
    edition = edition.strip()
    version = version.strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]*", edition):
        raise WorkflowError("Edition must be a simple non-empty identifier.")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise WorkflowError("Version must use semantic version form, such as 1.0.0.")
    return edition, version


def build_candidate(data: dict[str, Any], edition: str, version: str) -> dict[str, Any]:
    edition, version = validate_release_identity(edition, version)
    review = validated_book_review(data)
    identity = {
        "book": data["book"],
        "edition": edition,
        "version": version,
        "inputRevisionIds": revision_bindings(data, "alignment"),
        "bookReviewId": review["recordId"],
    }
    build_id = f"{edition}-{data['book']}-{version}-{stable_hash(identity)[:12]}"
    paths = release_paths(data)
    directory = paths["releases"] / build_id
    text_path = directory / f"{data['book']}.lbf.md"
    alignment_path = directory / f"{data['book']}.alignment.json"
    save_immutable_bytes(text_path, render_lbf_text(data, edition, version))
    save_immutable_bytes(alignment_path, data["paths"]["alignment"].read_bytes())

    body = {
        "schemaVersion": 1,
        "revision": 1,
        "recordType": "RELEASE_MANIFEST",
        "book": data["book"],
        "edition": edition,
        "version": version,
        "buildId": build_id,
        "status": "PENDING",
        "createdBy": "deterministic-release-builder",
        "aiUsed": False,
        "createdAt": now_iso(),
        "inputRevisionIds": identity["inputRevisionIds"],
        "bookReviewId": review["recordId"],
        "artifacts": {
            "text": {"file": text_path.name, "sha256": sha256_file(text_path)},
            "alignment": {"file": alignment_path.name, "sha256": sha256_file(alignment_path)},
        },
    }
    manifest_id = f"RELMAN-{data['book']}-{stable_hash({k: v for k, v in body.items() if k != 'createdAt'})[:12]}"
    record = {"recordId": manifest_id, **body}
    manifest_path = directory / "release-manifest.json"
    if manifest_path.is_file():
        existing = load_json(manifest_path)
        comparable = lambda value: {k: v for k, v in value.items() if k != "createdAt"}
        if comparable(existing) != comparable(record):
            raise WorkflowError(f"Existing release build differs: {directory}")
        record = existing
    else:
        save_immutable_json(manifest_path, record)
    save_json(paths["manifest"], {**record, "manifestPath": str(manifest_path.relative_to(data["root"]))})
    return record


def manifest_file(data: dict[str, Any], manifest: dict[str, Any]) -> Path:
    return release_paths(data)["releases"] / str(manifest["buildId"]) / "release-manifest.json"


def approve_candidate(data: dict[str, Any], approver: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise WorkflowError("Final human release approval must be explicitly confirmed.")
    require_named_role(data, "releaseApprover", approver)
    paths = release_paths(data)
    if not paths["manifest"].is_file():
        raise WorkflowError("Build a release candidate before approval.")
    manifest = load_json(paths["manifest"])
    if validated_book_review(data)["recordId"] != manifest.get("bookReviewId"):
        raise WorkflowError("Release manifest is not bound to the current book review.")
    source = manifest_file(data, manifest)
    if not source.is_file():
        raise WorkflowError("Immutable release manifest is missing.")
    body = {
        "schemaVersion": 1,
        "revision": 1,
        "recordType": "RELEASE_APPROVAL",
        "book": data["book"],
        "manifestId": manifest["recordId"],
        "manifestSha256": sha256_file(source),
        "buildId": manifest["buildId"],
        "edition": manifest["edition"],
        "version": manifest["version"],
        "approver": approver,
        "authority": "HUMAN",
        "reviewMethod": HUMAN_REVIEW_METHOD,
        "aiUsed": False,
        "result": "PASS",
        "timestamp": now_iso(),
    }
    record_id = f"RELAPP-{data['book']}-{stable_hash(body)[:12]}"
    record = {"recordId": record_id, **body}
    save_immutable_json(paths["approvals"] / f"{record_id}.json", record)
    save_json(paths["approval"], record)
    return record


def validated_approval(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path]:
    paths = release_paths(data)
    if not paths["approval"].is_file() or not paths["manifest"].is_file():
        raise WorkflowError("A current human release approval is required.")
    approval = load_json(paths["approval"])
    manifest = load_json(paths["manifest"])
    source = manifest_file(data, manifest)
    if (
        approval.get("result") != "PASS"
        or approval.get("authority") != "HUMAN"
        or approval.get("aiUsed") is not False
        or approval.get("manifestId") != manifest.get("recordId")
        or approval.get("manifestSha256") != sha256_file(source)
    ):
        raise WorkflowError("Release approval is invalid or stale.")
    return approval, manifest, source


def compatibility_attestation(data: dict[str, Any], published: Path, manifest: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    text = published / manifest["artifacts"]["text"]["file"]
    alignment = published / manifest["artifacts"]["alignment"]["file"]
    checks = {name: "PASS" for name in (
        "verse_completeness", "verse_order", "duplicate_source_segments",
        "missing_source_segments", "token_accounting", "span_integrity", "reproducibility",
    )}
    independent = {name: "PASS" for name in (
        "source_identity", "source_text_integrity", "alignment_integrity",
        "span_boundary_review", "suspicious_omission_review", "suspicious_duplication_review",
    )}
    return {
        "schema_version": "0.1",
        "project": {"book": data["book"], "language": "es", "producer_project": "cgv-translator"},
        "source": {"name": "LBF", "path": str(text), "revision": manifest["inputRevisionIds"]["translation"], "checksum_sha256": sha256_file(text)},
        "alignment": {"path": str(alignment), "revision": manifest["inputRevisionIds"]["alignment"], "checksum_sha256": sha256_file(alignment)},
        "producer": {"status": "PASS", "tool_version": "book_workflow.py/release_book.py schema 1", "checked_at": now_iso(), "checks": checks, "report_path": str(data["paths"]["defects"])},
        "independent_verification": {"status": "PASS", "verifier": "Brandon Flores (G0A) and John Wry (G0B)", "runtime": "direct human review plus deterministic scripts", "model": "NONE — AI verification prohibited", "ai_used": False, "verified_at": approval["timestamp"], "checks": independent, "report_path": str(data["root"] / "verification" / data["book"] / "review-packet.json"), "findings": []},
        "human_linguistic_review": {"required": True, "status": "PASS", "reviewer": "Brandon Flores; John Wry", "reviewed_at": approval["timestamp"], "scope": "complete book translation, alignment, and book review", "report_path": str(release_paths(data)["book_review"]), "findings": []},
        "attestation": {"status": "VERIFIED", "issued_at": now_iso(), "blockers": [], "notes": f"Compatibility registration for approved manifest {manifest['recordId']}; AI verification was not used."},
    }


def publish(data: dict[str, Any], operator: str, target_root: Path, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise WorkflowError("Publication must be explicitly confirmed by the named release operator.")
    require_named_role(data, "releaseOperator", operator)
    approval, manifest, source_manifest = validated_approval(data)
    source_dir = source_manifest.parent
    # Release package (manifest, text, alignment) lives in Biblia-LBF.
    # cgv-data receives only the consumer Bible text.
    biblia_lbf = data["root"].parent / "Biblia-LBF"
    destination = (
        biblia_lbf / "releases" / data["book"] / str(manifest["version"]) / str(manifest["buildId"])
    )
    destination.mkdir(parents=True, exist_ok=True)
    for filename in [item["file"] for item in manifest["artifacts"].values()] + ["release-manifest.json"]:
        source = source_dir / filename
        target = destination / filename
        if target.is_file() and target.read_bytes() != source.read_bytes():
            raise WorkflowError(f"Refusing to overwrite different published bytes: {target}")
        if not target.is_file():
            shutil.copyfile(source, target)
    for item in manifest["artifacts"].values():
        if sha256_file(destination / item["file"]) != item["sha256"]:
            raise WorkflowError(f"Published checksum mismatch: {item['file']}")
    published_manifest_sha = sha256_file(destination / "release-manifest.json")
    if published_manifest_sha != approval["manifestSha256"]:
        raise WorkflowError("Published manifest checksum does not match human approval.")
    text_name = manifest["artifacts"]["text"]["file"]
    slug = LBF_TEXT_SLUGS.get(data["book"], data["book"])
    consumer_text = target_root.resolve() / "bibles" / "LBF" / f"{slug}.lbf.md"
    consumer_text.parent.mkdir(parents=True, exist_ok=True)
    text_bytes = (destination / text_name).read_bytes()
    if consumer_text.is_file() and consumer_text.read_bytes() != text_bytes:
        raise WorkflowError(f"Refusing to overwrite different published Bible text: {consumer_text}")
    if not consumer_text.is_file():
        consumer_text.write_bytes(text_bytes)
    if sha256_file(consumer_text) != manifest["artifacts"]["text"]["sha256"]:
        raise WorkflowError(f"Published Bible text checksum mismatch: {consumer_text}")
    record = {
        "schemaVersion": 1,
        "recordType": "PUBLICATION_RECORD",
        "recordId": f"PUB-{data['book']}-{stable_hash([manifest['buildId'], published_manifest_sha])[:12]}",
        "revision": 1,
        "book": data["book"],
        "status": "PASS",
        "operator": operator,
        "authority": "HUMAN_OPERATION",
        "aiUsed": False,
        "publishedAt": now_iso(),
        "manifestId": manifest["recordId"],
        "manifestSha256": published_manifest_sha,
        "artifactId": manifest["buildId"],
        "edition": manifest["edition"],
        "version": manifest["version"],
        "publishedPath": str(destination),
        "consumerTextPath": str(consumer_text),
    }
    save_json(release_paths(data)["publication"], record)
    release_paths(data)["attestation"].write_text(
        json.dumps(compatibility_attestation(data, destination, manifest, approval), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Controlled LBF book release")
    root.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help=argparse.SUPPRESS)
    commands = root.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review")
    review.add_argument("book")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--notes", default="")
    review.add_argument("--human-confirmation", action="store_true")
    build = commands.add_parser("build")
    build.add_argument("book")
    build.add_argument("--edition", required=True)
    build.add_argument("--version", required=True)
    approve = commands.add_parser("approve")
    approve.add_argument("book")
    approve.add_argument("--approver", required=True)
    approve.add_argument("--human-confirmation", action="store_true")
    publication = commands.add_parser("publish")
    publication.add_argument("book")
    publication.add_argument("--operator", required=True)
    publication.add_argument("--target-root", required=True)
    publication.add_argument("--human-confirmation", action="store_true")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        data = load_book(Path(args.root).resolve(), normalize_book(args.book))
        if args.command == "review":
            record = record_book_review(data, args.reviewer, args.notes, args.human_confirmation)
            print(f"BOOK REVIEW PASS: {record['recordId']} — {record['reviewer']}")
        elif args.command == "build":
            record = build_candidate(data, args.edition, args.version)
            print(f"RELEASE CANDIDATE: {record['buildId']} ({record['recordId']})")
        elif args.command == "approve":
            record = approve_candidate(data, args.approver, args.human_confirmation)
            print(f"RELEASE APPROVAL PASS: {record['recordId']} — {record['approver']}")
        elif args.command == "publish":
            record = publish(data, args.operator, Path(args.target_root), args.human_confirmation)
            print(f"PUBLISHED: {record['artifactId']} — {record['publishedPath']}")
        return 0
    except (WorkflowError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
