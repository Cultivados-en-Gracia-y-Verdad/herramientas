#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime, timezone
import yaml


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def item_checksum(payload) -> str:
    """Stable checksum of the evidence that a reviewer actually judged."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_existing_queue(path: Path):
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def preserve_review(new_items, old_queue):
    """Preserve decisions only when the item's review evidence is unchanged."""
    old_by_key = {}
    for old in old_queue.get("items", []):
        key = old.get("review_key")
        checksum = old.get("item_checksum")
        if key and checksum:
            old_by_key[key] = old

    preserved = 0
    reset = 0
    for item in new_items:
        old = old_by_key.get(item.get("review_key"))
        if old and old.get("item_checksum") == item.get("item_checksum"):
            old_review = old.get("review", {})
            if old_review.get("decision", "PENDING") != "PENDING":
                item["review"] = old_review
                preserved += 1
        elif old:
            reset += 1
    return preserved, reset


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def cv_from_ref(ref: str | None):
    m = re.search(r"(\d+):(\d+)$", str(ref or ""))
    return m.group(0) if m else None


def build_token_index(spine_doc):
    verses = spine_doc.get("verses")
    if not isinstance(verses, dict):
        raise SystemExit("Invalid spine: top-level 'verses' must be a dictionary.")

    idx = {}
    verse_tokens = {}

    for cv, rec in verses.items():
        toks = rec.get("tokens", []) if isinstance(rec, dict) else []
        vt = []
        for tok in toks:
            if not isinstance(tok, dict):
                continue
            tid = tok.get("sourceTokenId")
            if tid is None:
                continue
            tid = str(tid)
            compact = {
                "sourceTokenId": tid,
                "surface": tok.get("surface", ""),
                "lang": tok.get("lang"),
                "lemma": tok.get("lemma"),
                "morph": tok.get("morph"),
                "gloss": tok.get("gloss"),
            }
            idx[tid] = compact
            vt.append(compact)
        verse_tokens[cv] = vt
    return idx, verse_tokens


def phrase_mt_cv(phrase):
    ch = phrase.get("mtChapter")
    vs = phrase.get("mtVerse")
    if ch is not None and vs is not None:
        return f"{ch}:{vs}"
    return cv_from_ref(phrase.get("reference"))


def reverse_mt_cv(link):
    return cv_from_ref(link.get("mtReference")) or cv_from_ref(link.get("reference"))


def make_g0a(book, spine_doc, phrase_doc, spine_path, phrase_path):
    token_index, _ = build_token_index(spine_doc)
    phrases = phrase_doc.get("phrases")
    if not isinstance(phrases, list):
        raise SystemExit("Invalid phrase file: top-level 'phrases' must be a list.")

    items = []
    seq = 1

    for phrase in phrases:
        if not isinstance(phrase, dict):
            continue
        status = str(phrase.get("suggestionSource") or "UNKNOWN")
        if status == "lbf-approved":
            continue

        tids = [str(x) for x in phrase.get("sourceTokenIds", [])]
        source_tokens = [token_index[tid] for tid in tids if tid in token_index]

        review_key = f"G0A:{phrase.get('reference')}"
        evidence_payload = {
            "reference": phrase.get("reference"),
            "mt_reference": phrase.get("mtReference") or (
                f"Daniel {phrase.get('mtChapter')}:{phrase.get('mtVerse')}"
                if phrase.get("mtChapter") is not None and phrase.get("mtVerse") is not None
                else None
            ),
            "spanish": phrase.get("spanish", ""),
            "sourceTokenIds": tids,
            "source_tokens": source_tokens,
        }

        items.append({
            "id": f"G0A-{seq:04d}",
            "review_key": review_key,
            "item_checksum": item_checksum(evidence_payload),
            "gate": "G0A_TRANSLATION_APPROVAL",
            "reference": phrase.get("reference"),
            "mt_reference": evidence_payload["mt_reference"],
            "spanish": phrase.get("spanish", ""),
            "sourceTokenIds": tids,
            "source_tokens": source_tokens,
            "current_status": status,
            "review": {
                "decision": "PENDING",
                "reviewer": None,
                "runtime": None,
                "model": None,
                "confidence": None,
                "evidence": "",
                "notes": "",
                "reviewed_at": None,
            },
        })
        seq += 1

    return {
        "schema_version": "0.1",
        "queue": {
            "id": f"{book}-G0A",
            "gate": "G0A_TRANSLATION_APPROVAL",
            "book": book,
            "artifact_revision": "",
            "artifacts": {
                "spine": {
                    "path": str(spine_path),
                    "checksum_sha256": sha256(spine_path),
                },
                "phrases": {
                    "path": str(phrase_path),
                    "checksum_sha256": sha256(phrase_path),
                },
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN",
        },
        "summary": {
            "total": len(items),
            "approved_or_verified": 0,
            "pending": len(items),
            "needs_revision_or_relink": 0,
            "rejected": 0,
            "escalated": 0,
        },
        "items": items,
    }


def make_g0b(book, spine_doc, phrase_doc, reverse_doc, spine_path, phrase_path, reverse_path):
    token_index, _ = build_token_index(spine_doc)

    phrases = phrase_doc.get("phrases")
    if not isinstance(phrases, list):
        raise SystemExit("Invalid phrase file: top-level 'phrases' must be a list.")

    phrase_by_cv = {}
    for phrase in phrases:
        if isinstance(phrase, dict):
            cv = phrase_mt_cv(phrase)
            if cv:
                phrase_by_cv[cv] = phrase

    links = reverse_doc.get("links")
    if not isinstance(links, list):
        raise SystemExit("Invalid reverse-link file: top-level 'links' must be a list.")

    items = []
    seq = 1

    for link in links:
        if not isinstance(link, dict):
            continue
        record_status = str(link.get("status") or "UNKNOWN")
        cv = reverse_mt_cv(link)
        phrase = phrase_by_cv.get(cv, {})
        spanish = str(phrase.get("spanish") or "")

        units = link.get("units", [])
        if not isinstance(units, list):
            continue

        for unit in units:
            if not isinstance(unit, dict):
                continue

            method = str(unit.get("method") or "UNKNOWN")

            # Queue only units that have not already been explicitly verified.
            if record_status == "verified" and method not in {"gloss-match", "seed"}:
                continue

            tids = [str(x) for x in unit.get("sourceTokenIds", [])]
            source_tokens = [token_index[tid] for tid in tids if tid in token_index]

            start = unit.get("charStart")
            end = unit.get("charEnd")
            actual_surface = None
            if isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(spanish):
                actual_surface = spanish[start:end]

            review_key = f"G0B:{link.get('reference')}:{unit.get('unitId')}"
            evidence_payload = {
                "reference": link.get("reference"),
                "mt_reference": link.get("mtReference"),
                "unitId": unit.get("unitId"),
                "spanish_unit": unit.get("surface", ""),
                "actual_phrase_slice": actual_surface,
                "char_start": start,
                "char_end": end,
                "sourceTokenIds": tids,
                "source_tokens": source_tokens,
            }

            items.append({
                "id": f"G0B-{seq:05d}",
                "review_key": review_key,
                "item_checksum": item_checksum(evidence_payload),
                "gate": "G0B_ALIGNMENT_VERIFICATION",
                "reference": link.get("reference"),
                "mt_reference": link.get("mtReference"),
                "unitId": unit.get("unitId"),
                "spanish_unit": unit.get("surface", ""),
                "actual_phrase_slice": actual_surface,
                "char_start": start,
                "char_end": end,
                "sourceTokenIds": tids,
                "source_tokens": source_tokens,
                "current_method": method,
                "current_status": record_status,
                "review": {
                    "decision": "PENDING",
                    "reviewer": None,
                    "runtime": None,
                    "model": None,
                    "confidence": None,
                    "evidence": "",
                    "notes": "",
                    "reviewed_at": None,
                },
            })
            seq += 1

    return {
        "schema_version": "0.1",
        "queue": {
            "id": f"{book}-G0B",
            "gate": "G0B_ALIGNMENT_VERIFICATION",
            "book": book,
            "artifact_revision": "",
            "artifacts": {
                "spine": {
                    "path": str(spine_path),
                    "checksum_sha256": sha256(spine_path),
                },
                "phrases": {
                    "path": str(phrase_path),
                    "checksum_sha256": sha256(phrase_path),
                },
                "reverse_links": {
                    "path": str(reverse_path),
                    "checksum_sha256": sha256(reverse_path),
                },
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN",
        },
        "summary": {
            "total": len(items),
            "approved_or_verified": 0,
            "pending": len(items),
            "needs_revision_or_relink": 0,
            "rejected": 0,
            "escalated": 0,
        },
        "items": items,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--spine", required=True)
    ap.add_argument("--phrases", required=True)
    ap.add_argument("--reverse-links", required=True)
    ap.add_argument("--out-dir", default="gate0/queues")
    args = ap.parse_args()

    spine_path = Path(args.spine).expanduser().resolve()
    phrase_path = Path(args.phrases).expanduser().resolve()
    reverse_path = Path(args.reverse_links).expanduser().resolve()

    for p in (spine_path, phrase_path, reverse_path):
        if not p.is_file():
            raise SystemExit(f"Missing artifact: {p}")

    spine_doc = load_json(spine_path)
    phrase_doc = load_json(phrase_path)
    reverse_doc = load_json(reverse_path)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    g0a_path = out_dir / f"{args.book}-g0a-translation-review.yaml"
    g0b_path = out_dir / f"{args.book}-g0b-alignment-review.yaml"

    old_g0a = load_existing_queue(g0a_path)
    old_g0b = load_existing_queue(g0b_path)

    g0a = make_g0a(
        args.book, spine_doc, phrase_doc, spine_path, phrase_path
    )
    g0b = make_g0b(
        args.book, spine_doc, phrase_doc, reverse_doc,
        spine_path, phrase_path, reverse_path
    )

    g0a_preserved, g0a_reset = preserve_review(g0a["items"], old_g0a)
    g0b_preserved, g0b_reset = preserve_review(g0b["items"], old_g0b)

    # Recompute summaries after preservation.
    for queue, positive in ((g0a, "APPROVED"), (g0b, "VERIFIED")):
        decisions = [i.get("review", {}).get("decision", "PENDING") for i in queue["items"]]
        queue["summary"] = {
            "total": len(decisions),
            "approved_or_verified": sum(d == positive for d in decisions),
            "pending": sum(d == "PENDING" for d in decisions),
            "needs_revision_or_relink": sum(d in {"NEEDS_REVISION", "NEEDS_RELINK"} for d in decisions),
            "rejected": sum(d == "REJECTED" for d in decisions),
            "escalated": sum(d == "ESCALATE" for d in decisions),
        }

    g0a_path.write_text(
        yaml.safe_dump(g0a, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    g0b_path.write_text(
        yaml.safe_dump(g0b, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print(f"G0A queue: {g0a_path}")
    print(f"  items: {g0a['summary']['total']}")
    print(f"  preserved reviews: {g0a_preserved}")
    print(f"  reset changed items: {g0a_reset}")
    print(f"G0B queue: {g0b_path}")
    print(f"  items: {g0b['summary']['total']}")
    print(f"  preserved reviews: {g0b_preserved}")
    print(f"  reset changed items: {g0b_reset}")


if __name__ == "__main__":
    main()
