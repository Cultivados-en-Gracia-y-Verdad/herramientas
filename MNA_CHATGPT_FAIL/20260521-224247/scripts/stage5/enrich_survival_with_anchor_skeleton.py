#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ANCHOR_FIELDS = [
    "anchor_order",
    "greek_surface",
    "greek_clean",
    "lemma",
    "mood",
    "mood_code",
    "morphology",
    "person",
    "person_code",
    "number",
    "number_code",
    "token_index_in_verse",
    "source_line_number",
    "stage1_ref_code",
    "skeleton_status",
]


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if raw:
                yield json.loads(raw)


def load_anchor_skeleton(path):
    anchors = {}
    for row in load_jsonl(path):
        if row.get("record_type") == "metadata":
            continue
        if row.get("record_type") != "anchor_skeleton_row":
            continue
        anchor_id = row.get("predicate_anchor_id")
        if anchor_id:
            anchors[anchor_id] = row
    return anchors


def enrich(row, anchors):
    anchor_id = row.get("unit_id") or row.get("clause_id")
    anchor = anchors.get(anchor_id)

    out = dict(row)
    out["anchor_enrichment_status"] = "FOUND" if anchor else "MISSING"

    if anchor:
        out["predicate_anchor_id"] = anchor.get("predicate_anchor_id")
        for field in ANCHOR_FIELDS:
            out[f"anchor_{field}"] = anchor.get(field)

    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("survival_jsonl", type=Path)
    p.add_argument("anchor_skeleton_jsonl", type=Path)
    p.add_argument("output_jsonl", type=Path)
    args = p.parse_args()

    anchors = load_anchor_skeleton(args.anchor_skeleton_jsonl)
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    missing = 0

    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for row in load_jsonl(args.survival_jsonl):
            enriched = enrich(row, anchors)
            if enriched.get("anchor_enrichment_status") == "MISSING":
                missing += 1
            f.write(json.dumps(enriched, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1

    print(f"WROTE {count} records -> {args.output_jsonl}")
    print(f"ANCHOR_MISSING: {missing}")


if __name__ == "__main__":
    main()
