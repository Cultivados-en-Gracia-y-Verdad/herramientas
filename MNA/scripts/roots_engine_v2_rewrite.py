#!/usr/bin/env python3

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FINITE_PREFIXES = (
    "V-PAI", "V-AAI", "V-FAI", "V-IMI", "V-PMI", "V-API", "V-XPI",
    "V-AAS", "V-PAS", "V-AMS", "V-AMO", "V-FPI", "V-AAD", "V-AMD", "V-PAD",
)

CLAUSE_LEVEL = "clause-level"
PHRASE_LEVEL = "phrase-level"
DISCOURSE_LEVEL = "discourse-level"

CONDITION_LEMMAS = {"εἰ"}
ALTERNATIVE_LEMMAS = {"ἤ"}
PURPOSE_LEMMAS = {"ἵνα"}
CONTENT_LEMMAS = {"ὅτι"}
COORDINATION_LEMMAS = {"καί"}
REPORTING_LEMMA_STEMS = ["λεγω", "γραφ"]
REPORTING_GLOSS_STEMS = ["digo", "decir", "escrib"]


@dataclass
class Clause:
    cid: str
    greek: str
    gloss: str
    mood: str
    lemma: str = ""
    greek_pos: int = 999999
    nbla_start: int = 999999
    nbla_end: int = 999999
    finite_surface: str = ""
    clause_surface: str = ""
    is_imperative: bool = False
    embedded_label: Optional[str] = None
    owner_clause_id: Optional[str] = None
    relation_type: Optional[str] = None
    structural_level: str = CLAUSE_LEVEL
    children: List["Clause"] = field(default_factory=list)

    def surface_text(self) -> str:
        return (self.clause_surface or self.gloss or "").strip()

    def surface(self) -> str:
        text = self.surface_text()
        finite = (self.finite_surface or self.gloss or "").strip()

        if not text:
            return ""

        if "==" in text:
            return text

        if finite and finite in text:
            return text.replace(finite, f"=={finite}==", 1)

        # Fallback: normalized whitespace match.
        if finite:
            pattern = re.compile(re.escape(finite), re.IGNORECASE)
            return pattern.sub(f"=={finite}==", text, count=1)

        return f"=={text}=="

    def rendered_clause(self) -> str:
        prefix = self.cid
        if self.is_imperative:
            prefix += " [IMP]"
        return f"{prefix}. {self.surface()}"


@dataclass
class Connector:
    greek: str
    lemma: str
    gloss: str
    greek_pos: int
    level: str
    relation_type: str


class VisibleStructureRenderer:
    def __init__(self):
        self.lines: List[str] = []

    def add_clause(self, clause: Clause, indent: int = 0):
        spacing = "    " * indent
        self.lines.append(f"{spacing}{clause.rendered_clause()}")

        for child in clause.children:
            if child.embedded_label:
                self.lines.append(f"{spacing}    {child.embedded_label}")
            self.add_clause(child, indent + 1)

    def render(self) -> str:
        return "\n".join(self.lines)


def attach_child(parent: Clause, child: Clause, relation_type: str) -> bool:
    if child.owner_clause_id is not None:
        return False
    child.owner_clause_id = parent.cid
    child.relation_type = relation_type
    parent.children.append(child)
    return True


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def norm(text: str) -> str:
    return strip_accents(text).lower().strip(".,;:·⸀⸃[]() ")


def greek_index(col: Dict) -> int:
    for token in col.get("greek_tokens") or []:
        try:
            return int(token)
        except Exception:
            continue
    return 999999


def nbla_indexes(col: Dict) -> List[int]:
    raw = str(col.get("nbla_idx", "") or "").strip()
    if not raw or raw == "-":
        return []
    values: List[int] = []
    for part in re.split(r"[,;\s]+", raw):
        if not part:
            continue
        try:
            values.append(int(part))
        except ValueError:
            continue
    return values


def first_nbla_index(col: Dict) -> int:
    indexes = nbla_indexes(col)
    return min(indexes) if indexes else 999999


def build_nbla_chunks(data) -> List[Tuple[int, int, str]]:
    chunks: List[Tuple[int, int, str]] = []
    seen_spans = set()

    for col in sorted(data.get("columns", []), key=lambda c: (first_nbla_index(c), greek_index(c))):
        indexes = nbla_indexes(col)
        text = str(col.get("nbla", "") or "").strip()
        if not indexes or not text:
            continue

        span = (min(indexes), max(indexes), text)
        if span in seen_spans:
            continue
        seen_spans.add(span)
        chunks.append(span)

    # Remove chunks fully covered by a previous multi-token chunk.
    filtered: List[Tuple[int, int, str]] = []
    covered_indexes = set()
    for start, end, text in chunks:
        span_indexes = set(range(start, end + 1))
        if span_indexes and span_indexes.issubset(covered_indexes):
            continue
        filtered.append((start, end, text))
        covered_indexes.update(span_indexes)

    return filtered


def collect_nbla_surface(chunks: List[Tuple[int, int, str]], start: int, end: int) -> str:
    parts: List[str] = []
    for chunk_start, chunk_end, text in chunks:
        if chunk_start < start:
            continue
        if chunk_start > end:
            continue
        parts.append(text)
    return " ".join(parts).strip()


def has_stem(clause: Clause, stems: List[str]) -> bool:
    values = [norm(clause.greek), norm(clause.lemma), norm(clause.gloss), norm(clause.clause_surface)]
    return any(value.startswith(stem) or stem in value for value in values for stem in stems)


def is_reporting_clause(clause: Clause) -> bool:
    return (
        has_stem(clause, REPORTING_LEMMA_STEMS)
        and any(norm(clause.gloss).startswith(stem) for stem in REPORTING_GLOSS_STEMS)
    )


def build_relative_embedding(parent: Clause, child: Clause):
    child.embedded_label = "REL [pronombre relativo griego]"
    attach_child(parent, child, "relative")


def build_apposition_embedding(parent: Clause, child: Clause):
    child.embedded_label = "APP [explicación / es decir]"
    attach_child(parent, child, "apposition")


def build_condition_group(main_clause: Clause, condition_members: List[Clause], has_alternative: bool):
    if not condition_members:
        return
    condition_members[0].embedded_label = "COND [εἰ ... ἢ]" if len(condition_members) > 1 or has_alternative else "COND [εἰ]"
    for member in condition_members:
        attach_child(main_clause, member, "condition")


def build_connector_embedding(parent: Clause, child: Clause, label: str, relation_type: str):
    child.embedded_label = label
    attach_child(parent, child, relation_type)


def build_purpose_group(parent: Clause, purpose_members: List[Clause]):
    if not purpose_members:
        return
    purpose_members[0].embedded_label = "PURP [ἵνα]"
    for member in purpose_members:
        attach_child(parent, member, "purpose")


def is_finite_rmac(rmac: str) -> bool:
    if not rmac:
        return False
    return any(rmac.startswith(prefix) for prefix in FINITE_PREFIXES)


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
    clauses: List[Clause] = []
    nbla_chunks = build_nbla_chunks(data)

    for col in data.get("columns", []):
        rmac = col.get("rmac", "")
        if not is_finite_rmac(rmac):
            continue

        greek = col.get("greek", "")
        gloss = col.get("nbla", "")
        lemma = col.get("lemma", "")
        indexes = nbla_indexes(col)

        clause = Clause(
            cid="",
            greek=greek,
            gloss=gloss,
            mood=rmac,
            lemma=lemma,
            greek_pos=greek_index(col),
            nbla_start=min(indexes) if indexes else 999999,
            nbla_end=max(indexes) if indexes else 999999,
            finite_surface=gloss,
            is_imperative=is_imperative_rmac(rmac),
        )
        clauses.append(clause)

    clauses.sort(key=lambda item: item.greek_pos)

    # Build a visible Spanish clause span from this finite verb up to the next finite verb.
    # This fixes the previous bug where the visible structure printed only the finite-verb column.
    sorted_by_nbla = sorted(clauses, key=lambda item: item.nbla_start)
    max_nbla_index = max((end for _, end, _ in nbla_chunks), default=0)
    for i, clause in enumerate(sorted_by_nbla):
        next_start = sorted_by_nbla[i + 1].nbla_start if i + 1 < len(sorted_by_nbla) else max_nbla_index + 1
        clause.nbla_end = max(clause.nbla_end, next_start - 1)
        clause.clause_surface = collect_nbla_surface(nbla_chunks, clause.nbla_start, clause.nbla_end)

    for i, clause in enumerate(clauses, start=1):
        clause.cid = f"C{i}"

    return clauses


def connector_key(col: Dict) -> str:
    return norm(col.get("lemma", "") or col.get("greek", ""))


def classify_connector(col: Dict) -> Optional[Connector]:
    lemma = col.get("lemma", "")
    greek = col.get("greek", "")
    gloss = col.get("nbla", "")
    pos = greek_index(col)
    key = connector_key(col)

    if key in {norm(item) for item in CONDITION_LEMMAS}:
        return Connector(greek, lemma, gloss, pos, CLAUSE_LEVEL, "condition")
    if key in {norm(item) for item in PURPOSE_LEMMAS}:
        return Connector(greek, lemma, gloss, pos, CLAUSE_LEVEL, "purpose")
    if key in {norm(item) for item in CONTENT_LEMMAS}:
        return Connector(greek, lemma, gloss, pos, CLAUSE_LEVEL, "content")
    if key in {norm(item) for item in ALTERNATIVE_LEMMAS}:
        return Connector(greek, lemma, gloss, pos, PHRASE_LEVEL, "alternative")
    if key in {norm(item) for item in COORDINATION_LEMMAS}:
        return Connector(greek, lemma, gloss, pos, PHRASE_LEVEL, "coordination")
    return None


def build_connectors(data) -> List[Connector]:
    connectors: List[Connector] = []
    for col in data.get("columns", []):
        connector = classify_connector(col)
        if connector is not None:
            connectors.append(connector)
    return sorted(connectors, key=lambda item: item.greek_pos)


def is_relative_pair(first: Clause, second: Clause) -> bool:
    return has_stem(first, ["παρακαλ"]) and has_stem(second, ["γεννα", "γενν"])


def is_apposition_pair(first: Clause, second: Clause) -> bool:
    return has_stem(first, ["αναπεμπ", "ανεπεμψ"]) and has_stem(second, ["ειμι", "εστι"])


def clause_before(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    prior = [clause for clause in clauses if clause.greek_pos < pos]
    return prior[-1] if prior else None


def clause_after(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    for clause in clauses:
        if clause.greek_pos > pos:
            return clause
    return None


def next_clause_after(clause: Clause, clauses: List[Clause]) -> Optional[Clause]:
    return clause_after(clause.greek_pos, clauses)


def first_imperative_after(clause: Clause, clauses: List[Clause]) -> Optional[Clause]:
    started = False
    for candidate in clauses:
        if candidate is clause:
            started = True
            continue
        if not started:
            continue
        if candidate.is_imperative:
            return candidate
    return None


def alternatives_between(start: Clause, end: Clause, connectors: List[Connector]) -> bool:
    return any(
        connector.relation_type == "alternative" and start.greek_pos < connector.greek_pos < end.greek_pos
        for connector in connectors
    )


def clause_level_connector_between(start_pos: int, end_pos: int, connectors: List[Connector]) -> bool:
    return any(
        connector.level == CLAUSE_LEVEL and start_pos < connector.greek_pos < end_pos
        for connector in connectors
    )


def apply_condition_grouping(clauses: List[Clause], connectors: List[Connector]) -> List[Clause]:
    for connector in connectors:
        if connector.level != CLAUSE_LEVEL or connector.relation_type != "condition":
            continue
        first_condition = clause_after(connector.greek_pos, clauses)
        if first_condition is None:
            continue
        main_clause = first_imperative_after(first_condition, clauses)
        if main_clause is None:
            continue

        condition_members: List[Clause] = []
        for clause in clauses:
            if clause.greek_pos < first_condition.greek_pos:
                continue
            if clause is main_clause or clause.is_imperative:
                break
            condition_members.append(clause)

        has_alternative = alternatives_between(first_condition, main_clause, connectors)
        build_condition_group(main_clause, condition_members, has_alternative)
    return clauses


def collect_purpose_members(first_child: Clause, clauses: List[Clause], connectors: List[Connector]) -> List[Clause]:
    members = [first_child]
    previous = first_child
    for clause in clauses:
        if clause.greek_pos <= first_child.greek_pos:
            continue
        if clause.owner_clause_id is not None:
            continue
        if clause.is_imperative:
            break
        if clause_level_connector_between(previous.greek_pos, clause.greek_pos, connectors):
            break
        members.append(clause)
        previous = clause
    return members


def apply_subordinating_connectors(clauses: List[Clause], connectors: List[Connector]) -> List[Clause]:
    for connector in connectors:
        if connector.level != CLAUSE_LEVEL or connector.relation_type == "condition":
            continue
        child = clause_after(connector.greek_pos, clauses)
        parent = clause_before(connector.greek_pos, clauses)
        if child is None or parent is None:
            continue

        if connector.relation_type == "purpose":
            build_purpose_group(parent, collect_purpose_members(child, clauses, connectors))
            continue
        if connector.relation_type == "content":
            build_connector_embedding(parent, child, "CONT [ὅτι]", "content")
            continue
    return clauses


def apply_implicit_reporting_content(clauses: List[Clause]) -> List[Clause]:
    for clause in clauses:
        if not is_reporting_clause(clause):
            continue
        child = next_clause_after(clause, clauses)
        if child is None or child.owner_clause_id is not None or child.is_imperative:
            continue
        build_connector_embedding(clause, child, "CONT [implícito]", "content-implicit")
    return clauses


def apply_simple_embeddings(clauses: List[Clause]):
    if len(clauses) < 2:
        return clauses
    for i, clause in enumerate(clauses):
        if clause.owner_clause_id is not None or i + 1 >= len(clauses):
            continue
        next_clause = clauses[i + 1]
        if next_clause.owner_clause_id is not None:
            continue
        if is_relative_pair(clause, next_clause):
            build_relative_embedding(clause, next_clause)
            continue
        if is_apposition_pair(clause, next_clause):
            build_apposition_embedding(clause, next_clause)
            continue
    return clauses


def render_structure(clauses: List[Clause]):
    renderer = VisibleStructureRenderer()
    root_clauses = [clause for clause in clauses if clause.owner_clause_id is None]
    for clause in root_clauses:
        renderer.add_clause(clause)
    return renderer.render()


def main():
    if len(sys.argv) != 2:
        print("usage: python3 roots_engine_v2_rewrite.py path/to/verse.json")
        sys.exit(1)

    data = load_json(str(Path(sys.argv[1])))
    clauses = build_clauses(data)
    connectors = build_connectors(data)

    clauses = apply_condition_grouping(clauses, connectors)
    clauses = apply_subordinating_connectors(clauses, connectors)
    clauses = apply_implicit_reporting_content(clauses)
    clauses = apply_simple_embeddings(clauses)

    print(render_structure(clauses))


if __name__ == "__main__":
    main()
