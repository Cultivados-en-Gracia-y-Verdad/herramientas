#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Add morphology-derived grammatical features ("gram") to OT token jsonl files.

Usage:
  python3 MNA/scripts/ot_add_gram.py --book genesis --dry-run
  python3 MNA/scripts/ot_add_gram.py --book genesis --inplace
  python3 MNA/scripts/ot_add_gram.py --book genesis            # writes a .with_gram.jsonl copy

Input:
  MNA/datasets/interlinear/OT/<book>.tokens.jsonl

Output:
  - If --inplace: overwrites the original file after writing a .bak backup
  - Otherwise: writes <book>.tokens.jsonl.with_gram.jsonl
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


def parse_component(comp: str) -> Dict[str, Any]:
	"""Parse a single OSHB morph component WITHOUT slashes.

	Examples after stripping leading 'H' when present:
	  "C"        -> conjunction
	  "R"        -> preposition
	  "To"       -> object marker
	  "Td"       -> article marker (as seen in HTd)
	  "Ncbsa"    -> noun pattern
	  "Vqw3ms"   -> verb pattern
	  "Aamsa"    -> adjective pattern
	  "Rd"       -> preposition variant (handled outside here)
	"""
	part: Dict[str, Any] = {}
	if not comp:
		return part

	# Function markers
	if comp == "C":
		return {"pos": "C"}
	if comp == "R":
		return {"pos": "R"}
	if comp == "To":
		return {"pos": "To"}
	if comp == "Td":
		return {"pos": "Td"}

	# POS is first char for content components like N..., V..., A...
	pos = comp[0]
	rest = comp[1:]
	part["pos"] = pos

	# VERBS: V <stem> <aspect> <...png...>
	# Examples: Vqw3ms, Vqp3fs, Vqj3ms, Vprfsa
	if pos == "V":
		if len(rest) >= 1:
			part["stem"] = rest[0]  # e.g. q
		if len(rest) >= 2:
			part["aspect"] = rest[1]  # e.g. w, p, j, h, r...

		tail = rest[2:] if len(rest) > 2 else ""
		# Find PNG pattern: digit + [mfc] + [spd]
		for i in range(0, max(0, len(tail) - 2)):
			if tail[i].isdigit():
				person = int(tail[i])
				g = tail[i + 1]
				n = tail[i + 2]
				if g in ("m", "f", "c") and n in ("s", "p", "d"):
					part["person"] = person
					part["gender"] = g
					part["number"] = n
					break
		return part

	# NOUNS/ADJECTIVES: best-effort extraction (Pass 1)
	if pos in ("N", "A"):
		# State often last char
		if rest:
			last = rest[-1]
			if last.isalpha():
				part["state"] = last

		gender = None
		number = None
		for ch in rest:
			if gender is None and ch in ("m", "f", "c"):
				gender = ch
			if number is None and ch in ("s", "p", "d"):
				number = ch

		if gender is not None:
			part["gender"] = gender
		if number is not None:
			part["number"] = number

		return part

	# Other POS: keep only pos for now
	return part


def parse_morph(morph_raw: str) -> Dict[str, Any]:
	"""Parse OSHB morph strings like:
	  HNcmpa
	  HVqj3ms
	  HC/Vqw3ms
	  HTd/Ncbsa
	  HRd/Ncbsa
	  HR/Ncfsa
	  HC/R
	  HTo
	  HC/To

	Returns:
	  {
		"lang": "hbo",
		"raw": "...",
		"parts": [ {...}, {...}, ... ]
	  }
	"""
	gram: Dict[str, Any] = {"lang": "hbo", "raw": morph_raw, "parts": []}
	if not morph_raw:
		return gram

	comps = morph_raw.split("/")
	for comp in comps:
		# Each comp often starts with 'H' (language marker) in the first position
		if comp.startswith("H"):
			comp = comp[1:]

		# Handle simple function markers
		if comp in ("C", "R", "To", "Td"):
			gram["parts"].append(parse_component(comp))
			continue

		# Handle preposition variants like "Rd" (from HRd/Ncbsa)
		if comp.startswith("R") and len(comp) > 1 and comp != "R":
			gram["parts"].append({"pos": "R", "form": comp[1:]})
			continue

		gram["parts"].append(parse_component(comp))

	return gram


def iter_jsonl(path: Path):
	with path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			yield json.loads(line)


def write_jsonl(path: Path, rows: List[Dict[str, Any]]):
	with path.open("w", encoding="utf-8") as f:
		for r in rows:
			f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--book", required=True, help="Book slug, e.g. genesis")
	ap.add_argument("--inplace", action="store_true", help="Overwrite original file (with .bak backup)")
	ap.add_argument("--dry-run", action="store_true", help="Do not write; print a few parsed examples")
	args = ap.parse_args()

	tokens_path = Path(f"MNA/datasets/interlinear/OT/{args.book}.tokens.jsonl")
	if not tokens_path.exists():
		raise SystemExit(f"File not found: {tokens_path}")

	rows: List[Dict[str, Any]] = []
	examples = 0

	for r in iter_jsonl(tokens_path):
		morph_raw = r.get("morph", "")
		r["gram"] = parse_morph(morph_raw)

		if args.dry_run and examples < 10:
			print(r.get("surface"), morph_raw, "=>", r["gram"])
			examples += 1

		rows.append(r)

	if args.dry_run:
		print(f"DRY RUN OK: would update {len(rows)} tokens in {tokens_path}")
		return

	if args.inplace:
		bak = tokens_path.with_suffix(tokens_path.suffix + ".bak")
		tmp = tokens_path.with_suffix(tokens_path.suffix + ".tmp")
		shutil.copy2(tokens_path, bak)
		write_jsonl(tmp, rows)
		tmp.replace(tokens_path)
		print(f"WROTE inplace: {tokens_path} (backup: {bak})  rows={len(rows)}")
	else:
		out = tokens_path.with_suffix(tokens_path.suffix + ".with_gram.jsonl")
		write_jsonl(out, rows)
		print(f"WROTE: {out}  rows={len(rows)}")


if __name__ == "__main__":
	main()
