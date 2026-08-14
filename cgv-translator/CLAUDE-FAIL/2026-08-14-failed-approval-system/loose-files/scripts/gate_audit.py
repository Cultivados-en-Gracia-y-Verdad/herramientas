#!/usr/bin/env python3
"""
Deterministic Gate 0 audit. No AI. No network. No judgement.

Purpose
-------
Decide mechanically everything that can be decided mechanically, and REFUSE anything
suspect, so that human review is spent only on faithfulness questions that genuinely
require a person.

This script never approves anything. It emits FAIL / WARN / PASS per check and a
worklist of items a human must judge. WORKFLOW.md §15: production is not verification.

Checks
------
STRUCTURE   spans, token references, coverage, tautological whole-verse units
POLICY      gate0-policy.yaml conformance (allowed methods, minimum status)
EVIDENCE    rubber-stamp detection: templated/duplicated review evidence
INDEPENDENCE producer identity vs reviewer identity (§15)
BINDING     queue/report checksums against the current artifacts

Exit code is non-zero if any FAIL is present.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

FAIL, WARN, PASS = "FAIL", "WARN", "PASS"


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, str]] = []

    def add(self, level: str, area: str, check: str, detail: str = "") -> None:
        self.rows.append((level, area, check, detail))

    def render(self) -> int:
        width = max(len(r[2]) for r in self.rows) if self.rows else 10
        order = {FAIL: 0, WARN: 1, PASS: 2}
        for level, area, check, detail in sorted(self.rows, key=lambda r: (order[r[0]], r[1])):
            line = f"{level:<5} {area:<12} {check:<{width}}"
            print(line + (f"  {detail}" if detail else ""))
        fails = sum(1 for r in self.rows if r[0] == FAIL)
        warns = sum(1 for r in self.rows if r[0] == WARN)
        print(f"\n{fails} FAIL, {warns} WARN, {sum(1 for r in self.rows if r[0] == PASS)} PASS")
        return 1 if fails else 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def audit_structure(rep: Report, phrases: dict, spine: dict, links: dict) -> list[str]:
    spanish = {p["reference"]: p["spanish"] for p in phrases["phrases"]}
    tokens_of = {p["reference"]: list(p["sourceTokenIds"]) for p in phrases["phrases"]}
    spine_ids = {str(t.get("sourceTokenId")) for v in spine.get("verses", {}).values()
                 for t in v.get("tokens", []) if t.get("sourceTokenId")}

    missing_verses = sorted(set(spanish) - {l["reference"] for l in links["links"]})
    rep.add(FAIL if missing_verses else PASS, "STRUCTURE", "every verse has alignment",
            f"{len(missing_verses)} missing" if missing_verses else "")

    span_bad, tok_bad, overlap, tautology, unassigned = [], [], [], [], []
    for link in links["links"]:
        ref = link["reference"]
        text = spanish.get(ref, "")
        seen: set[str] = set()
        prev_end = -1
        for u in link["units"]:
            s, e = u.get("charStart"), u.get("charEnd")
            if not isinstance(s, int) or not isinstance(e, int) or not (0 <= s <= e <= len(text)) \
               or text[s:e] != u.get("surface"):
                span_bad.append(f"{ref}:{u.get('unitId')}")
            if s is not None and s < prev_end:
                overlap.append(f"{ref}:{u.get('unitId')}")
            prev_end = e if isinstance(e, int) else prev_end
            for t in u.get("sourceTokenIds", []):
                if t not in spine_ids:
                    tok_bad.append(f"{ref}:{t}")
                seen.add(t)
        # a single unit covering the whole verse and every token carries no information
        if len(link["units"]) == 1:
            u = link["units"][0]
            if u.get("charStart") == 0 and u.get("charEnd") == len(text) \
               and set(u.get("sourceTokenIds", [])) == set(tokens_of.get(ref, [])):
                tautology.append(ref)
        miss = [t for t in tokens_of.get(ref, []) if t not in seen]
        if miss:
            unassigned.append(f"{ref}({len(miss)})")

    rep.add(FAIL if span_bad else PASS, "STRUCTURE", "char spans match phrase text",
            f"{len(span_bad)} bad: {span_bad[:4]}" if span_bad else "")
    rep.add(FAIL if tok_bad else PASS, "STRUCTURE", "source tokens exist in spine",
            f"{len(tok_bad)} invalid" if tok_bad else "")
    rep.add(WARN if overlap else PASS, "STRUCTURE", "units do not overlap",
            f"{len(overlap)} overlapping" if overlap else "")
    rep.add(WARN if unassigned else PASS, "STRUCTURE", "all source tokens assigned",
            f"{len(unassigned)} verses leave tokens unlinked" if unassigned else "")
    rep.add(FAIL if tautology else PASS, "STRUCTURE", "no whole-verse tautology (WORKFLOW §10)",
            f"{len(tautology)} verses are one unit covering the whole verse and all tokens"
            if tautology else "")
    return tautology


def audit_policy(rep: Report, links: dict, policy: dict) -> None:
    rl = policy.get("reverse_link_policy", {})
    allowed = set(rl.get("allowed_methods", []))
    minimum = rl.get("minimum_status")
    methods = collections.Counter(u.get("method") for l in links["links"] for u in l["units"])
    statuses = collections.Counter(u.get("status") for l in links["links"] for u in l["units"])
    bad_m = {m: c for m, c in methods.items() if m not in allowed}
    bad_s = {s: c for s, c in statuses.items() if s != minimum}
    rep.add(FAIL if bad_m else PASS, "POLICY", "link methods are permitted",
            f"disallowed: {bad_m}" if bad_m else "")
    rep.add(FAIL if bad_s else PASS, "POLICY", f"unit status is '{minimum}'",
            f"below minimum: {bad_s}" if bad_s else "")


def audit_evidence(rep: Report, gate0: Path) -> None:
    """Rubber-stamp detection: a review whose evidence is templated is not a review."""
    worst = None
    for f in sorted(gate0.glob("review-results/*.yaml")) + sorted(gate0.glob("queues/*.yaml")):
        doc = load_yaml(f)
        items = doc.get("items", [])
        texts = []
        for i in items:
            ev = i.get("evidence") if "evidence" in i else i.get("review", {}).get("evidence", "")
            dec = i.get("decision") or i.get("review", {}).get("decision")
            if dec in ("APPROVED", "VERIFIED") and str(ev or "").strip():
                texts.append(str(ev).strip())
        if len(texts) < 20:
            continue
        distinct = len(set(texts))
        ratio = distinct / len(texts)
        if worst is None or ratio < worst[1]:
            worst = (f.name, ratio, distinct, len(texts))
        if ratio < 0.10:
            rep.add(FAIL, "EVIDENCE", "review evidence is not templated",
                    f"{f.name}: {distinct} distinct strings across {len(texts)} approvals")
    if worst and worst[1] >= 0.10:
        rep.add(PASS, "EVIDENCE", "review evidence is not templated",
                f"lowest diversity {worst[0]}: {worst[2]}/{worst[3]}")


def audit_independence(rep: Report, gate0: Path, workflow_dir: Path) -> None:
    """WORKFLOW.md §15 — the producer must not be the sole verifier of its own output."""
    edits = workflow_dir / "lexical-edits.jsonl"
    if not edits.is_file():
        rep.add(PASS, "INDEPENDENCE", "producer is not sole verifier", "no scripted edits recorded")
        return
    produced: set[str] = set()
    for line in edits.read_text(encoding="utf-8").splitlines():
        produced.update(json.loads(line).get("changedReferences", []))

    reviewers: dict[str, set[str]] = collections.defaultdict(set)
    for f in gate0.glob("evidence/*.yaml"):
        for i in load_yaml(f).get("items", []):
            r = i.get("review", {})
            if r.get("decision") == "APPROVED" and i.get("reference") in produced:
                reviewers[i["reference"]].add(str(r.get("reviewer")))

    solo = {ref: revs for ref, revs in reviewers.items() if len(revs) == 1}
    rep.add(FAIL if solo else PASS, "INDEPENDENCE", "producer is not sole verifier (§15)",
            f"{len(solo)} scripted-edit verses reviewed by a single reviewer: "
            f"{sorted({r for revs in solo.values() for r in revs})}" if solo else "")


def audit_binding(rep: Report, gate0: Path, book: str, phrases: Path, spine: Path, links: Path) -> None:
    report = gate0 / "reports" / f"{book}-g0a-promotion-report.yaml"
    if report.is_file():
        doc = load_yaml(report)
        ok = doc.get("artifacts", {}).get("phrases_sha256_after") == sha256(phrases)
        rep.add(PASS if ok else FAIL, "BINDING", "G0A report matches current phrases",
                "" if ok else "report is bound to different bytes")
    q = gate0 / "queues" / f"{book}-g0b-alignment-review.yaml"
    if q.is_file():
        a = load_yaml(q).get("queue", {}).get("artifacts", {})
        for key, path in (("phrases", phrases), ("reverse_links", links), ("spine", spine)):
            declared = a.get(key, {}).get("checksum_sha256")
            if declared:
                ok = declared == sha256(path)
                rep.add(PASS if ok else FAIL, "BINDING", f"G0B queue matches current {key}",
                        "" if ok else "stale")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--reverse-links", help="override the alignment file to audit")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    base = root / "translations" / "oshb-spine" / args.book
    phrases_p = base / f"{args.book}-phrases.json"
    spine_p = base / f"{args.book}-oshb-spine.json"
    links_p = Path(args.reverse_links) if args.reverse_links else base / f"{args.book}-reverse-links.json"
    gate0 = root / "gate0"

    rep = Report()
    phrases, spine, links = load_json(phrases_p), load_json(spine_p), load_json(links_p)

    taut = audit_structure(rep, phrases, spine, links)
    audit_policy(rep, links, load_yaml(gate0 / "gate0-policy.yaml"))
    audit_evidence(rep, gate0)
    audit_independence(rep, gate0, root / "workflow" / args.book)
    audit_binding(rep, gate0, args.book, phrases_p, spine_p, links_p)

    print(f"GATE 0 DETERMINISTIC AUDIT — {args.book}   (alignment: {links_p.name})\n")
    code = rep.render()
    units = sum(len(l["units"]) for l in links["links"])
    print(f"\nHuman worklist: {units} alignment units require a faithfulness judgement.")
    print(f"Of these, {sum(1 for l in links['links'] if len(l['units']) == 1)} verses "
          f"are still single-unit ({len(taut)} tautological).")
    print("This script approves nothing. WORKFLOW.md §15.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
