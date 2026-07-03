#!/usr/bin/env python3
"""Merge OT token index + CGV glosses + AHRC entries into lemma compare index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OT_INDEX = ROOT / "data" / "index" / "ot-lemmas.jsonl"
AHRC = ROOT / "data" / "ahrc" / "strongs.jsonl"
OUT = ROOT / "data" / "index" / "lemma-compare.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build merged lemma compare index.")
    parser.add_argument("--ot-index", type=Path, default=OT_INDEX)
    parser.add_argument("--ahrc", type=Path, default=AHRC)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()

    ot_rows = {r["strongs"]: r for r in load_jsonl(args.ot_index)}
    ahrc_by_strongs: dict[str, list[dict]] = {}
    for row in load_jsonl(args.ahrc):
        ahrc_by_strongs.setdefault(row["strongs"], []).append(row)

    all_strongs = sorted(set(ot_rows) | set(ahrc_by_strongs), key=lambda s: int(s[1:]))
    merged: list[dict] = []

    for strongs in all_strongs:
        ot = ot_rows.get(strongs)
        ahrc = ahrc_by_strongs.get(strongs, [])
        merged.append({
            "strongs": strongs,
            "in_ot": ot is not None,
            "in_ahrc": bool(ahrc),
            "mna": ot,
            "ahrc": ahrc,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )

    ot_only = sum(1 for r in merged if r["in_ot"] and not r["in_ahrc"])
    ahrc_only = sum(1 for r in merged if r["in_ahrc"] and not r["in_ot"])
    both = sum(1 for r in merged if r["in_ot"] and r["in_ahrc"])
    print(f"wrote {args.output} ({len(merged)} lemmas: {both} linked, {ot_only} OT-only, {ahrc_only} AHRC-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
