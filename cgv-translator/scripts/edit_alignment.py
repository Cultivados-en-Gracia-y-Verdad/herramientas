#!/usr/bin/env python3
"""Edit one reverse-alignment unit while enforcing targeted G0B invalidation.

This command owns alignment mutation only. It never changes Spanish, G0A state,
or translation approval. When source-token evidence changes, the affected unit
and containing link are marked needs-review so G0B must verify them again.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


def apply_source_token_edit(reverse_doc: dict, reference: str, unit_id: str, source_token_ids: list[str]) -> bool:
    links = reverse_doc.get("links")
    if not isinstance(links, list):
        raise ValueError("Invalid reverse-link artifact: links[] is required")

    for link in links:
        if not isinstance(link, dict) or str(link.get("reference") or "") != reference:
            continue
        units = link.get("units")
        if not isinstance(units, list):
            raise ValueError(f"Invalid reverse-link record for {reference}: units[] is required")
        for unit in units:
            if not isinstance(unit, dict) or str(unit.get("unitId") or "") != unit_id:
                continue
            previous = [str(value) for value in unit.get("sourceTokenIds", [])]
            next_ids = [str(value) for value in source_token_ids]
            if previous == next_ids:
                return False

            unit["sourceTokenIds"] = next_ids
            unit["status"] = "needs-review"
            # Preserve generation/edit method as provenance; verification status
            # is independent from how the alignment was produced.
            link["status"] = "needs-review"
            return True
        raise ValueError(f"Alignment unit not found: {reference} / {unit_id}")
    raise ValueError(f"Alignment reference not found: {reference}")


def token_index(spine_doc: dict) -> dict[str, str]:
    index: dict[str, str] = {}
    for cv, verse in (spine_doc.get("verses") or {}).items():
        for token in (verse or {}).get("tokens", []):
            token_id = str((token or {}).get("sourceTokenId") or "")
            if token_id:
                index[token_id] = str(cv)
    return index


def validate_tokens_for_link(spine_doc: dict, reverse_doc: dict, reference: str, token_ids: list[str]) -> None:
    idx = token_index(spine_doc)
    unknown = [token_id for token_id in token_ids if token_id not in idx]
    if unknown:
        raise ValueError(f"Unknown source token IDs: {', '.join(unknown)}")

    link = next((item for item in reverse_doc.get("links", []) if item.get("reference") == reference), None)
    if not link:
        raise ValueError(f"Alignment reference not found: {reference}")
    mt_reference = str(link.get("mtReference") or reference)
    cv = mt_reference.rsplit(" ", 1)[-1]
    wrong_verse = [token_id for token_id in token_ids if idx.get(token_id) != cv]
    if wrong_verse:
        raise ValueError(
            f"Source token IDs outside {mt_reference}: {', '.join(wrong_verse)}"
        )


def parse_tokens(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if len(values) != len(set(values)):
        raise ValueError("Duplicate source token IDs are not allowed")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit one alignment unit and reopen only affected G0B")
    parser.add_argument("--book", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--unit", required=True, dest="unit_id")
    parser.add_argument("--tokens", required=True, help="comma-separated sourceTokenIds; empty string clears the link")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    book = args.book.strip().lower()
    base = root / "translations" / "oshb-spine" / book
    reverse_path = base / f"{book}-reverse-links.json"
    spine_path = base / f"{book}-oshb-spine.json"
    if not reverse_path.is_file():
        raise SystemExit(f"Reverse-link artifact missing: {reverse_path}")
    if not spine_path.is_file():
        raise SystemExit(f"OSHB spine missing: {spine_path}")

    reverse_doc = json.loads(reverse_path.read_text(encoding="utf-8"))
    spine_doc = json.loads(spine_path.read_text(encoding="utf-8"))
    token_ids = parse_tokens(args.tokens)
    validate_tokens_for_link(spine_doc, reverse_doc, args.reference, token_ids)

    candidate = deepcopy(reverse_doc)
    changed = apply_source_token_edit(candidate, args.reference, args.unit_id, token_ids)
    if not changed:
        print("UNCHANGED: alignment evidence is identical; G0B state preserved")
        return 0

    print(f"CHANGED: {args.reference} / {args.unit_id}")
    print("G0A: unchanged")
    print("G0B: needs-review for affected link")
    if args.dry_run:
        print("DRY RUN: artifact not written")
        return 0

    reverse_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(reverse_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
