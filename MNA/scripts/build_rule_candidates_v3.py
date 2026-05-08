#!/usr/bin/env python3
"""
build_rule_candidates_v3.py

MNA v3 review-layer TSV builder.

Purpose:
- Run/read validate_all.py output.
- Find failing verse stems.
- Read existing alignment TSVs and Spanish token files.
- Compute unused NBLA spans directly from TSV coverage.
- Propose SAFER YAML rule candidates using adjacent Greek WINDOWS, not only a nearest singleton.
- Detect existing/duplicate rules.
- Write data/review/rule_candidates.tsv.

This script NEVER writes alignment_rules.yaml.

Run from MNA root:
  python3 scripts/build_rule_candidates_v3.py --run-validate

Helpful diagnostic run:
  python3 scripts/build_rule_candidates_v3.py --run-validate \
    --save-validation-log data/review/validate_failures.log
"""

from __future__ import annotations

SCRIPT_VERSION = "v3.1-quality-filter-2026-05-08"

import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ALIGN_HEADER = ["BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"]
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

FAIL_LINE_RE = re.compile(r"^FAIL\s+([\wñáéíóúü]+-\d+-\d+)\s*$", re.I)
SUMMARY_BLOCK_RE = re.compile(r"^---\s+([\wñáéíóúü]+-\d+-\d+)\s+---\s*$", re.I)
UNUSED_MSG_RE = re.compile(r"NBLA\s+token\s+(\d+)\s+unused:\s*(.+)$", re.I)
BAD_LINE_RE = re.compile(r"line\s+(\d+):", re.I)

MAX_GREEK_WINDOW = 5
MAX_SAFE_SINGLETON_CONSUME = 3
FUNCTION_WORDS = {
    "ὁ", "ἡ", "τό", "τοῦ", "τῆς", "τῷ", "τῇ", "τόν", "τήν", "τὸ", "οἱ", "αἱ", "τά", "τῶν", "τοῖς", "ταῖς", "τούς", "τάς",
    "καί", "δὲ", "δέ", "γάρ", "οὖν", "τε", "μέν", "ἀλλά", "ἤ", "εἰ", "ὅτι", "ἵνα",
}

BAD_SINGLETON_GREEK = FUNCTION_WORDS | {
    "περὶ", "ἐν", "εἰς", "ἐκ", "διὰ", "κατὰ", "πρὸς", "ἀπὸ",
    "τοῦ", "τῆς", "τῷ", "τῇ", "τὸν", "τὴν", "τὸ",
}

BAD_SINGLETON_SPANISH = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "a", "en", "con", "por", "para", "y", "pero",
    "que", "se", "lo", "le", "les", "su", "sus",
}

VERY_COMMON_SPANISH = {
    "todos", "todo", "y", "que", "de", "la", "el",
    "los", "las", "a", "en", "con", "para",
    "como", "por", "se", "lo", "le",
    "ustedes", "nosotros",
}

def is_semantically_weak_singleton(
    win: Sequence[AlignRow],
    group: Sequence[Tuple[int, str]],
) -> bool:
    if len(win) != 1:
        return False

    if len(group) != 1:
        return False

    spanish = norm_text(group[0][1])

    if spanish in VERY_COMMON_SPANISH:
        return True

    return False

def greek_clean_token(s: str) -> str:
    return norm_text(s).replace("ς", "σ")


def is_function_greek_token(s: str) -> bool:
    raw = str(s).strip()
    clean = greek_clean_token(raw)
    return raw in FUNCTION_WORDS or raw in BAD_SINGLETON_GREEK or clean in {greek_clean_token(x) for x in BAD_SINGLETON_GREEK}

def right_edge_is_content(win: Sequence[AlignRow]) -> bool:
    if not win:
        return False

    return not is_function_greek_token(win[-1].greek)

def has_content_anchor(win: Sequence[AlignRow]) -> bool:
    return any(not is_function_greek_token(r.greek) for r in win)


def is_bad_spanish_singleton(group: Sequence[Tuple[int, str]]) -> bool:
    if len(group) != 1:
        return False
    return norm_text(group[0][1]) in BAD_SINGLETON_SPANISH

def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", str(s)) if unicodedata.category(ch) != "Mn")


def norm_text(s: Any) -> str:
    s = strip_accents(str(s).strip().lower())
    s = re.sub(r"[.,;:!?¿¡\[\](){}\"'“”‘’··⸂⸃]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def token_to_text(x: Any) -> str:
    """Normalize YAML tokens. PyYAML reads unquoted `no` as False; convert back safely."""
    if x is False:
        return "no"
    if x is True:
        return "sí"
    if x is None:
        return ""
    return str(x)


def as_text_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, (list, tuple)):
        return [token_to_text(i) for i in x if token_to_text(i) != ""]
    return [token_to_text(x)]


def stem_to_ref(stem: str) -> str:
    book, ch, vs = stem.rsplit("-", 2)
    return f"{book} {int(ch)}:{int(vs)}"


def stem_book(stem: str) -> str:
    return stem.rsplit("-", 2)[0]


def stem_sort_key(stem: str) -> Tuple[str, int, int]:
    book, ch, vs = stem.rsplit("-", 2)
    return (book, int(ch), int(vs))


def parse_idx_list(raw: Any) -> List[int]:
    raw = str(raw).strip()
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
                start, end = int(a), int(b)
                out.extend(range(min(start, end), max(start, end) + 1))
        elif part.isdigit():
            out.append(int(part))
    return sorted(set(out))


def compact_span(nums: Sequence[int]) -> str:
    nums = sorted(set(int(n) for n in nums))
    if not nums:
        return "-"
    chunks: List[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            chunks.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
            start = prev = n
    chunks.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
    return ",".join(chunks)


def load_tokens(path: Path) -> List[Tuple[int, str]]:
    tokens: List[Tuple[int, str]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"{path}:{line_no}: invalid token line: {line}")
            idx_raw, tok = parts
            tokens.append((int(idx_raw), tok))
    return tokens


@dataclass
class AlignRow:
    line_no: int
    book: str
    ch: str
    vs: str
    g_idx: int
    greek: str
    nbla_idx_raw: str
    nbla_text: str
    alignment: str

    @property
    def nbla_indexes(self) -> List[int]:
        return parse_idx_list(self.nbla_idx_raw)

    @property
    def is_weak(self) -> bool:
        a = self.alignment.strip().lower()
        return (
            a in {"missing", "shared", "fallback", "unknown", "", "supplied"}
            or self.nbla_idx_raw.strip() in {"", "-"}
            or self.nbla_text.strip() in {"", "-", "[missing]"}
        )


@dataclass
class FailureInfo:
    stem: str
    unused_from_log: Dict[int, str]
    bad_lines: List[int]


@dataclass
class Candidate:
    stem: str
    ref: str
    greek_idx: str
    greek_span: str
    nbla_idx: str
    nbla_span: str
    suggested_type: str
    source: str
    reason: str
    confidence: float
    phrase_key: str
    existing_rule: str = "no"
    duplicate_of: str = ""
    repeat_count: int = 1
    yaml_suggestion: str = ""
    approved: str = ""


def load_alignment(path: Path) -> List[AlignRow]:
    rows: List[AlignRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames or []
        missing = [h for h in ALIGN_HEADER if h not in fieldnames]
        if missing:
            raise ValueError(f"{path}: missing TSV columns: {missing}")
        for line_no, row in enumerate(reader, 2):
            rows.append(
                AlignRow(
                    line_no=line_no,
                    book=row["BOOK"],
                    ch=row["CH"],
                    vs=row["VS"],
                    g_idx=int(row["G_IDX"]),
                    greek=row["GREEK"],
                    nbla_idx_raw=row["NBLA_IDX"],
                    nbla_text=row["NBLA_TEXT"],
                    alignment=row["ALIGNMENT"],
                )
            )
    return rows


def run_validate(cmd: Sequence[str]) -> str:
    result = subprocess.run(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    return result.stdout


def default_validate_cmd() -> List[str]:
    if Path("scripts/validate_all.py").exists():
        return [sys.executable, "scripts/validate_all.py"]
    return [sys.executable, "validate_all.py"]


def parse_validation_output(text: str) -> Dict[str, FailureInfo]:
    failures: Dict[str, FailureInfo] = {}
    current: Optional[str] = None
    for raw in text.splitlines():
        line = raw.strip()
        m_fail = FAIL_LINE_RE.match(line)
        m_block = SUMMARY_BLOCK_RE.match(line)
        if m_fail or m_block:
            current = (m_fail or m_block).group(1)  # type: ignore[union-attr]
            failures.setdefault(current, FailureInfo(current, {}, []))
            continue
        if current is None:
            continue
        m_unused = UNUSED_MSG_RE.search(line)
        if m_unused:
            failures[current].unused_from_log[int(m_unused.group(1))] = m_unused.group(2).strip()
            continue
        m_bad = BAD_LINE_RE.search(line)
        if m_bad:
            failures[current].bad_lines.append(int(m_bad.group(1)))
    return failures


def used_nbla_indexes(rows: Sequence[AlignRow]) -> set[int]:
    used: set[int] = set()
    for r in rows:
        used.update(r.nbla_indexes)
    return used


def find_unused_from_tsv(rows: Sequence[AlignRow], s_tokens: Sequence[Tuple[int, str]]) -> Dict[int, str]:
    used = used_nbla_indexes(rows)
    return {idx: tok for idx, tok in s_tokens if idx not in used}


def group_contiguous(index_to_word: Dict[int, str]) -> List[List[Tuple[int, str]]]:
    groups: List[List[Tuple[int, str]]] = []
    for idx in sorted(index_to_word):
        if not groups or idx != groups[-1][-1][0] + 1:
            groups.append([])
        groups[-1].append((idx, index_to_word[idx]))
    return groups


def duplicate_key(greek_words: Sequence[str] | str, nbla_words: Sequence[str] | str) -> str:
    g = greek_words if isinstance(greek_words, str) else " ".join(token_to_text(x) for x in greek_words)
    s = nbla_words if isinstance(nbla_words, str) else " ".join(token_to_text(x) for x in nbla_words)
    return f"{norm_text(g)} => {norm_text(s)}"


def load_rules(path: Path) -> Any:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")
    if yaml is None:
        return None
    try:
        return yaml.safe_load(raw)
    except Exception as e:
        print(f"WARNING: Could not parse YAML rules at {path}: {e}", file=sys.stderr)
        return None


def collect_existing_rule_keys(obj: Any) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    if not obj:
        return keys
    rules = obj.get("rules", []) if isinstance(obj, dict) else []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        match = rule.get("match", {}) or {}
        action = rule.get("action", {}) or {}
        greek_words = as_text_list(match.get("greek", []))
        nbla_words = as_text_list(action.get("nbla", []))
        if greek_words and nbla_words:
            keys[duplicate_key(greek_words, nbla_words)] = f"rules[{i}]"
    return keys


def make_yaml_suggestion(greek_span: str, nbla_span: str, suggested_type: str) -> str:
    greek_words = greek_span.split()
    nbla_words = nbla_span.split()
    if not greek_words or not nbla_words or suggested_type.startswith("diagnostic") or suggested_type == "rejected":
        return ""
    obj = {
        "match": {"greek": greek_words},
        "action": {
            "nbla": nbla_words,
            "type": suggested_type if suggested_type != "phrase-anchor" else "expanded",
            "consume": len(nbla_words),
        },
    }
    return json.dumps(obj, ensure_ascii=False)


def locate_alignment_file(stem: str, align_root: Path) -> Optional[Path]:
    book = stem_book(stem)
    candidates = [align_root / book / f"{stem}.tsv", align_root / f"{stem}.tsv"]
    for p in candidates:
        if p.exists():
            return p
    matches = list(align_root.glob(f"**/{stem}.tsv"))
    return matches[0] if matches else None


def choose_rules_path(explicit: Optional[Path]) -> Path:
    if explicit:
        return explicit
    for p in [Path("data/rules/alignment_rules.yaml"), Path("alignment_rules.yaml")]:
        if p.exists():
            return p
    return Path("data/rules/alignment_rules.yaml")


def get_local_rows_for_gap(rows: Sequence[AlignRow], nbla_idxs: Sequence[int], bad_lines: Sequence[int]) -> List[AlignRow]:
    """Return a small ordered row region around the unused NBLA gap."""
    if not rows:
        return []
    u_min, u_max = min(nbla_idxs), max(nbla_idxs)

    # Use validator bad lines when available, widened to context.
    if bad_lines:
        bad_gs = [r.g_idx for r in rows if r.line_no in set(bad_lines)]
        if bad_gs:
            lo, hi = min(bad_gs) - 2, max(bad_gs) + 2
            return [r for r in rows if lo <= r.g_idx <= hi]

    left_candidates = [r for r in rows if r.nbla_indexes and max(r.nbla_indexes) < u_min]
    right_candidates = [r for r in rows if r.nbla_indexes and min(r.nbla_indexes) > u_max]
    left_g = max((r.g_idx for r in left_candidates), default=0)
    right_g = min((r.g_idx for r in right_candidates), default=max(r.g_idx for r in rows) + 1)

    between = [r for r in rows if left_g < r.g_idx < right_g]
    if between:
        # Do not allow a huge uncontrolled span.
        if len(between) <= MAX_GREEK_WINDOW:
            return between
        weak = [r for r in between if r.is_weak]
        center = weak[0].g_idx if weak else between[len(between) // 2].g_idx
        return [r for r in rows if center - 2 <= r.g_idx <= center + 2]

    # Fallback: nearest Greek row to NBLA gap by covered NBLA distance.
    scored: List[Tuple[int, AlignRow]] = []
    for r in rows:
        if r.nbla_indexes:
            dist = min(abs(i - u_min) for i in r.nbla_indexes)
        else:
            dist = 0 if r.is_weak else 99
        scored.append((dist, r))
    scored.sort(key=lambda x: (x[0], x[1].g_idx))
    center = scored[0][1].g_idx
    return [r for r in rows if center - 2 <= r.g_idx <= center + 2]


def candidate_type(greek_rows: Sequence[AlignRow], nbla_group: Sequence[Tuple[int, str]]) -> str:
    g_len = len(greek_rows)
    s_len = len(nbla_group)
    if g_len == 1 and s_len == 1:
        return "direct"
    if g_len == 1 and s_len > 1:
        return "expanded"
    if g_len > 1 and s_len == 1:
        return "merged-forward"
    return "phrase-anchor"


def window_score(win: Sequence[AlignRow], nbla_group: Sequence[Tuple[int, str]]) -> float:
    g_len = len(win)
    s_len = len(nbla_group)

    ownership_ratio = s_len / max(g_len, 1)

    score = 0.30

    # Weak rows are likely repair locations.
    if any(r.is_weak for r in win):
        score += 0.18

    # Prefer multi-token Greek windows for longer Spanish spans.
    if s_len > MAX_SAFE_SINGLETON_CONSUME and g_len > 1:
        score += 0.22

    # Prefer compact phrase-sized Greek windows.
    if 2 <= g_len <= 4:
        score += 0.12

    # Direct one-to-one mappings can be valid, but should not dominate.
    if g_len == 1 and s_len == 1:
        score += 0.08

    # Penalize unsafe singleton expansions.
    if g_len == 1 and s_len > MAX_SAFE_SINGLETON_CONSUME:
        score -= 0.55

    # Penalize Greek function-word ownership.
    if g_len == 1 and is_function_greek_token(win[0].greek):
        score -= 0.40

    # Penalize very long Spanish ownership.
    # Strongly penalize unrealistic ownership ratios.
        ownership_ratio = s_len / max(g_len, 1)

    if ownership_ratio >= 4:
        score -= 0.35

    if ownership_ratio >= 6:
        score -= 0.55

    if ownership_ratio >= 8:
        score -= 0.75

    # Strongly prefer windows whose last Greek token is weak.
    # This helps avoid drift like Δαυὶδ → carne when σάρκα is closer.
    if win[-1].is_weak:
        score += 0.20

    # Penalize windows that begin with a content word but end before the likely weak row.
    if g_len == 1 and not win[0].is_weak:
        score -= 0.25

    # Prefer windows ending in a lexical/content anchor.
    if right_edge_is_content(win):
        score += 0.18
    else:
        score -= 0.22

    return max(0.01, min(score, 0.95))


def make_windows(local_rows: Sequence[AlignRow], nbla_group: Sequence[Tuple[int, str]]) -> List[List[AlignRow]]:
    """Generate Greek window candidates. Prefer windows containing weak rows."""
    rows = list(local_rows)
    if not rows:
        return []

    windows: List[List[AlignRow]] = []
    n = len(rows)
    weak_positions = [i for i, r in enumerate(rows) if r.is_weak]

    for length in range(1, min(MAX_GREEK_WINDOW, n) + 1):
        for start in range(0, n - length + 1):
            end = start + length

            # Keep only windows that touch a weak row, unless there are no weak rows.
            if weak_positions and not any(start <= p < end for p in weak_positions):
                continue

            win = rows[start:end]

            # Reject impossible ownership expansions before scoring.
            # Example: 2 Greek tokens should not own 8 Spanish tokens.
            ownership_ratio = len(nbla_group) / max(len(win), 1)
            if ownership_ratio > 3.5:
                continue

            windows.append(win)

    # Deduplicate by g_idx tuple.
    seen: set[Tuple[int, ...]] = set()
    unique: List[List[AlignRow]] = []

    for win in windows:
        key = tuple(r.g_idx for r in win)

        if key not in seen:
            seen.add(key)
            unique.append(win)

    unique = [w for w in unique if has_content_anchor(w)]
    unique.sort(key=lambda w: (-window_score(w, nbla_group), len(w), w[0].g_idx))

    return unique


def is_rejected_singleton(win: Sequence[AlignRow], nbla_group: Sequence[Tuple[int, str]]) -> bool:
    if not win:
        return True

    # Never allow candidates with no meaningful Greek anchor.
    if not has_content_anchor(win):
        return True

    # Reject unsafe one-Greek-token ownership of long Spanish spans.
    if len(win) == 1 and len(nbla_group) > MAX_SAFE_SINGLETON_CONSUME:
        return True

    # Reject Greek function word → Spanish phrase.
    if len(win) == 1 and is_function_greek_token(win[0].greek) and len(nbla_group) > 1:
        return True

    # Reject Greek function word → weak Spanish singleton.
    if len(win) == 1 and is_function_greek_token(win[0].greek) and is_bad_spanish_singleton(nbla_group):
        return True

    # Reject content Greek singleton → very common Spanish singleton.
    if is_semantically_weak_singleton(win, nbla_group):
        return True

    return False


def candidate_from_window(stem: str, win: Sequence[AlignRow], group: Sequence[Tuple[int, str]], reason: str, existing: Dict[str, str]) -> Candidate:
    greek_span = " ".join(r.greek for r in win)
    greek_idx = compact_span([r.g_idx for r in win])
    nbla_span = " ".join(word for _, word in group)
    nbla_idx = compact_span([idx for idx, _ in group])
    suggested = candidate_type(win, group)
    key = duplicate_key(greek_span, nbla_span)
    confidence = window_score(win, group)
    c = Candidate(
        stem=stem,
        ref=stem_to_ref(stem),
        greek_idx=greek_idx,
        greek_span=greek_span,
        nbla_idx=nbla_idx,
        nbla_span=nbla_span,
        suggested_type=suggested,
        source="validation-failure",
        reason=reason,
        confidence=confidence,
        phrase_key=key,
        existing_rule="yes" if key in existing else "no",
        duplicate_of=existing.get(key, ""),
    )
    c.yaml_suggestion = make_yaml_suggestion(c.greek_span, c.nbla_span, c.suggested_type)
    return c


def build_candidates(
    failures: Dict[str, FailureInfo],
    align_root: Path,
    s_token_root: Path,
    existing: Dict[str, str],
) -> List[Candidate]:
    candidates: List[Candidate] = []

    for stem in sorted(failures, key=stem_sort_key):
        info = failures[stem]
        ref = stem_to_ref(stem)
        alignment_file = locate_alignment_file(stem, align_root)
        book = stem_book(stem)
        s_file = s_token_root / book / f"{stem}.txt"

        if not alignment_file:
            candidates.append(Candidate(stem, ref, "-", "[alignment TSV not found]", "-", "-", "diagnostic-missing-file", "missing-file", f"Could not find {stem}.tsv under {align_root}", 0.0, f"{stem}:missing-alignment"))
            continue
        if not s_file.exists():
            candidates.append(Candidate(stem, ref, "-", "[Spanish token file not found]", "-", "-", "diagnostic-missing-file", "missing-file", f"Could not find {s_file}", 0.0, f"{stem}:missing-s-token"))
            continue

        rows = load_alignment(alignment_file)
        s_tokens = load_tokens(s_file)
        unused = find_unused_from_tsv(rows, s_tokens)
        # Merge log unused, but TSV computation remains primary.
        for k, v in info.unused_from_log.items():
            unused.setdefault(k, v)

        if not unused:
            weak = [r for r in rows if r.is_weak]
            if weak:
                for r in weak[:5]:
                    key = duplicate_key(r.greek, r.nbla_text or "-")
                    c = Candidate(
                        stem=stem,
                        ref=ref,
                        greek_idx=compact_span([r.g_idx]),
                        greek_span=r.greek,
                        nbla_idx=r.nbla_idx_raw or "-",
                        nbla_span=r.nbla_text or "-",
                        suggested_type="manual-review",
                        source="weak-row-no-unused-nbla",
                        reason="Validation failed; no unused NBLA tokens computed, but weak alignment row exists",
                        confidence=0.20,
                        phrase_key=key,
                    )
                    candidates.append(c)
            else:
                candidates.append(Candidate(stem, ref, "-", "[no candidate]", "-", "-", "diagnostic-no-candidate", "validator", "Validation failed, but no unused NBLA tokens or weak rows were found", 0.0, f"{stem}:no-candidate"))
            continue

        for group in group_contiguous(unused):
            nbla_idxs = [idx for idx, _ in group]
            local_rows = get_local_rows_for_gap(rows, nbla_idxs, info.bad_lines)
            windows = make_windows(local_rows, group)
            safe_windows = [w for w in windows if not is_rejected_singleton(w, group)]

            if safe_windows:
                # Write the best two candidates max. The TSV is for review, not auto-application.
                for n, win in enumerate(safe_windows[:2], 1):
                    reason = "contiguous unused NBLA span + adjacent Greek window"
                    if n == 2:
                        reason += "; alternate candidate"
                    candidates.append(candidate_from_window(stem, win, group, reason, existing))
            elif windows:
                # Do not produce a YAML suggestion for rejected singleton-long ownership.
                win = windows[0]
                greek_span = " ".join(r.greek for r in win)
                nbla_span = " ".join(word for _, word in group)
                c = Candidate(
                    stem=stem,
                    ref=ref,
                    greek_idx=compact_span([r.g_idx for r in win]),
                    greek_span=greek_span,
                    nbla_idx=compact_span(nbla_idxs),
                    nbla_span=nbla_span,
                    suggested_type="rejected",
                    source="validation-failure",
                    reason="rejected unsafe singleton/function-word candidate; needs manual review or wider Greek span",
                    confidence=0.05,
                    phrase_key=duplicate_key(greek_span, nbla_span),
                )
                candidates.append(c)
            else:
                nbla_span = " ".join(word for _, word in group)
                candidates.append(Candidate(stem, ref, "-", "[no Greek window found]", compact_span(nbla_idxs), nbla_span, "diagnostic-no-window", "validation-failure", "Unused NBLA span found, but no Greek window could be selected", 0.0, f"{stem}:{compact_span(nbla_idxs)}"))

    # Duplicate/repetition detection.
    counts = Counter(c.phrase_key for c in candidates)
    first_seen: Dict[str, str] = {}
    for c in candidates:
        c.repeat_count = counts[c.phrase_key]
        if c.phrase_key not in first_seen:
            first_seen[c.phrase_key] = c.ref
        elif not c.duplicate_of:
            c.duplicate_of = f"candidate in {first_seen[c.phrase_key]}"
        if c.repeat_count >= 2 and c.existing_rule != "yes" and c.suggested_type not in {"rejected"} and not c.suggested_type.startswith("diagnostic"):
            c.reason += f"; repeated candidate behavior x{c.repeat_count}"
            c.confidence = min(c.confidence + 0.10, 0.98)

    return candidates


def write_tsv(candidates: Sequence[Candidate], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_HEADER, delimiter="\t")
        writer.writeheader()
        for c in candidates:
            writer.writerow({
                "approved": c.approved,
                "stem": c.stem,
                "ref": c.ref,
                "greek_idx": c.greek_idx,
                "greek_span": c.greek_span,
                "nbla_idx": c.nbla_idx,
                "nbla_span": c.nbla_span,
                "suggested_type": c.suggested_type,
                "source": c.source,
                "reason": c.reason,
                "confidence": f"{c.confidence:.2f}",
                "repeat_count": c.repeat_count,
                "phrase_key": c.phrase_key,
                "existing_rule": c.existing_rule,
                "duplicate_of": c.duplicate_of,
                "yaml_suggestion": c.yaml_suggestion,
            })


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build reviewable TSV YAML-rule candidates from MNA validation failures.")
    p.add_argument("--validation-log", type=Path, default=None, help="Read validation output from this file instead of running validate_all.py.")
    p.add_argument("--run-validate", action="store_true", help="Run validate_all.py and capture its output.")
    p.add_argument("--validate-cmd", nargs="+", default=None, help="Command used with --run-validate. Default: python scripts/validate_all.py")
    p.add_argument("--rules", type=Path, default=None, help="Path to alignment_rules.yaml. Default: data/rules/alignment_rules.yaml if present, else alignment_rules.yaml.")
    p.add_argument("--align-root", type=Path, default=Path("data/alignments"), help="Alignment root. Default: data/alignments")
    p.add_argument("--s-token-root", type=Path, default=Path("data/s-tokens"), help="Spanish token root. Default: data/s-tokens")
    p.add_argument("--out", type=Path, default=Path("data/review/rule_candidates.tsv"), help="Output TSV path. Default: data/review/rule_candidates.tsv")
    p.add_argument("--save-validation-log", type=Path, default=None, help="Optional path to save captured validate_all.py output.")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    print(f"build_rule_candidates_v3.py {SCRIPT_VERSION}")

    if args.validation_log:
        if not args.validation_log.exists():
            print(f"ERROR: validation log not found: {args.validation_log}", file=sys.stderr)
            return 2
        validation_text = args.validation_log.read_text(encoding="utf-8")
    elif args.run_validate:
        validate_cmd = args.validate_cmd if args.validate_cmd else default_validate_cmd()
        validation_text = run_validate(validate_cmd)
        if args.save_validation_log:
            args.save_validation_log.parent.mkdir(parents=True, exist_ok=True)
            args.save_validation_log.write_text(validation_text, encoding="utf-8")
    else:
        print("ERROR: use --run-validate or --validation-log", file=sys.stderr)
        return 2

    rules_path = choose_rules_path(args.rules)
    existing = collect_existing_rule_keys(load_rules(rules_path))
    failures = parse_validation_output(validation_text)
    candidates = build_candidates(failures, args.align_root, args.s_token_root, existing)
    write_tsv(candidates, args.out)

    print(f"Failures parsed: {len(failures)}")
    print(f"Rules path: {rules_path}")
    print(f"Existing YAML keys: {len(existing)}")
    print(f"Candidates written: {len(candidates)}")
    print(f"Output: {args.out}")
    if failures and not candidates:
        print("WARNING: validation failures existed, but no candidates were built. Inspect saved validation log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
