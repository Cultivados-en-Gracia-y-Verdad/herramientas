"""Build Phase 1 lemma observation records (Greek verbs, Milestone 1)."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from lexicon_engine.books import display_book, format_ref
from lexicon_engine.corpus import Token, VerseKey, context_window, verse_clause_text
from lexicon_engine.morph import (
    display_morph_rmac,
    is_imperative,
    is_subjunctive,
    is_verb_morph,
    verb_morphology_summary,
)
from lexicon_engine.stoplist import GREEK_COLLOCATION_STOPLIST

NEGATOR_LEMMAS = frozenset({"οὐ", "οὐκ", "οὐχ", "μή", "μηδέ", "οὐδέ"})
NEGATOR_SURFACES = frozenset({"οὐ", "οὐκ", "οὐχ", "μή", "μηδέ", "οὐδέ", "μὴ", "οὐκὶ"})


@dataclass(frozen=True)
class VerbOccurrence:
    token: Token
    ref: str
    left_context: str
    right_context: str
    verse_tokens: list[Token]
    verse_index: int


def _lemma_filename(lemma: str) -> str:
    return f"{lemma}.json"


def collect_verb_occurrences(
    tokens: list[Token],
    verses: dict[VerseKey, list[Token]],
    *,
    context_before: int = 6,
    context_after: int = 6,
) -> dict[str, list[VerbOccurrence]]:
    by_lemma: dict[str, list[VerbOccurrence]] = defaultdict(list)
    for token in tokens:
        if not is_verb_morph(token.morph):
            continue
        key = (token.book, token.ch, token.vs)
        verse_tokens = verses[key]
        left, right = context_window(verse_tokens, token.tok, context_before, context_after)
        idx = next(i for i, t in enumerate(verse_tokens) if t.tok == token.tok)
        by_lemma[token.lemma].append(
            VerbOccurrence(
                token=token,
                ref=format_ref(token.book, token.ch, token.vs),
                left_context=left,
                right_context=right,
                verse_tokens=verse_tokens,
                verse_index=idx,
            )
        )
    return dict(by_lemma)


def _count_forms(occurrences: list[VerbOccurrence]) -> list[dict[str, Any]]:
    counts = Counter(o.token.surface for o in occurrences)
    return [{"form": form, "count": count} for form, count in counts.most_common()]


def _count_books(occurrences: list[VerbOccurrence]) -> dict[str, int]:
    counts = Counter(display_book(o.token.book) for o in occurrences)
    return dict(counts.most_common())


def _build_references(occurrences: list[VerbOccurrence]) -> list[dict[str, Any]]:
    refs = []
    for o in occurrences:
        refs.append(
            {
                "ref": o.ref,
                "form": o.token.surface,
                "morph": display_morph_rmac(o.token.morph),
                "book": display_book(o.token.book),
                "chapter": o.token.ch,
                "verse": o.token.vs,
                "left_context": o.left_context,
                "right_context": o.right_context,
            }
        )
    return refs


def _detect_negated(occurrences: list[VerbOccurrence], *, window: int = 4) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for o in occurrences:
        vt = o.verse_tokens
        lo = max(0, o.verse_index - window)
        hi = min(len(vt), o.verse_index + window + 1)
        negator = None
        for t in vt[lo:hi]:
            if t.lemma in NEGATOR_LEMMAS or t.surface in NEGATOR_SURFACES:
                negator = t.surface
                break
        if negator:
            results.append(
                {
                    "ref": o.ref,
                    "negator": negator,
                    "clause_text": verse_clause_text(vt, o.verse_index),
                }
            )
    return results


def _detect_commands(occurrences: list[VerbOccurrence]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for o in occurrences:
        morph = o.token.morph
        is_imp = is_imperative(morph)
        is_prohibition = False
        if is_imp or is_subjunctive(morph):
            lo = max(0, o.verse_index - 3)
            for t in o.verse_tokens[lo : o.verse_index]:
                if t.lemma == "μή" or t.surface in ("μή", "μὴ"):
                    is_prohibition = True
                    break
        if is_imp or is_prohibition:
            commands.append(
                {
                    "ref": o.ref,
                    "form": o.token.surface,
                    "morph": display_morph_rmac(morph),
                    "clause_text": verse_clause_text(o.verse_tokens, o.verse_index),
                    **({"kind": "prohibition"} if is_prohibition else {}),
                }
            )
    return commands


def _collocations(
    occurrences: list[VerbOccurrence],
    *,
    window: int = 5,
) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for o in occurrences:
        vt = o.verse_tokens
        lo = max(0, o.verse_index - window)
        hi = min(len(vt), o.verse_index + window + 1)
        for t in vt[lo:hi]:
            if t.tok == o.token.tok:
                continue
            if t.lemma in GREEK_COLLOCATION_STOPLIST:
                continue
            counts[t.lemma] += 1
            if t.lemma not in display:
                display[t.lemma] = t.es or t.lemma
    return [
        {
            "lemma": lemma,
            "display": display[lemma],
            "count": count,
            "window": window,
        }
        for lemma, count in counts.most_common(25)
    ]


def _score_representative(o: VerbOccurrence, book_counts: Counter[str], has_commands: bool) -> float:
    score = 0.0
    book = display_book(o.token.book)
    score += book_counts[book] * 0.01
    morph = o.token.morph
    if morph and "-" not in morph[2:8]:
        score += 2
    if is_imperative(morph) and has_commands:
        score += 5
    if o.left_context or o.right_context:
        score += 1
    return score


def _representative_passages(
    occurrences: list[VerbOccurrence],
    commands: list[dict[str, Any]],
    collocations: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not occurrences:
        return []

    book_counts = Counter(display_book(o.token.book) for o in occurrences)
    command_refs = {c["ref"] for c in commands}
    top_coll_lemmas = {c["lemma"] for c in collocations[:5]}
    has_commands = bool(commands)

    scored: list[tuple[float, VerbOccurrence, str]] = []
    for o in occurrences:
        reasons: list[str] = []
        if o.ref in command_refs:
            reasons.append("imperative or prohibition use")
        if is_imperative(o.token.morph):
            reasons.append("imperative morphology")
        book = display_book(o.token.book)
        if book_counts[book] >= 5:
            reasons.append(f"frequent in {book}")
        near = set()
        lo = max(0, o.verse_index - 5)
        hi = min(len(o.verse_tokens), o.verse_index + 6)
        for t in o.verse_tokens[lo:hi]:
            if t.lemma in top_coll_lemmas:
                near.add(t.lemma)
        if near:
            reasons.append(f"occurs near {', '.join(sorted(near)[:3])}")
        if not reasons:
            reasons.append("typical occurrence")
        score = _score_representative(o, book_counts, has_commands)
        scored.append((score, o, reasons[0]))

    scored.sort(key=lambda x: (-x[0], x[1].ref))
    picked: list[dict[str, Any]] = []
    used_books: set[str] = set()
    used_refs: set[str] = set()
    for _, o, reason in scored:
        if o.ref in used_refs:
            continue
        book = display_book(o.token.book)
        if len(picked) >= limit:
            break
        if len(used_books) < 4 or book not in used_books or len(picked) < 5:
            picked.append({"ref": o.ref, "reason": reason})
            used_refs.add(o.ref)
            used_books.add(book)

    if len(picked) < min(5, len(occurrences)):
        for _, o, reason in scored:
            if o.ref in used_refs:
                continue
            picked.append({"ref": o.ref, "reason": reason})
            used_refs.add(o.ref)
            if len(picked) >= min(limit, len(occurrences)):
                break
    return picked


def build_verb_observation(
    lemma: str,
    occurrences: list[VerbOccurrence],
    *,
    context_before: int = 6,
    context_after: int = 6,
    collocation_window: int = 5,
) -> dict[str, Any]:
    morphs = [o.token.morph for o in occurrences if o.token.morph]
    commands = _detect_commands(occurrences)
    collocations = _collocations(occurrences, window=collocation_window)

    return {
        "lemma": lemma,
        "language": "greek",
        "total_occurrences": len(occurrences),
        "forms": _count_forms(occurrences),
        "morphology_summary": verb_morphology_summary(morphs) if morphs else {"part_of_speech": "verb"},
        "references": _build_references(occurrences),
        "books": _count_books(occurrences),
        "subjects": [],
        "objects": [],
        "common_constructions": [],
        "collocations": collocations,
        "commands": commands,
        "questions": [],
        "negated_uses": _detect_negated(occurrences),
        "clause_roles": [],
        "discourse_contexts": [],
        "representative_passages": _representative_passages(occurrences, commands, collocations),
        "definition_phase2": None,
        "definition_status": "not_started",
    }
