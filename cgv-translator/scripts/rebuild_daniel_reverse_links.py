#!/usr/bin/env python3
"""
Rebuild Daniel reverse links deterministically, verse-by-verse.

Purpose
-------
Preserve the existing Spanish unit segmentation/character offsets, but recompute
sourceTokenIds from the approved phrase artifact. Alignment state is RESET for
every phrase/verse, so a bad match can never drift into later verses.

Inputs
------
--phrases       translations/oshb-spine/daniel/daniel-phrases.json
--reverse-links translations/oshb-spine/daniel/daniel-reverse-links.json

Optional
--------
--out           output file (default: sibling *.rebuilt.json)
--max-span      max consecutive source tokens assignable to one Spanish unit
--skip-penalty  penalty for leaving a source token unmatched
--zero-penalty  penalty for a Spanish unit receiving no token
--report        YAML diagnostic report

The algorithm uses the BLE Spanish glosses already stored in phrase tokenRows as
alignment hints. It does NOT use alignment state from another verse.

This is a seed/rebuild tool, not a verifier. Output remains:
    method: gloss-match
    status: gloss-seed

G0B must still review the rebuilt links.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    yaml = None


# ---------------------------
# Normalization / tokenization
# ---------------------------

STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "los",
    "un", "una", "unos", "unas", "y", "e", "o", "que",
    "en", "por", "para", "con", "sin", "su", "sus",
}

def strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )

def norm_word(word: str) -> str:
    word = strip_accents(word.lower())
    word = re.sub(r"[^a-z0-9ñü]+", "", word)
    return word

def words(text: str) -> list[str]:
    # BLE commonly uses middle dot separators.
    text = text.replace("·", " ").replace("/", " ")
    return [w for w in (norm_word(x) for x in re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+", text)) if w]

def content_words(text: str) -> list[str]:
    ws = words(text)
    non_stop = [w for w in ws if w not in STOPWORDS]
    return non_stop or ws

def stemish(w: str) -> str:
    """
    Tiny deterministic Spanish fuzzy normalizer.
    Not a linguistic stemmer; just softens common inflection differences.
    """
    if len(w) > 5:
        for suf in ("ando", "iendo", "ados", "adas", "idos", "idas",
                    "aron", "ieron", "aba", "aban", "ian", "ía", "ias",
                    "es", "os", "as", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                return w[:-len(suf)]
    return w

def word_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if stemish(a) == stemish(b):
        return 0.82

    # conservative prefix similarity
    m = min(len(a), len(b))
    if m >= 4 and a[:4] == b[:4]:
        return 0.68
    return 0.0

def sequence_similarity(spanish: str, gloss: str) -> float:
    a = content_words(spanish)
    b = content_words(gloss)
    if not a or not b:
        return 0.0

    # Best bipartite-ish lexical overlap.
    used = set()
    score = 0.0
    for x in a:
        best = (0.0, None)
        for j, y in enumerate(b):
            if j in used:
                continue
            s = word_similarity(x, y)
            if s > best[0]:
                best = (s, j)
        if best[1] is not None:
            score += best[0]
            used.add(best[1])

    precision = score / max(1, len(a))
    recall = score / max(1, len(b))
    if precision + recall == 0:
        return 0.0
    f1 = 2 * precision * recall / (precision + recall)

    # Reward exact phrase containment after normalization.
    na = " ".join(words(spanish))
    nb = " ".join(words(gloss))
    if na and nb and (na == nb or na in nb or nb in na):
        f1 = max(f1, 0.92)

    return min(1.0, f1)


# ---------------------------
# JSON shape helpers
# ---------------------------

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

def phrase_records(doc: Any) -> list[dict]:
    if isinstance(doc, list):
        return doc
    for key in ("phrases", "records", "items", "data"):
        value = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(value, list):
            return value
    raise ValueError("Unsupported phrases JSON shape")

def reverse_records(doc: Any) -> list[dict]:
    if isinstance(doc, list):
        return doc
    for key in ("links", "records", "reverseLinks", "reverse_links", "items", "data"):
        value = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(value, list):
            return value
    raise ValueError("Unsupported reverse-links JSON shape")

def unit_records(record: dict) -> list[dict]:
    for key in ("units", "links", "reverseLinks", "reverse_links", "items"):
        value = record.get(key)
        if isinstance(value, list):
            return value
    raise ValueError(
        f"{record.get('reference', record.get('phraseIndex'))}: "
        "could not locate unit list"
    )

def unit_text(unit: dict) -> str:
    for key in ("surface", "spanishUnit", "spanish_unit", "spanish", "text", "target"):
        value = unit.get(key)
        if isinstance(value, str):
            return value
    return ""

def get_reference(record: dict) -> str | None:
    return record.get("reference") or record.get("ref")

def set_source_ids(unit: dict, ids: list[str]) -> None:
    # Preserve whichever spelling the file already uses.
    if "sourceTokenIds" in unit or "source_token_ids" not in unit:
        unit["sourceTokenIds"] = ids
    else:
        unit["source_token_ids"] = ids

def set_method_status(unit: dict) -> None:
    unit["method"] = "gloss-match"
    unit["status"] = "gloss-seed"

def token_rows_for_phrase(phrase: dict) -> list[dict]:
    rows = phrase.get("tokenRows")
    if isinstance(rows, list):
        return rows
    return []

def ordered_source_tokens(phrase: dict) -> list[dict]:
    rows = token_rows_for_phrase(phrase)
    by_id = {r.get("sourceTokenId"): r for r in rows if r.get("sourceTokenId")}
    ids = phrase.get("sourceTokenIds") or list(by_id.keys())

    out = []
    for tid in ids:
        row = by_id.get(tid, {"sourceTokenId": tid})
        out.append(row)
    return out

def token_gloss(row: dict) -> str:
    # BLE is the intended Spanish seed. Fall back conservatively.
    for key in ("ble", "gloss", "rv1909"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


# ---------------------------
# Dynamic-programming aligner
# ---------------------------

def span_gloss(tokens: list[dict], i: int, j: int) -> str:
    return " ".join(token_gloss(t) for t in tokens[i:j] if token_gloss(t))

def align_units(
    units: list[dict],
    tokens: list[dict],
    max_span: int,
    skip_penalty: float,
    zero_penalty: float,
) -> tuple[list[list[int]], list[float]]:
    """
    Monotonic DP.

    State (u, t): first u units and first t source tokens consumed.

    Transitions:
      - assign next unit 0..max_span consecutive tokens
      - skip one source token with penalty

    No state crosses phrase/verse boundaries.
    """
    U, T = len(units), len(tokens)
    neg_inf = -1e18

    dp = [[neg_inf] * (T + 1) for _ in range(U + 1)]
    prev: list[list[tuple | None]] = [[None] * (T + 1) for _ in range(U + 1)]
    dp[0][0] = 0.0

    for u in range(U + 1):
        for t in range(T + 1):
            cur = dp[u][t]
            if cur <= neg_inf / 2:
                continue

            # Skip source token, still within this verse.
            if t < T:
                cand = cur - skip_penalty
                if cand > dp[u][t + 1]:
                    dp[u][t + 1] = cand
                    prev[u][t + 1] = (u, t, "skip", None)

            if u >= U:
                continue

            txt = unit_text(units[u])

            # Allow zero-token unit, but penalize heavily.
            cand = cur - zero_penalty
            if cand > dp[u + 1][t]:
                dp[u + 1][t] = cand
                prev[u + 1][t] = (u, t, "assign", (t, t, 0.0))

            for span in range(1, min(max_span, T - t) + 1):
                g = span_gloss(tokens, t, t + span)
                sim = sequence_similarity(txt, g)

                # Strongly discourage unrelated assignments.
                lexical = 3.2 * sim
                span_penalty = 0.11 * max(0, span - 1)
                unrelated_penalty = 0.55 if sim < 0.20 else 0.0
                cand = cur + lexical - span_penalty - unrelated_penalty

                if cand > dp[u + 1][t + span]:
                    dp[u + 1][t + span] = cand
                    prev[u + 1][t + span] = (
                        u, t, "assign", (t, t + span, sim)
                    )

    # Best terminal state consumes all units; leftover source tokens are already
    # represented through skip transitions. Prefer full token consumption.
    end_t = max(range(T + 1), key=lambda t: dp[U][t] - 0.02 * (T - t))

    assignments = [[] for _ in range(U)]
    sims = [0.0 for _ in range(U)]

    u, t = U, end_t
    while u > 0 or t > 0:
        p = prev[u][t]
        if p is None:
            break
        pu, pt, kind, payload = p
        if kind == "assign":
            start, end, sim = payload
            assignments[pu] = list(range(start, end))
            sims[pu] = sim
        u, t = pu, pt

    return assignments, sims


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phrases", required=True, type=Path)
    ap.add_argument("--reverse-links", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--max-span", type=int, default=4)
    ap.add_argument("--skip-penalty", type=float, default=0.35)
    ap.add_argument("--zero-penalty", type=float, default=1.25)
    args = ap.parse_args()

    phrases_doc = load_json(args.phrases)
    reverse_doc = load_json(args.reverse_links)
    rebuilt = copy.deepcopy(reverse_doc)

    phrases = phrase_records(phrases_doc)
    records = reverse_records(rebuilt)

    by_ref = {
        p.get("reference"): p
        for p in phrases
        if p.get("reference")
    }

    diagnostics = []
    total_units = 0
    zero_units = 0
    low_units = 0
    unmatched_source_total = 0

    for idx, record in enumerate(records):
        ref = get_reference(record)

        phrase = by_ref.get(ref)
        if phrase is None:
            # Fallback by phraseIndex.
            pi = record.get("phraseIndex")
            if isinstance(pi, int) and 0 <= pi < len(phrases):
                phrase = phrases[pi]
                ref = phrase.get("reference")
            else:
                raise ValueError(
                    f"Reverse-link record {idx} cannot be matched to a phrase: "
                    f"reference={ref!r}, phraseIndex={pi!r}"
                )

        units = unit_records(record)
        tokens = ordered_source_tokens(phrase)

        assignments, sims = align_units(
            units,
            tokens,
            max_span=args.max_span,
            skip_penalty=args.skip_penalty,
            zero_penalty=args.zero_penalty,
        )

        used = set()

        for unit, indexes, sim in zip(units, assignments, sims):
            ids = [
                tokens[i].get("sourceTokenId")
                for i in indexes
                if tokens[i].get("sourceTokenId")
            ]
            set_source_ids(unit, ids)
            set_method_status(unit)

            # Optional diagnostic fields are deliberately NOT written into the
            # production JSON. Report carries confidence diagnostics instead.
            used.update(indexes)
            total_units += 1

            if not ids:
                zero_units += 1
            if sim < 0.35:
                low_units += 1

            diagnostics.append({
                "reference": ref,
                "unitId": unit.get("unitId"),
                "spanish_unit": unit_text(unit),
                "sourceTokenIds": ids,
                "source_surface": " ".join(
                    tokens[i].get("surface", "")
                    for i in indexes
                ),
                "ble_gloss": span_gloss(
                    tokens,
                    indexes[0],
                    indexes[-1] + 1
                ) if indexes else "",
                "similarity": round(sim, 4),
                "flag": (
                    "NO_SOURCE_TOKEN" if not ids
                    else "LOW_SIMILARITY" if sim < 0.35
                    else ""
                ),
            })

        unmatched_source_total += sum(1 for i in range(len(tokens)) if i not in used)

        # Keep record-level status honest: rebuilt is still a seed.
        if "status" in record:
            record["status"] = "gloss-seed"
        if "method" in record:
            record["method"] = "gloss-match"

    out = args.out
    if out is None:
        out = args.reverse_links.with_name(
            args.reverse_links.stem + ".rebuilt.json"
        )

    save_json(out, rebuilt)

    summary = {
        "phrases": len(phrases),
        "reverse_link_records": len(records),
        "units": total_units,
        "units_without_source_tokens": zero_units,
        "units_low_similarity": low_units,
        "unmatched_source_tokens": unmatched_source_total,
        "output": str(out),
        "method": "gloss-match",
        "status": "gloss-seed",
        "critical_property": "alignment cursor resets for every phrase/verse",
    }

    report = args.report
    if report is None:
        report = out.with_suffix(".report.yaml")

    if yaml is not None:
        report.write_text(
            yaml.safe_dump(
                {"summary": summary, "diagnostics": diagnostics},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    else:
        report = report.with_suffix(".json")
        save_json(report, {"summary": summary, "diagnostics": diagnostics})

    print("DANIEL REVERSE-LINK REBUILD")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"report: {report}")
    print()
    print("NOTE: output is still gloss-seed. Run G0B review before trusting links.")


if __name__ == "__main__":
    main()
