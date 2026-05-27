#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List


CONNECTOR_LEMMAS = {
    "καί": "y",
    "δέ": "pero/y",
    "γάρ": "porque/pues",
    "ἀλλά": "pero/sino",
    "οὖν": "por tanto",
    "ὅτι": "que/porque",
    "ἵνα": "para que",
    "εἰ": "si",
    "ὡς": "como",
}


def fail(message: str) -> None:
    print("FAIL")
    print()
    print(f"- {message}")
    sys.exit(1)


def load_json(path: Path) -> Dict:
    if not path.exists():
        fail(f"JSON not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_finite_verb(rmac: str) -> bool:
    """
    Conservative first pass.

    Expected RMAC-style examples:
    V-PAI-1S
    V-AAI-3S
    V-PAS-2P

    We exclude:
    participles, infinitives, adjectives, nouns, pronouns, articles, conjunctions.
    """
    if not rmac:
        return False

    if not rmac.startswith("V-"):
        return False

    parts = rmac.split("-")

    if len(parts) < 3:
        return False

    code = parts[1]

    # Infinitive / participle patterns are not finite.
    if "N" in code:
        return False

    if "P" in code and len(parts) < 3:
        return False

    # Require person-number in final slot, e.g. 1S, 3P.
    person_number = parts[-1]

    return person_number in {
        "1S", "2S", "3S",
        "1P", "2P", "3P",
    }


def get_nbla_text(columns: List[Dict]) -> str:
    words = []

    for col in columns:
        alignment = col.get("alignment", "").strip()

        # Shared rows attach Greek data to an already-used NBLA word.
        # They should not duplicate the NBLA surface text.
        if alignment == "shared":
            continue

        text = col.get("nbla", "").strip()

        if not text or text == "-":
            continue

        words.append(text)

    text = " ".join(words)

    # Light cleanup for punctuation spacing.
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")
    text = text.replace(" :", ":")
    text = text.replace(" ?", "?")
    text = text.replace(" !", "!")

    return text


def find_finite_verbs(columns: List[Dict]) -> List[Dict]:
    verbs = []

    for col in columns:
        rmac = col.get("rmac", "")

        if is_finite_verb(rmac):
            verbs.append({
                "column": col.get("column"),
                "nbla": col.get("nbla", ""),
                "greek": col.get("greek", ""),
                "lemma": col.get("lemma", ""),
                "rmac": rmac,
                "greek_tokens": col.get("greek_tokens", []),
            })

    return verbs


def find_connectors(columns: List[Dict]) -> List[Dict]:
    connectors = []

    for col in columns:
        lemma = col.get("lemma", "")
        greek = col.get("greek", "")

        if lemma in CONNECTOR_LEMMAS or greek in CONNECTOR_LEMMAS:
            connectors.append({
                "column": col.get("column"),
                "nbla": col.get("nbla", ""),
                "greek": greek,
                "lemma": lemma,
                "function_hint": CONNECTOR_LEMMAS.get(
                    lemma,
                    CONNECTOR_LEMMAS.get(greek, "")
                ),
                "greek_tokens": col.get("greek_tokens", []),
            })

    return connectors


def render_roots_seed(data: Dict) -> None:
    reference = data.get("reference", "")
    columns = data.get("columns", [])

    nbla_text = get_nbla_text(columns)
    finite_verbs = find_finite_verbs(columns)
    connectors = find_connectors(columns)

    print(f"### {reference}")
    print()

    print("#### NBLA")
    print()
    print(nbla_text)
    print()

    print("#### Verbos finitos")
    print()

    if not finite_verbs:
        print("- ninguno detectado")
    else:
        for verb in finite_verbs:
            print(
                f"- col {verb['column']}: "
                f"{verb['greek']} → {verb['nbla']} "
                f"({verb['rmac']})"
            )

    print()

    print("#### Conectores")
    print()

    if not connectors:
        print("- ninguno detectado")
    else:
        for connector in connectors:
            print(
                f"- col {connector['column']}: "
                f"{connector['greek']} → {connector['nbla']} "
                f"[{connector['function_hint']}]"
            )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:")
        print(
            "  python3 scripts/roots_from_interlinear_json.py "
            "data/interlinear/filemon/1/1.json"
        )
        sys.exit(2)

    path = Path(sys.argv[1])
    data = load_json(path)

    render_roots_seed(data)


if __name__ == "__main__":
    main()