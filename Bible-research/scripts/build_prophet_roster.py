#!/usr/bin/env python3
"""Derive the roster of prophets from the text, not from a supplied list.

A proper noun joins the roster when Scripture itself does one of two things
with it: stands it next to נָבִיא / נְבִיאָה ("Isaiah the prophet"), or makes it
the subject of נבא ("Haggai prophesied"). Both are the text's own designation,
so the roster stays inside the corpus.

Writes `data/prophet_roster.json`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree.ElementTree import parse

ROOT = Path(__file__).resolve().parents[1]
HEB_DIR = ROOT / "MACULA" / "macula-hebrew-main" / "WLC" / "lowfat"
OUT = ROOT / "data" / "prophet_roster.json"

NABI = {"נביא", "נביאה"}
PROPHESY = "נבא"
SON = "בן"
ARTICLE = "ה"

# "prophet of YHWH" / "prophets of Baal" name the deity a prophet serves, not
# the prophet. They survive the construct filter where MACULA marks the noun
# absolute, so exclude them by name.
DEITIES = {"יהוה", "אלהים", "בעל", "אשרה"}


def cons(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )


def ref_of(word) -> str | None:
    ref = word.get("ref") or ""
    m = re.match(r"^([A-Z0-9]{3})\s+(\d+):(\d+)", ref)
    return f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m else None


def named_before(words, types, lemmas, i: int) -> int | None:
    """Index of the name in '<Name> [son of <Father>] the prophet', or None.

    Walks back past the article, then past any patronymic chain, so that
    'Isaiah son of Amoz the prophet' credits Isaiah rather than Amoz.
    """
    j = i - 1
    while j >= 0 and (lemmas[j] == ARTICLE or types[j] == "definite article"):
        j -= 1
    if j < 0 or types[j] != "proper":
        return None
    while j - 2 >= 0 and lemmas[j - 1] == SON and types[j - 2] == "proper":
        j -= 2
    return j


def named_after(types, lemmas, i: int) -> int | None:
    """Index of the name in 'the prophet <Name>', or None."""
    j = i + 1
    if j < len(lemmas) and types[j] == "proper" and lemmas[j]:
        return j
    return None


def main() -> int:
    files = sorted(HEB_DIR.glob("*-lowfat.xml"))
    if not files:
        print(f"no lowfat files under {HEB_DIR}")
        return 1

    # lemma -> English label, and lemma -> how often it is a proper noun
    proper_english: dict[str, Counter] = defaultdict(Counter)
    proper_lemmas: set[str] = set()
    # Pointed forms too: stripping points collapses הַ (article) and הֵם (they)
    # onto the consonants of Ham and Hakkoz, which then masquerade as names.
    proper_pointed: set[str] = set()
    adjacency: Counter = Counter()
    attestations: dict[str, set] = defaultdict(set)
    lemma_total: Counter = Counter()
    lemma_proper: Counter = Counter()

    for path in files:
        words = list(parse(str(path)).iter("w"))
        types = [w.get("type") for w in words]
        lemmas = [cons(w.get("lemma") or "") for w in words]

        for i, w in enumerate(words):
            if not lemmas[i]:
                continue
            lemma_total[lemmas[i]] += 1
            if types[i] == "proper":
                lemma_proper[lemmas[i]] += 1
                proper_lemmas.add(lemmas[i])
                proper_pointed.add(w.get("lemma") or "")
                eng = (w.get("english") or "").strip()
                if eng:
                    proper_english[lemmas[i]][eng] += 1

        for i, lem in enumerate(lemmas):
            if lem not in NABI:
                continue
            # A construct נְבִיאֵי heads a genitive ("prophets of Baal", "prophets
            # of Israel"); only an absolute הַנָּבִיא is apposition to a name.
            if words[i].get("state") == "construct":
                continue
            j = named_before(words, types, lemmas, i)
            if j is None:
                j = named_after(types, lemmas, i)
            if j is None:
                continue
            adjacency[lemmas[j]] += 1
            r = ref_of(words[j])
            if r:
                attestations[lemmas[j]].add(r)

    # Rule (b): proper-noun subject of נבא, read off the extracted clauses
    subject_of_prophesy: Counter = Counter()
    clauses = ROOT / "clauses" / "hebrew.jsonl"
    if clauses.exists():
        with clauses.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if cons(row.get("verb_lemma") or "") != PROPHESY:
                    continue
                # Hebrew puts the head first, so the first proper noun in the
                # subject is the prophet; later ones are patronymic or gentilic
                # ("Eliezer son of Dodavahu of Mareshah").
                for lem in row.get("subject_lemmas") or []:
                    if lem not in proper_pointed:
                        continue
                    c = cons(lem)
                    subject_of_prophesy[c] += 1
                    if row.get("ref_protestant"):
                        attestations[c].add(row["ref_protestant"])
                    break

    roster = {}
    for lem in (set(adjacency) | set(subject_of_prophesy)) - DEITIES:
        # Homograph guard: בֵּן "son" and the article הַ share consonants with the
        # names Ben and Hakkoz. A real name is a proper noun in most of its uses.
        if lemma_proper[lem] * 2 <= lemma_total[lem]:
            continue
        label = proper_english[lem].most_common(1)
        roster[lem] = {
            "english": label[0][0] if label else None,
            "called_prophet": adjacency.get(lem, 0),
            "subject_of_prophesy": subject_of_prophesy.get(lem, 0),
            "refs": sorted(attestations[lem])[:8],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(roster, ensure_ascii=False, indent=2), encoding="utf-8")

    ranked = sorted(roster.items(), key=lambda kv: -(kv[1]["called_prophet"] + kv[1]["subject_of_prophesy"]))
    print(f"roster: {len(roster)} proper nouns the text designates prophetic")
    for lem, info in ranked[:30]:
        print(
            f"  {lem:12} {str(info['english'] or ''):14}"
            f" called_prophet={info['called_prophet']:3} prophesied={info['subject_of_prophesy']:3}"
            f"  {info['refs'][0] if info['refs'] else ''}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
