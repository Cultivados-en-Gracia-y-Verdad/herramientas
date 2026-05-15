#!/usr/bin/env python3
"""Print ROOTS-GREEK data layers for one verse."""

import argparse
import csv
from pathlib import Path


def read_tsv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def rows_for(rows, book, ch, vs):
    return [r for r in rows if r.get("BOOK") == book and r.get("CH") == ch and r.get("VS") == vs]


def sort_key(row):
    raw = row.get("G_IDX") or row.get("FINITE_G_IDX") or row.get("CLAUSE_ID", "999")
    try:
        return int(str(raw).replace("C", ""))
    except Exception:
        return 999999


def main():
    p = argparse.ArgumentParser()
    p.add_argument("book")
    p.add_argument("chapter")
    p.add_argument("verse")
    p.add_argument("--db-dir", default="MNA/roots-greek/db")
    p.add_argument("--dataset-dir", default="MNA/roots-greek/dataset")
    args = p.parse_args()

    db = read_tsv(Path(args.db_dir) / f"{args.book}-verbs-connectors.tsv")
    spans = read_tsv(Path(args.dataset_dir) / f"{args.book}-clause-spans.tsv")
    tree = read_tsv(Path(args.dataset_dir) / f"{args.book}-structure-tree.tsv")
    certainty = read_tsv(Path(args.dataset_dir) / f"{args.book}-certainty-gate.tsv")

    dbv = rows_for(db, args.book, args.chapter, args.verse)
    spanv = rows_for(spans, args.book, args.chapter, args.verse)
    treev = rows_for(tree, args.book, args.chapter, args.verse)
    certv = rows_for(certainty, args.book, args.chapter, args.verse)

    print(f"# {args.book} {args.chapter}:{args.verse}")
    print("\n## DB verbs/connectors")
    for r in sorted(dbv, key=sort_key):
        print("\t".join([
            r.get("G_IDX", ""), r.get("TYPE", ""), r.get("ID", ""),
            r.get("GREEK", ""), r.get("LEMMA", ""), r.get("RMAC", ""),
            r.get("FINITE", ""), r.get("CONNECTOR_KIND", ""), r.get("DEFAULT_RELATION", ""),
        ]))

    print("\n## Clause spans")
    for r in sorted(spanv, key=sort_key):
        print("\t".join([
            r.get("CLAUSE_ID", ""), r.get("FINITE_G_IDX", ""), r.get("FINITE_GREEK", ""),
            r.get("SPAN_START", ""), r.get("SPAN_END", ""), r.get("SPAN_GIDX", ""),
            r.get("SPAN_TEXT", ""), r.get("BOUNDARY_NOTES", ""),
        ]))

    print("\n## Structure tree")
    for r in sorted(treev, key=lambda x: sort_key({"CLAUSE_ID": x.get("CLAUSE_ID", "")})):
        print("\t".join([
            r.get("CLAUSE_ID", ""), r.get("PARENT_CLAUSE", ""),
            r.get("TREE_DEPTH", ""), r.get("NODE_TYPE", ""),
            r.get("OWNERSHIP_SOURCE", ""), r.get("OWNERSHIP_CONNECTOR", ""),
            r.get("OWNERSHIP_CONFIDENCE", ""),
        ]))

    print("\n## Certainty rows")
    for r in certv:
        print("\t".join([
            r.get("LAYER", ""), r.get("ITEM_ID", ""), r.get("ITEM_TYPE", ""),
            r.get("CLASSIFICATION", ""), r.get("ALLOWED_DOWNSTREAM_USE", ""),
            r.get("BLOCKS_PASO_RENDERING", ""), r.get("REASON", ""),
        ]))


if __name__ == "__main__":
    main()
