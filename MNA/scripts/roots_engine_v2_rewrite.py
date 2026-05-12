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
        if finite:
            return re.sub(re.escape(finite), f"=={finite}==", text, count=1, flags=re.IGNORECASE)
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
            pass
    return 999999


def nbla_indexes(col: Dict) -> List[int]:
    """Parse NBLA indexes in all current project forms: 01,02 / 01-02 / 01, 02 / -."""
    raw = str(col.get("nbla_idx", "") or "").strip()
    if not raw or raw == "-":
        return []

    values: List[int] = []
    for part in re.split(r"[,;\s]+", raw):
        part = part.strip()
        if not part or part == "-":
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            try:
                start = int(left)
                end = int(right)
            except ValueError:
                continue
            values.extend(range(start, end + 1))
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
    seen = set()
    for col in sorted(data.get("columns", []), key=lambda c: (first_nbla_index(c), greek_index(c))):
        indexes = nbla_indexes(col)
        text = str(col.get("nbla", "") or "").strip()
        if not indexes or not text or text == "-":
            continue
        span = (min(indexes), max(indexes), text)
        if span in seen:
            continue
        seen.add(span)
        chunks.append(span)

    filtered: List[Tuple[int, int, str]] = []
    covered = set()
    for start, end, text in chunks:
        span_indexes = set(range(start, end + 1))
        if span_indexes and span_indexes.issubset(covered):
            continue
        filtered.append((start, end, text))
        covered.update(span_indexes)
    return filtered


def collect_nbla_surface(chunks: List[Tuple[int, int, str]], start: int, end: int) -> str:
    return " ".join(text for chunk_start, _, text in chunks if start <= chunk_start <= end).strip()


def is_finite_rmac(rmac: str) -> bool:
    return bool(rmac) and any(rmac.startswith(prefix) for prefix in FINITE_PREFIXES)


def is_imperative_rmac(rmac: str) -> bool:
    parts = (rmac or "").split("-")
    return len(parts) >= 2 and (parts[1].endswith("M") or parts[1].endswith("D"))


def has_stem(clause: Clause, stems: List[str]) -> bool:
    values = [norm(clause.greek), norm(clause.lemma), norm(clause.gloss), norm(clause.clause_surface)]
    return any(value.startswith(stem) or stem in value for value in values for stem in stems)


def is_reporting_clause(clause: Clause) -> bool:
    return has_stem(clause, REPORTING_LEMMA_STEMS) and any(norm(clause.gloss).startswith(stem) for stem in REPORTING_GLOSS_STEMS)


def attach_child(parent: Clause, child: Clause, relation_type: str) -> bool:
    if child.owner_clause_id is not None:
        return False
    child.owner_clause_id = parent.cid
    child.relation_type = relation_type
    parent.children.append(child)
    return True


def build_clauses(data) -> List[Clause]:
    clauses: List[Clause] = []
    nbla_chunks = build_nbla_chunks(data)

    for col in data.get("columns", []):
        rmac = col.get("rmac", "")
        if not is_finite_rmac(rmac):
            continue
        indexes = nbla_indexes(col)
        gloss = str(col.get("nbla", "") or "").strip()
        clauses.append(Clause(
            cid="",
            greek=col.get("greek", ""),
            gloss=gloss,
            mood=rmac,
            lemma=col.get("lemma", ""),
            greek_pos=greek_index(col),
            nbla_start=min(indexes) if indexes else 999999,
            nbla_end=max(indexes) if indexes else 999999,
            finite_surface=gloss,
            is_imperative=is_imperative_rmac(rmac),
        ))

    clauses.sort(key=lambda item: item.greek_pos)

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
    key = connector_key(col)
    greek = col.get("greek", "")
    lemma = col.get("lemma", "")
    gloss = col.get("nbla", "")
    pos = greek_index(col)

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
    return sorted((c for col in data.get("columns", []) if (c := classify_connector(col))), key=lambda item: item.greek_pos)


def clause_before(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    prior = [clause for clause in clauses if clause.greek_pos < pos]
    return prior[-1] if prior else None


def clause_after(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    for clause in clauses:
        if clause.greek_pos > pos:
            return clause
    return None


def first_imperative_after(clause: Clause, clauses: List[Clause]) -> Optional[Clause]:
    started = False
    for candidate in clauses:
        if candidate is clause:
            started = True
            continue
        if started and candidate.is_imperative:
            return candidate
    return None


def alternatives_between(start: Clause, end: Clause, connectors: List[Connector]) -> bool:
    return any(c.relation_type == "alternative" and start.greek_pos < c.greek_pos < end.greek_pos for c in connectors)


def clause_level_connector_between(start_pos: int, end_pos: int, connectors: List[Connector]) -> bool:
    return any(c.level == CLAUSE_LEVEL and start_pos < c.greek_pos < end_pos for c in connectors)


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
        members = []
        for clause in clauses:
            if clause.greek_pos < first_condition.greek_pos:
                continue
            if clause is main_clause or clause.is_imperative:
                break
            members.append(clause)
        if members:
            members[0].embedded_label = "COND [εἰ ... ἢ]" if len(members) > 1 or alternatives_between(first_condition, main_clause, connectors) else "COND [εἰ]"
            for member in members:
                attach_child(main_clause, member, "condition")
    return clauses


def collect_purpose_members(first_child: Clause, clauses: List[Clause], connectors: List[Connector]) -> List[Clause]:
    members = [first_child]
    previous = first_child
    for clause in clauses:
        if clause.greek_pos <= first_child.greek_pos or clause.owner_clause_id is not None:
            continue
        if clause.is_imperative or clause_level_connector_between(previous.greek_pos, clause.greek_pos, connectors):
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
            members = collect_purpose_members(child, clauses, connectors)
            if members:
                members[0].embedded_label = "PURP [ἵνα]"
                for member in members:
                    attach_child(parent, member, "purpose")
        elif connector.relation_type == "content":
            child.embedded_label = "CONT [ὅτι]"
            attach_child(parent, child, "content")
    return clauses


def apply_implicit_reporting_content(clauses: List[Clause]) -> List[Clause]:
    for clause in clauses:
        if not is_reporting_clause(clause):
            continue
        child = clause_after(clause.greek_pos, clauses)
        if child is not None and child.owner_clause_id is None and not child.is_imperative:
            child.embedded_label = "CONT [implícito]"
            attach_child(clause, child, "content-implicit")
    return clauses


def apply_simple_embeddings(clauses: List[Clause]) -> List[Clause]:
    for i, clause in enumerate(clauses[:-1]):
        if clause.owner_clause_id is not None:
            continue
        nxt = clauses[i + 1]
        if nxt.owner_clause_id is not None:
            continue
        if has_stem(clause, ["παρακαλ"]) and has_stem(nxt, ["γεννα", "γενν"]):
            nxt.embedded_label = "REL [pronombre relativo griego]"
            attach_child(clause, nxt, "relative")
        elif has_stem(clause, ["αναπεμπ", "ανεπεμψ"]) and has_stem(nxt, ["ειμι", "εστι"]):
            nxt.embedded_label = "APP [explicación / es decir]"
            attach_child(clause, nxt, "apposition")
    return clauses


def render_structure(clauses: List[Clause]) -> str:
    renderer = VisibleStructureRenderer()
    for clause in [c for c in clauses if c.owner_clause_id is None]:
        renderer.add_clause(clause)
    return renderer.render()


def render_json_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    clauses = build_clauses(data)
    connectors = build_connectors(data)
    clauses = apply_condition_grouping(clauses, connectors)
    clauses = apply_subordinating_connectors(clauses, connectors)
    clauses = apply_implicit_reporting_content(clauses)
    clauses = apply_simple_embeddings(clauses)
    return render_structure(clauses)


def main():
    if len(sys.argv) != 2:
        print("usage: python3 roots_engine_v2_rewrite.py path/to/verse.json")
        sys.exit(1)
    print(render_json_file(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
