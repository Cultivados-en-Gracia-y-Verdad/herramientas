#!/usr/bin/env python3
"""One honest, hash-bound verification path for an LBF book.

The program performs deterministic completeness checks, prepares readable review
evidence, records human verse decisions, and reports exactly two gates:

    TRANSLATION  PENDING | PASS | CHANGES_REQUIRED | BLOCKED
    ALIGNMENT    PENDING | PASS | CHANGES_REQUIRED | BLOCKED

It never turns generated text, producer labels, or an automated check into PASS.
It uses only the Python standard library so it runs in a clean checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
GATES = ("translation", "alignment")
DECISIONS = ("PASS", "CHANGES_REQUIRED", "BLOCKED")
HUMAN_REVIEW_METHOD = "DIRECT_HUMAN_REVIEW"


class WorkflowError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"Required file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"Invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def save_immutable_json(path: Path, value: Any) -> None:
    if path.is_file():
        if load_json(path) != value:
            raise WorkflowError(f"Refusing to overwrite immutable record: {path}")
        return
    save_json(path, value)


def normalize_book(value: str) -> str:
    book = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", book):
        raise WorkflowError(f"Invalid book id: {value!r}")
    return book


def resolve_paths(root: Path, book: str) -> dict[str, Path]:
    oshb = root / "translations" / "oshb-spine" / book
    tr = root / "translations" / "tr-spine" / book
    choices = [
        {
            "spine": oshb / f"{book}-oshb-spine.json",
            "translation": oshb / f"{book}-phrases.json",
            "alignment": oshb / f"{book}-reverse-links.json",
        },
        {
            "spine": tr / f"{book}-tr-spine.json",
            "translation": tr / f"{book}-phrases-tr.json",
            "alignment": tr / f"{book}-reverse-links.json",
        },
    ]
    selected = next((choice for choice in choices if choice["spine"].is_file()), choices[0])
    base = root / "verification" / book
    return {
        **selected,
        "packet": base / "review-packet.json",
        "html": base / "review-packet.html",
        "defects": base / "defects.json",
        "translation_review": base / "translation-review.json",
        "alignment_review": base / "alignment-review.json",
        "roles": base / "role-assignments.json",
        "records": base / "records",
        "decisions": base / "decisions",
    }


def relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def artifact(root: Path, path: Path) -> dict[str, str]:
    return {"path": relative(root, path), "sha256": sha256_file(path)}


def revision_id(book: str, record_type: str, checksum: str) -> str:
    prefixes = {"source": "SRC", "translation": "TR", "alignment": "ALN"}
    return f"{prefixes[record_type]}-{book}-{checksum[:12]}"


def revision_bindings(data: dict[str, Any], gate: str) -> dict[str, str]:
    bindings = {}
    for record_type, artifact_data in artifacts_for_gate(data, gate).items():
        bindings[record_type] = revision_id(data["book"], record_type, artifact_data["sha256"])
    return bindings


def ensure_revision_records(data: dict[str, Any]) -> dict[str, str]:
    paths = data["paths"]
    definitions = {
        "source": {
            "path": paths["spine"],
            "author": "source-importer-unresolved",
            "status": "BLOCKED",
            "owner": "John Wry",
            "nextAction": "Confirm the OSHB/WLC source edition and tokenization provenance.",
            "details": {
                "declaredEdition": data["spine"].get("textualBasis"),
                "tokenizationVersion": data["spine"].get("schemaVersion"),
                "sourceTokenIdScheme": data["spine"].get("sourceTokenIdScheme"),
            },
        },
        "translation": {
            "path": paths["translation"],
            "author": "translation-producer-unresolved",
            "status": "BLOCKED",
            "owner": "John Wry",
            "nextAction": "Resolve producer identity or use a reviewer independent of every possible producer.",
            "details": {"textualBasis": "LBF staging"},
        },
    }
    if data["alignment"] is not None:
        definitions["alignment"] = {
            "path": paths["alignment"],
            "author": str(data["alignment"].get("generator", {}).get("name") or "legacy-alignment-producer"),
            "status": str(data["alignment"].get("generator", {}).get("status") or "DRAFT"),
            "owner": "John Wry",
            "nextAction": "Submit only after current G0A PASS, then perform direct human G0B review.",
            "details": {
                "generator": data["alignment"].get("generator"),
                "textualBasis": data["alignment"].get("textualBasis"),
            },
        }
    ids = {}
    for record_type, definition in definitions.items():
        artifact_data = artifact(data["root"], definition["path"])
        record_id = revision_id(data["book"], record_type, artifact_data["sha256"])
        ids[record_type] = record_id
        record = {
            "schemaVersion": SCHEMA_VERSION,
            "recordId": record_id,
            "revision": 1,
            "recordType": record_type.upper(),
            "book": data["book"],
            "author": definition["author"],
            "recordedAt": now_iso(),
            "status": definition["status"],
            "artifact": artifact_data,
            "details": definition["details"],
            "owner": definition["owner"],
            "nextAction": definition["nextAction"],
        }
        target = paths["records"] / record_type / f"{record_id}.json"
        if target.is_file():
            # recordedAt belongs to the immutable first record and must not be
            # regenerated when prepare is rerun.
            record = load_json(target)
        save_immutable_json(target, record)
    return ids


def phrase_rows(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        rows = document
    elif isinstance(document, dict):
        rows = document.get("phrases")
    else:
        rows = None
    if not isinstance(rows, list) or not rows:
        raise WorkflowError("Translation artifact must be a non-empty phrase array.")
    if not all(isinstance(row, dict) for row in rows):
        raise WorkflowError("Every translation phrase must be an object.")
    return rows


def verse_key_from_reference(reference: str) -> str | None:
    match = re.search(r"(\d+):(\d+)\s*$", reference)
    return f"{int(match.group(1))}:{int(match.group(2))}" if match else None


def source_verse_key(row: dict[str, Any]) -> str | None:
    chapter, verse = row.get("mtChapter"), row.get("mtVerse")
    if chapter is not None and verse is not None:
        try:
            return f"{int(chapter)}:{int(verse)}"
        except (TypeError, ValueError):
            return None
    return verse_key_from_reference(str(row.get("reference") or ""))


def natural_reference(reference: str) -> tuple[int, int, str]:
    key = verse_key_from_reference(reference)
    if not key:
        return (10**9, 10**9, reference)
    chapter, verse = key.split(":")
    return (int(chapter), int(verse), reference)


def phrase_key(row: dict[str, Any]) -> tuple[str, int] | None:
    reference = str(row.get("reference") or "").strip()
    try:
        index = int(row.get("phraseIndex"))
    except (TypeError, ValueError):
        return None
    return (reference, index) if reference else None


def load_book(root: Path, book: str) -> dict[str, Any]:
    paths = resolve_paths(root, book)
    spine = load_json(paths["spine"])
    translation = load_json(paths["translation"])
    alignment = load_json(paths["alignment"]) if paths["alignment"].is_file() else None
    if not isinstance(spine, dict) or not isinstance(spine.get("verses"), dict):
        raise WorkflowError("Source spine must contain a verses object.")
    if alignment is not None and (
        not isinstance(alignment, dict) or not isinstance(alignment.get("links"), list)
    ):
        raise WorkflowError("Alignment artifact must contain a links array.")
    return {
        "root": root,
        "book": book,
        "paths": paths,
        "spine": spine,
        "rows": phrase_rows(translation),
        "alignment": alignment,
    }


def source_indexes(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    tokens: dict[str, dict[str, Any]] = {}
    by_verse: dict[str, list[str]] = {}
    for key, verse in data["spine"]["verses"].items():
        verse_tokens = verse.get("tokens", []) if isinstance(verse, dict) else []
        ids: list[str] = []
        for token in verse_tokens:
            token_id = str(token.get("sourceTokenId") or "") if isinstance(token, dict) else ""
            if not token_id:
                raise WorkflowError(f"Source verse {key} contains a token without sourceTokenId.")
            if token_id in tokens:
                raise WorkflowError(f"Duplicate sourceTokenId: {token_id}")
            tokens[token_id] = token
            ids.append(token_id)
        by_verse[str(key)] = ids
    if not tokens:
        raise WorkflowError("Source spine contains no tokens.")
    return tokens, by_verse


def translation_audit(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tokens, source_by_verse = source_indexes(data)
    seen: set[tuple[str, int]] = set()
    rows_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data["rows"]:
        key = phrase_key(row)
        if key is None:
            errors.append("Translation phrase has an invalid reference or phraseIndex.")
            continue
        if key in seen:
            errors.append(f"Duplicate translation phrase: {key[0]} #{key[1]}")
        seen.add(key)
        if not str(row.get("spanish") or "").strip():
            errors.append(f"{key[0]} phrase {key[1]}: Spanish is blank.")
        source_key = source_verse_key(row)
        if not source_key or source_key not in source_by_verse:
            errors.append(f"{key[0]} phrase {key[1]}: source verse is invalid ({source_key!r}).")
            continue
        ids = row.get("sourceTokenIds")
        if not isinstance(ids, list) or not ids:
            errors.append(f"{key[0]} phrase {key[1]}: sourceTokenIds are missing.")
            continue
        ids = [str(value) for value in ids]
        foreign = [token_id for token_id in ids if token_id not in tokens or token_id not in source_by_verse[source_key]]
        if foreign:
            errors.append(f"{key[0]} phrase {key[1]}: invalid source tokens {foreign[:6]}.")
        rows_by_source[source_key].append(row)

    for source_key, expected in source_by_verse.items():
        rows = rows_by_source.get(source_key, [])
        if not rows:
            errors.append(f"Source verse {source_key} has no Spanish translation.")
            continue
        covered = {
            str(token_id)
            for row in rows
            for token_id in row.get("sourceTokenIds", [])
        }
        missing = [token_id for token_id in expected if token_id not in covered]
        if missing:
            refs = sorted({str(row.get("reference")) for row in rows})
            errors.append(f"{', '.join(refs)}: {len(missing)} source tokens are omitted ({missing[:6]}).")
    return errors


def has_lexical_text(value: str) -> bool:
    return any(unicodedata.category(char)[0] in {"L", "N"} for char in value)


def alignment_audit(data: dict[str, Any]) -> list[str]:
    if data["alignment"] is None:
        return [
            "Alignment has not been submitted. Submit it only after the current translation receives G0A PASS."
        ]
    errors: list[str] = []
    tokens, _ = source_indexes(data)
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in data["rows"]:
        key = phrase_key(row)
        if key is not None:
            rows[key] = row

    links: dict[tuple[str, int], dict[str, Any]] = {}
    for link in data["alignment"]["links"]:
        if not isinstance(link, dict):
            errors.append("Alignment link is not an object.")
            continue
        key = phrase_key(link)
        if key is None:
            errors.append("Alignment link has an invalid reference or phraseIndex.")
            continue
        if key in links:
            errors.append(f"Duplicate alignment link: {key[0]} phrase {key[1]}.")
        links[key] = link

    for key in sorted(set(rows) - set(links)):
        errors.append(f"{key[0]} phrase {key[1]}: alignment is missing.")
    for key in sorted(set(links) - set(rows)):
        errors.append(f"{key[0]} phrase {key[1]}: alignment has no translation phrase.")

    for key, row in rows.items():
        link = links.get(key)
        if link is None:
            continue
        spanish = str(row.get("spanish") or "")
        expected = {str(value) for value in row.get("sourceTokenIds", [])}
        units = link.get("units")
        if not isinstance(units, list) or not units:
            errors.append(f"{key[0]} phrase {key[1]}: alignment units are missing.")
            continue
        covered_tokens: set[str] = set()
        covered_chars: set[int] = set()
        for position, unit in enumerate(units, 1):
            if not isinstance(unit, dict):
                errors.append(f"{key[0]} phrase {key[1]} unit {position}: invalid unit.")
                continue
            unit_id = str(unit.get("unitId") or position)
            start, end = unit.get("charStart"), unit.get("charEnd")
            surface = str(unit.get("surface") or "")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or not (0 <= start < end <= len(spanish))
            ):
                errors.append(f"{key[0]} phrase {key[1]} unit {unit_id}: invalid character span.")
            elif spanish[start:end] != surface:
                errors.append(f"{key[0]} phrase {key[1]} unit {unit_id}: surface does not match Spanish.")
            else:
                positions = set(range(start, end))
                if positions & covered_chars:
                    errors.append(f"{key[0]} phrase {key[1]} unit {unit_id}: Spanish span overlaps another unit.")
                covered_chars.update(positions)
            ids = unit.get("sourceTokenIds")
            if not isinstance(ids, list) or not ids:
                errors.append(f"{key[0]} phrase {key[1]} unit {unit_id}: sourceTokenIds are missing.")
                continue
            ids = [str(value) for value in ids]
            invalid = [token_id for token_id in ids if token_id not in tokens or token_id not in expected]
            if invalid:
                errors.append(f"{key[0]} phrase {key[1]} unit {unit_id}: invalid source relationship {invalid[:6]}.")
            covered_tokens.update(ids)

        missing_tokens = sorted(expected - covered_tokens)
        if missing_tokens:
            errors.append(f"{key[0]} phrase {key[1]}: {len(missing_tokens)} source tokens are unaligned ({missing_tokens[:6]}).")
        uncovered = "".join(char for index, char in enumerate(spanish) if index not in covered_chars)
        if has_lexical_text(uncovered):
            errors.append(f"{key[0]} phrase {key[1]}: Spanish text is left unaligned ({uncovered!r}).")
        if len(units) == 1:
            unit = units[0]
            if (
                unit.get("charStart") == 0
                and unit.get("charEnd") == len(spanish)
                and set(str(value) for value in unit.get("sourceTokenIds", [])) == expected
                and len(expected) > 1
            ):
                errors.append(
                    f"{key[0]} phrase {key[1]}: one whole-verse link manufactures alignment completeness."
                )
    return errors


def artifacts_for_gate(data: dict[str, Any], gate: str) -> dict[str, dict[str, str]]:
    paths = data["paths"]
    values = {
        "source": artifact(data["root"], paths["spine"]),
        "translation": artifact(data["root"], paths["translation"]),
    }
    if gate == "alignment" and data["alignment"] is not None and paths["alignment"].is_file():
        values["alignment"] = artifact(data["root"], paths["alignment"])
    return values


def verse_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    tokens, source_by_verse = source_indexes(data)
    alignment_links = data["alignment"]["links"] if data["alignment"] is not None else []
    links = {phrase_key(link): link for link in alignment_links if phrase_key(link)}
    rows_by_reference: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data["rows"]:
        rows_by_reference[str(row.get("reference"))].append(row)

    evidence: list[dict[str, Any]] = []
    for reference in sorted(rows_by_reference, key=natural_reference):
        rows = sorted(rows_by_reference[reference], key=lambda row: int(row.get("phraseIndex", 0)))
        source_keys = list(dict.fromkeys(source_verse_key(row) for row in rows if source_verse_key(row)))
        source_ids = [token_id for key in source_keys for token_id in source_by_verse.get(key, [])]
        source = [
            {
                "id": token_id,
                "surface": tokens[token_id].get("surface") or tokens[token_id].get("greek") or tokens[token_id].get("greekPunct") or "",
                "lemma": tokens[token_id].get("lemma") or "",
                "morph": tokens[token_id].get("morph") or tokens[token_id].get("robinson") or "",
                "gloss": tokens[token_id].get("es") or tokens[token_id].get("gloss") or "",
            }
            for token_id in source_ids
        ]
        phrases = []
        for row in rows:
            key = phrase_key(row)
            link = links.get(key, {})
            phrases.append(
                {
                    "phraseIndex": int(row.get("phraseIndex", 0)),
                    "spanish": str(row.get("spanish") or ""),
                    "sourceTokenIds": [str(value) for value in row.get("sourceTokenIds", [])],
                    "units": [
                        {
                            "surface": str(unit.get("surface") or ""),
                            "sourceTokenIds": [str(value) for value in unit.get("sourceTokenIds", [])],
                        }
                        for unit in link.get("units", [])
                        if isinstance(unit, dict)
                    ],
                }
            )
        translation = {"reference": reference, "source": source, "phrases": [
            {key: phrase[key] for key in ("phraseIndex", "spanish", "sourceTokenIds")}
            for phrase in phrases
        ]}
        alignment = {"translation": translation, "units": [
            {"phraseIndex": phrase["phraseIndex"], "units": phrase["units"]}
            for phrase in phrases
        ]}
        evidence.append(
            {
                "reference": reference,
                "source": source,
                "phrases": phrases,
                "translationEvidenceHash": stable_hash(translation),
                "alignmentEvidenceHash": stable_hash(alignment),
            }
        )
    return evidence


def review_path(data: dict[str, Any], gate: str) -> Path:
    return data["paths"][f"{gate}_review"]


def make_review(data: dict[str, Any], gate: str, evidence: list[dict[str, Any]]) -> tuple[dict[str, Any], int, int]:
    path = review_path(data, gate)
    old = load_json(path) if path.is_file() else {}
    old_items = {
        str(item.get("reference")): item
        for item in old.get("verses", [])
        if isinstance(item, dict)
    } if isinstance(old, dict) else {}
    hash_field = f"{gate}EvidenceHash"
    verses = []
    preserved = reset = 0
    for verse in evidence:
        reference = verse["reference"]
        evidence_hash = verse[hash_field]
        previous = old_items.get(reference, {})
        if previous.get("evidenceHash") == evidence_hash:
            decision = previous.get("decision", "PENDING")
            reviewer = previous.get("reviewer", "")
            authority = previous.get("authority", "")
            review_method = previous.get("reviewMethod", "")
            ai_used = previous.get("aiUsed")
            reviewed_at = previous.get("reviewedAt", "")
            notes = previous.get("notes", "")
            owner = previous.get("owner", "")
            next_action = previous.get("nextAction", "")
            decision_id = previous.get("decisionId", "")
            if decision in DECISIONS:
                preserved += 1
        else:
            decision = "PENDING"
            reviewer = authority = review_method = reviewed_at = notes = owner = next_action = ""
            ai_used = None
            decision_id = ""
            if previous:
                reset += 1
        verses.append(
            {
                "reference": reference,
                "evidenceHash": evidence_hash,
                "decision": decision,
                "reviewer": reviewer,
                "authority": authority,
                "reviewMethod": review_method,
                "aiUsed": ai_used,
                "reviewedAt": reviewed_at,
                "notes": notes,
                "owner": owner,
                "nextAction": next_action,
                "decisionId": decision_id,
            }
        )
    review = {
        "schemaVersion": SCHEMA_VERSION,
        "book": data["book"],
        "gate": gate.upper(),
        "artifacts": artifacts_for_gate(data, gate),
        "inputRevisionIds": revision_bindings(data, gate),
        "preparedAt": now_iso(),
        "aiVerificationPermitted": False,
        "rule": "PASS requires direct HUMAN review for every verse. AI review, generated status, and producer status are invalid.",
        "verses": verses,
    }
    return review, preserved, reset


def render_html(data: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    sections = []
    for verse in evidence:
        source_rows = "".join(
            f"<tr><td>{esc(token['surface'])}</td><td>{esc(token['lemma'])}</td>"
            f"<td>{esc(token['morph'])}</td><td>{esc(token['gloss'])}</td></tr>"
            for token in verse["source"]
        )
        phrase_blocks = []
        for phrase in verse["phrases"]:
            unit_rows = []
            source_by_id = {token["id"]: token for token in verse["source"]}
            for unit in phrase["units"]:
                originals = " ".join(
                    str(source_by_id.get(token_id, {}).get("surface") or token_id)
                    for token_id in unit["sourceTokenIds"]
                )
                unit_rows.append(f"<tr><td>{esc(unit['surface'])}</td><td>{esc(originals)}</td></tr>")
            phrase_blocks.append(
                f"<div class='phrase'><p class='spanish'>{esc(phrase['spanish'])}</p>"
                f"<table><thead><tr><th>Spanish unit</th><th>Source unit</th></tr></thead>"
                f"<tbody>{''.join(unit_rows)}</tbody></table></div>"
            )
        sections.append(
            f"<section><h2>{esc(verse['reference'])}</h2>"
            f"<h3>Source</h3><table><thead><tr><th>Text</th><th>Lemma</th><th>Morphology</th><th>Gloss</th></tr></thead>"
            f"<tbody>{source_rows}</tbody></table><h3>Translation and alignment</h3>"
            f"{''.join(phrase_blocks)}<div class='checks'><strong>Translation:</strong> nothing omitted, added, or distorted; "
            f"ambiguity preserved where necessary. <strong>Alignment:</strong> every Spanish unit is linked to the source unit it actually represents.</div></section>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data['book'].title())} verification packet</title>
<style>
:root {{ font: 20px/1.55 system-ui, sans-serif; color: #24221f; background: #f5f2eb; }}
body {{ margin: 0 auto; max-width: 1100px; padding: 2rem; }}
h1 {{ font-size: 2.2rem; }} h2 {{ font-size: 1.65rem; border-bottom: 3px solid #5f6f52; }}
h3 {{ font-size: 1.2rem; }} section {{ background: #fffdf8; padding: 1.5rem; margin: 1.5rem 0; border-radius: .5rem; }}
table {{ width: 100%; border-collapse: collapse; margin: .5rem 0 1rem; }}
th, td {{ text-align: left; vertical-align: top; padding: .5rem; border: 1px solid #ddd4c5; }}
.spanish {{ font: 700 1.25rem/1.5 Georgia, serif; }} .phrase {{ margin: 1rem 0 1.5rem; }}
.checks {{ padding: 1rem; background: #e3eadc; }}
</style></head><body><h1>{esc(data['book'].title())}: Translation + Alignment Review</h1>
<p><strong>AI verification is prohibited.</strong> This packet contains mechanically assembled evidence for direct human review. It does not approve itself.</p>{''.join(sections)}</body></html>"""


def prepare(data: dict[str, Any]) -> None:
    revision_ids = ensure_revision_records(data)
    translation_errors = translation_audit(data)
    alignment_errors = alignment_audit(data)
    evidence = verse_evidence(data)
    packet = {
        "schemaVersion": SCHEMA_VERSION,
        "book": data["book"],
        "artifacts": artifacts_for_gate(data, "alignment"),
        "preparedAt": now_iso(),
        "verses": evidence,
    }
    save_json(data["paths"]["packet"], packet)
    data["paths"]["html"].write_text(render_html(data, evidence), encoding="utf-8")
    save_json(
        data["paths"]["defects"],
        {
            "schemaVersion": SCHEMA_VERSION,
            "book": data["book"],
            "artifacts": artifacts_for_gate(data, "alignment"),
            "checkedAt": now_iso(),
            "translation": translation_errors,
            "alignment": alignment_errors,
        },
    )
    gate_errors = {"translation": translation_errors, "alignment": alignment_errors}
    for gate in GATES:
        if gate_errors[gate]:
            print(f"{gate.upper():<12} BLOCKED by {len(gate_errors[gate])} deterministic defect(s)")
            continue
        review, preserved, reset = make_review(data, gate, evidence)
        save_json(review_path(data, gate), review)
        print(f"{gate.upper():<12} {len(review['verses'])} verses; {preserved} decisions preserved; {reset} reset")
    print(f"PACKET       {relative(data['root'], data['paths']['html'])}")
    print(f"DEFECTS      {relative(data['root'], data['paths']['defects'])}")
    print(f"REVISIONS    {', '.join(revision_ids.values())}")


def expected_evidence(data: dict[str, Any], gate: str) -> dict[str, str]:
    field = f"{gate}EvidenceHash"
    return {verse["reference"]: verse[field] for verse in verse_evidence(data)}


def gate_state(data: dict[str, Any], gate: str) -> tuple[str, str]:
    structural = translation_audit(data) if gate == "translation" else alignment_audit(data)
    if structural:
        return "CHANGES_REQUIRED", f"{len(structural)} deterministic defect(s); first: {structural[0]}"
    path = review_path(data, gate)
    if not path.is_file():
        return "PENDING", "review has not been prepared"
    review = load_json(path)
    if not isinstance(review, dict) or review.get("schemaVersion") != SCHEMA_VERSION or review.get("book") != data["book"] or review.get("gate") != gate.upper():
        return "BLOCKED", "review identity is invalid; owner: workflow operator; next: run prepare"
    if review.get("artifacts") != artifacts_for_gate(data, gate):
        return "PENDING", "artifact bytes changed; run prepare to compute the affected scope"
    if review.get("inputRevisionIds") != revision_bindings(data, gate):
        return "PENDING", "input revision IDs changed; run prepare"
    expected = expected_evidence(data, gate)
    items = review.get("verses")
    if not isinstance(items, list):
        return "BLOCKED", "review has no verse list; owner: workflow operator; next: run prepare"
    actual = {str(item.get("reference")): item for item in items if isinstance(item, dict)}
    if set(actual) != set(expected) or any(actual[ref].get("evidenceHash") != digest for ref, digest in expected.items()):
        return "PENDING", "review evidence does not match the current book; run prepare"
    changes_required = blocked = pending = invalid = 0
    for item in actual.values():
        decision = item.get("decision")
        if decision == "PENDING":
            pending += 1
        elif decision in DECISIONS:
            if (
                item.get("authority") != "HUMAN"
                or item.get("reviewMethod") != HUMAN_REVIEW_METHOD
                or item.get("aiUsed") is not False
                or not str(item.get("reviewer") or "").strip()
                or not str(item.get("reviewedAt") or "").strip()
            ):
                invalid += 1
            decision_id = str(item.get("decisionId") or "")
            decision_path = data["paths"]["decisions"] / gate / f"{decision_id}.json"
            if not decision_id or not decision_path.is_file():
                invalid += 1
            else:
                decision_record = load_json(decision_path)
                if (
                    decision_record.get("recordId") != decision_id
                    or decision_record.get("result") != decision
                    or decision_record.get("inputRevisionIds") != revision_bindings(data, gate)
                    or item.get("reference") not in decision_record.get("scope", {}).get("references", [])
                ):
                    invalid += 1
            try:
                require_independent_reviewer(data, gate, str(item.get("reviewer") or ""))
            except WorkflowError:
                invalid += 1
            if decision == "CHANGES_REQUIRED":
                changes_required += 1
                if not str(item.get("notes") or "").strip():
                    invalid += 1
            if decision == "BLOCKED":
                blocked += 1
                if not str(item.get("owner") or "").strip() or not str(item.get("nextAction") or "").strip():
                    invalid += 1
        else:
            invalid += 1
    if invalid:
        return "BLOCKED", f"{invalid} decision(s) lack required provenance or action details"
    if changes_required:
        return "CHANGES_REQUIRED", f"{changes_required} verse(s) have actionable human findings"
    if blocked:
        return "BLOCKED", f"{blocked} verse(s) identify an owner and next action"
    if pending:
        return "PENDING", f"{pending} of {len(actual)} verse(s) still require human review"
    return "PASS", f"all {len(actual)} verses passed human review for these exact bytes"


def status(data: dict[str, Any]) -> int:
    translation_defects = translation_audit(data)
    alignment_defects = alignment_audit(data)
    translation, translation_detail = gate_state(data, "translation")
    alignment, alignment_detail = gate_state(data, "alignment")
    if translation != "PASS":
        alignment, alignment_detail = "PENDING", f"G0B waits for current G0A PASS; G0A is {translation}"
    verse_gates = "PASS" if translation == alignment == "PASS" else "PENDING"
    print(f"\n{data['book'].upper()} — BOOK VERIFICATION\n")
    print("SCRIPT FACTS")
    print(f"TRANSLATION COMPLETENESS   {'PASS' if not translation_defects else 'CHANGES_REQUIRED'}")
    print(f"ALIGNMENT INTEGRITY        {'PASS' if not alignment_defects else 'CHANGES_REQUIRED'}")
    print("AI VERIFICATION            PROHIBITED")
    print("\nHUMAN GATES")
    print(f"TRANSLATION   {translation}")
    print(f"              {translation_detail}")
    print(f"ALIGNMENT     {alignment}")
    print(f"              {alignment_detail}")
    print(f"\nVERSE GATES   {verse_gates}")
    print("BOOK          NOT APPROVED — book review and release approval are separate human decisions\n")
    return 0 if verse_gates == "PASS" else 1


def normalized_person(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def require_independent_reviewer(data: dict[str, Any], gate: str, reviewer: str) -> None:
    path = data["paths"]["roles"]
    if not path.is_file():
        raise WorkflowError("Role assignments are missing; PASS cannot establish review independence.")
    roles = load_json(path)
    assignments = roles.get("assignments", {})
    reviewer_role = assignments.get(f"{gate}Reviewer", {})
    assigned_reviewer = str(reviewer_role.get("name") or "")
    if normalized_person(assigned_reviewer) != normalized_person(reviewer):
        raise WorkflowError(f"{reviewer!r} is not the assigned {gate} reviewer ({assigned_reviewer!r}).")
    producer = assignments.get(f"{gate}Producer", {})
    producer_name = str(producer.get("name") or "")
    possible = [str(value) for value in producer.get("possibleProducers", [])]
    if producer.get("status") == "BLOCKED" or normalized_person(producer_name) in {"", "unresolved"}:
        if not possible or any(normalized_person(value) == normalized_person(reviewer) for value in possible):
            raise WorkflowError(
                f"{gate.upper()} reviewer independence is unresolved for {reviewer}. "
                "Assign a reviewer independent of every possible producer."
            )
    elif normalized_person(producer_name) == normalized_person(reviewer):
        raise WorkflowError(f"{reviewer} cannot be the sole reviewer of their own {gate} production revision.")


def write_gate_decision(
    data: dict[str, Any], gate: str, references: list[str], decision: str,
    reviewer: str, notes: str, owner: str, next_action: str,
) -> str:
    timestamp = now_iso()
    body = {
        "schemaVersion": SCHEMA_VERSION,
        "revision": 1,
        "recordType": "GATE_DECISION",
        "book": data["book"],
        "gate": "G0A" if gate == "translation" else "G0B",
        "inputRevisionIds": revision_bindings(data, gate),
        "reviewer": reviewer,
        "authority": "HUMAN",
        "reviewMethod": HUMAN_REVIEW_METHOD,
        "aiUsed": False,
        "result": decision,
        "scope": {"type": "VERSE_SET", "references": references},
        "findings": notes,
        "timestamp": timestamp,
        "owner": owner,
        "nextAction": next_action,
    }
    digest = stable_hash(body)
    decision_id = f"{'G0A' if gate == 'translation' else 'G0B'}-{data['book']}-{digest[:12]}"
    record = {"recordId": decision_id, **body}
    path = data["paths"]["decisions"] / gate / f"{decision_id}.json"
    save_immutable_json(path, record)
    return decision_id


def record(
    data: dict[str, Any], gate: str, reference: str, decision: str,
    reviewer: str, notes: str, human_confirmation: bool,
    owner: str = "", next_action: str = "",
) -> None:
    gate = gate.lower()
    if gate not in GATES:
        raise WorkflowError(f"Unknown gate: {gate}")
    decision = decision.upper()
    if decision not in DECISIONS:
        raise WorkflowError("Decision must be PASS, CHANGES_REQUIRED, or BLOCKED.")
    reviewer = reviewer.strip()
    if not reviewer:
        raise WorkflowError("A human reviewer name is required.")
    if human_confirmation is not True:
        raise WorkflowError("Direct human review must be explicitly confirmed. AI verification is prohibited.")
    notes = notes.strip()
    owner = owner.strip()
    next_action = next_action.strip()
    if decision == "CHANGES_REQUIRED" and not notes:
        raise WorkflowError("CHANGES_REQUIRED must contain actionable findings in --notes.")
    if decision == "BLOCKED" and (not owner or not next_action):
        raise WorkflowError("BLOCKED requires --owner and --next-action.")
    require_independent_reviewer(data, gate, reviewer)
    path = review_path(data, gate)
    if not path.is_file():
        raise WorkflowError(f"Run prepare before recording {gate} review.")
    state, detail = gate_state(data, gate)
    if state == "BLOCKED" and "identity" in detail:
        raise WorkflowError(detail)
    if gate == "alignment":
        translation_review = load_json(review_path(data, "translation")) if review_path(data, "translation").is_file() else {}
        translation_item = next((item for item in translation_review.get("verses", []) if item.get("reference") == reference), None)
        if not translation_item or translation_item.get("decision") != "PASS" or translation_item.get("authority") != "HUMAN":
            raise WorkflowError(f"{reference}: translation must receive a human PASS before alignment review.")
    review = load_json(path)
    item = next((item for item in review["verses"] if item.get("reference") == reference), None)
    if item is None:
        raise WorkflowError(f"Reference is not in this book: {reference}")
    item.update(
        {
            "decision": decision,
            "reviewer": reviewer,
            "authority": "HUMAN",
            "reviewMethod": HUMAN_REVIEW_METHOD,
            "aiUsed": False,
            "reviewedAt": now_iso(),
            "notes": notes,
            "owner": owner,
            "nextAction": next_action,
        }
    )
    decision_id = write_gate_decision(
        data, gate, [reference], decision, reviewer, notes, owner, next_action
    )
    item["decisionId"] = decision_id
    save_json(path, review)
    print(f"{gate.upper()} {decision}: {reference} — {reviewer} ({decision_id})")


def record_chapter(
    data: dict[str, Any], gate: str, chapter: int, decision: str,
    reviewer: str, notes: str, human_confirmation: bool,
    owner: str = "", next_action: str = "",
) -> None:
    path = review_path(data, gate)
    if not path.is_file():
        raise WorkflowError(f"Run prepare before recording {gate} review.")
    review = load_json(path)
    pattern = re.compile(rf"\b{chapter}:\d+\s*$")
    references = [
        str(item.get("reference"))
        for item in review.get("verses", [])
        if pattern.search(str(item.get("reference") or ""))
    ]
    if not references:
        raise WorkflowError(f"Chapter {chapter} is not present in {data['book']}.")
    print(
        f"Recording {decision.upper()} for {len(references)} verses in chapter {chapter}. "
        "The human confirmation applies to every listed verse."
    )
    for reference in references:
        record(
            data, gate, reference, decision, reviewer, notes,
            human_confirmation, owner, next_action,
        )


def record_book(
    data: dict[str, Any], gate: str, decision: str,
    reviewer: str, notes: str, human_confirmation: bool,
    owner: str = "", next_action: str = "",
) -> None:
    """Record one book reading. Verse rows store that attestation; they are not 211 reviews."""
    gate = gate.lower()
    if gate not in GATES:
        raise WorkflowError(f"Unknown gate: {gate}")
    decision = decision.upper()
    if decision not in {"PASS", "BLOCKED"}:
        raise WorkflowError(
            "record-book is a book reading: PASS or BLOCKED. "
            "Record verse findings with `record` and CHANGES_REQUIRED."
        )
    reviewer = reviewer.strip()
    if not reviewer:
        raise WorkflowError("A human reviewer name is required.")
    if human_confirmation is not True:
        raise WorkflowError("Direct human review must be explicitly confirmed. AI verification is prohibited.")
    notes = notes.strip()
    owner = owner.strip()
    next_action = next_action.strip()
    if decision == "BLOCKED" and (not owner or not next_action):
        raise WorkflowError("BLOCKED requires --owner and --next-action.")
    require_independent_reviewer(data, gate, reviewer)
    path = review_path(data, gate)
    if not path.is_file():
        raise WorkflowError(f"Run prepare before recording {gate} review.")
    review = load_json(path)
    pending_items = [item for item in review.get("verses", []) if item.get("decision") == "PENDING"]
    if not pending_items:
        raise WorkflowError(f"No pending {gate} verses to record for {data['book']}.")
    if gate == "alignment":
        translation_review = load_json(review_path(data, "translation")) if review_path(data, "translation").is_file() else {}
        translation_by_ref = {
            str(item.get("reference")): item
            for item in translation_review.get("verses", [])
        }
        for item in pending_items:
            reference = str(item.get("reference"))
            translation_item = translation_by_ref.get(reference)
            if not translation_item or translation_item.get("decision") != "PASS" or translation_item.get("authority") != "HUMAN":
                raise WorkflowError(f"{reference}: translation must receive a human PASS before alignment review.")
    references = [str(item.get("reference")) for item in pending_items]
    timestamp = now_iso()
    decision_id = write_gate_decision(
        data, gate, references, decision, reviewer, notes, owner, next_action
    )
    for item in pending_items:
        item.update(
            {
                "decision": decision,
                "reviewer": reviewer,
                "authority": "HUMAN",
                "reviewMethod": HUMAN_REVIEW_METHOD,
                "aiUsed": False,
                "reviewedAt": timestamp,
                "notes": notes,
                "owner": owner,
                "nextAction": next_action,
                "decisionId": decision_id,
            }
        )
    save_json(path, review)
    print(
        f"{gate.upper()} {decision}: {data['book']} book reading — "
        f"{len(references)} pending verse(s) — {reviewer} ({decision_id})"
    )


def pending(data: dict[str, Any], gate: str) -> None:
    gate = gate.lower()
    path = review_path(data, gate)
    if not path.is_file():
        raise WorkflowError(f"Run prepare before listing {gate} review.")
    review = load_json(path)
    rows = [item for item in review.get("verses", []) if item.get("decision") == "PENDING"]
    print(f"{gate.upper()} pending: {len(rows)}")
    for item in rows:
        print(item["reference"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LBF translation and alignment verification")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "status"):
        command = commands.add_parser(name)
        command.add_argument("book")
    decision_choices = ("PASS", "CHANGES_REQUIRED", "BLOCKED", "pass", "changes_required", "blocked")
    for command_name in ("record", "record-chapter", "record-book"):
        command = commands.add_parser(command_name)
        command.add_argument("book")
        command.add_argument("gate", choices=GATES)
        if command_name == "record":
            command.add_argument("reference")
        elif command_name == "record-chapter":
            command.add_argument("chapter", type=int)
        command.add_argument("decision", choices=decision_choices)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--notes", default="")
        command.add_argument("--owner", default="")
        command.add_argument("--next-action", default="")
        command.add_argument(
            "--human-confirmation",
            action="store_true",
            help="attest that the named human read the book (or the named verses) without AI verification",
        )
    command = commands.add_parser("pending")
    command.add_argument("book")
    command.add_argument("gate", choices=GATES)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = Path(args.root).resolve()
        data = load_book(root, normalize_book(args.book))
        if args.command == "prepare":
            prepare(data)
            return status(data)
        if args.command == "status":
            return status(data)
        if args.command == "record":
            record(
                data, args.gate, args.reference, args.decision,
                args.reviewer, args.notes, args.human_confirmation,
                args.owner, args.next_action,
            )
            return status(data)
        if args.command == "record-chapter":
            record_chapter(
                data, args.gate, args.chapter, args.decision,
                args.reviewer, args.notes, args.human_confirmation,
                args.owner, args.next_action,
            )
            return status(data)
        if args.command == "record-book":
            record_book(
                data, args.gate, args.decision,
                args.reviewer, args.notes, args.human_confirmation,
                args.owner, args.next_action,
            )
            return status(data)
        if args.command == "pending":
            pending(data, args.gate)
            return 0
        raise WorkflowError(f"Unknown command: {args.command}")
    except WorkflowError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
