#!/usr/bin/env python3
"""Canonical cgv-translator book workflow through human approval.

Publication/package layout for cgv-data remains blocked until its canonical schema is
specified; this command does not invent downstream storage.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from workflow_core import (
    WORKFLOW_VERSION, WorkflowError, current_bindings, investigation_status,
    load_json, load_yaml, normalize_book, preserve_review, recompute_summary,
    relative, resolve_paths, safe_component, save_yaml, stable_digest,
    translation_errors,
)
from workflow_queues import alignment_errors, make_g0a, make_g0b
from workflow_state import g0a_status, g0b_status, latest_approval, latest_final_review, load_history


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(path: Path, label: str) -> None:
    if not path.is_file():
        raise WorkflowError(f"{label} missing: {path}")


def prior_queue(path: Path) -> dict:
    return load_yaml(path) if path.is_file() else {}


def cmd_status(args) -> int:
    root, book = Path(args.root).resolve(), normalize_book(args.book)
    paths = resolve_paths(root, book)
    spine, phrases, reverse = (Path(paths[key]) for key in ("spine", "phrases", "reverse"))
    source_ok = spine.is_file()
    translation_detail = ["phrase artifact missing"] if not phrases.is_file() else translation_errors(book, load_json(phrases))
    translation_ok = source_ok and not translation_detail
    g0a_ok, g0a_detail = g0a_status(root, book, paths)
    align_detail = ["alignment missing"]
    if spine.is_file() and phrases.is_file() and reverse.is_file():
        align_detail = alignment_errors(book, load_json(spine), load_json(phrases), load_json(reverse))
    align_ok = g0a_ok and not align_detail
    g0b_ok, g0b_detail = g0b_status(root, book, paths)
    inv_ok, inv = investigation_status(paths)
    final, final_detail = latest_final_review(root, book, paths)
    approval, approval_detail = latest_approval(root, book, paths)
    stages = [
        ("SOURCE", source_ok, [] if source_ok else ["source spine missing"]),
        ("TRANSLATE", translation_ok, translation_detail), ("G0A", g0a_ok, g0a_detail),
        ("ALIGN", align_ok, align_detail), ("G0B", g0b_ok, g0b_detail),
        ("INVESTIGATIONS", inv_ok, inv["open"] + inv["invalid"]),
        ("BOOK FINAL CHECK", final is not None and not final_detail, final_detail),
        ("APPROVE", approval is not None and not approval_detail, approval_detail),
    ]
    print(f"BOOK WORKFLOW — {book}\nworkflow: {WORKFLOW_VERSION}\nlayout: {paths['layout']}")
    for label, ok, _ in stages:
        print(f"{label:<18} {'PASS' if ok else 'PENDING'}")
    print("PUBLISH cgv-data   BLOCKED (canonical import/storage schema not yet defined)")
    print("REGISTER MANAGER   BLOCKED until published data is verified")
    next_text = {
        "SOURCE": "bootstrap the declared source book", "TRANSLATE": "complete Spanish translation",
        "G0A": "generate/review G0A, then promote the exact reviewed artifact",
        "ALIGN": "align the G0A-approved Spanish", "G0B": "generate/review G0B for the exact alignment",
        "INVESTIGATIONS": "resolve or supersede required difficult-word investigations",
        "BOOK FINAL CHECK": "perform and record the human book-level final check",
        "APPROVE": "record human approval with explicit release identity/revisions",
    }
    for label, ok, detail in stages:
        if not ok:
            print(f"\nNEXT: {next_text[label]}.")
            for error in list(detail)[:10]: print(f"  - {error}")
            return 0
    print("\nTRANSLATOR APPROVED: exact artifact identity is recorded.")
    print("NEXT: define/use the canonical cgv-data publication schema; do not invent one here.")
    return 0


def cmd_queue_g0a(args) -> int:
    root, book = Path(args.root).resolve(), normalize_book(args.book); paths = resolve_paths(root, book)
    spine_path, phrase_path = Path(paths["spine"]), Path(paths["phrases"])
    require(spine_path, "source spine"); require(phrase_path, "phrase artifact")
    spine, phrase_doc = load_json(spine_path), load_json(phrase_path)
    errors = translation_errors(book, phrase_doc)
    if errors: raise WorkflowError("G0A cannot start:\n- " + "\n- ".join(errors))
    ok, _ = g0a_status(root, book, paths)
    if ok:
        print("G0A already PASS for the exact current artifact."); return 0
    queue = make_g0a(root, book, spine, phrase_doc, spine_path, phrase_path)
    if not queue["items"]:
        raise WorkflowError("No G0A items exist, but exact G0A approval is not established; approval cannot be inferred")
    path = Path(paths["g0a_queue"])
    preserved, reset = preserve_review(queue["items"], prior_queue(path)); recompute_summary(queue, "APPROVED"); save_yaml(path, queue)
    print(f"G0A queue: {relative(root, path)}\nitems: {queue['summary']['total']}; preserved: {preserved}; reset: {reset}")
    return 0


def cmd_promote_g0a(args) -> int:
    root, book = Path(args.root).resolve(), normalize_book(args.book); paths = resolve_paths(root, book)
    queue, phrases, spine = Path(paths["g0a_queue"]), Path(paths["phrases"]), Path(paths["spine"])
    for path, label in ((queue, "G0A queue"), (phrases, "phrase artifact"), (spine, "source spine")): require(path, label)
    command = [sys.executable, str(root / "gate0" / "promote-g0a-approvals.py"), "--queue", str(queue), "--phrases", str(phrases), "--spine", str(spine)]
    if args.apply: command.append("--apply")
    return subprocess.run(command, cwd=root).returncode


def cmd_queue_g0b(args) -> int:
    root, book = Path(args.root).resolve(), normalize_book(args.book); paths = resolve_paths(root, book)
    ok, errors = g0a_status(root, book, paths)
    if not ok: raise WorkflowError("ALIGN/G0B cannot start before exact G0A PASS:\n- " + "\n- ".join(errors))
    spine_path, phrase_path, reverse_path = (Path(paths[key]) for key in ("spine", "phrases", "reverse")); require(reverse_path, "alignment")
    spine, phrase_doc, reverse = load_json(spine_path), load_json(phrase_path), load_json(reverse_path)
    errors = alignment_errors(book, spine, phrase_doc, reverse)
    if errors: raise WorkflowError("G0B cannot start; alignment is incomplete:\n- " + "\n- ".join(errors))
    queue = make_g0b(root, book, spine, phrase_doc, reverse, spine_path, phrase_path, reverse_path)
    path = Path(paths["g0b_queue"]); preserved, reset = preserve_review(queue["items"], prior_queue(path)); recompute_summary(queue, "VERIFIED"); save_yaml(path, queue)
    print(f"G0B queue: {relative(root, path)}\nunits: {queue['summary']['total']}; preserved: {preserved}; reset: {reset}")
    return 0


def cmd_final_check(args) -> int:
    if not args.confirm: raise WorkflowError("Book final check is human scholarly judgment; use --confirm after doing the review")
    root, book = Path(args.root).resolve(), normalize_book(args.book); paths = resolve_paths(root, book)
    ok, errors = g0a_status(root, book, paths)
    if not ok: raise WorkflowError("Final check blocked by G0A:\n- " + "\n- ".join(errors))
    spine, phrases, reverse = load_json(Path(paths["spine"])), load_json(Path(paths["phrases"])), load_json(Path(paths["reverse"]))
    errors = alignment_errors(book, spine, phrases, reverse)
    if errors: raise WorkflowError("Final check blocked by alignment:\n- " + "\n- ".join(errors))
    ok, errors = g0b_status(root, book, paths)
    if not ok: raise WorkflowError("Final check blocked by G0B:\n- " + "\n- ".join(errors))
    inv_ok, inv = investigation_status(paths)
    if not inv_ok: raise WorkflowError("Final check blocked by investigations:\n- " + "\n- ".join(inv["open"] + inv["invalid"]))
    path = Path(paths["final_reviews"]); history = load_history(path, book, "reviews")
    reviewer = args.reviewed_by.strip()
    if not reviewer: raise WorkflowError("--reviewed-by is required")
    review = {"id": f"BFR-{len(history['reviews'])+1:04d}", "status": "PASS", "workflow_version": WORKFLOW_VERSION,
              "reviewed_by": reviewer, "reviewed_at": now_iso(), "human_consistency_review_confirmed": True,
              "investigations": inv, "artifacts": current_bindings(root, paths), "notes": args.notes.strip()}
    history["reviews"].append(review); save_yaml(path, history); print(f"Recorded {review['id']}: {relative(root, path)}"); return 0


def cmd_approve(args) -> int:
    if not args.confirm: raise WorkflowError("Final approval is human authority; use --confirm")
    root, book = Path(args.root).resolve(), normalize_book(args.book); paths = resolve_paths(root, book)
    review, errors = latest_final_review(root, book, paths)
    if errors or review is None: raise WorkflowError("Approval blocked by final review:\n- " + "\n- ".join(errors))
    identity = {"edition": safe_component(args.edition, "edition"), "book_release_version": safe_component(args.book_version, "book version"),
                "source_identity": load_json(Path(paths["spine"])).get("textualBasis") or "declared-source-spine",
                "source_revision": safe_component(args.source_revision, "source revision"),
                "translation_revision": safe_component(args.translation_revision, "translation revision"),
                "alignment_revision": safe_component(args.alignment_revision, "alignment revision")}
    approver = args.approved_by.strip()
    if not approver: raise WorkflowError("--approved-by is required")
    path = Path(paths["approvals"]); history = load_history(path, book, "approvals")
    approval = {"id": f"APP-{len(history['approvals'])+1:04d}", "status": "TRANSLATION_APPROVED", "authority": "human",
                "approved_by": approver, "approved_at": now_iso(), "workflow_version": WORKFLOW_VERSION,
                "release_identity": identity, "final_review_id": review["id"], "final_review_digest": stable_digest(review),
                "artifacts": current_bindings(root, paths), "notes": args.notes.strip()}
    history["approvals"].append(approval); save_yaml(path, history); print(f"Recorded {approval['id']}: {relative(root, path)}"); return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="book-workflow"); p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help=argparse.SUPPRESS); sub = p.add_subparsers(dest="command", required=True)
    for name, func in (("status", cmd_status), ("queue-g0a", cmd_queue_g0a), ("queue-g0b", cmd_queue_g0b)):
        q = sub.add_parser(name); q.add_argument("book"); q.set_defaults(func=func)
    q = sub.add_parser("promote-g0a"); q.add_argument("book"); q.add_argument("--apply", action="store_true"); q.set_defaults(func=cmd_promote_g0a)
    q = sub.add_parser("final-check"); q.add_argument("book"); q.add_argument("--reviewed-by", required=True); q.add_argument("--notes", default=""); q.add_argument("--confirm", action="store_true"); q.set_defaults(func=cmd_final_check)
    q = sub.add_parser("approve"); q.add_argument("book"); q.add_argument("--approved-by", required=True); q.add_argument("--edition", required=True); q.add_argument("--book-version", required=True); q.add_argument("--source-revision", required=True); q.add_argument("--translation-revision", required=True); q.add_argument("--alignment-revision", required=True); q.add_argument("--notes", default=""); q.add_argument("--confirm", action="store_true"); q.set_defaults(func=cmd_approve)
    return p


def main() -> int:
    args = parser().parse_args()
    try: return int(args.func(args) or 0)
    except WorkflowError as exc: print(f"BLOCKED: {exc}", file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
