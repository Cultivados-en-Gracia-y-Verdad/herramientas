#!/usr/bin/env python3
"""Preview/apply a book-scoped lexical rendering change without creating approval."""
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


def find_phrase_file(root: Path, book: str) -> Path:
    candidates = [
        root / "translations" / "oshb-spine" / book / f"{book}-phrases.json",
        root / "translations" / "tr-spine" / book / f"{book}-phrases-tr.json",
        root / "translations" / f"{book}-phrases.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"phrase artifact not found for {book}")


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
    items = []
    total = mapped = 0
    old_pattern = pattern(old)
    new_pattern = pattern(new)
    for phrase in phrases:
        token_rows = phrase.get("tokenRows", []) if isinstance(phrase.get("tokenRows"), list) else []
        source_count = sum(1 for token in token_rows if matches(token, target))
        if not source_count:
            continue
        total += source_count
        spanish = str(phrase.get("spanish") or "")
        old_count = len(old_pattern.findall(spanish))
        new_count = len(new_pattern.findall(spanish))
        safe = old_count + new_count == source_count
        if safe:
            mapped += source_count
        proposed = old_pattern.sub(new, spanish) if safe else spanish
        items.append({
            "reference": phrase.get("reference"),
            "phraseIndex": phrase.get("phraseIndex"),
            "sourceCount": source_count,
            "safe": safe,
            "before": spanish,
            "after": proposed,
            "changed": safe and proposed != spanish,
        })
    return {
        "safe": total > 0 and mapped == total,
        "totalSourceOccurrences": total,
        "phrasesAffected": len(items),
        "phrasesChanged": sum(bool(item["changed"]) for item in items),
        "items": items,
    }


def apply_plan(doc: dict, plan: dict) -> dict:
    if not plan.get("safe"):
        raise ValueError("refusing partial book-wide edit")
    result = deepcopy(doc)
    by_index = {int(item["phraseIndex"]): item for item in plan["items"] if item["changed"]}
    for phrase in rows(result):
        item = by_index.get(int(phrase.get("phraseIndex", -1)))
        if not item:
            continue
        phrase["spanish"] = item["after"]
        phrase["suggestionSource"] = "lbf-preliminary"
        phrase["approval"] = {
            "status": "invalidated",
            "authority": "none",
            "invalidatedBecause": "spanish-changed",
            "invalidatedAt": datetime.now(timezone.utc).isoformat(),
        }
    return result


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
    path = find_phrase_file(root, book)
    doc = json.loads(path.read_text(encoding="utf-8"))
    strongs, lemma, surface = find_target(rows(doc), args.reference, args.source_surface)
    plan = build_plan(rows(doc), (strongs, lemma), args.old, args.new)

    print(f"book: {book}")
    print(f"origin: {args.reference}")
    print(f"source: {surface}")
    print(f"lemma: {lemma or '—'}")
    print(f"strongs: {strongs or '—'}")
    print(f"rendering: {args.old!r} -> {args.new!r}")
    print(f"source occurrences: {plan['totalSourceOccurrences']}")
    print(f"phrases affected: {plan['phrasesAffected']}")
    print(f"phrases changing: {plan['phrasesChanged']}")
    for item in plan["items"]:
        marker = "CHANGE" if item["changed"] else ("OK" if item["safe"] else "MANUAL")
        suffix = f" -> {item['after']}" if item["changed"] else ""
        print(f"{marker:6} {item['reference']}: {item['before']}{suffix}")

    if not plan["safe"]:
        raise SystemExit("BLOCKED: at least one source occurrence cannot be mapped safely; no files changed")
    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply after reviewing every listed occurrence.")
        return 0

    updated = apply_plan(doc, plan)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)

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
        "sourceOccurrences": plan["totalSourceOccurrences"],
        "changedReferences": [item["reference"] for item in plan["items"] if item["changed"]],
        "authority": "editorial-change-not-approval",
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"APPLIED: {path}")
    print(f"AUDIT: {audit_path}")
    print("Changed phrases are lbf-preliminary; run canonical G0A next. No approval was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
