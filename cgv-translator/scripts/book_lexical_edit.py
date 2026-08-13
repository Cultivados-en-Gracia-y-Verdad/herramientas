#!/usr/bin/env python3
"""Preview/apply a book-wide Spanish terminology change safely.

A Book Default edit means exactly that: every whole-word occurrence of the selected
Spanish rendering in the book is part of the operation. The source token selected at
``--reference`` is retained as provenance, but incomplete source metadata may never
silently narrow a book-wide edit.

When applying, this command also re-synchronizes reverse-link surfaces and character
spans without changing sourceTokenIds. Only translation approval is invalidated;
source-token alignment evidence is preserved because the mapping itself did not change.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


def normalize_source(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in {"L", "N"})


def token_id(token: dict) -> tuple[str, str]:
    return str(token.get("strongs") or "").strip().upper(), str(token.get("lemma") or "").strip()


def matches(token: dict, target: tuple[str, str]) -> bool:
    strongs, lemma = target
    token_strongs, token_lemma = token_id(token)
    return token_strongs == strongs if strongs else bool(lemma) and token_lemma == lemma


def pattern(rendering: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(rendering)}(?!\w)")


def rows(doc: dict) -> list[dict]:
    value = doc.get("phrases")
    if not isinstance(value, list):
        raise ValueError("phrase artifact must contain a phrases list")
    return value


def find_book_file(root: Path, book: str, suffixes: list[str]) -> Path:
    bases = [
        root / "translations" / "oshb-spine" / book,
        root / "translations" / "tr-spine" / book,
        root / "translations",
    ]
    for base in bases:
        for suffix in suffixes:
            path = base / suffix
            if path.is_file():
                return path
    raise FileNotFoundError(f"book artifact not found for {book}: {', '.join(suffixes)}")


def find_phrase_file(root: Path, book: str) -> Path:
    return find_book_file(root, book, [f"{book}-phrases.json", f"{book}-phrases-tr.json"])


def find_reverse_file(root: Path, book: str) -> Path:
    return find_book_file(root, book, [f"{book}-reverse-links.json"])


def find_target(phrases: list[dict], reference: str, surface: str) -> tuple[str, str, str]:
    wanted = normalize_source(surface)
    candidates = []
    for phrase in phrases:
        if str(phrase.get("reference") or "") != reference:
            continue
        for token in phrase.get("tokenRows", []) if isinstance(phrase.get("tokenRows"), list) else []:
            forms = [token.get("surface"), token.get("greek"), token.get("lemma")]
            if any(normalize_source(value) == wanted for value in forms if value):
                candidates.append(token)
    identities = {(token_id(token), str(token.get("surface") or token.get("greek") or "")) for token in candidates}
    if len(identities) != 1:
        raise ValueError(f"source surface must identify exactly one token at {reference}; found {len(identities)}")
    (strongs, lemma), found_surface = next(iter(identities))
    if not strongs and not lemma:
        raise ValueError("selected source token lacks Strong's and lemma identity")
    return strongs, lemma, found_surface


def build_plan(phrases: list[dict], target: tuple[str, str], old: str, new: str) -> dict:
    """Plan a true book-wide rendering change.

    Every whole-word old/new occurrence is included. ``sourceCount`` remains diagnostic
    provenance only; it can never silently exclude another Spanish occurrence.
    """
    if old == new:
        raise ValueError("--from and --to must differ")
    items = []
    old_pattern = pattern(old)
    new_pattern = pattern(new)
    source_total = 0
    for phrase in phrases:
        token_rows = phrase.get("tokenRows", []) if isinstance(phrase.get("tokenRows"), list) else []
        source_count = sum(1 for token in token_rows if matches(token, target))
        source_total += source_count
        spanish = str(phrase.get("spanish") or "")
        old_count = len(old_pattern.findall(spanish))
        new_count = len(new_pattern.findall(spanish))
        if not old_count and not new_count:
            continue
        proposed = old_pattern.sub(new, spanish)
        items.append({
            "reference": phrase.get("reference"),
            "phraseIndex": phrase.get("phraseIndex"),
            "sourceCount": source_count,
            "oldCount": old_count,
            "newCount": new_count,
            "before": spanish,
            "after": proposed,
            "changed": proposed != spanish,
        })
    old_total = sum(item["oldCount"] for item in items)
    new_total = sum(item["newCount"] for item in items)
    return {
        "safe": bool(items) and old_total > 0,
        "totalSourceOccurrences": source_total,
        "terminologyOccurrences": old_total + new_total,
        "oldOccurrences": old_total,
        "newOccurrences": new_total,
        "phrasesAffected": len(items),
        "phrasesChanged": sum(bool(item["changed"]) for item in items),
        "items": items,
    }


def apply_plan(doc: dict, plan: dict) -> dict:
    if not plan.get("safe"):
        raise ValueError("refusing incomplete book-wide edit")
    result = deepcopy(doc)
    by_index = {int(item["phraseIndex"]): item for item in plan["items"] if item["changed"]}
    now = datetime.now(timezone.utc).isoformat()
    for phrase in rows(result):
        item = by_index.get(int(phrase.get("phraseIndex", -1)))
        if not item:
            continue
        phrase["spanish"] = item["after"]
        phrase["suggestionSource"] = "lbf-preliminary"
        phrase["approval"] = {
            "status": "invalidated",
            "authority": "none",
            "invalidatedBecause": "book-wide-spanish-rendering-changed",
            "invalidatedAt": now,
        }
    return result


def _units_match(text: str, units: list[dict]) -> bool:
    for unit in units:
        start, end = unit.get("charStart"), unit.get("charEnd")
        surface = str(unit.get("surface") or "")
        if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start <= end <= len(text)):
            return False
        if text[start:end] != surface:
            return False
    return True


def _shift_before(matches: list[re.Match[str]], position: int, delta: int) -> int:
    return sum(delta for match in matches if match.end() <= position)


def synchronize_reverse_links(reverse_doc: dict, plan: dict, old: str, new: str) -> tuple[dict, list[dict]]:
    """Rebase reverse-link spans onto the post-edit Spanish without relinking tokens.

    This supports the common interrupted state where the editor already changed one
    phrase (for example Daniel 2:39) but reverse links still point at the old rendering.
    """
    links = reverse_doc.get("links")
    if not isinstance(links, list):
        raise ValueError("reverse-link artifact must contain links[]")
    by_ref = {str(link.get("reference") or ""): link for link in links if isinstance(link, dict)}
    old_pattern = pattern(old)
    new_pattern = pattern(new)
    delta = len(new) - len(old)
    result = deepcopy(reverse_doc)
    result_by_ref = {str(link.get("reference") or ""): link for link in result.get("links", []) if isinstance(link, dict)}
    changed_units: list[dict] = []

    for item in plan.get("items", []):
        ref = str(item.get("reference") or "")
        source_link = by_ref.get(ref)
        target_link = result_by_ref.get(ref)
        if source_link is None or target_link is None:
            raise ValueError(f"alignment reference missing for terminology occurrence: {ref}")
        units = source_link.get("units")
        if not isinstance(units, list) or not units:
            raise ValueError(f"alignment units missing for terminology occurrence: {ref}")

        desired = str(item["after"])
        candidates = [str(item["before"])]
        reconstructed = new_pattern.sub(old, str(item["before"]))
        if reconstructed not in candidates:
            candidates.append(reconstructed)
        base = next((candidate for candidate in candidates if _units_match(candidate, units)), None)
        if base is None:
            raise ValueError(f"{ref}: alignment matches neither current nor pre-edit Spanish; refusing blind rewrite")
        if old_pattern.sub(new, base) != desired:
            raise ValueError(f"{ref}: deterministic rendering substitution does not reproduce current Spanish")

        replacements = list(old_pattern.finditer(base))
        for match in replacements:
            containers = [
                unit for unit in units
                if isinstance(unit.get("charStart"), int)
                and isinstance(unit.get("charEnd"), int)
                and unit["charStart"] <= match.start()
                and match.end() <= unit["charEnd"]
            ]
            if len(containers) != 1:
                raise ValueError(f"{ref}: rendering occurrence crosses alignment-unit boundary")

        target_units = target_link.get("units", [])
        for source_unit, target_unit in zip(units, target_units):
            start, end = int(source_unit["charStart"]), int(source_unit["charEnd"])
            new_start = start + _shift_before(replacements, start, delta)
            new_end = end + _shift_before(replacements, end, delta)
            if not (0 <= new_start <= new_end <= len(desired)):
                raise ValueError(f"{ref} / {source_unit.get('unitId')}: rebased character span is invalid")
            new_surface = desired[new_start:new_end]
            surface_changed = new_surface != str(source_unit.get("surface") or "")
            target_unit["charStart"] = new_start
            target_unit["charEnd"] = new_end
            target_unit["surface"] = new_surface
            if surface_changed:
                changed_units.append({"reference": ref, "unitId": target_unit.get("unitId")})

        if not _units_match(desired, target_units):
            raise ValueError(f"{ref}: rebased alignment does not match current Spanish")

    return result, changed_units


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--book", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--source-surface", required=True)
    parser.add_argument("--from", dest="old", required=True)
    parser.add_argument("--to", dest="new", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    book = args.book.strip().lower()
    phrase_path = find_phrase_file(root, book)
    reverse_path = find_reverse_file(root, book)
    doc = json.loads(phrase_path.read_text(encoding="utf-8"))
    reverse_doc = json.loads(reverse_path.read_text(encoding="utf-8"))
    strongs, lemma, surface = find_target(rows(doc), args.reference, args.source_surface)
    plan = build_plan(rows(doc), (strongs, lemma), args.old, args.new)

    print(f"book: {book}")
    print(f"origin: {args.reference}")
    print(f"source: {surface}")
    print(f"lemma: {lemma or '—'}")
    print(f"strongs: {strongs or '—'}")
    print("scope: Book Default (every Spanish whole-word occurrence)")
    print(f"rendering: {args.old!r} -> {args.new!r}")
    print(f"selected-source occurrences (diagnostic): {plan['totalSourceOccurrences']}")
    print(f"book terminology occurrences: {plan['terminologyOccurrences']}")
    print(f"already {args.new!r}: {plan['newOccurrences']}")
    print(f"changing from {args.old!r}: {plan['oldOccurrences']}")
    print(f"phrases affected: {plan['phrasesAffected']}")
    print(f"phrases changing: {plan['phrasesChanged']}")
    for item in plan["items"]:
        marker = "CHANGE" if item["changed"] else "OK"
        suffix = f" -> {item['after']}" if item["changed"] else ""
        print(f"{marker:6} {item['reference']}: {item['before']}{suffix}")

    if not plan["safe"]:
        raise SystemExit("BLOCKED: no book-wide occurrences can be changed; no files changed")

    updated_reverse, changed_units = synchronize_reverse_links(reverse_doc, plan, args.old, args.new)
    print(f"alignment units with changed Spanish surface: {len(changed_units)}")
    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply after reviewing every listed occurrence.")
        return 0

    updated = apply_plan(doc, plan)
    phrase_temp = phrase_path.with_suffix(phrase_path.suffix + ".tmp")
    reverse_temp = reverse_path.with_suffix(reverse_path.suffix + ".tmp")
    phrase_temp.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reverse_temp.write_text(json.dumps(updated_reverse, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    phrase_temp.replace(phrase_path)
    reverse_temp.replace(reverse_path)

    audit_path = root / "workflow" / book / "lexical-edits.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "Book Default",
        "book": book,
        "originReference": args.reference,
        "target": {"surface": surface, "lemma": lemma, "strongs": strongs},
        "from": args.old,
        "to": args.new,
        "terminologyOccurrences": plan["terminologyOccurrences"],
        "changedReferences": [item["reference"] for item in plan["items"] if item["changed"]],
        "synchronizedReferences": [item["reference"] for item in plan["items"]],
        "changedAlignmentUnits": changed_units,
        "authority": "editorial-change-not-approval",
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"APPLIED: {phrase_path}")
    print(f"SYNCHRONIZED: {reverse_path}")
    print(f"AUDIT: {audit_path}")
    print("Changed phrases are lbf-preliminary; run canonical G0A next. No approval was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
