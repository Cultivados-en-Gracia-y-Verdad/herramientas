#!/usr/bin/env python3
"""Label prophecy-marked verses fulfilled or unfulfilled.

Fulfilled: a clause on that verse uses fulfillment language (the 20
text-fulfillment rows, or a same-sentence πληρόω + γραφή/προφήτης tag).

Unfulfilled: the verse is marked by prophecy vocabulary (or sits in the
same MACULA sentence / tree nest as that marker) and no clause on that
verse uses fulfillment language.

This is not a date. It is not “still future.” It is only: the text never
said this verse’s word was fulfilled. No verse is closed because another
book later quotes it.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROP = ROOT / "prophecy"
REPORTS = ROOT / "reports"

FORMULA_GLOSS = {
    "the.utterance of.Yahweh",
    "the.utterance of.Yahweh ",
    "thus he.says Yahweh",
    "thus he.says Yahweh the.God of.Israel",
}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def ref_of(row: dict) -> str:
    return row.get("ref_protestant") or row.get("ref") or ""


def gloss_ok(row: dict) -> str:
    g = (row.get("own_gloss") or "").strip()
    return g


def book_order() -> dict[str, int]:
    eng = json.loads((ROOT / "data" / "versification" / "eng.json").read_text(encoding="utf-8"))
    return {code: i for i, code in enumerate(eng["maxVerses"])}


REF_PARSE = re.compile(r"^([0-9A-Z]+)\s+(\d+):(\d+|title)$")


def verse_sort_key(v: dict, order: dict[str, int]) -> tuple:
    ref = v.get("ref_protestant") or ""
    m = REF_PARSE.match(ref)
    if not m:
        return (order.get(v.get("book") or "", 999), 9999, 9999, ref)
    book, ch, vs = m.group(1), int(m.group(2)), m.group(3)
    verse_n = 0 if vs == "title" else int(vs)
    return (order.get(book, 999), ch, verse_n, ref)


def main() -> int:
    frames = load_jsonl(PROP / "frames.jsonl")
    oracles = load_jsonl(PROP / "oracle_content.jsonl")
    fills = load_jsonl(PROP / "text_fulfillments.jsonl")

    claim_refs = {ref_of(r) for r in fills if ref_of(r)}

    by_ref: dict[str, dict] = {}

    def bucket(row: dict, kind: str) -> None:
        ref = ref_of(row)
        if not ref:
            return
        rec = by_ref.setdefault(
            ref,
            {
                "ref_protestant": ref,
                "ref": row.get("ref"),
                "book": row.get("book"),
                "corpus": row.get("corpus"),
                "tags": set(),
                "glosses": [],
                "kinds": set(),
            },
        )
        rec["kinds"].add(kind)
        for t in row.get("frame_tags") or row.get("under_frame_tags") or row.get("markers") or []:
            rec["tags"].add(t)
        g = gloss_ok(row)
        if g and g not in rec["glosses"]:
            rec["glosses"].append(g)

    for r in frames:
        bucket(r, "frame")
    for r in oracles:
        bucket(r, "oracle")
    for r in fills:
        bucket(r, "fulfillment_claim")

    verses = []
    for ref, rec in by_ref.items():
        tags = rec["tags"]
        claimed = ref in claim_refs or (
            "fulfillment_citation" in tags
            and bool(
                tags
                & {
                    "prophet_named",
                    "prophecy_noun",
                    "spoken_by_lord_through_prophet",
                    "spirit_via_prophet",
                }
            )
        )
        status = "fulfilled" if claimed else "unfulfilled"
        # Prefer content glosses over bare formulas when both exist.
        content = [g for g in rec["glosses"] if g not in FORMULA_GLOSS]
        shown = content or rec["glosses"]
        verses.append(
            {
                "ref_protestant": ref,
                "ref": rec["ref"],
                "book": rec["book"],
                "corpus": rec["corpus"],
                "status": status,
                "tags": sorted(rec["tags"]),
                "kinds": sorted(rec["kinds"]),
                "own_gloss": " | ".join(shown[:8]),
            }
        )

    order = book_order()
    verses.sort(key=lambda v: verse_sort_key(v, order))
    unful = [v for v in verses if v["status"] == "unfulfilled"]
    ful = [v for v in verses if v["status"] == "fulfilled"]

    with (PROP / "unfulfilled.jsonl").open("w", encoding="utf-8") as fh:
        for v in unful:
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")
    with (PROP / "fulfilled.jsonl").open("w", encoding="utf-8") as fh:
        for v in ful:
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")

    REPORTS.mkdir(parents=True, exist_ok=True)
    cols = ["ref_protestant", "ref", "book", "status", "tags", "own_gloss"]
    for name, rows in (("unfulfilled.tsv", unful), ("fulfilled.tsv", ful)):
        with (REPORTS / name).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            w.writerow(cols)
            for r in rows:
                w.writerow(
                    [
                        r["ref_protestant"],
                        r.get("ref") or "",
                        r.get("book") or "",
                        r["status"],
                        "; ".join(r.get("tags") or []),
                        r.get("own_gloss") or "",
                    ]
                )

    summary = {
        "method": (
            "A prophecy-marked verse is fulfilled only if a clause on that same "
            "verse uses fulfillment language. Every other prophecy-marked verse "
            "is unfulfilled. Quotation in another book does not close it. "
            "The label is not a date."
        ),
        "unfulfilled_verses": len(unful),
        "fulfilled_verses": len(ful),
        "unfulfilled_by_book": dict(
            Counter(v["book"] for v in unful).most_common()
        ),
        "fulfilled_refs": [v["ref_protestant"] for v in ful],
    }
    (PROP / "status_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "unfulfilled_verses": len(unful),
                "fulfilled_verses": len(ful),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
