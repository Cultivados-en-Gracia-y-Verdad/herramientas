#!/usr/bin/env python3
"""
build_rule_candidates_v4.py

Robust candidate builder for validate_all.py summary output.

Fixes v3 limitations:
- Parses summary blocks like:
    --- 1corintios/1corintios-15-10 ---
- Accepts either align/token roots at the book folder level or parent level.
- Writes the same review TSV header used by v3/promote workflow.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

OUT_HEADER = [
    "approved",
    "stem",
    "ref",
    "greek_idx",
    "greek_span",
    "nbla_idx",
    "nbla_span",
    "suggested_type",
    "source",
    "reason",
    "confidence",
    "repeat_count",
    "phrase_key",
    "existing_rule",
    "duplicate_of",
    "yaml_suggestion",
]

ALIGN_HEADER = ["BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"]

BLOCK_RE = re.compile(r"^---\s+(?:(?P<path>[\wñáéíóúü]+)/)?(?P<stem>[\wñáéíóúü]+-\d+-\d+)\s+---\s*$", re.I)
FAIL_RE = re.compile(r"^FAIL\s+(?:(?P<path>[\wñáéíóúü]+)/)?(?P<stem>[\wñáéíóúü]+-\d+-\d+)\s*$", re.I)
UNUSED_RE = re.compile(r"NBLA\s+token\s+(\d+)\s+unused:\s*(.+)$", re.I)

FUNCTION_GREEK = {
    "ὁ", "ἡ", "τό", "τοῦ", "τῆς", "τῷ", "τῇ", "τόν", "τήν", "τὸ",
    "οἱ", "αἱ", "τά", "τῶν", "τοῖς", "ταῖς", "τούς", "τάς",
    "καί", "καὶ", "δὲ", "δέ", "γάρ", "γὰρ", "οὖν", "τε", "μέν", "ἀλλά", "ἀλλὰ",
    "ἤ", "εἰ", "ὅτι", "ἵνα", "ἐν", "εἰς", "ἐκ", "διὰ", "κατὰ", "πρὸς", "ἀπὸ",
}


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", str(s)) if unicodedata.category(ch) != "Mn")


def norm(s: str) -> str:
    s = strip_accents(str(s).strip().lower())
    s = re.sub(r"[.,;:!?¿¡\[\](){}\"'“”‘’··⸂⸃]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def compact(nums: Sequence[int]) -> str:
    nums = sorted(set(nums))
    if not nums:
        return "-"
    chunks: List[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        chunks.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
        start = prev = n
    chunks.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
    return ",".join(chunks)


def parse_idx(raw: str) -> List[int]:
    raw = (raw or "").strip()
    if not raw or raw == "-":
        return []
    out: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part or part == "-":
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                x, y = int(a), int(b)
                out.extend(range(min(x, y), max(x, y) + 1))
        elif part.isdigit():
            out.append(int(part))
    return sorted(set(out))


def stem_ref(stem: str) -> str:
    book, ch, vs = stem.rsplit("-", 2)
    return f"{book} {int(ch)}:{int(vs)}"


def stem_key(stem: str) -> Tuple[str, int, int]:
    book, ch, vs = stem.rsplit("-", 2)
    return (book, int(ch), int(vs))


def phrase_key(greek: str, nbla: str) -> str:
    return f"{norm(greek)} => {norm(nbla)}"


def yaml_suggestion(greek_span: str, nbla_span: str, suggested_type: str) -> str:
    if suggested_type.startswith("diagnostic") or suggested_type == "rejected":
        return ""
    greek_words = greek_span.split()
    nbla_words = nbla_span.split()
    if not greek_words or not nbla_words:
        return ""
    typ = "expanded" if suggested_type == "phrase-anchor" else suggested_type
    return '{"match":{"greek":' + repr(greek_words).replace("'", '"') + '},"action":{"nbla":' + repr(nbla_words).replace("'", '"') + f',"type":"{typ}","consume":{len(nbla_words)}}}'


@dataclass
class Failure:
    stem: str
    unused: Dict[int, str]


@dataclass
class Row:
    g_idx: int
    greek: str
    nbla_idx: List[int]
    nbla_text: str
    alignment: str

    @property
    def weak(self) -> bool:
        return (
            self.alignment.lower() in {"missing", "shared", "fallback", "unknown", "", "supplied"}
            or not self.nbla_idx
            or self.nbla_text.strip() in {"", "-", "[missing]"}
        )


def parse_validation_log(path: Path) -> Dict[str, Failure]:
    failures: Dict[str, Failure] = {}
    current: Optional[str] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = BLOCK_RE.match(line) or FAIL_RE.match(line)
        if m:
            current = m.group("stem")
            failures.setdefault(current, Failure(current, {}))
            continue
        if current is None:
            continue
        u = UNUSED_RE.search(line)
        if u:
            failures[current].unused[int(u.group(1))] = u.group(2).strip()
    return failures


def locate_file(root: Path, stem: str, suffix: str) -> Optional[Path]:
    book = stem.rsplit("-", 2)[0]
    candidates = [
        root / f"{stem}{suffix}",
        root / book / f"{stem}{suffix}",
    ]
    for c in candidates:
        if c.exists():
            return c
    matches = list(root.glob(f"**/{stem}{suffix}"))
    return matches[0] if matches else None


def load_alignment(path: Path) -> List[Row]:
    rows: List[Row] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        missing = [h for h in ALIGN_HEADER if h not in (reader.fieldnames or [])]
        if missing:
            raise RuntimeError(f"{path}: missing columns: {missing}")
        for r in reader:
            rows.append(Row(
                g_idx=int(r["G_IDX"]),
                greek=r["GREEK"].strip(),
                nbla_idx=parse_idx(r["NBLA_IDX"]),
                nbla_text=r["NBLA_TEXT"].strip(),
                alignment=r["ALIGNMENT"].strip(),
            ))
    return rows


def group_unused(unused: Dict[int, str]) -> List[List[Tuple[int, str]]]:
    groups: List[List[Tuple[int, str]]] = []
    for idx in sorted(unused):
        if not groups or idx != groups[-1][-1][0] + 1:
            groups.append([])
        groups[-1].append((idx, unused[idx]))
    return groups


def choose_window(rows: List[Row], group: List[Tuple[int, str]]) -> List[Row]:
    idxs = [i for i, _ in group]
    lo, hi = min(idxs), max(idxs)

    left = [r for r in rows if r.nbla_idx and max(r.nbla_idx) < lo]
    right = [r for r in rows if r.nbla_idx and min(r.nbla_idx) > hi]
    left_g = max((r.g_idx for r in left), default=0)
    right_g = min((r.g_idx for r in right), default=max((r.g_idx for r in rows), default=0) + 1)
    between = [r for r in rows if left_g < r.g_idx < right_g]

    if between:
        weak = [r for r in between if r.weak]
        base = weak if weak else between
    else:
        weak_all = [r for r in rows if r.weak]
        base = weak_all[:1] if weak_all else rows[:1]

    # Use a compact content-bearing window around weak rows.
    selected = base[:5]
    selected = [r for r in selected if norm(r.greek) not in {norm(x) for x in FUNCTION_GREEK}] or selected[:1]
    return selected[:5]


def candidate_type(win: List[Row], group: List[Tuple[int, str]]) -> str:
    if len(win) == 1 and len(group) == 1:
        return "direct"
    if len(win) == 1 and len(group) > 1:
        return "expanded"
    if len(win) > 1 and len(group) == 1:
        return "merged-forward"
    return "phrase-anchor"


def build_candidates(failures: Dict[str, Failure], align_root: Path, s_root: Path) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for stem in sorted(failures, key=stem_key):
        failure = failures[stem]
        align = locate_file(align_root, stem, ".tsv")
        sfile = locate_file(s_root, stem, ".txt")
        if not align:
            out.append(diag(stem, "diagnostic-missing-alignment", f"Could not find alignment TSV for {stem}"))
            continue
        if not sfile:
            out.append(diag(stem, "diagnostic-missing-s-token", f"Could not find Spanish token file for {stem}"))
            continue
        rows = load_alignment(align)
        for group in group_unused(failure.unused):
            win = choose_window(rows, group)
            greek_span = " ".join(r.greek for r in win) if win else "[no Greek window found]"
            nbla_span = " ".join(w for _, w in group)
            suggested = candidate_type(win, group) if win else "diagnostic-no-window"
            key = phrase_key(greek_span, nbla_span)
            row = {
                "approved": "",
                "stem": stem,
                "ref": stem_ref(stem),
                "greek_idx": compact([r.g_idx for r in win]) if win else "-",
                "greek_span": greek_span,
                "nbla_idx": compact([i for i, _ in group]),
                "nbla_span": nbla_span,
                "suggested_type": suggested,
                "source": "validation-failure",
                "reason": "contiguous unused NBLA span + nearby Greek weak/content window",
                "confidence": "0.45",
                "repeat_count": "1",
                "phrase_key": key,
                "existing_rule": "no",
                "duplicate_of": "",
                "yaml_suggestion": yaml_suggestion(greek_span, nbla_span, suggested),
            }
            out.append(row)
    counts = Counter(r["phrase_key"] for r in out)
    first: Dict[str, str] = {}
    for r in out:
        key = r["phrase_key"]
        r["repeat_count"] = str(counts[key])
        if key in first:
            r["duplicate_of"] = f"candidate in {first[key]}"
        else:
            first[key] = r["ref"]
    return out


def diag(stem: str, typ: str, reason: str) -> Dict[str, str]:
    return {
        "approved": "",
        "stem": stem,
        "ref": stem_ref(stem),
        "greek_idx": "-",
        "greek_span": "-",
        "nbla_idx": "-",
        "nbla_span": "-",
        "suggested_type": typ,
        "source": "diagnostic",
        "reason": reason,
        "confidence": "0.0",
        "repeat_count": "1",
        "phrase_key": f"{stem}:{typ}",
        "existing_rule": "no",
        "duplicate_of": "",
        "yaml_suggestion": "",
    }


def write_tsv(rows: List[Dict[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADER, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--validation-log", required=True)
    p.add_argument("--align-root", default="data/alignments/1corintios")
    p.add_argument("--s-token-root", default="data/s-tokens/1corintios")
    p.add_argument("--out", default="data/review/1corintios-rule_candidates.tsv")
    args = p.parse_args()

    failures = parse_validation_log(Path(args.validation_log))
    rows = build_candidates(failures, Path(args.align_root), Path(args.s_token_root))
    write_tsv(rows, Path(args.out))

    print("build_rule_candidates_v4")
    print(f"Failures parsed: {len(failures)}")
    print(f"Candidates written: {len(rows)}")
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
