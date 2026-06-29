#!/usr/bin/env python3
"""ROOTS Lexicon Engine — Phase 1 observation layer (Greek verbs)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lexicon_engine.corpus import load_nt_tokens  # noqa: E402
from lexicon_engine.phase1 import build_verb_observation, collect_verb_occurrences, _lemma_filename  # noqa: E402
from lexicon_engine.validate import load_and_validate_json, validate_index, validate_lemma_record  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build ROOTS Lexicon Phase 1 (Greek verbs)")
    p.add_argument(
        "--nt-dir",
        type=Path,
        default=None,
        help="Directory of *.tokens.jsonl (default: MNA/datasets/interlinear/NT)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "lexicon" / "phase1" / "greek",
        help="Output directory for lemma JSON files",
    )
    p.add_argument("--context-before", type=int, default=6)
    p.add_argument("--context-after", type=int, default=6)
    p.add_argument("--collocation-window", type=int, default=5)
    p.add_argument("--limit", type=int, default=0, help="Process only N lemmas (debug)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    warnings: list[str] = []

    print("ROOTS Lexicon Phase 1")
    print("Language: Greek")
    print("Scope: verbs (Milestone 1)")

    tokens, verses = load_nt_tokens(args.nt_dir)
    books_processed = len({t.book for t in tokens})
    morph_missing = sum(1 for t in tokens if not t.morph)
    if morph_missing:
        warnings.append(f"{morph_missing} tokens missing morphology")

    warnings.append("ROOTS clause data unavailable — clause_roles left empty")
    warnings.append("Alignment data unavailable — subjects/objects deferred to Milestone 2")

    by_lemma = collect_verb_occurrences(
        tokens,
        verses,
        context_before=args.context_before,
        context_after=args.context_after,
    )

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    lemma_items = sorted(by_lemma.items(), key=lambda x: x[0])
    if args.limit:
        lemma_items = lemma_items[: args.limit]

    errors: list[str] = []
    index_entries = []
    occurrence_total = 0

    for lemma, occurrences in lemma_items:
        record = build_verb_observation(
            lemma,
            occurrences,
            context_before=args.context_before,
            context_after=args.context_after,
            collocation_window=args.collocation_window,
        )
        fname = _lemma_filename(lemma)
        out_path = out_dir / fname
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(record, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        loaded, json_err = load_and_validate_json(out_path)
        if json_err:
            errors.append(json_err)
        elif loaded:
            errors.extend(validate_lemma_record(loaded, out_path))

        occurrence_total += len(occurrences)
        index_entries.append(
            {
                "lemma": lemma,
                "file": fname,
                "occurrences": len(occurrences),
            }
        )

    index = {
        "language": "greek",
        "scope": "verbs",
        "milestone": 1,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "books_processed": books_processed,
        "lemma_count": len(index_entries),
        "occurrence_count": occurrence_total,
        "output_dir": str(out_dir.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else str(out_dir),
        "lemmas": index_entries,
    }
    index_path = out_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    idx_loaded, idx_err = load_and_validate_json(index_path)
    if idx_err:
        errors.append(idx_err)
    elif idx_loaded:
        errors.extend(validate_index(idx_loaded, out_dir))

    if not index_path.is_file():
        errors.append("index.json was not generated")

    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    print(f"Books processed: {books_processed}")
    print(f"Lemmas processed: {len(index_entries)}")
    print(f"Occurrences processed: {occurrence_total}")
    print(f"Output: {out_dir}")

    if errors:
        print("Build failed validation:", file=sys.stderr)
        for e in errors[:20]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
