#!/usr/bin/env python3
from __future__ import annotations

"""
ROOTS — local connector registry

Purpose:
- inventory local connector evidence
- keep connectors subordinate to already-established clause structure
- support later Paso 9 label evidence without assigning labels here

This layer records ONLY local observable connector evidence.

Current scope:
- local Paso 9 evidence only
- no Paso 4–8 rebuilding
- no macro-structure
- no clause ownership expansion
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

# Canonical, accentless connector forms.
# Original surface form is preserved separately in output.
CONNECTOR_MAP = {
    "και": ("coordinating", "coordination"),
    "δε": ("coordinating", "coordination"),
    "αλλα": ("adversative", "coordination"),
    "ουδε": ("coordinating", "coordination"),
    "μηδε": ("coordinating", "coordination"),
    "η": ("coordinating", "coordination"),
    "γαρ": ("explanatory", "support"),
    "οτι": ("explanatory", "subordination"),
    "διο": ("inferential", "result"),
    "διοτι": ("explanatory", "support"),
    "ωστε": ("inferential", "result"),
    "ουν": ("inferential", "result"),
    "ινα": ("purpose", "subordination"),
    "ει": ("conditional", "subordination"),
    "εαν": ("conditional", "subordination"),
    "οταν": ("temporal", "subordination"),
    "ως": ("comparative", "subordination"),
    "καθως": ("comparative", "subordination"),
}

TEXT_FIELDS = [
    "greek",
    "greek_text",
    "clause_greek",
    "text_greek",
    "surface",
    "clause_text",
    "sentence_greek",
    "finite_clause_greek",
    "context_greek",
    "raw_greek",
    "sblgnt",
]

TOKEN_ARRAY_FIELDS = [
    "tokens",
    "greek_tokens",
    "g_tokens",
    "clause_tokens",
    "source_tokens",
]

TOKEN_DICT_FIELDS = [
    "text",
    "surface",
    "greek",
    "token",
    "word",
    "form",
]


def mna_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: int(row.get("stream_index") or row.get("predication_index") or row.get("id") or 0))


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_token(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^[\s\W_]+|[\s\W_]+$", "", text, flags=re.UNICODE)
    text = strip_diacritics(text)
    return text


def clean_surface(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[\s\W_]+|[\s\W_]+$", "", text, flags=re.UNICODE)
    return text


def collect_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(collect_strings(item))
    elif isinstance(value, dict):
        for key in TOKEN_DICT_FIELDS:
            if key in value:
                strings.extend(collect_strings(value[key]))
    return strings


def token_candidates(row: dict[str, Any]) -> list[str]:
    tokens: list[str] = []

    for field in TEXT_FIELDS:
        value = row.get(field)
        if isinstance(value, str):
            tokens.extend(value.split())

    for field in TOKEN_ARRAY_FIELDS:
        value = row.get(field)
        for string in collect_strings(value):
            tokens.extend(string.split())

    # Last-resort nested scan, restricted to Greek-looking strings.
    for value in row.values():
        for string in collect_strings(value):
            if re.search(r"[α-ωΑ-Ω]", string):
                tokens.extend(string.split())

    return tokens


def find_connectors(row: dict[str, Any]) -> list[dict[str, str]]:
    """Return one connector hit per normalized connector per predication row.

    Upstream rows may contain both accented and accentless versions of the
    same connector in nested fields. We preserve the first observed original
    surface but deduplicate by canonical normalized form so counts are not
    inflated.
    """
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    for token in token_candidates(row):
        surface_original = clean_surface(token)
        normalized = normalize_token(token)

        if normalized not in CONNECTOR_MAP:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        found.append({
            "surface_original": surface_original,
            "normalized": normalized,
        })

    return found


def link_direction(connector: str) -> str:
    if connector in {"γαρ", "διο", "διοτι", "ουν", "ωστε"}:
        return "backward_local"
    if connector in {"ινα", "ει", "εαν", "οταν", "ως", "καθως", "οτι"}:
        return "forward_or_embedded_local"
    return "parallel_local"


def build_registry(predications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = ordered(predications)
    registry: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        connectors = find_connectors(row)
        previous_row = rows[idx - 1] if idx > 0 else None
        next_row = rows[idx + 1] if idx + 1 < len(rows) else None

        for occurrence_index, connector_hit in enumerate(connectors, start=1):
            connector = connector_hit["normalized"]
            connector_class, dependency_type = CONNECTOR_MAP[connector]
            direction = link_direction(connector)
            source = previous_row if direction in {"backward_local", "parallel_local"} else row
            target = row if direction in {"backward_local", "parallel_local"} else next_row

            registry.append({
                "connector_registry_id": f"CN{len(registry)+1:05d}",
                "book": row.get("book"),
                "chapter": row.get("chapter"),
                "verse": row.get("verse"),
                "reference": f"{row.get('chapter')}:{row.get('verse')}",
                "stream_index": row.get("stream_index"),
                "predication_id": row.get("predication_id"),
                "connector_occurrence_index": occurrence_index,
                "connector_surface_original": connector_hit["surface_original"],
                "connector_surface": connector,
                "connector_lemma": connector,
                "connector_class": connector_class,
                "dependency_type": dependency_type,
                "direction": direction,
                "source_predication_id": source.get("predication_id") if source else None,
                "target_predication_id": target.get("predication_id") if target else None,
                "source_reference": f"{source.get('chapter')}:{source.get('verse')}" if source else None,
                "target_reference": f"{target.get('chapter')}:{target.get('verse')}" if target else None,
                "explicit_connector": True,
                "scope_status": "local_candidate",
                "label_support_status": "not_assigned_here",
            })

    return registry


def build_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters = {
        "connector_surface": Counter(str(row.get("connector_surface")) for row in rows),
        "connector_class": Counter(str(row.get("connector_class")) for row in rows),
        "dependency_type": Counter(str(row.get("dependency_type")) for row in rows),
        "direction": Counter(str(row.get("direction")) for row in rows),
    }
    summary: list[dict[str, Any]] = []
    for summary_type, counter in counters.items():
        for name, count in sorted(counter.items()):
            summary.append({"summary_type": summary_type, "name": name, "count": count})
    return summary


def build_diagnostics(rows: list[dict[str, Any]], in_path: Path) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for idx, row in enumerate(rows[:10], start=1):
        keys = sorted(str(k) for k in row.keys())
        sample_tokens = token_candidates(row)[:25]
        diagnostics.append({
            "input_path": str(in_path),
            "sample_row": idx,
            "keys": json.dumps(keys, ensure_ascii=False),
            "sample_tokens": json.dumps(sample_tokens, ensure_ascii=False),
            "connector_hits": json.dumps(find_connectors(row), ensure_ascii=False),
        })
    return diagnostics


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def find_input_path(book: str) -> Path:
    root = mna_root()
    candidates = [
        root / "data" / "predications" / f"{book}-predications.jsonl",
        root / "data" / "independent-stream" / f"{book}-independent-stream.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No connector input found. Tried:\n" + "\n".join(str(p) for p in candidates))


def process_book(book: str) -> tuple[int, Path, Path, Path, Path, Path]:
    in_path = find_input_path(book)
    rows = read_jsonl(in_path)
    registry = build_registry(rows)
    summary = build_summary(registry)
    diagnostics = build_diagnostics(rows, in_path) if not registry else []

    out_dir = mna_root() / "data" / "connectors"
    jsonl_out = out_dir / f"{book}-connector-registry.jsonl"
    tsv_out = out_dir / f"{book}-connector-registry.tsv"
    summary_out = out_dir / f"{book}-connector-summary.tsv"
    diagnostics_out = out_dir / f"{book}-connector-diagnostics.tsv"

    write_jsonl(jsonl_out, registry)
    write_tsv(tsv_out, registry)
    write_tsv(summary_out, summary)
    write_tsv(diagnostics_out, diagnostics)

    return len(registry), in_path, jsonl_out, tsv_out, summary_out, diagnostics_out


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 MNA/scripts/roots_build_connector_registry.py <book>", file=sys.stderr)
        sys.exit(2)

    book = sys.argv[1].lower()
    count, in_path, jsonl_out, tsv_out, summary_out, diagnostics_out = process_book(book)

    print(f"read: {in_path}")
    print(f"connector_occurrences = {count}")
    print(f"wrote: {jsonl_out}")
    print(f"wrote: {tsv_out}")
    print(f"wrote: {summary_out}")
    if count == 0:
        print(f"wrote diagnostics: {diagnostics_out}")
        print("No connectors found. Inspect diagnostics to see the actual upstream row fields/tokens.")


if __name__ == "__main__":
    main()
