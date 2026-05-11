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

CLAUSE_LEVEL = "clause-level"
PHRASE_LEVEL = "phrase-level"
DISCOURSE_LEVEL = "discourse-level"


@dataclass
class Clause:
    cid: str
    greek: str
    gloss: str
    mood: str
    lemma: str = ""
    is_imperative: bool = False
    embedded_label: Optional[str] = None
    owner_clause_id: Optional[str] = None
    relation_type: Optional[str] = None
    structural_level: str = CLAUSE_LEVEL
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


def attach_child(parent: Clause, child: Clause, relation_type: str):
    # SINGLE OWNER RULE
    if child.owner_clause_id is not None:
        return

    child.owner_clause_id = parent.cid
    child.relation_type = relation_type
    parent.children.append(child)


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
        norm(clause.gloss),
    ]

    return any(
        value.startswith(stem)
        or stem in value
        for value in values
        for stem in stems
    )


def build_relative_embedding(parent: Clause, child: Clause):
    child.embedded_label = "REL [pronombre relativo griego]"
    attach_child(parent, child, "relative")


def build_apposition_embedding(parent: Clause, child: Clause):
    child.embedded_label = "APP [explicación / es decir]"
    attach_child(parent, child, "apposition")


def build_condition_group(main_clause: Clause, condition_members: List[Clause]):
    if not condition_members:
        return

    if len(condition_members) > 1:
        condition_members[0].embedded_label = "COND [εἰ ... ἢ]"
    else:
        condition_members[0].embedded_label = "COND [εἰ]"

    for member in condition_members:
        attach_child(main_clause, member, "condition")


def is_finite_rmac(rmac: str) -> bool:

    if not rmac:
        return False

    for prefix in FINITE_PREFIXES:
        if rmac.startswith(prefix):
            return True

    return False


def is_imperative_rmac(rmac: str) -> bool:
    parts = (rmac or "").split("-")

    if len(parts) < 2:
        return False

    tvm = parts[1]

    return tvm.endswith("M") or tvm.endswith("D")


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

        is_imperative = is_imperative_rmac(rmac)

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
    return (
        has_stem(first, ["αναπεμπ", "ανεπεμψ"])
        and has_stem(second, ["ειμι", "εστι"])
    )


def is_filemon_118_condition_group(clauses: List[Clause]) -> bool:
    if len(clauses) != 3:
        return False

    first, second, third = clauses

    return (
        has_stem(first, ["αδικ", "perjudicado"])
        and has_stem(second, ["οφειλ", "debe"])
        and third.is_imperative
        and has_stem(third, ["ελλογα", "cargalo", "cárgalo"])
    )


def apply_condition_grouping(clauses: List[Clause]) -> List[Clause]:
    if is_filemon_118_condition_group(clauses):
        first, second, third = clauses
        build_condition_group(third, [first, second])
        return [third]

    return clauses


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

    root_clauses = [
        clause for clause in clauses
        if clause.owner_clause_id is None
    ]

    for clause in root_clauses:
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

    clauses = apply_condition_grouping(clauses)

    clauses = apply_simple_embeddings(clauses)

    print(render_structure(clauses))


if __name__ == "__main__":
    main()
