#!/usr/bin/env python3
"""Finalize the investigation workflow invariants discovered during Daniel regression work.

This is deliberately a guarded source migration, not an investigation-data migration.
It changes application behavior only and does not rewrite existing investigation records.

Dry-run by default. Use --apply to write the checked transformations.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from apply_investigation_scope_patch import (
    ROOT,
    patch_analyze_gates,
    patch_assist_gates,
    patch_create_investigation,
    patch_index,
    patch_server,
    patch_main as patch_main_scope,
    replace_exact,
)


def patch_main(text: str) -> str:
    text = patch_main_scope(text)
    old = '''[
  decisionStatus,
  decisionEffectiveDate,
  decisionRendering,
  decisionConfidence,
  decisionReason
].forEach(control => {
'''
    new = '''[
  decisionStatus,
  decisionEffectiveDate,
  decisionRendering,
  decisionConfidence,
  decisionScope,
  decisionScopeReference,
  decisionScopeCondition,
  decisionReason
].forEach(control => {
'''
    return replace_exact(text, old, new, "main scope dirty tracking")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply checked migration. Default is dry-run.")
    args = parser.parse_args()

    targets = [
        (ROOT / "public" / "index.html", patch_index),
        (ROOT / "public" / "main.js", patch_main),
        (ROOT / "server.js", patch_server),
        (ROOT / "src" / "investigations" / "createInvestigation.js", patch_create_investigation),
        (ROOT / "src" / "pipeline" / "analyzeGates.js", patch_analyze_gates),
        (ROOT / "src" / "pipeline" / "assistGates.js", patch_assist_gates),
    ]

    prepared = []
    print("INVESTIGATION WORKFLOW FINALIZATION")
    for path, patcher in targets:
        original = path.read_text(encoding="utf-8")
        updated = patcher(original)
        if updated == original:
            raise RuntimeError(f"{path.relative_to(ROOT)}: migration produced no change")
        prepared.append((path, updated))
        print(f"CHECKED {path.relative_to(ROOT)}")

    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply after review.")
        return 0

    for path, updated in prepared:
        path.write_text(updated, encoding="utf-8")
        print(f"UPDATED {path.relative_to(ROOT)}")

    print("PASS: scope, approval, precedence, creation defaults, and dirty tracking are finalized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
