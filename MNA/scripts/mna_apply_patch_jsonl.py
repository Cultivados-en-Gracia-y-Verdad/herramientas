#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple, Any
​
Key = Tuple[int, int, int]  # (ch, vs, tok)
def read_jsonl(path: Path) -> list[dict[str, Any]]:
rows: list[dict[str, Any]] = []
for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
line = line.strip()
if not line:
continue
try:
rows.append(json.loads(line))
except Exception as e:
raise SystemExit(f"{path}:{i}: invalid JSON: {e}")
return rows
def main() -> None:
ap = argparse.ArgumentParser()
ap.add_argument("--book-jsonl", required=True)
ap.add_argument("--patch-jsonl", required=True)
ap.add_argument("--ch", type=int, required=True, help="Only apply to this chapter number")
ap.add_argument("--force", action="store_true", help="Overwrite existing es values (default: only fill '?')")
args = ap.parse_args()
book_path = Path(args.book_jsonl)
patch_path = Path(args.patch_jsonl)
book_rows = read_jsonl(book_path)
patch_rows = read_jsonl(patch_path)
patch: Dict[Key, str] = {}
for r in patch_rows:
try:
ch = int(r["ch"]); vs = int(r["vs"]); tok = int(r["tok"])
es = str(r["es"])
except Exception:
raise SystemExit(f"Bad patch row (needs ch/vs/tok/es): {r}")
if ch != args.ch:
continue
patch[(ch, vs, tok)] = es
changed = 0
out_lines: list[str] = []
for r in book_rows:
if str(r.get("book", "")) == "":
raise SystemExit("Book JSONL row missing 'book' field")
ch = int(r["ch"]); vs = int(r["vs"]); tok = int(r["tok"])
if ch == args.ch:
key = (ch, vs, tok)
if key in patch:
current = str(r.get("es", "?"))
if args.force or current == "?":
if current != patch[key]:
r["es"] = patch[key]
changed += 1
out_lines.append(json.dumps(r, ensure_ascii=False))
book_path.write_text("n".join(out_lines) + "n", encoding="utf-8")
print(f"UPDATED TOKENS: {changed}")
if name == "main":
main()