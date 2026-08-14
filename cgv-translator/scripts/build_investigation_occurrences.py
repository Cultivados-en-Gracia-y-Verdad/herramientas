#!/usr/bin/env python3
"""Build deterministic, book-local source occurrence evidence for an investigation.

The output is source data, not a linguistic conclusion and never an approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from book_workflow import load_book, normalize_book, now_iso, revision_bindings


def stable_id(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build(root: Path, book: str, strongs: str, investigation: str) -> dict:
    data = load_book(root, book)
    number_match = re.search(r"\d+", strongs)
    if not number_match:
        raise ValueError(f"Strong's identifier has no number: {strongs}")
    number = number_match.group(0)
    pattern = re.compile(rf"(?<!\d){re.escape(number)}(?!\d)")

    reference_by_token = {
        str(token_id): str(row.get("reference") or "")
        for row in data["rows"]
        for token_id in row.get("sourceTokenIds", [])
    }
    spanish_by_reference = {
        str(row.get("reference") or ""): str(row.get("spanish") or "")
        for row in data["rows"]
    }
    occurrences = []
    for source_key, verse in data["spine"]["verses"].items():
        tokens = verse.get("tokens", [])
        source_text = " ".join(str(token.get("surface") or "") for token in tokens).strip()
        for token in tokens:
            if not pattern.search(str(token.get("lemma") or "")):
                continue
            token_id = str(token.get("sourceTokenId") or "")
            reference = reference_by_token.get(token_id, f"{book.title()} {source_key}")
            occurrences.append({
                "reference": reference,
                "sourceCoordinate": source_key,
                "sourceTokenId": token_id,
                "surface": str(token.get("surface") or ""),
                "lemma": str(token.get("lemma") or ""),
                "morph": str(token.get("morph") or ""),
                "storedGloss": str(token.get("es") or ""),
                "sourceVerse": source_text,
                "currentSpanish": spanish_by_reference.get(reference, ""),
            })

    payload = {
        "schemaVersion": 1,
        "recordType": "INVESTIGATION_SOURCE_OCCURRENCES",
        "investigationId": investigation,
        "book": book,
        "strongs": strongs.upper(),
        "status": "EVIDENCE_ONLY",
        "authority": "DETERMINISTIC_SOURCE_EXTRACTION",
        "aiUsed": False,
        "generatedAt": now_iso(),
        "inputRevisionIds": {"source": revision_bindings(data, "translation")["source"]},
        "matchingRule": f"numeric Strong's component {number} in source lemma field",
        "counts": {
            "occurrences": len(occurrences),
            "surfaceForms": dict(sorted(Counter(row["surface"] for row in occurrences).items())),
            "morphology": dict(sorted(Counter(row["morph"] for row in occurrences).items())),
            "storedGlosses": dict(sorted(Counter(row["storedGloss"] for row in occurrences).items())),
        },
        "occurrences": occurrences,
    }
    payload["recordId"] = f"EVID-{investigation}-{stable_id({k: v for k, v in payload.items() if k != 'generatedAt'})}"
    return payload


def markdown(document: dict) -> str:
    lines = [
        f"# Source Occurrences — {document['investigationId']}",
        "",
        f"**Status:** Evidence only — no conclusion or approval  ",
        f"**Strong's:** {document['strongs']}  ",
        f"**Source revision:** {document['inputRevisionIds']['source']}  ",
        f"**Occurrences in {document['book'].title()}:** {document['counts']['occurrences']}  ",
        "**AI used:** No",
        "",
        "| Reference | Source form | Lemma | Morphology | Stored gloss | Current Spanish |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in document["occurrences"]:
        values = [row[key].replace("|", "\\|").replace("\n", " ") for key in (
            "reference", "surface", "lemma", "morph", "storedGloss", "currentSpanish"
        )]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend([
        "",
        "This table is mechanically extracted from the controlled source snapshot. "
        "John Wry remains responsible for the investigation conclusion, rationale, confidence, and approval.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("book")
    parser.add_argument("strongs")
    parser.add_argument("investigation")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    document = build(root, normalize_book(args.book), args.strongs, args.investigation)
    output = root / "investigations" / args.book / args.investigation / "evidence" / "source-occurrences.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown(document), encoding="utf-8")
    print(f"{args.investigation}: {document['counts']['occurrences']} source occurrence(s)")
    print(output.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
