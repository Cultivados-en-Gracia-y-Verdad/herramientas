#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = "stage2-frozen-predicate-anchors-builder-v1"

CONNECTORS = {
    "καί", "δέ", "γάρ", "οὖν", "ἀλλά", "ἵνα", "ὅτι", "εἰ", "ἐάν", "μή", "οὐ", "οὐκ", "οὐχ"
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if obj.get("record_type") == "metadata":
                continue
            rows.append(obj)
    return rows


def load_tokens(path: Path):
    tokens = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            if "\t" not in raw:
                continue
            idx, text = raw.split("\t", 1)
            tokens[int(idx)] = text.strip()
    return tokens


def previous_connector(tokens, token_index):
    prev = tokens.get(token_index - 1, "")
    return prev if prev in CONNECTORS else ""


def previous_subject(tokens, token_index):
    prev = tokens.get(token_index - 1, "")
    if prev and prev not in CONNECTORS:
        return prev
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("book")
    args = ap.parse_args()

    book = args.book.strip().lower()
    mna = root()

    stage1 = mna / "datasets" / "finite-verbs" / f"{book}.jsonl"
    token_file = mna / "datasets" / "g-tokens" / book / "tokens.txt"
    out = mna / "datasets" / "predicate-anchors" / f"{book}.jsonl"

    rows = load_jsonl(stage1)
    tokens = load_tokens(token_file) if token_file.exists() else {}

    anchors = []

    for i, row in enumerate(rows):
        token_index = int(row["token_index"])
        anchor_id = f"{book}-{i+1:05d}"
        prev_anchor = f"{book}-{i:05d}" if i > 0 else ""
        next_anchor = f"{book}-{i+2:05d}" if i < len(rows)-1 else ""
        prev_token_index = int(rows[i-1]["token_index"]) if i > 0 else token_index
        adjacency = token_index - prev_token_index if i > 0 else 0

        anchors.append({
            "record_type": "predicate_anchor",
            "anchor_id": anchor_id,
            "book": book,
            "chapter": row["chapter"],
            "verse": row["verse"],
            "token_index": token_index,
            "greek_form": row["greek_form"],
            "lemma": row["lemma"],
            "morphology": row["morphology"],
            "previous_anchor": prev_anchor,
            "next_anchor": next_anchor,
            "adjacency_distance": adjacency,
            "explicit_connector_before": previous_connector(tokens, token_index),
            "explicit_subject_before": previous_subject(tokens, token_index),
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"record_type":"metadata","builder_version":VERSION,"book":book,"rows_written":len(anchors)}, ensure_ascii=False, sort_keys=True)+"\n")
        for row in anchors:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n")

    print("MNA Stage 2 — Frozen Predicate Anchors Builder")
    print(f"BOOK: {book}")
    print(f"ROWS WRITTEN: {len(anchors)}")
    print(f"OUTPUT: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
