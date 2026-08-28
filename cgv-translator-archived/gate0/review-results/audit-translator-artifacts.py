#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    ap = argparse.ArgumentParser(
        description="Audit real cgv-translator OSHB/LBF artifacts for Gate 0."
    )
    ap.add_argument("--book", required=True)
    ap.add_argument("--spine", required=True)
    ap.add_argument("--phrases", required=True)
    ap.add_argument("--reverse-links", required=True)
    ap.add_argument("--export", required=True)
    ap.add_argument(
        "--policy",
        default=str(Path(__file__).with_name("gate0-policy.yaml")),
    )
    ap.add_argument(
        "--out",
        default="gate0/reports/translator-gate0-report.yaml",
    )
    args = ap.parse_args()

    spine_path = Path(args.spine).expanduser().resolve()
    phrase_path = Path(args.phrases).expanduser().resolve()
    reverse_path = Path(args.reverse_links).expanduser().resolve()
    export_path = Path(args.export).expanduser().resolve()
    policy_path = Path(args.policy).expanduser().resolve()

    for p in (spine_path, phrase_path, reverse_path, export_path, policy_path):
        if not p.is_file():
            raise SystemExit(f"Missing artifact: {p}")

    spine_doc = load_json(spine_path)
    phrase_doc = load_json(phrase_path)
    reverse_doc = load_json(reverse_path)
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}

    # ------------------------------------------------------------------
    # A. REAL OSHB SPINE SHAPE
    # {
    #   "bookId": "daniel",
    #   ...
    #   "verses": {
    #       "1:1": {"ch":1,"vs":1,"tokens":[...]},
    #       ...
    #   }
    # }
    # ------------------------------------------------------------------
    verses = spine_doc.get("verses")
    if not isinstance(verses, dict):
        raise SystemExit("Invalid spine: top-level 'verses' must be a dictionary.")

    spine_verse_keys = list(verses.keys())
    all_tokens = []
    malformed_token_records = []
    verse_key_mismatches = []

    for ref, verse in verses.items():
        if not isinstance(verse, dict):
            malformed_token_records.append({"reference": ref, "reason": "verse is not object"})
            continue

        ch = verse.get("ch")
        vs = verse.get("vs")
        if ch is not None and vs is not None and f"{ch}:{vs}" != ref:
            verse_key_mismatches.append({
                "key": ref,
                "record": f"{ch}:{vs}",
            })

        tokens = verse.get("tokens")
        if not isinstance(tokens, list):
            malformed_token_records.append({"reference": ref, "reason": "tokens is not list"})
            continue

        for token in tokens:
            if not isinstance(token, dict):
                malformed_token_records.append({
                    "reference": ref,
                    "reason": "token is not object",
                })
                continue
            all_tokens.append((ref, token))

    source_token_ids = [
        str(t.get("sourceTokenId"))
        for _, t in all_tokens
        if t.get("sourceTokenId") is not None
    ]
    source_id_counts = Counter(source_token_ids)
    duplicate_source_token_ids = sorted(
        tid for tid, n in source_id_counts.items() if n > 1
    )
    source_id_set = set(source_token_ids)

    missing_source_token_id = [
        {"reference": ref, "w": tok.get("w"), "surface": tok.get("surface", "")}
        for ref, tok in all_tokens
        if not tok.get("sourceTokenId")
    ]

    language_distribution = Counter(
        str(tok.get("lang", "UNKNOWN")) for _, tok in all_tokens
    )

    # ------------------------------------------------------------------
    # B. REAL PHRASE SHAPE
    # top-level "phrases": list
    # approval is in suggestionSource
    # reference = "Daniel 1:1"
    # ------------------------------------------------------------------
    phrases = phrase_doc.get("phrases")
    if not isinstance(phrases, list):
        raise SystemExit("Invalid phrase file: top-level 'phrases' must be a list.")

    phrase_refs = []
    phrase_ref_counts = Counter()
    invalid_phrase_token_refs = []
    empty_spanish = []
    phrase_status_distribution = Counter()
    unknown_phrase_statuses = []
    phrase_token_coverage = Counter()

    required_phrase_status = (
        policy.get("approval_policy", {})
        .get("required_phrase_status", "lbf-approved")
    )
    allow_preliminary = bool(
        policy.get("approval_policy", {}).get("allow_preliminary", False)
    )
    allow_unknown_status = bool(
        policy.get("approval_policy", {}).get("allow_unknown_status", False)
    )

    known_phrase_statuses = {"lbf-approved", "lbf-preliminary"}

    def ref_to_cv(reference):
        m = re.search(r"(\d+):(\d+)$", str(reference or ""))
        return m.group(0) if m else None

    phrase_by_cv = {}
    phrase_ordered_spanish = []

    for i, phrase in enumerate(phrases):
        if not isinstance(phrase, dict):
            continue

        reference = phrase.get("reference")

        # Compare phrase coverage to the OSHB spine using MT numbering.
        # Translator display references may follow a different verse numbering
        # scheme (for example Daniel 5:31 vs MT/OSHB 6:1).
        mt_ch = phrase.get("mtChapter")
        mt_vs = phrase.get("mtVerse")
        if mt_ch is not None and mt_vs is not None:
            cv = f"{mt_ch}:{mt_vs}"
        else:
            cv = ref_to_cv(reference)

        phrase_refs.append(cv)
        if cv:
            phrase_ref_counts[cv] += 1

        spanish = str(phrase.get("spanish") or "")
        phrase_ordered_spanish.append(spanish)
        if not spanish.strip():
            empty_spanish.append(reference or f"phraseIndex {i}")

        status = str(phrase.get("suggestionSource") or "UNKNOWN")
        phrase_status_distribution[status] += 1
        if status not in known_phrase_statuses:
            unknown_phrase_statuses.append({
                "reference": reference,
                "status": status,
            })

        tids = phrase.get("sourceTokenIds")
        if not isinstance(tids, list):
            tids = []

        bad = [str(tid) for tid in tids if str(tid) not in source_id_set]
        if bad:
            invalid_phrase_token_refs.append({
                "reference": reference,
                "tokenIds": bad,
            })

        for tid in tids:
            phrase_token_coverage[str(tid)] += 1

        if cv:
            phrase_by_cv[cv] = phrase

    duplicate_phrase_refs = sorted(
        ref for ref, n in phrase_ref_counts.items() if ref and n > 1
    )
    missing_phrase_refs = sorted(
        set(spine_verse_keys) - set(r for r in phrase_refs if r)
    )
    extra_phrase_refs = sorted(
        set(r for r in phrase_refs if r) - set(spine_verse_keys)
    )

    source_tokens_not_in_phrase_map = sorted(
        source_id_set - set(phrase_token_coverage)
    )
    source_tokens_in_multiple_phrases = sorted(
        tid for tid, n in phrase_token_coverage.items() if n > 1
    )

    # ------------------------------------------------------------------
    # C. REAL REVERSE LINK SHAPE
    # top-level "links": list
    # per verse: status
    # per unit: surface, sourceTokenIds, method
    # ------------------------------------------------------------------
    links = reverse_doc.get("links")
    if not isinstance(links, list):
        raise SystemExit("Invalid reverse-link file: top-level 'links' must be a list.")

    reverse_refs = []
    reverse_ref_counts = Counter()
    reverse_status_distribution = Counter()
    reverse_method_distribution = Counter()
    invalid_reverse_token_refs = []
    empty_reverse_units = []
    bad_char_ranges = []
    unit_surface_mismatch = []
    reverse_token_coverage = Counter()
    seed_or_unverified = []

    for link in links:
        if not isinstance(link, dict):
            continue

        reference = link.get("reference")

        # Reverse links also carry an MT/OSHB reference. Use that for
        # source-spine coverage checks instead of the display reference.
        mt_reference = link.get("mtReference")
        cv = ref_to_cv(mt_reference) if mt_reference else ref_to_cv(reference)

        reverse_refs.append(cv)
        if cv:
            reverse_ref_counts[cv] += 1

        record_status = str(link.get("status") or "UNKNOWN")
        reverse_status_distribution[record_status] += 1

        phrase = phrase_by_cv.get(cv)
        spanish = str(phrase.get("spanish") or "") if phrase else ""

        units = link.get("units")
        if not isinstance(units, list):
            units = []

        for unit in units:
            if not isinstance(unit, dict):
                continue

            surface = str(unit.get("surface") or "")
            method = str(unit.get("method") or "UNKNOWN")
            reverse_method_distribution[method] += 1

            if not surface.strip():
                empty_reverse_units.append({
                    "reference": reference,
                    "unitId": unit.get("unitId"),
                })

            start = unit.get("charStart")
            end = unit.get("charEnd")
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and spanish
            ):
                if start < 0 or end < start or end > len(spanish):
                    bad_char_ranges.append({
                        "reference": reference,
                        "unitId": unit.get("unitId"),
                        "charStart": start,
                        "charEnd": end,
                        "spanishLength": len(spanish),
                    })
                else:
                    actual = spanish[start:end]
                    if actual != surface:
                        unit_surface_mismatch.append({
                            "reference": reference,
                            "unitId": unit.get("unitId"),
                            "declared": surface,
                            "actual": actual,
                        })

            tids = unit.get("sourceTokenIds")
            if not isinstance(tids, list):
                tids = []

            bad = [str(tid) for tid in tids if str(tid) not in source_id_set]
            if bad:
                invalid_reverse_token_refs.append({
                    "reference": reference,
                    "unitId": unit.get("unitId"),
                    "surface": surface,
                    "tokenIds": bad,
                })

            for tid in tids:
                reverse_token_coverage[str(tid)] += 1

            if record_status in {
                "gloss-seed", "seed", "preliminary", "unverified"
            } or method == "gloss-match":
                seed_or_unverified.append({
                    "reference": reference,
                    "unitId": unit.get("unitId"),
                    "surface": surface,
                    "status": record_status,
                    "method": method,
                })

    duplicate_reverse_refs = sorted(
        ref for ref, n in reverse_ref_counts.items() if ref and n > 1
    )
    missing_reverse_refs = sorted(
        set(spine_verse_keys) - set(r for r in reverse_refs if r)
    )
    extra_reverse_refs = sorted(
        set(r for r in reverse_refs if r) - set(spine_verse_keys)
    )

    source_tokens_not_reverse_linked = sorted(
        source_id_set - set(reverse_token_coverage)
    )
    source_tokens_reverse_linked_multiple_times = sorted(
        tid for tid, n in reverse_token_coverage.items() if n > 1
    )

    # ------------------------------------------------------------------
    # D. REAL EXPORT SHAPE
    # Daniel export is currently a continuous Markdown text, not verse-marked.
    # Therefore the objective export check is:
    # normalized(export) == normalized(joined Spanish phrases in phrase order)
    # ------------------------------------------------------------------
    export_text = export_path.read_text(encoding="utf-8")
    expected_export = " ".join(phrase_ordered_spanish)

    normalized_export = normalize_text(export_text)
    normalized_expected = normalize_text(expected_export)

    export_exact_normalized_match = normalized_export == normalized_expected

    first_export_difference = None
    if not export_exact_normalized_match:
        limit = min(len(normalized_export), len(normalized_expected))
        pos = next(
            (i for i in range(limit)
             if normalized_export[i] != normalized_expected[i]),
            limit,
        )
        first_export_difference = {
            "position": pos,
            "expected_context": normalized_expected[max(0, pos-60):pos+120],
            "actual_context": normalized_export[max(0, pos-60):pos+120],
            "expected_length": len(normalized_expected),
            "actual_length": len(normalized_export),
        }

    # ------------------------------------------------------------------
    # E. POLICY / BLOCKERS
    # ------------------------------------------------------------------
    blockers = []

    if duplicate_source_token_ids:
        blockers.append("duplicate sourceTokenIds in OSHB spine")
    if missing_source_token_id:
        blockers.append("source tokens missing sourceTokenId")
    if malformed_token_records:
        blockers.append("malformed OSHB spine records")
    if verse_key_mismatches:
        blockers.append("spine verse-key/record mismatch")

    if missing_phrase_refs:
        blockers.append("OSHB verses missing phrase records")
    if extra_phrase_refs:
        blockers.append("phrase records not present in OSHB spine")
    if duplicate_phrase_refs:
        blockers.append("duplicate phrase records for verse")
    if invalid_phrase_token_refs:
        blockers.append("phrase records contain invalid sourceTokenIds")
    if empty_spanish:
        blockers.append("empty Spanish phrase records")
    if source_tokens_not_in_phrase_map:
        blockers.append("OSHB source tokens not represented in phrase map")
    if source_tokens_in_multiple_phrases:
        blockers.append("OSHB source tokens assigned to multiple phrase records")

    preliminary_count = phrase_status_distribution.get("lbf-preliminary", 0)
    required_count = phrase_status_distribution.get(required_phrase_status, 0)
    if preliminary_count and not allow_preliminary:
        blockers.append(
            f"{preliminary_count} phrase records remain lbf-preliminary"
        )
    if unknown_phrase_statuses and not allow_unknown_status:
        blockers.append("unknown phrase approval statuses remain")

    if missing_reverse_refs:
        blockers.append("OSHB verses missing reverse-link records")
    if extra_reverse_refs:
        blockers.append("reverse-link records not present in OSHB spine")
    if duplicate_reverse_refs:
        blockers.append("duplicate reverse-link records for verse")
    if invalid_reverse_token_refs:
        blockers.append("reverse links contain invalid sourceTokenIds")
    if empty_reverse_units:
        blockers.append("empty reverse-link units")
    if bad_char_ranges:
        blockers.append("reverse-link character ranges are invalid")
    if unit_surface_mismatch:
        blockers.append("reverse-link unit surfaces do not match phrase character ranges")
    if source_tokens_not_reverse_linked:
        blockers.append("OSHB source tokens are not reverse-linked")

    allow_seed_only = bool(
        policy.get("reverse_link_policy", {}).get("allow_seed_only", False)
    )
    if seed_or_unverified and not allow_seed_only:
        blockers.append(
            f"{len(seed_or_unverified)} reverse-link units remain seed/gloss-match"
        )

    if not export_exact_normalized_match:
        blockers.append("translations/<book>.md diverges from ordered phrase Spanish")

    report = {
        "schema_version": "0.3",
        "book": args.book,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer_status": "PASS" if not blockers else "FAIL",
        "blockers": blockers,
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
            "export": {
                "path": str(export_path),
                "checksum_sha256": sha256(export_path),
            },
        },
        "spine": {
            "bookId": spine_doc.get("bookId"),
            "textualBasis": spine_doc.get("textualBasis"),
            "verse_count": len(verses),
            "source_token_count": len(all_tokens),
            "language_distribution": dict(language_distribution),
            "duplicate_source_token_ids": duplicate_source_token_ids,
            "tokens_missing_sourceTokenId": missing_source_token_id,
            "malformed_token_records": malformed_token_records,
            "verse_key_mismatches": verse_key_mismatches,
            "declared_stats": spine_doc.get("stats", {}),
        },
        "phrases": {
            "bookId": phrase_doc.get("bookId"),
            "textualBasis": phrase_doc.get("textualBasis"),
            "record_count": len(phrases),
            "missing_oshb_mt_verses": missing_phrase_refs,
            "extra_verses": extra_phrase_refs,
            "duplicate_verse_records": duplicate_phrase_refs,
            "empty_spanish_records": empty_spanish,
            "invalid_sourceTokenIds": invalid_phrase_token_refs,
            "source_tokens_not_in_phrase_map_count": len(
                source_tokens_not_in_phrase_map
            ),
            "source_tokens_not_in_phrase_map": source_tokens_not_in_phrase_map,
            "source_tokens_in_multiple_phrases_count": len(
                source_tokens_in_multiple_phrases
            ),
            "source_tokens_in_multiple_phrases": source_tokens_in_multiple_phrases,
            "approval_status_distribution": dict(phrase_status_distribution),
            "required_phrase_status": required_phrase_status,
            "required_status_count": required_count,
            "unknown_status_records": unknown_phrase_statuses,
        },
        "reverse_links": {
            "bookId": reverse_doc.get("bookId"),
            "textualBasis": reverse_doc.get("textualBasis"),
            "record_count": len(links),
            "missing_oshb_mt_verses": missing_reverse_refs,
            "extra_verses": extra_reverse_refs,
            "duplicate_verse_records": duplicate_reverse_refs,
            "invalid_sourceTokenIds": invalid_reverse_token_refs,
            "empty_units": empty_reverse_units,
            "bad_character_ranges": bad_char_ranges,
            "unit_surface_mismatches": unit_surface_mismatch,
            "source_tokens_not_reverse_linked_count": len(
                source_tokens_not_reverse_linked
            ),
            "source_tokens_not_reverse_linked": source_tokens_not_reverse_linked,
            "source_tokens_reverse_linked_multiple_times_count": len(
                source_tokens_reverse_linked_multiple_times
            ),
            "status_distribution": dict(reverse_status_distribution),
            "method_distribution": dict(reverse_method_distribution),
            "seed_or_unverified_unit_count": len(seed_or_unverified),
            "seed_or_unverified_units": seed_or_unverified,
            "declared_stats": reverse_doc.get("stats", {}),
        },
        "export": {
            "comparison_method": (
                "normalized export text == normalized concatenation "
                "of phrase Spanish in phrase order"
            ),
            "normalized_exact_match": export_exact_normalized_match,
            "first_difference": first_export_difference,
        },
        "policy": policy,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print(f"Report: {out}")
    print(f"OSHB verses: {len(verses)}")
    print(f"OSHB tokens: {len(all_tokens)}")
    print(f"Phrase records: {len(phrases)}")
    print(
        "Phrase status:",
        ", ".join(
            f"{k}={v}" for k, v in sorted(phrase_status_distribution.items())
        ),
    )
    print(f"Reverse-link records: {len(links)}")
    print(
        "Reverse status:",
        ", ".join(
            f"{k}={v}" for k, v in sorted(reverse_status_distribution.items())
        ),
    )
    print(
        "Reverse methods:",
        ", ".join(
            f"{k}={v}" for k, v in sorted(reverse_method_distribution.items())
        ),
    )
    print(f"Export matches phrase text: {export_exact_normalized_match}")
    print(f"producer_status: {report['producer_status']}")
    print(f"blockers: {len(blockers)}")
    for blocker in blockers:
        print(f"- {blocker}")


if __name__ == "__main__":
    main()
