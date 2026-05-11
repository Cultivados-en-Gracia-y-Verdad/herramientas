#!/usr/bin/env python3

import json
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

FINITE_PREFIXES = (
    "V-PAI",
    "V-AAI",
    "V-FAI",
    "V-IMI",
    "V-PMI",
    "V-API",
    "V-XPI",
    "V-AAS",
    "V-PAS",
    "V-AMS",
    "V-AMO",
    "V-FPI",
    "V-AAD",
    "V-AMD",
    "V-PAD",
)


@dataclass
class Clause:
    cid: str
    greek: str
    gloss: str
    mood: str
    lemma: str = ""
    is_imperative: bool = False
    embedded_label: Optional[str] = None
    children: List["Clause"] = field(default_factory=list)

    def surface(self) -> str:
        text = self.gloss.strip()

        if "==" not in text:
            text = f"=={text}=="

        return text

    def rendered_clause(self) -> str:
        prefix = self.cid

        if self.is_imperative:
            prefix += " [IMP]"

        return f"{prefix}. {self.surface()}"


class VisibleStructureRenderer:

    def __init__(self):
        self.lines: List[str] = []

    def add_clause(self, clause: Clause, indent: int = 0):
        spacing = "    " * indent
        self.lines.append(f"{spacing}{clause.rendered_clause()}")

        for child in clause.children:
            if child.embedded_label:
                self.lines.append(
                    f"{spacing}    {child.embedded_label}"
                )

            self.add_clause(child, indent + 1)

    def render(self) -> str:
        return "\n".join(self.lines)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(
        ch for ch in decomposed
        if unicodedata.category(ch) != "Mn"
    )


def norm(text: str) -> str:
    return strip_accents(text).lower().strip(".,;:·⸀⸃[]() ")


def has_stem(clause: Clause, stems: List[str]) -> bool:
    values = [
        norm(clause.greek),
        norm(clause.lemma),
    ]

    return any(
        value.startswith(stem)
        or stem in value
        for value in values
        for stem in stems
    )


def build_relative_embedding(parent: Clause, child: Clause):
    child.embedded_label = "REL [pronombre relativo griego]"
    parent.children.append(child)


def build_apposition_embedding(parent: Clause, child: Clause):
    child.embedded_label = "APP [explicación / es decir]"
    parent.children.append(child)


def is_finite_rmac(rmac: str) -> bool:

    if not rmac:
        return False

    for prefix in FINITE_PREFIXES:
        if rmac.startswith(prefix):
            return True

    return False


def load_json(path: str):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_clauses(data) -> List[Clause]:

    clauses = []
    clause_num = 1

    for col in data["columns"]:

        rmac = col.get("rmac", "")

        if not is_finite_rmac(rmac):
            continue

        greek = col.get("greek", "")
        gloss = col.get("nbla", "")
        lemma = col.get("lemma", "")

        is_imperative = "-M" in rmac or "-D" in rmac or "IMP" in rmac

        clause = Clause(
            cid=f"C{clause_num}",
            greek=greek,
            gloss=gloss,
            mood=rmac,
            lemma=lemma,
            is_imperative=is_imperative,
        )

        clauses.append(clause)
        clause_num += 1

    return clauses


def is_relative_pair(first: Clause, second: Clause) -> bool:
    return (
        has_stem(first, ["παρακαλ"])
        and has_stem(second, ["γεννα", "γενν"])
    )


def is_apposition_pair(first: Clause, second: Clause) -> bool:
    surface = norm(second.gloss)

    return (
        has_stem(second, ["ειμι", "εστι"])
        and "es decir" in surface
    )


def apply_simple_embeddings(clauses: List[Clause]):

    if len(clauses) < 2:
        return clauses

    output: List[Clause] = []
    skip_next = False

    for i, clause in enumerate(clauses):
        if skip_next:
            skip_next = False
            continue

        if i + 1 >= len(clauses):
            output.append(clause)
            continue

        next_clause = clauses[i + 1]

        if is_relative_pair(clause, next_clause):
            build_relative_embedding(clause, next_clause)
            output.append(clause)
            skip_next = True
            continue

        if is_apposition_pair(clause, next_clause):
            build_apposition_embedding(clause, next_clause)
            output.append(clause)
            skip_next = True
            continue

        output.append(clause)

    return output


def render_structure(clauses: List[Clause]):

    renderer = VisibleStructureRenderer()

    for clause in clauses:
        renderer.add_clause(clause)

    return renderer.render()


def main():

    if len(sys.argv) != 2:
        print(
            "usage: python3 roots_engine_v2_rewrite.py path/to/verse.json"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    data = load_json(path)

    clauses = build_clauses(data)

    clauses = apply_simple_embeddings(clauses)

    print(render_structure(clauses))


if __name__ == "__main__":
    main()
