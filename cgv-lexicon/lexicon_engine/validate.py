"""Validate Phase 1 Greek lexicon build output."""

from __future__ import annotations

import json
from pathlib import Path


def validate_lemma_record(data: dict, path: Path) -> list[str]:
    errors: list[str] = []
    if not data.get("lemma"):
        errors.append(f"{path}: missing lemma")
    total = data.get("total_occurrences")
    if total is None:
        errors.append(f"{path}: missing total_occurrences")
    elif total != len(data.get("references") or []):
        errors.append(
            f"{path}: total_occurrences ({total}) != references length ({len(data.get('references') or [])})"
        )
    for i, ref in enumerate(data.get("references") or []):
        if not ref.get("ref"):
            errors.append(f"{path}: references[{i}] missing ref")
    return errors


def validate_index(index: dict, lemma_dir: Path) -> list[str]:
    errors: list[str] = []
    if not index.get("lemmas"):
        errors.append("index.json: empty lemmas list")
    for entry in index.get("lemmas") or []:
        if not entry.get("lemma"):
            errors.append("index.json: entry missing lemma")
        fname = entry.get("file")
        if not fname:
            errors.append(f"index.json: entry {entry.get('lemma')} missing file")
        elif not (lemma_dir / fname).is_file():
            errors.append(f"index.json: missing file {fname}")
    return errors


def load_and_validate_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh), None
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc}"
