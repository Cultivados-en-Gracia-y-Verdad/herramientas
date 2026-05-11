#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Clause:
    cid: str
    greek: str
    gloss: str
    mood: str
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


@dataclass
class Relation:
    rid: str
    connector: str
    relation: str
    direction: str
    source_clause: str
    target_clause: str
    subordinate: bool = False


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


def build_relative_embedding(
    parent: Clause,
    child: Clause,
):
    child.embedded_label = (
        "REL [pronombre relativo griego]"
    )

    parent.children.append(child)


def build_apposition_embedding(
    parent: Clause,
    child: Clause,
):
    child.embedded_label = (
        "APP [explicación / es decir]"
    )

    parent.children.append(child)


def demo():

    c1 = Clause(
        cid="C1",
        greek="παρακαλῶ",
        gloss="te ruego",
        mood="indicative",
    )

    c2 = Clause(
        cid="C2",
        greek="ἐγέννησα",
        gloss="he engendrado",
        mood="indicative",
    )

    build_relative_embedding(c1, c2)

    renderer = VisibleStructureRenderer()
    renderer.add_clause(c1)

    print(renderer.render())


if __name__ == "__main__":
    demo()
