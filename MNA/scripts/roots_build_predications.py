#!/usr/bin/env python3

"""
ROOTS — Independent Predication Dataset

PURPOSE
-------
Build machine-readable finite predication candidates from
Greek token + MorphGNT datasets.

THIS SCRIPT DOES:
- detect finite verbs
- recover subject source
- recover conservative predicate spans
- detect explicit subordination markers
- emit machine-readable predication records

THIS SCRIPT DOES NOT:
- infer topology
- infer discourse trees
- infer Paso 5
- infer Paso 6
- infer hierarchy
- infer ownership
- infer semantics

OUTPUT
------
JSONL
(one predication candidate per line)

INPUT TSV
---------
Required columns:

BOOK
CH
VS
TOKEN_ID
GREEK
LEMMA
MORPH
"""

import csv
import json
import sys
from collections import defaultdict


FINITE_CODES = {
    "PAI", "PMI", "PPI",
    "IAI", "IMI", "IPI",
    "FAI", "FMI", "FPI",
    "AAI", "AMI", "API",
    "AAS", "AMS", "APS",
    "RAI", "RMI", "RPI",
    "LAI"
}


SUBORDINATORS = {
    "ἵνα",
    "εἰ",
    "ἐάν",
    "ὅτι",
    "ὡς",
    "ὅταν",
    "ἐπειδή",
    "καθώς",
    "πρίν"
}


def load_tsv(path):

    verses = defaultdict(list)

    with open(path, encoding="utf-8") as f:

        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:

            key = (
                row["BOOK"],
                row["CH"],
                row["VS"]
            )

            verses[key].append(row)

    return verses


def is_finite_verb(morph):

    if not morph.startswith("V-"):
        return False

    parts = morph.split("-")

    if len(parts) < 2:
        return False

    return parts[1] in FINITE_CODES


def parse_person_number(morph):

    parts = morph.split("-")

    if len(parts) < 3:
        return None, None

    pn = parts[2]

    if len(pn) != 2:
        return None, None

    return pn[0], pn[1]


def is_nominative(morph):

    parts = morph.split("-")

    if len(parts) < 3:
        return False

    final = parts[-1]

    if len(final) < 1:
        return False

    return final[0] == "N"


def recover_subject(tokens, verb_index, person, number):

    WINDOW = 6

    start = max(0, verb_index - WINDOW)
    end = min(len(tokens), verb_index + WINDOW + 1)

    nearby = tokens[start:end]

    for tok in nearby:

        morph = tok["MORPH"]

        if is_nominative(morph):

            return {
                "subject_type": "explicit",
                "subject_token": int(tok["TOKEN_ID"]),
                "subject_form": tok["GREEK"],
                "subject_lemma": tok["LEMMA"],
                "subject_morph": morph,
                "subject_confidence": "medium"
            }

    if person and number:

        return {
            "subject_type": "implied",
            "subject_person": person,
            "subject_number": number,
            "subject_confidence": "high"
        }

    return {
        "subject_type": "unresolved",
        "subject_confidence": "low"
    }


def detect_subordination(tokens, verb_index):

    LOOKBACK = 3

    start = max(0, verb_index - LOOKBACK)

    for i in range(start, verb_index):

        tok = tokens[i]["GREEK"]

        if tok in SUBORDINATORS:

            return {
                "subordinated": True,
                "marker": tok,
                "confidence": "high"
            }

    return {
        "subordinated": False,
        "marker": None,
        "confidence": "low"
    }


def recover_predicate_span(tokens, verb_index):

    start = max(0, verb_index - 2)
    end = min(len(tokens) - 1, verb_index + 2)

    return start, end


def main():

    if len(sys.argv) != 3:

        print(
            "usage:\n"
            "python3 roots_build_predications.py input.tsv output.jsonl"
        )

        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    verses = load_tsv(input_path)

    predication_counter = 1

    with open(output_path, "w", encoding="utf-8") as out:

        for ref, tokens in verses.items():

            book, ch, vs = ref

            for i, tok in enumerate(tokens):

                morph = tok["MORPH"]

                if not is_finite_verb(morph):
                    continue

                person, number = parse_person_number(morph)

                subject = recover_subject(
                    tokens,
                    i,
                    person,
                    number
                )

                subordination = detect_subordination(
                    tokens,
                    i
                )

                span_start, span_end = recover_predicate_span(
                    tokens,
                    i
                )

                record = {

                    "predication_id":
                        f"P{predication_counter:06d}",

                    "book": book,
                    "chapter": int(ch),
                    "verse": int(vs),

                    "finite_verb_token":
                        int(tok["TOKEN_ID"]),

                    "finite_verb":
                        tok["GREEK"],

                    "finite_lemma":
                        tok["LEMMA"],

                    "finite_morph":
                        morph,

                    **subject,

                    "predicate_token_start":
                        int(tokens[span_start]["TOKEN_ID"]),

                    "predicate_token_end":
                        int(tokens[span_end]["TOKEN_ID"]),

                    "independence_status":
                        "candidate",

                    "subordination":
                        subordination,

                    "confidence": "medium"
                }

                out.write(
                    json.dumps(
                        record,
                        ensure_ascii=False
                    ) + "\n"
                )

                predication_counter += 1


if __name__ == "__main__":
    main()
