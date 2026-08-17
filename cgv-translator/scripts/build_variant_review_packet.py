#!/usr/bin/env python3
"""Build a large-text human evidence packet for a ketiv/qere investigation.

This script only verifies checksums and assembles existing source, morphology,
gloss, and Spanish data. It never selects a reading or records an approval.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def reference_key(reference: str) -> tuple[int, int]:
    match = re.search(r"(\d+):(\d+)\s*$", reference)
    if not match:
        raise ValueError(f"Invalid reference: {reference}")
    return int(match.group(1)), int(match.group(2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic ketiv/qere review evidence")
    parser.add_argument("book")
    parser.add_argument("investigation")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    investigation = root / "investigations" / args.book / args.investigation
    evidence_path = investigation / "evidence" / "source-variants.json"
    evidence = load_json(evidence_path)
    if evidence.get("authority") != "DETERMINISTIC_SOURCE_FACTS_ONLY" or evidence.get("aiUsed") is not False:
        raise SystemExit("Evidence authority is invalid.")

    source_path = root.parent / evidence["source"]["path"]
    spine_path = root / evidence["controlledSpine"]["path"]
    if sha256(source_path) != evidence["source"]["sha256"]:
        raise SystemExit("Source checksum does not match the investigation evidence.")
    if sha256(spine_path) != evidence["controlledSpine"]["sha256"]:
        raise SystemExit("Spine checksum does not match the investigation evidence.")

    phrases_path = root / "translations" / "oshb-spine" / args.book / f"{args.book}-phrases.json"
    phrases = load_json(phrases_path)["phrases"]
    by_reference = {str(row["reference"]): row for row in phrases}
    spine = load_json(spine_path)
    by_source_id = {
        str(token["sourceTokenId"]): token
        for verse in spine["verses"].values()
        for token in verse["tokens"]
    }

    dataset_path = root.parent / "MNA" / "datasets" / "interlinear" / "OT" / "zacarias.tokens.jsonl"
    dataset_rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gloss_by_oshb_id = {str(row["id"]): str(row.get("es") or "") for row in dataset_rows}

    sections = []
    for number, variant in enumerate(sorted(evidence["variants"], key=lambda row: reference_key(row["reference"])), 1):
        reference = str(variant["reference"])
        phrase = by_reference[reference]
        verse_tokens = [by_source_id[str(token_id)] for token_id in phrase["sourceTokenIds"]]
        source_verse = " ".join(str(token.get("surface") or "") for token in verse_tokens)
        rows = []
        for label in ("ketiv", "qere"):
            token = variant[label]
            rows.append(
                "<tr>"
                f"<th>{esc(label.upper())}</th>"
                f"<td class='hebrew'>{esc(token['surface'])}</td>"
                f"<td>{esc(token['lemma'])}</td>"
                f"<td>{esc(token['morph'])}</td>"
                f"<td>{esc(gloss_by_oshb_id.get(str(token['id']), ''))}</td>"
                "</tr>"
            )
        sections.append(
            f"<section><h2>{number}. {esc(reference)}</h2>"
            f"<p><strong>Full OSHB verse:</strong> <span class='hebrew'>{esc(source_verse)}</span></p>"
            f"<p><strong>Current Spanish:</strong> <span class='spanish'>{esc(phrase['spanish'])}</span></p>"
            "<table><thead><tr><th>Reading</th><th>Source</th><th>Lemma</th>"
            f"<th>Morphology</th><th>Dataset gloss</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
            "<div class='question'><strong>Human decision required:</strong> select the reading governing this occurrence, "
            "state the reason, and state whether the current Spanish must change.</div></section>"
        )

    output = investigation / "review-packet.html"
    output.write_text(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(args.investigation)} source-variant review</title>
<style>
:root {{ font: 21px/1.6 system-ui, sans-serif; color: #24221f; background: #f5f2eb; }}
body {{ margin: 0 auto; max-width: 1180px; padding: 2rem; }}
h1 {{ font-size: 2.35rem; }} h2 {{ font-size: 1.75rem; border-bottom: 3px solid #5f6f52; }}
section {{ background: #fffdf8; padding: 1.6rem; margin: 1.7rem 0; border-radius: .6rem; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ text-align: left; vertical-align: top; padding: .65rem; border: 1px solid #d7cebf; }}
.hebrew {{ font: 1.35rem/1.7 serif; direction: rtl; unicode-bidi: isolate; }}
.spanish {{ font: 700 1.2rem/1.55 Georgia, serif; }}
.warning, .guidance, .question {{ padding: 1rem; border-left: 6px solid; }}
.warning, .question {{ background: #f3e4b5; border-color: #9b7418; }}
.guidance {{ background: #dceaf4; border-color: #316b94; margin: 1.2rem 0; }}
</style></head><body>
<h1>{esc(args.investigation)}: Ketiv/Qere Human Decision Packet</h1>
<div class="warning"><strong>No AI judgment and no automatic approval.</strong> This packet assembles checksum-verified evidence only. John Wry is the accountable human decision-maker.</div>
<div class="guidance"><strong>No Spanish word-to-word assignment is expected at this stage.</strong> Under the LBF workflow, exact alignment begins only after the translation receives G0A PASS. Each occurrence below therefore gives the exact Hebrew readings, deterministic dataset glosses, and the complete current Spanish verse as context. The human decision is which source reading governs and whether that decision requires a Spanish change. No alignment is invented here.</div>
<p><strong>Controlled source:</strong> {esc(evidence['controlledSpine']['revisionId'])}</p>
<p><strong>Occurrences:</strong> {len(evidence['variants'])}</p>
{''.join(sections)}
</body></html>""",
        encoding="utf-8",
    )
    print(output)
    print(f"variants: {len(evidence['variants'])}; decisions recorded: 0; AI used: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
