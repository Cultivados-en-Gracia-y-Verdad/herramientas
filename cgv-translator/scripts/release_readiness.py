#!/usr/bin/env python3
"""Report cold, reproducible facts that block or permit an LBF book release.

This program does not review translation or alignment and cannot approve a book.
It only combines controlled human gate records, deterministic audits, role records,
investigation classifications, and publication-repository state.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from book_workflow import (
    WorkflowError,
    alignment_audit,
    gate_state,
    load_book,
    normalize_book,
    now_iso,
    revision_bindings,
    save_json,
    sha256_file,
    translation_audit,
)
from release_book import validated_approval, validated_book_review


def git_tracked(repo: Path, path: Path) -> bool | None:
    if not repo.is_dir() or not path.exists():
        return None
    try:
        relative = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return None
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def file_fact(repo: Path, path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "exists": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "gitTracked": git_tracked(repo, path),
    }


def source_origin_fact(data: dict[str, Any], data_repo: Path) -> dict[str, Any]:
    path = data_repo / "interlinears" / "OT" / f"{data['book']}.tokens.jsonl"
    fact = file_fact(data_repo, path)
    fact.update({"spineTokenCount": None, "originTokenCount": None, "mismatchCount": None})
    if not path.is_file():
        return fact
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    spine_rows = [
        token
        for verse in data["spine"]["verses"].values()
        for token in verse.get("tokens", [])
    ]
    fields = (("surface", "surface"), ("lemma", "lemma"), ("morph", "morph"),
              ("oshbId", "id"), ("es", "es"), ("w", "w"))
    mismatches = abs(len(spine_rows) - len(rows))
    mismatches += sum(
        1
        for spine_token, origin_token in zip(spine_rows, rows)
        if any(spine_token.get(left) != origin_token.get(right) for left, right in fields)
    )
    fact.update({
        "spineTokenCount": len(spine_rows),
        "originTokenCount": len(rows),
        "mismatchCount": mismatches,
        "exactFieldMatch": mismatches == 0,
    })
    return fact


def investigation_facts(root: Path, book: str) -> list[dict[str, Any]]:
    directory = root / "investigations" / book
    facts = []
    if not directory.is_dir():
        return facts
    for investigation in sorted(path for path in directory.iterdir() if path.is_dir()):
        decision = investigation / "decision.md"
        readme = investigation / "README.md"
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (readme, decision)
            if path.is_file()
        )
        status_match = re.search(r"(?im)^Status:\s*([^\n]+)", text)
        blocking_match = re.search(
            r"(?im)^(?:Release[- ]Blocking|Blocks Release):\s*(yes|no|true|false)\s*$",
            text,
        )
        release_blocking: bool | None = None
        if blocking_match:
            release_blocking = blocking_match.group(1).lower() in {"yes", "true"}
        facts.append(
            {
                "id": investigation.name,
                "status": status_match.group(1).strip().upper() if status_match else "UNCLASSIFIED",
                "releaseBlocking": release_blocking,
                "classification": "EXPLICIT" if blocking_match else "UNCLASSIFIED",
            }
        )
    return facts


def role_facts(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    path = data["paths"]["roles"]
    if not path.is_file():
        return {}, [{
            "id": "ROLE-MISSING",
            "owner": "workflow operator",
            "nextAction": "Create controlled role assignments.",
            "reason": "Role assignments are missing.",
        }]
    roles = json.loads(path.read_text(encoding="utf-8"))
    blockers = [item for item in roles.get("blockers", []) if item.get("status") == "BLOCKED"]
    operator = roles.get("assignments", {}).get("releaseOperator", {})
    if operator.get("status") != "ASSIGNED" or not str(operator.get("name") or "").strip() or operator.get("name") == "UNASSIGNED":
        blockers.append({
            "id": "ROLE-OPERATOR",
            "owner": "John Wry",
            "nextAction": "Assign the named human release operator before publication.",
            "reason": "The release operator is unassigned.",
        })
    return roles, blockers


def make_report(root: Path, book: str) -> dict[str, Any]:
    data = load_book(root, book)
    translation_errors = translation_audit(data)
    alignment_errors = alignment_audit(data)
    g0a, g0a_detail = gate_state(data, "translation")
    g0b, g0b_detail = gate_state(data, "alignment")
    if g0a != "PASS":
        g0b, g0b_detail = "PENDING", f"G0B waits for current G0A PASS; G0A is {g0a}"
    roles, blockers = role_facts(data)
    investigations = investigation_facts(root, book)

    if g0a != "PASS":
        blockers.append({
            "id": "G0A",
            "owner": roles.get("assignments", {}).get("translationReviewer", {}).get("name", "translation reviewer"),
            "nextAction": "Complete direct human G0A review of the exact translation revision.",
            "reason": f"G0A is {g0a}: {g0a_detail}",
        })
    if alignment_errors:
        blockers.append({
            "id": "ALIGNMENT-STRUCTURE",
            "owner": "alignment producer",
            "nextAction": "After G0A PASS, submit a structurally valid alignment revision for G0B.",
            "reason": f"The canonical alignment has {len(alignment_errors)} deterministic defects.",
        })
    if g0b != "PASS":
        blockers.append({
            "id": "G0B",
            "owner": roles.get("assignments", {}).get("alignmentReviewer", {}).get("name", "alignment reviewer"),
            "nextAction": "Complete direct human G0B review after current G0A PASS.",
            "reason": f"G0B is {g0b}: {g0b_detail}",
        })
    for item in investigations:
        if item["classification"] == "UNCLASSIFIED":
            blockers.append({
                "id": f"{item['id']}-CLASSIFICATION",
                "owner": "John Wry",
                "nextAction": "Resolve the investigation or explicitly classify it as a non-blocking deferred question.",
                "reason": f"{item['id']} has no explicit release-blocking classification.",
            })
        elif item["releaseBlocking"] and item["status"] not in {"RESOLVED", "SUPERSEDED"}:
            blockers.append({
                "id": item["id"],
                "owner": "John Wry",
                "nextAction": "Resolve the release-blocking investigation.",
                "reason": f"{item['id']} is release-blocking and {item['status']}.",
            })

    try:
        validated_book_review(data)
    except WorkflowError as exc:
        blockers.append({
            "id": "BOOK-REVIEW",
            "owner": "book reviewer",
            "nextAction": "After all verses are READY, perform and record the complete-book review.",
            "reason": str(exc),
        })
    manifest_path = root / "verification" / book / "release-manifest.json"
    if not manifest_path.is_file():
        blockers.append({
            "id": "RELEASE-MANIFEST",
            "owner": "release operator",
            "nextAction": "After book review PASS, create the versioned release manifest for approval.",
            "reason": "No release manifest exists.",
        })
    else:
        try:
            validated_approval(data)
        except WorkflowError as exc:
            blockers.append({
                "id": "RELEASE-APPROVAL",
                "owner": roles.get("assignments", {}).get("releaseApprover", {}).get("name", "release approver"),
                "nextAction": "The assigned human release approver must approve the exact manifest.",
                "reason": str(exc),
            })

    translator_parent = root.parent.parent
    data_repo = translator_parent / "cgv-data"
    manager_repo = translator_parent / "herramientas" / "cgv-MANAGER"
    publication = {
        "cgvDataRepository": str(data_repo.resolve()),
        "textCandidates": [
            file_fact(data_repo, data_repo / "bibles" / "LBF" / f"{book}.lbf.md"),
            file_fact(data_repo, data_repo / "bibles" / "LBF" / f"{book}.lbf.final.md"),
        ],
        "alignmentCandidate": file_fact(
            data_repo, data_repo / "bibles" / "LBF" / "alignments" / f"{book}.alignment.json"
        ),
        "managerState": file_fact(
            manager_repo, manager_repo / "projects" / book / "state.yaml"
        ),
    }

    source_origin = source_origin_fact(data, data_repo)
    if source_origin.get("mismatchCount") not in {None, 0}:
        blockers.append({
            "id": "SOURCE-PROVENANCE",
            "owner": "source snapshot producer",
            "nextAction": "Reconcile the controlled source snapshot with its declared origin.",
            "reason": f"The source snapshot differs in {source_origin['mismatchCount']} token row(s).",
        })

    labels = Counter(str(row.get("suggestionSource") or "") for row in data["rows"])
    draft_path = data["paths"]["alignment"].with_name(f"{book}-reverse-links.draft-v1.json")
    draft_fact = file_fact(root, draft_path)
    if draft_path.is_file():
        draft_data = {**data, "alignment": json.loads(draft_path.read_text(encoding="utf-8"))}
        draft_fact["deterministicDefectCount"] = len(alignment_audit(draft_data))
        draft_fact["verificationAuthority"] = False
    return {
        "schemaVersion": 1,
        "recordType": "RELEASE_READINESS_REPORT",
        "book": book,
        "checkedAt": now_iso(),
        "authority": "DETERMINISTIC_FACTS_ONLY",
        "aiVerificationPermitted": False,
        "status": "PASS" if not blockers else "BLOCKED",
        "inputRevisionIds": revision_bindings(data, "alignment"),
        "scriptFacts": {
            "translationDefectCount": len(translation_errors),
            "alignmentDefectCount": len(alignment_errors),
            "translationLegacyLabels": dict(sorted(labels.items())),
            "alignmentDraft": draft_fact,
            "sourceOrigin": source_origin,
        },
        "humanGates": {
            "G0A": {"status": g0a, "detail": g0a_detail},
            "G0B": {"status": g0b, "detail": g0b_detail},
        },
        "investigations": investigations,
        "publicationInventory": publication,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic LBF release-readiness report")
    parser.add_argument("book")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        book = normalize_book(args.book)
        report = make_report(root, book)
        output = root / "verification" / book / "release-readiness.json"
        save_json(output, report)
        print(f"{book.upper()} RELEASE READINESS: {report['status']}")
        print(f"Translation defects: {report['scriptFacts']['translationDefectCount']}")
        print(f"Alignment defects:   {report['scriptFacts']['alignmentDefectCount']}")
        print(f"G0A: {report['humanGates']['G0A']['status']}")
        print(f"G0B: {report['humanGates']['G0B']['status']}")
        print(f"Blockers: {len(report['blockers'])}")
        for blocker in report["blockers"]:
            print(f"- {blocker['id']}: {blocker['reason']}")
        print(f"REPORT: {output.relative_to(root)}")
        return 0 if report["status"] == "PASS" else 1
    except (WorkflowError, OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
