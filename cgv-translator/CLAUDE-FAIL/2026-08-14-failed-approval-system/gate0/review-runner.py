#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import yaml

G0A_ALLOWED = {"PENDING", "APPROVED", "NEEDS_REVISION", "REJECTED", "ESCALATE"}
G0B_ALLOWED = {"PENDING", "VERIFIED", "NEEDS_RELINK", "REJECTED", "ESCALATE"}

TERMINAL_G0A = {"APPROVED", "NEEDS_REVISION", "REJECTED", "ESCALATE"}
TERMINAL_G0B = {"VERIFIED", "NEEDS_RELINK", "REJECTED", "ESCALATE"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def gate_of(queue):
    return queue.get("queue", {}).get("gate")


def allowed_decisions(queue):
    gate = gate_of(queue)
    if gate == "G0A_TRANSLATION_APPROVAL":
        return G0A_ALLOWED
    if gate == "G0B_ALIGNMENT_VERIFICATION":
        return G0B_ALLOWED
    raise ValueError(f"Unsupported queue gate: {gate}")


def terminal_decisions(queue):
    gate = gate_of(queue)
    if gate == "G0A_TRANSLATION_APPROVAL":
        return TERMINAL_G0A
    if gate == "G0B_ALIGNMENT_VERIFICATION":
        return TERMINAL_G0B
    raise ValueError(f"Unsupported queue gate: {gate}")


def recompute_summary(queue):
    gate = gate_of(queue)
    items = queue.get("items", [])

    approved_or_verified = 0
    pending = 0
    needs = 0
    rejected = 0
    escalated = 0

    for item in items:
        decision = item.get("review", {}).get("decision", "PENDING")
        if decision == "PENDING":
            pending += 1
        elif gate == "G0A_TRANSLATION_APPROVAL" and decision == "APPROVED":
            approved_or_verified += 1
        elif gate == "G0B_ALIGNMENT_VERIFICATION" and decision == "VERIFIED":
            approved_or_verified += 1
        elif decision in {"NEEDS_REVISION", "NEEDS_RELINK"}:
            needs += 1
        elif decision == "REJECTED":
            rejected += 1
        elif decision == "ESCALATE":
            escalated += 1

    queue["summary"] = {
        "total": len(items),
        "approved_or_verified": approved_or_verified,
        "pending": pending,
        "needs_revision_or_relink": needs,
        "rejected": rejected,
        "escalated": escalated,
    }

    if pending == 0 and needs == 0 and rejected == 0 and escalated == 0:
        queue["queue"]["status"] = "PASS"
    elif pending == 0:
        queue["queue"]["status"] = "REVIEW_REQUIRED"
    else:
        queue["queue"]["status"] = "OPEN"


def select_batch(queue, batch_size, start_after=None):
    items = queue.get("items", [])
    pending = [i for i in items if i.get("review", {}).get("decision", "PENDING") == "PENDING"]

    if start_after:
        found = False
        filtered = []
        for item in pending:
            if found:
                filtered.append(item)
            elif item.get("id") == start_after:
                found = True
        pending = filtered

    return pending[:batch_size]


def packet_item(item, gate):
    if gate == "G0A_TRANSLATION_APPROVAL":
        return {
            "id": item.get("id"),
            "reference": item.get("reference"),
            "mt_reference": item.get("mt_reference"),
            "spanish": item.get("spanish"),
            "source_tokens": item.get("source_tokens", []),
            "current_status": item.get("current_status"),
            "decision": "PENDING",
            "evidence": "",
            "notes": "",
        }

    return {
        "id": item.get("id"),
        "reference": item.get("reference"),
        "mt_reference": item.get("mt_reference"),
        "unitId": item.get("unitId"),
        "spanish_unit": item.get("spanish_unit"),
        "actual_phrase_slice": item.get("actual_phrase_slice"),
        "char_start": item.get("char_start"),
        "char_end": item.get("char_end"),
        "source_tokens": item.get("source_tokens", []),
        "current_method": item.get("current_method"),
        "current_status": item.get("current_status"),
        "decision": "PENDING",
        "evidence": "",
        "notes": "",
    }


def make_packet(queue, batch_size, start_after=None):
    gate = gate_of(queue)
    items = select_batch(queue, batch_size, start_after)

    return {
        "schema_version": "0.1",
        "packet": {
            "queue_id": queue.get("queue", {}).get("id"),
            "gate": gate,
            "book": queue.get("queue", {}).get("book"),
            "created_at": now_iso(),
            "batch_size": len(items),
            "source_queue_artifacts": deepcopy(queue.get("queue", {}).get("artifacts", {})),
        },
        "review_instructions": {
            "G0A_TRANSLATION_APPROVAL": (
                "Review each Spanish phrase against the supplied source-token evidence. "
                "Use APPROVED only when the phrase is defensible and complete. "
                "Use NEEDS_REVISION when correction is required, REJECTED for unusable output, "
                "and ESCALATE when judgment requires a stronger specialist/human decision."
            ),
            "G0B_ALIGNMENT_VERIFICATION": (
                "Review whether each Spanish unit corresponds to the supplied source tokens. "
                "Use VERIFIED only when the link is defensible. Use NEEDS_RELINK for incorrect "
                "token relationships, REJECTED for unusable units, and ESCALATE for unresolved ambiguity."
            ),
        }[gate],
        "items": [packet_item(item, gate) for item in items],
    }


def validate_result_packet(queue, result):
    errors = []
    expected_gate = gate_of(queue)
    packet = result.get("packet", {})

    if packet.get("gate") != expected_gate:
        errors.append("Result packet gate does not match queue gate.")
    if packet.get("queue_id") != queue.get("queue", {}).get("id"):
        errors.append("Result packet queue_id does not match queue.")

    allowed = allowed_decisions(queue)
    seen = set()

    queue_ids = {i.get("id") for i in queue.get("items", [])}

    for item in result.get("items", []):
        iid = item.get("id")
        decision = item.get("decision")

        if iid not in queue_ids:
            errors.append(f"Unknown review item: {iid}")
        if iid in seen:
            errors.append(f"Duplicate review result: {iid}")
        seen.add(iid)

        if decision not in allowed or decision == "PENDING":
            errors.append(f"{iid}: invalid final decision {decision!r}")

        if decision in {"APPROVED", "VERIFIED"} and not str(item.get("evidence", "")).strip():
            errors.append(f"{iid}: approval/verification requires evidence.")

        if decision in {"NEEDS_REVISION", "NEEDS_RELINK", "REJECTED", "ESCALATE"}:
            if not str(item.get("notes", "")).strip():
                errors.append(f"{iid}: {decision} requires notes.")

    return errors


def apply_results(queue, result, reviewer, runtime, model):
    errors = validate_result_packet(queue, result)
    if errors:
        raise ValueError("Review result rejected:\n- " + "\n- ".join(errors))

    by_id = {i["id"]: i for i in queue.get("items", [])}

    for r in result.get("items", []):
        item = by_id[r["id"]]
        review = item.setdefault("review", {})
        review["decision"] = r["decision"]
        review["reviewer"] = reviewer
        review["runtime"] = runtime
        review["model"] = model
        review["confidence"] = r.get("confidence")
        review["evidence"] = r.get("evidence", "")
        review["notes"] = r.get("notes", "")
        review["reviewed_at"] = now_iso()

    queue.setdefault("history", []).append({
        "timestamp": now_iso(),
        "reviewer": reviewer,
        "runtime": runtime,
        "model": model,
        "item_ids": [r["id"] for r in result.get("items", [])],
    })

    recompute_summary(queue)


def cmd_packet(args):
    qpath = Path(args.queue)
    queue = load_yaml(qpath)
    packet = make_packet(queue, args.batch_size, args.start_after)

    out = Path(args.out) if args.out else qpath.with_name(
        qpath.stem + f"-packet-{packet['packet']['created_at'].replace(':','').replace('+','_')}.yaml"
    )
    save_yaml(out, packet)

    print(out)
    print(f"gate: {packet['packet']['gate']}")
    print(f"items: {len(packet['items'])}")


def cmd_apply(args):
    qpath = Path(args.queue)
    rpath = Path(args.results)

    queue = load_yaml(qpath)
    result = load_yaml(rpath)

    apply_results(
        queue,
        result,
        reviewer=args.reviewer,
        runtime=args.runtime,
        model=args.model,
    )
    save_yaml(qpath, queue)

    print(f"Updated: {qpath}")
    for k, v in queue["summary"].items():
        print(f"{k}: {v}")
    print(f"queue_status: {queue['queue']['status']}")


def cmd_status(args):
    queue = load_yaml(Path(args.queue))
    recompute_summary(queue)
    print(f"queue: {queue['queue']['id']}")
    print(f"gate: {queue['queue']['gate']}")
    print(f"status: {queue['queue']['status']}")
    for k, v in queue["summary"].items():
        print(f"{k}: {v}")


def cmd_validate(args):
    queue = load_yaml(Path(args.queue))
    allowed = allowed_decisions(queue)
    errors = []

    for item in queue.get("items", []):
        iid = item.get("id")
        decision = item.get("review", {}).get("decision", "PENDING")
        if decision not in allowed:
            errors.append(f"{iid}: invalid decision {decision!r}")

    if errors:
        print("INVALID")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("VALID")


def build_parser():
    ap = argparse.ArgumentParser(prog="review-runner")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("packet")
    p.add_argument("--queue", required=True)
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--start-after")
    p.add_argument("--out")
    p.set_defaults(func=cmd_packet)

    p = sub.add_parser("apply")
    p.add_argument("--queue", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--model", required=True)
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("status")
    p.add_argument("--queue", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("validate")
    p.add_argument("--queue", required=True)
    p.set_defaults(func=cmd_validate)

    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
