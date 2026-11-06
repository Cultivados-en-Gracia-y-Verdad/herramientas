#!/usr/bin/env python3
"""Tag MACULA clauses the Bible itself marks as prophetic speech.

Matching uses consonantal skeletons so MACULA pointing variants
(יהוה vs יְהוָה, כֹּה vs כֹּה, דָּבָר vs דָּבָר) do not drop formulas.
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUSE_DIR = ROOT / "clauses"
OUT_DIR = ROOT / "prophecy"


def strip_points(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def cons_set(lemmas: list[str] | None) -> set[str]:
    return {strip_points(x) for x in (lemmas or []) if x}


# Consonantal Hebrew keys.
YHWH = {"יהוה"}
ADONAI = {"אדני"}
SAY = {"אמר"}
UTTER = {"נאם"}
WORD = {"דבר"}
HAYAH = {"היה"}
PROPHESY = {"נבא"}
PROPHET = {"נביא", "נביאה"}
# חזון / חזות are the text's "vision" nouns for oracles. מראה is also
# "appearance" (a beautiful face). חזה is also "breast" and ordinary "see".
VISION = {"חזון", "חזות"}
MASSA = {"משא"}
KOH = {"כה"}
ELOHIM = {"אלהים"}
# משא is also a person's name and "load". Keep it only when the same clause
# also has one of these prophecy or divine-speech words.
MASSA_COMPANY = {"יהוה", "אדני", "אלהים", "נביא", "נביאה", "נבא", "חזון", "חזות", "חזה"}
SPEECH_VERBS = {"אמר", "דבר", "נבא", "צוה"}

# Greek lemmas (unpointed already).
EL_PROPHESY = {"προφητεύω"}
EL_PROPHET = {"προφήτης", "προφῆτις"}
EL_PROPHECY = {"προφητεία", "προφητικός"}
EL_FULFILL = {"πληρόω"}
EL_SAY = {"λέγω"}
EL_LORD = {"κύριος"}
EL_SPIRIT = {"πνεῦμα"}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def tag_hebrew(row: dict) -> tuple[list[str], str | None]:
    C = cons_set(row.get("lemmas"))
    subj = cons_set(row.get("subject_lemmas"))
    addr = cons_set(row.get("addressee_lemmas"))
    verb_c = strip_points(row.get("verb_lemma") or "")
    divine = bool(C & YHWH) or bool(C & ADONAI)
    yhwh_subject = bool(subj & YHWH) or bool(subj & ADONAI)
    elohim_subject = bool(subj & ELOHIM)
    divine_subject = yhwh_subject or elohim_subject
    yhwh_addressed = bool(addr & YHWH) or bool(addr & ADONAI)
    tags: list[str] = []

    if C & UTTER:
        tags.append("utterance_formula")
    if C & KOH and C & SAY and divine:
        tags.append("messenger_formula")
        tags.append("thus_says")
    if C & WORD and divine and C & HAYAH:
        tags.append("word_event")
    if verb_c in PROPHESY or C & PROPHESY:
        tags.append("prophesy_verb")
    if C & SAY and (subj & PROPHET):
        tags.append("prophet_speaks")
    if C & VISION:
        tags.append("vision")
    if C & MASSA and C & MASSA_COMPANY:
        tags.append("massa_oracle")
    if verb_c in SAY and yhwh_subject:
        tags.append("yhwh_said")
    elif verb_c in SAY and elohim_subject:
        tags.append("elohim_said")
    elif verb_c in SAY and yhwh_addressed and not yhwh_subject:
        tags.append("said_to_yhwh")
    if verb_c == "דבר" and divine_subject:
        tags.append("yhwh_spoke")

    if "said_to_yhwh" in tags and not any(
        t in tags
        for t in (
            "utterance_formula",
            "messenger_formula",
            "thus_says",
            "word_event",
            "prophesy_verb",
            "yhwh_said",
            "elohim_said",
            "yhwh_spoke",
        )
    ):
        return tags, None

    prophecy_words = {
        "utterance_formula",
        "messenger_formula",
        "word_event",
        "prophesy_verb",
        "prophet_speaks",
        "vision",
        "massa_oracle",
    }
    divine_speech = {"yhwh_said", "elohim_said", "yhwh_spoke"}
    tagged = set(tags)
    if tagged & prophecy_words:
        tier = "A"
    elif tagged & divine_speech:
        tier = "D"  # divine speech the text attributes; it does not say "prophecy"
    else:
        tier = None
    return tags, tier


def tag_greek(row: dict) -> tuple[list[str], str | None]:
    L = set(row.get("lemmas") or [])
    tags: list[str] = []
    if (row.get("verb_lemma") in EL_PROPHESY) or (L & EL_PROPHESY):
        tags.append("prophesy_verb")
    if L & EL_PROPHET:
        tags.append("prophet_named")
    if L & EL_PROPHECY:
        tags.append("prophecy_noun")
    subj = set(row.get("subject_lemmas") or [])
    if (L & EL_SAY) and (subj & EL_PROPHET):
        tags.append("prophet_speaks")
    if L & EL_SPIRIT and L & EL_PROPHET:
        tags.append("spirit_via_prophet")
    if L & EL_SAY and L & EL_LORD and L & EL_PROPHET:
        tags.append("spoken_by_lord_through_prophet")
    form = row.get("verb_form") or ""
    # Do not treat every "the master said" as prophecy. κύριος is also a
    # household master in parables.

    prophecy_words = {
        "prophesy_verb",
        "prophet_named",
        "prophecy_noun",
        "prophet_speaks",
        "spirit_via_prophet",
        "spoken_by_lord_through_prophet",
    }
    if set(tags) & prophecy_words:
        tier = "A"
    else:
        tier = None
    return tags, tier


def apply_sentence_fulfillment(rows: list[dict]) -> None:
    by_sent: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["corpus"] == "greek" and row.get("sentence_id"):
            by_sent[row["sentence_id"]].append(row)
    for group in by_sent.values():
        lemmas = [set(r.get("lemmas") or []) for r in group]
        has_fill = any(L & EL_FULFILL for L in lemmas)
        has_prophet = any(L & EL_PROPHET for L in lemmas)
        has_said = any(L & EL_SAY for L in lemmas)
        if has_fill and (has_prophet or has_said):
            for row, L in zip(group, lemmas):
                if L & EL_FULFILL or L & EL_PROPHET or (L & EL_SAY and (L & EL_LORD or L & EL_PROPHET)):
                    if "fulfillment_citation" not in row["frame_tags"]:
                        row["frame_tags"].append("fulfillment_citation")
                    if row.get("tier") not in {"A"}:
                        row["tier"] = "A"
                    row["is_frame"] = True


def mark_same_sentence_oracles(rows: list[dict]) -> None:
    by_sent: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["corpus"], row.get("sentence_id") or f"nosent:{row['id']}")
        by_sent[key].append(row)

    for group in by_sent.values():
        frames = [r for r in group if r.get("is_frame") and r.get("tier") == "A"]
        if not frames:
            continue
        for i, row in enumerate(group):
            if row.get("is_frame"):
                continue
            if row.get("kind") not in {"content", "reduced", "embed"}:
                continue
            nearest = min(
                frames,
                key=lambda f: abs(group.index(f) - i),
            )
            row["is_oracle_content"] = True
            row["under_frame_id"] = nearest["id"]
            row["under_frame_tags"] = list(nearest.get("frame_tags") or [])
            row["under_frame_tier"] = nearest.get("tier")
            row["oracle_span"] = row.get("oracle_span") or "same_sentence"


def is_narrative_seam(row: dict) -> bool:
    """A story event that closes prophetic/divine speech.

    wayyiqtol of a non-speech verb (he formed, he went, there was light).
    Speech verbs (אמר/דבר/נבא/צוה) keep the span open. Human speech *to*
    YHWH also closes it.
    """
    if "said_to_yhwh" in (row.get("frame_tags") or []):
        return True
    if row.get("kind") not in {"content", "reduced"}:
        return False
    form = row.get("verb_form") or ""
    if "wayyiqtol" not in form:
        return False
    verb_c = strip_points(row.get("verb_lemma") or "")
    return verb_c not in SPEECH_VERBS


def expand_oracle_spans(rows: list[dict]) -> None:
    """Keep an open Tier A frame across following verses until a seam or new book."""
    open_frame: dict | None = None
    current_book = None
    current_chapter = None
    for row in rows:
        if row.get("corpus") != "hebrew":
            open_frame = None
            continue
        book = row.get("book")
        chapter = row.get("chapter")
        if book != current_book or chapter != current_chapter:
            current_book = book
            current_chapter = chapter
            open_frame = None
        if row.get("is_frame") and row.get("tier") == "A":
            open_frame = row
            continue
        if open_frame is None:
            continue
        if is_narrative_seam(row):
            open_frame = None
            continue
        if row.get("is_frame"):
            continue
        if row.get("kind") not in {"content", "reduced", "embed"}:
            continue
        if row.get("is_oracle_content"):
            continue
        row["is_oracle_content"] = True
        row["oracle_span"] = "expanded"
        row["under_frame_id"] = open_frame["id"]
        row["under_frame_tags"] = list(open_frame.get("frame_tags") or [])
        row["under_frame_tier"] = open_frame.get("tier")


def is_narrative_said(row: dict) -> bool:
    """Narrator: 'and YHWH / Elohim said.' Not a quote of 'God said'."""
    if row.get("tier") != "D":
        return False
    form = (row.get("verb_form") or "").lower()
    if "wayyiqtol" not in form:
        return False
    return strip_points(row.get("verb_lemma") or "") in {"אמר", "דבר"}


def expand_divine_spans(rows: list[dict]) -> None:
    """After 'and YHWH said', take the following clauses until the story resumes.

    This is not prophecy vocabulary. It is the speech the narrator attaches
    to that saying. Stops at a wayyiqtol seam, a new chapter, or a new book.
    """
    open_frame: dict | None = None
    current_book = None
    current_chapter = None
    for row in rows:
        if row.get("corpus") != "hebrew":
            open_frame = None
            continue
        book = row.get("book")
        chapter = row.get("chapter")
        if book != current_book or chapter != current_chapter:
            current_book = book
            current_chapter = chapter
            open_frame = None
        if is_narrative_said(row):
            open_frame = row
            continue
        if open_frame is None:
            continue
        if is_narrative_seam(row):
            open_frame = None
            continue
        if row.get("is_frame") or row.get("tier") == "D":
            if is_narrative_said(row):
                open_frame = row
            continue
        if row.get("kind") not in {"content", "reduced", "embed"}:
            continue
        if row.get("is_oracle_content") or row.get("is_divine_content"):
            continue
        row["is_divine_content"] = True
        row["under_frame_id"] = open_frame["id"]
        row["under_frame_tags"] = list(open_frame.get("frame_tags") or [])
        row["under_frame_tier"] = "D"
        row["oracle_span"] = "divine_said"


def nearest_tagged_ancestor(row: dict, by_id: dict[str, dict]) -> dict | None:
    pid = row.get("parent_id")
    while pid:
        parent = by_id.get(pid)
        if parent is None:
            return None
        if parent.get("is_frame") and parent.get("tier") == "A":
            return parent
        pid = parent.get("parent_id")
    return None


def pack(row: dict) -> dict:
    return {
        "id": row["id"],
        "corpus": row["corpus"],
        "ref": row.get("ref"),
        "ref_protestant": row.get("ref_protestant"),
        "book": row.get("book"),
        "chapter": row.get("chapter"),
        "verse": row.get("verse"),
        "chapter_protestant": row.get("chapter_protestant"),
        "verse_protestant": row.get("verse_protestant"),
        "sentence_id": row.get("sentence_id"),
        "rule": row.get("rule"),
        "kind": row.get("kind"),
        "depth": row.get("depth"),
        "parent_id": row.get("parent_id"),
        "tier": row.get("tier"),
        "frame_tags": row.get("frame_tags"),
        "under_frame_id": row.get("under_frame_id"),
        "under_frame_tags": row.get("under_frame_tags"),
        "is_frame": row.get("is_frame"),
        "is_oracle_content": row.get("is_oracle_content"),
        "is_divine_content": row.get("is_divine_content"),
        "oracle_span": row.get("oracle_span"),
        "under_frame_tier": row.get("under_frame_tier"),
        "verb_lemma": row.get("verb_lemma"),
        "verb_english": row.get("verb_english"),
        "subject_lemmas": row.get("subject_lemmas"),
        "addressee_lemmas": row.get("addressee_lemmas"),
        "own_gloss": row.get("own_gloss"),
        "own_text": row.get("own_text"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hebrew = load_jsonl(CLAUSE_DIR / "hebrew.jsonl")
    greek = load_jsonl(CLAUSE_DIR / "greek.jsonl")

    for row in hebrew:
        tags, tier = tag_hebrew(row)
        row["frame_tags"] = tags
        row["tier"] = tier
        row["is_frame"] = tier == "A"
        row["is_oracle_content"] = False
        row["is_divine_content"] = False
        row["under_frame_id"] = None
        row["under_frame_tags"] = []
        row["oracle_span"] = None
    for row in greek:
        tags, tier = tag_greek(row)
        row["frame_tags"] = tags
        row["tier"] = tier
        row["is_frame"] = tier == "A"
        row["is_oracle_content"] = False
        row["is_divine_content"] = False
        row["under_frame_id"] = None
        row["under_frame_tags"] = []
        row["oracle_span"] = None

    apply_sentence_fulfillment(greek)

    all_rows = hebrew + greek
    by_id = {row["id"]: row for row in all_rows}
    for row in all_rows:
        if row.get("is_oracle_content") or row.get("is_frame"):
            continue
        anc = nearest_tagged_ancestor(row, by_id)
        if anc:
            row["is_oracle_content"] = row.get("kind") in {"content", "reduced", "embed"}
            row["under_frame_id"] = anc["id"]
            row["under_frame_tags"] = list(anc.get("frame_tags") or [])
            row["under_frame_tier"] = anc.get("tier")
            row["oracle_span"] = "nested"

    mark_same_sentence_oracles(all_rows)
    # Tier A: same-sentence and nested tree only. Do not walk the chapter.
    # Tier D: narrator "and YHWH said" then the speech until a story seam.
    expand_divine_spans(hebrew)

    frames_ab = [r for r in all_rows if r.get("is_frame") and r.get("tier") == "A"]
    divine_speech = [r for r in all_rows if r.get("tier") == "D"]
    divine_content = [r for r in hebrew if r.get("is_divine_content")]
    said_to = [r for r in all_rows if "said_to_yhwh" in (r.get("frame_tags") or [])]
    yhwh_said = [r for r in divine_speech if "yhwh_said" in (r.get("frame_tags") or [])]
    elohim_said = [r for r in divine_speech if "elohim_said" in (r.get("frame_tags") or [])]
    yhwh_spoke = [r for r in divine_speech if "yhwh_spoke" in (r.get("frame_tags") or [])]
    oracles = [r for r in all_rows if r.get("is_oracle_content")]
    span_counts = Counter(r.get("oracle_span") or "unmarked" for r in oracles)

    with (OUT_DIR / "frames.jsonl").open("w", encoding="utf-8") as fh:
        for row in frames_ab:
            fh.write(json.dumps(pack(row), ensure_ascii=False) + "\n")
    with (OUT_DIR / "divine_speech.jsonl").open("w", encoding="utf-8") as fh:
        for row in divine_speech:
            fh.write(json.dumps(pack(row), ensure_ascii=False) + "\n")
    with (OUT_DIR / "said_to_yhwh.jsonl").open("w", encoding="utf-8") as fh:
        for row in said_to:
            fh.write(json.dumps(pack(row), ensure_ascii=False) + "\n")
    with (OUT_DIR / "oracle_content.jsonl").open("w", encoding="utf-8") as fh:
        for row in oracles:
            fh.write(json.dumps(pack(row), ensure_ascii=False) + "\n")
    with (OUT_DIR / "divine_content.jsonl").open("w", encoding="utf-8") as fh:
        for row in divine_content:
            fh.write(json.dumps(pack(row), ensure_ascii=False) + "\n")
    old_c = OUT_DIR / "yhwh_said_narrative.jsonl"
    if old_c.exists():
        old_c.unlink()

    tag_counts: Counter[str] = Counter()
    book_frames: dict[str, int] = defaultdict(int)
    book_oracles: dict[str, int] = defaultdict(int)
    samples: dict[str, list] = defaultdict(list)
    for row in frames_ab:
        book_frames[row.get("book") or "?"] += 1
        for t in row["frame_tags"]:
            tag_counts[t] += 1
            if len(samples[t]) < 6:
                samples[t].append({"ref": row.get("ref"), "gloss": row.get("own_gloss")})
    for row in oracles:
        book_oracles[row.get("book") or "?"] += 1

    summary = {
        "method": "Bible-internal speech formulas on MACULA clause own-lemmas (consonantal match)",
        "clause_universe": {
            "hebrew": len(hebrew),
            "greek": len(greek),
            "total": len(hebrew) + len(greek),
        },
        "tiers": {
            "A_text_uses_prophecy_vocabulary": "נאם, כה אמר + יהוה, דבר יהוה היה, נבא, נביא+אמר, חזון/חזות, משא+company, προφητ*, πληρόω+προφήτης/γραφή",
            "D_divine_speech_not_called_prophecy": "YHWH/Elohim said or spoke — the text attributes speech, not the word prophecy",
            "excluded": "said_to_yhwh; thus-says without YHWH; משא as load/name; מראה as appearance",
        },
        "frames_AB": {
            "count": len(frames_ab),
            "hebrew": sum(1 for r in frames_ab if r["corpus"] == "hebrew"),
            "greek": sum(1 for r in frames_ab if r["corpus"] == "greek"),
            "tier_A": sum(1 for r in frames_ab if r.get("tier") == "A"),
            "by_tag": dict(tag_counts.most_common()),
            "by_book": dict(sorted(book_frames.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "yhwh_said_included": {
            "count": len(yhwh_said),
            "by_book": dict(
                sorted(
                    Counter(r.get("book") or "?" for r in yhwh_said).items(),
                    key=lambda kv: (-kv[1], kv[0]),
                )
            ),
        },
        "elohim_said_included": {"count": len(elohim_said)},
        "yhwh_spoke_included": {"count": len(yhwh_spoke)},
        "divine_speech_not_called_prophecy": {
            "count": len(divine_speech),
            "yhwh_said": len(yhwh_said),
            "elohim_said": len(elohim_said),
            "yhwh_spoke": len(yhwh_spoke),
        },
        "said_to_yhwh_excluded": {
            "count": len(said_to),
            "by_book": dict(
                sorted(
                    Counter(r.get("book") or "?" for r in said_to).items(),
                    key=lambda kv: (-kv[1], kv[0]),
                )
            ),
        },
        "oracle_content": {
            "count": len(oracles),
            "hebrew": sum(1 for r in oracles if r["corpus"] == "hebrew"),
            "greek": sum(1 for r in oracles if r["corpus"] == "greek"),
            "by_span": dict(span_counts),
            "by_book": dict(sorted(book_oracles.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "samples_by_tag": samples,
        "not_yet": [
            "False-prophet vs true-prophet discernment from the text",
            "Predictive vs indictment vs promise classification inside the oracle",
            "Gospel κύριος-said mixes Jesus-as-Lord with λέγει κύριος citations",
        ],
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "frames_AB": len(frames_ab),
                "tier_A": summary["frames_AB"]["tier_A"],
                "divine_speech": len(divine_speech),
                "divine_content": len(divine_content),
                "said_to_yhwh_excluded": len(said_to),
                "oracles": len(oracles),
                "oracle_spans": dict(span_counts),
                "by_tag": dict(tag_counts.most_common()),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
