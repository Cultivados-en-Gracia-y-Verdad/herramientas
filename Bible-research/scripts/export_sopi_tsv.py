#!/usr/bin/env python3
"""Export sopi/index.json to a one-row-per-record TSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sopi" / "index.json"
OUT = ROOT / "sopi" / "index.tsv"

COLS = [
    "id",
    "ref",
    "status",
    "clause_ids",
    "speaker",
    "addressee",
    "concerning",
    "actions",
    "condition",
    "time",
    "place",
    "gloss",
    "basis",
    "interpretation",
    "later_scripture",
]


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for rec in data["records"]:
            roles = rec.get("roles") or {}
            pred = rec.get("prediction") or {}
            src = rec.get("source") or {}
            w.writerow(
                {
                    "id": rec["id"],
                    "ref": rec["ref"],
                    "status": rec["status"],
                    "clause_ids": " ".join(rec.get("clause_ids") or []),
                    "speaker": roles.get("speaker") or "",
                    "addressee": roles.get("addressee") or "",
                    "concerning": "; ".join(roles.get("concerning") or []),
                    "actions": " | ".join(pred.get("actions") or []),
                    "condition": pred.get("condition") or "",
                    "time": pred.get("time") or "",
                    "place": pred.get("place") or "",
                    "gloss": src.get("gloss") or "",
                    "basis": rec.get("basis") or "",
                    "interpretation": rec.get("interpretation") or "",
                    "later_scripture": rec.get("later_scripture") or "",
                }
            )
    print(f"wrote {OUT} ({len(data['records'])} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
