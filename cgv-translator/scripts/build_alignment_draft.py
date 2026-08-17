#!/usr/bin/env python3
"""Build a deterministic alignment draft without verifying or approving it.

This script uses only stored source-token glosses, exact Spanish character spans,
and a monotonic dynamic-programming partition. It does not use AI, network access,
prior alignment decisions, or producer status. The result is always DRAFT and must
receive direct human G0B review.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import unicodedata
from functools import lru_cache
from math import ceil
from pathlib import Path
from typing import Any

from book_workflow import WorkflowError, alignment_audit, load_book, save_json


WORD_RE = re.compile(r"[^\W_]+(?:[’'][^\W_]+)?", re.UNICODE)
IGNORED_GLOSSES = {"obj", "acc", "dobj"}
BLE_SLUGS = {"zechariah": "zacarias", "daniel": "daniel"}


def load_interlinear_glosses(root: Path, book_id: str) -> dict[str, str]:
    """Map OSHB token id / sourceTokenId to a stored interlinear gloss.

    Used only when phrase tokenRows have an empty ble field (common on
    Protestant/MT remapped verses). Does not change Spanish.
    """
    slug = BLE_SLUGS.get(book_id, book_id)
    candidates = [
        root.parent / "cgv-data" / "interlinears" / "OT" / f"{slug}.tokens.jsonl",
        root.parent / "MNA" / "datasets" / "interlinear" / "OT" / f"{slug}.tokens.jsonl",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return {}
    glosses: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        gloss = str(row.get("es") or row.get("gloss") or "").strip()
        if not gloss:
            continue
        for key in (row.get("id"), row.get("sourceTokenId"), row.get("source_token_id")):
            token_id = str(key or "").strip()
            if token_id:
                glosses[token_id] = gloss
    return glosses


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    plain = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", "", plain)


def word_spans(value: str) -> list[tuple[int, int, str]]:
    return [(match.start(), match.end(), match.group()) for match in WORD_RE.finditer(value)]


def gloss_words(value: str) -> list[str]:
    normalized = value.replace("·", " ").replace("/", " ")
    words = [normalize(match.group()) for match in WORD_RE.finditer(normalized)]
    return [word for word in words if word and word not in IGNORED_GLOSSES]


@lru_cache(maxsize=None)
def softened(word: str) -> str:
    for suffix in (
        "amientos", "imientos", "aciones", "adores", "adoras", "amiento",
        "imiento", "acion", "mente", "ando", "iendo", "aron", "ieron",
        "ados", "adas", "idos", "idas", "aba", "aban", "ia", "ian",
        "es", "os", "as", "s",
    ):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word


@lru_cache(maxsize=None)
def word_similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if softened(left) == softened(right):
        return 0.86
    common = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        common += 1
    if common >= 4:
        return 0.70 * (common / max(len(left), len(right)))
    return 0.0


def lexical_score(spanish: list[str], glosses: list[str]) -> float:
    if not spanish or not glosses:
        return 0.0
    used: set[int] = set()
    score = 0.0
    for word in spanish:
        best_score = 0.0
        best_index = None
        for index, gloss in enumerate(glosses):
            if index in used:
                continue
            candidate = word_similarity(word, gloss)
            if candidate > best_score:
                best_score, best_index = candidate, index
        if best_index is not None:
            used.add(best_index)
            score += best_score
    precision = score / len(spanish)
    recall = score / len(glosses)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def token_gloss(row: dict[str, Any], extra: dict[str, str] | None = None) -> str:
    for field in ("ble", "gloss", "es", "rv1909"):
        value = str(row.get(field) or "").strip()
        if value:
            return value
    extra = extra or {}
    for key in (row.get("oshbId"), row.get("sourceTokenId")):
        value = extra.get(str(key or "").strip(), "")
        if value:
            return value
    return ""


def partition(
    source_glosses: list[list[str]], spanish_words: list[str],
    max_source_span: int = 3, max_spanish_span: int = 6,
) -> list[tuple[int, int, int, int, float]]:
    """Partition both complete sequences into granular monotonic groups."""
    source_count, spanish_count = len(source_glosses), len(spanish_words)
    max_source_span = max(max_source_span, ceil(source_count / spanish_count))
    max_spanish_span = max(max_spanish_span, ceil(spanish_count / source_count))
    negative = -10**12
    scores = [[negative] * (spanish_count + 1) for _ in range(source_count + 1)]
    previous: list[list[tuple[int, int, float] | None]] = [
        [None] * (spanish_count + 1) for _ in range(source_count + 1)
    ]
    scores[0][0] = 0.0
    for source_at in range(source_count):
        for spanish_at in range(spanish_count):
            current = scores[source_at][spanish_at]
            if current == negative:
                continue
            for source_size in range(1, min(max_source_span, source_count - source_at) + 1):
                combined_glosses = [
                    word
                    for token_words in source_glosses[source_at:source_at + source_size]
                    for word in token_words
                ]
                for spanish_size in range(1, min(max_spanish_span, spanish_count - spanish_at) + 1):
                    target_words = spanish_words[spanish_at:spanish_at + spanish_size]
                    similarity = lexical_score(target_words, combined_glosses)
                    # Favor small, evidence-rich units while permitting the larger
                    # groups required by reordering and many-to-many translation.
                    group_penalty = 0.10 * (source_size - 1) + 0.075 * (spanish_size - 1)
                    unrelated_penalty = 0.80 if similarity == 0 else 0.0
                    candidate = current + (4.0 * similarity) + 0.18 - group_penalty - unrelated_penalty
                    next_source = source_at + source_size
                    next_spanish = spanish_at + spanish_size
                    if candidate > scores[next_source][next_spanish]:
                        scores[next_source][next_spanish] = candidate
                        previous[next_source][next_spanish] = (source_at, spanish_at, similarity)
    if previous[source_count][spanish_count] is None:
        raise WorkflowError(
            f"Cannot partition {source_count} source tokens and {spanish_count} Spanish words "
            f"within configured span limits."
        )
    groups = []
    source_at, spanish_at = source_count, spanish_count
    while source_at or spanish_at:
        prior = previous[source_at][spanish_at]
        if prior is None:
            raise WorkflowError("Alignment partition reconstruction failed.")
        prior_source, prior_spanish, similarity = prior
        groups.append((prior_source, source_at, prior_spanish, spanish_at, similarity))
        source_at, spanish_at = prior_source, prior_spanish
    groups.reverse()
    return groups


def build_units(
    row: dict[str, Any], extra_glosses: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    spanish = str(row.get("spanish") or "")
    spans = word_spans(spanish)
    if not spans:
        raise WorkflowError(f"{row.get('reference')}: Spanish contains no lexical words.")
    token_rows = {
        str(token.get("sourceTokenId")): token
        for token in row.get("tokenRows", [])
        if isinstance(token, dict) and token.get("sourceTokenId")
    }
    source_ids = [str(value) for value in row.get("sourceTokenIds", [])]
    # Tokens with no independent lexical realization (for example Hebrew/Aramaic
    # object markers stored as BLE=OBJ) are deterministically attached to the next
    # lexical token. This avoids manufacturing a Spanish span for a null morpheme.
    atoms: list[dict[str, Any]] = []
    pending_null_ids: list[str] = []
    for token_id in source_ids:
        words_for_token = gloss_words(token_gloss(token_rows.get(token_id, {}), extra_glosses))
        if not words_for_token:
            pending_null_ids.append(token_id)
            continue
        atoms.append({"ids": [*pending_null_ids, token_id], "glosses": words_for_token})
        pending_null_ids = []
    if pending_null_ids:
        if atoms:
            atoms[-1]["ids"].extend(pending_null_ids)
        else:
            atoms.append({"ids": pending_null_ids, "glosses": []})
    source_glosses = [atom["glosses"] for atom in atoms]
    spanish_words = [normalize(value) for _, _, value in spans]
    groups = partition(source_glosses, spanish_words)
    units, diagnostics = [], []
    phrase_index = int(row.get("phraseIndex"))
    for unit_index, (source_start, source_end, word_start, word_end, similarity) in enumerate(groups):
        char_start = 0 if unit_index == 0 else spans[word_start][0]
        if unit_index + 1 == len(groups):
            char_end = len(spanish)
        else:
            next_word_start = groups[unit_index + 1][2]
            char_end = spans[next_word_start][0]
        surface = spanish[char_start:char_end]
        ids = [token_id for atom in atoms[source_start:source_end] for token_id in atom["ids"]]
        units.append(
            {
                "unitId": f"{phrase_index}:{unit_index}",
                "surface": surface,
                "charStart": char_start,
                "charEnd": char_end,
                "sourceTokenIds": ids,
                "relationshipType": "DRAFT_CORRESPONDENCE",
                "method": "deterministic-gloss-dp-v1",
                "status": "DRAFT",
            }
        )
        diagnostics.append(
            {
                "unitId": f"{phrase_index}:{unit_index}",
                "spanish": surface,
                "sourceTokenIds": ids,
                "sourceGloss": " | ".join(token_gloss(token_rows.get(token_id, {}), extra_glosses) for token_id in ids),
                "lexicalScore": round(similarity, 4),
                "reviewPriority": "HIGH" if similarity < 0.25 else "NORMAL",
            }
        )
    return units, diagnostics


def build_draft(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    extra_glosses = load_interlinear_glosses(data["root"], data["book"])
    links, diagnostics = [], []
    for row in data["rows"]:
        units, unit_diagnostics = build_units(row, extra_glosses)
        links.append(
            {
                "phraseIndex": int(row.get("phraseIndex")),
                "reference": str(row.get("reference")),
                "status": "DRAFT",
                "method": "deterministic-gloss-dp-v1",
                "units": units,
            }
        )
        diagnostics.append({"reference": row.get("reference"), "units": unit_diagnostics})
    document = {
        "bookId": data["book"],
        "textualBasis": (data["alignment"] or {}).get("textualBasis") or data["spine"].get("textualBasis"),
        "schemaVersion": "draft-1",
        "generator": {
            "name": "deterministic-gloss-dp-v1",
            "usesAI": False,
            "verificationAuthority": False,
            "status": "DRAFT",
        },
        "links": links,
    }
    all_units = [unit for link in links for unit in link["units"]]
    high = sum(
        diagnostic["reviewPriority"] == "HIGH"
        for verse in diagnostics
        for diagnostic in verse["units"]
    )
    report = {
        "book": data["book"],
        "method": "deterministic-gloss-dp-v1",
        "usesAI": False,
        "createsVerification": False,
        "verses": len(links),
        "units": len(all_units),
        "highPriorityUnits": high,
        "diagnostics": diagnostics,
    }
    return document, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an unverified deterministic alignment draft")
    parser.add_argument("book")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output")
    parser.add_argument("--report")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    data = load_book(root, args.book.lower())
    document, report = build_draft(data)
    output = Path(args.output).resolve() if args.output else data["paths"]["alignment"].with_name(f"{args.book}-reverse-links.draft-v1.json")
    report_path = Path(args.report).resolve() if args.report else root / "verification" / args.book / "alignment-draft-report.json"
    trial = copy.copy(data)
    trial["alignment"] = document
    defects = alignment_audit(trial)
    report["deterministicDefects"] = defects
    save_json(output, document)
    save_json(report_path, report)
    print(f"DRAFT: {output}")
    print(f"REPORT: {report_path}")
    print(f"VERSES: {report['verses']}")
    print(f"UNITS: {report['units']}")
    print(f"HIGH-PRIORITY HUMAN REVIEW: {report['highPriorityUnits']}")
    print(f"DETERMINISTIC DEFECTS: {len(defects)}")
    print("G0B: PENDING — this command cannot verify or approve alignment")
    return 1 if defects else 0


if __name__ == "__main__":
    raise SystemExit(main())
