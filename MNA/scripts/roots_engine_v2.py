#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set


JSON_DIR = Path("data/interlinear/filemon/1")
CONNECTOR_RULES = Path("data/rules/connectors.json")
OUTPUT_FILE = Path("output/filemon-roots-engine-v2.md")


APPROVED_RELATIONSHIP_TYPES = {
    "reason",
    "content",
    "purpose",
    "result",
    "condition",
    "coordination",
    "contrast",
    "inference",
    "comparison",
}

CATEGORY_TO_RELATIONSHIP = {
    "reason_explanation": "reason",
    "content_or_reason": "content",
    "purpose_result": "purpose",
    "condition": "condition",
    "coordination_addition": "coordination",
    "development_contrast": "contrast",
    "strong_contrast": "contrast",
    "inference_conclusion": "inference",
    "comparison_manner": "comparison",
}

DIRECTION_MAP = {
    "backward": "backward",
    "forward": "forward",
    "parallel": "parallel",
    "parallel_or_backward": "backward",
    "backward_or_forward": "backward",
}

SPANISH_RELATIONSHIP_LABELS = {
    "reason": "razón",
    "content": "contenido",
    "purpose": "propósito",
    "result": "resultado",
    "condition": "condición",
    "coordination": "coordinación",
    "contrast": "contraste",
    "inference": "inferencia",
    "comparison": "comparación",
}

SPANISH_DIRECTION_LABELS = {
    "backward": "hacia atrás",
    "forward": "hacia adelante",
    "parallel": "paralelo",
}

SPANISH_DIRECTION_EXPLANATIONS = {
    "backward": "el conector normalmente busca A antes de B",
    "forward": "el conector normalmente busca A después de B",
    "parallel": "el conector normalmente relaciona cláusulas al mismo nivel",
}

SPANISH_HIERARCHY_LABELS = {
    "same_level": "mismo nivel",
    "subordinate": "subordinada",
}

SPANISH_DESCRIPTIONS = {
    "reason": "B da razón gramatical para A.",
    "content": "B presenta contenido relacionado con A.",
    "purpose": "B expresa propósito o resultado relacionado con A.",
    "result": "B expresa resultado relacionado con A.",
    "condition": "B establece condición relacionada con A.",
    "coordination": "B se coordina gramaticalmente con A.",
    "contrast": "B contrasta gramaticalmente con A.",
    "inference": "B presenta inferencia gramatical desde A.",
    "comparison": "B expresa comparación gramatical con A.",
}

PRIORITY = {
    "condition": 100,
    "purpose": 95,
    "result": 95,
    "content": 90,
    "reason": 85,
    "inference": 80,
    "contrast": 75,
    "coordination": 60,
    "comparison": 40,
}


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_indices(value: str) -> List[int]:
    value = str(value or "").strip()

    if not value or value == "-":
        return []

    out = []

    for part in value.split(","):
        part = part.strip()

        if not part or part == "-":
            continue

        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))

    return out


def greek_indices(col: Dict) -> List[int]:
    out = []

    for item in col.get("greek_tokens", []):
        try:
            out.append(int(item))
        except Exception:
            pass

    return out


def greek_pos(col: Dict) -> int:
    idxs = greek_indices(col)
    return min(idxs) if idxs else 999999


def nbla_indices(col: Dict) -> List[int]:
    return parse_indices(col.get("nbla_idx", ""))


def nbla_pos(col: Dict) -> int:
    idxs = nbla_indices(col)
    return min(idxs) if idxs else 999999


def clean_text(text: str) -> str:
    replacements = [
        (" ,", ","),
        (" .", "."),
        (" ;", ";"),
        (" :", ":"),
        (" ?", "?"),
        (" !", "!"),
        (" )", ")"),
        ("( ", "("),
        ("  ", " "),
    ]

    changed = True

    while changed:
        old = text
        for a, b in replacements:
            text = text.replace(a, b)
        changed = old != text

    return text.strip()


# ============================================================
# MORPHGNT AUTHORITATIVE LOGIC LAYER
# ============================================================
# Engine logic reads MorphGNT only.
# JSON "rmac" is display/export only.
# ============================================================


def morphgnt_code(col_or_code) -> str:
    if isinstance(col_or_code, dict):
        return (col_or_code.get("morphgnt") or "").strip()

    return (col_or_code or "").strip()


def morphgnt_parts(col_or_code) -> List[str]:
    code = morphgnt_code(col_or_code)

    if not code:
        return []

    return code.split("-")


def is_verb(col_or_code) -> bool:
    return morphgnt_code(col_or_code).startswith("V-")


def morphgnt_tvm(col_or_code) -> str:
    parts = morphgnt_parts(col_or_code)

    if len(parts) < 2:
        return ""

    return parts[1].strip()


def morphgnt_person(col_or_code) -> str:
    tvm = morphgnt_tvm(col_or_code)

    if tvm and tvm[0] in {"1", "2", "3"}:
        return tvm[0]

    parts = morphgnt_parts(col_or_code)

    if len(parts) >= 3:
        field = parts[2]

        if field and field[0] in {"1", "2", "3"}:
            return field[0]

    return ""


def morphgnt_number(col_or_code) -> str:
    parts = morphgnt_parts(col_or_code)

    if len(parts) < 3:
        return ""

    field = parts[2]

    for char in field:
        if char in {"S", "P"}:
            return char

    return ""


def verb_mood_code(col_or_code) -> str:
    tvm = morphgnt_tvm(col_or_code)

    if not tvm:
        return ""

    if tvm[0] in {"1", "2", "3"}:
        tvm = tvm[1:]

    if not tvm:
        return ""

    for char in reversed(tvm):
        if char.isalpha():
            return char

    return ""


def is_finite(col_or_code) -> bool:
    if not is_verb(col_or_code):
        return False

    return bool(
        morphgnt_person(col_or_code)
        and morphgnt_number(col_or_code)
    )


def finite_kind_label(col_or_code) -> str:
    if not is_finite(col_or_code):
        return "no-finito"

    mood = verb_mood_code(col_or_code)

    return {
        "I": "indicativo",
        "S": "subjuntivo",
        "O": "optativo",
        "M": "imperativo",
        "D": "imperativo",
    }.get(mood, f"finito:{mood or 'sin-modo'}")


def is_imperative_finite(col_or_code) -> bool:
    return is_finite(col_or_code) and verb_mood_code(col_or_code) in {"M", "D"}


def has_infinitival_surface(nbla: str) -> bool:
    words = (
        (nbla or "")
        .lower()
        .replace(",", "")
        .replace(".", "")
        .replace(";", "")
        .replace(":", "")
        .split()
    )

    if not words:
        return False

    finite_auxiliaries_or_finite_heads = {
        "he", "has", "ha", "hemos", "han",
        "había", "habían",
        "hubiera", "hubieras", "hubiésemos", "hubieran",
        "fue", "fuera", "será", "serán",
        "soy", "eres", "es", "somos", "son",
        "estoy", "estás", "está", "estamos", "están",
        "llegue", "llegó", "llegado",
        "vuelto", "volvieras", "volver",
        "puedo", "puedes", "puede", "podemos", "pueden",
    }

    endings = (
        "ar", "er", "ir",
        "arte", "erte", "irte",
        "arlo", "erlo", "irlo",
        "arnos", "ernos", "irnos",
    )

    if len(words) == 1:
        word = words[0]
        return len(word) >= 3 and word.endswith(endings)

    first = words[0]

    return (
        first not in finite_auxiliaries_or_finite_heads
        and len(first) >= 3
        and first.endswith(endings)
    )


def validate_morph_logic_source(columns: List[Dict]) -> None:
    for col in columns:
        greek = (col.get("greek") or "").strip()
        morph = morphgnt_code(col)
        rmac = (col.get("rmac") or "").strip()

        if greek and rmac.startswith("V-") and not morph:
            raise ValueError(
                "Verb-like RMAC display exists without MorphGNT source: "
                f"{greek} | rmac={rmac}"
            )


def load_connector_rules() -> Dict:
    return load_json(CONNECTOR_RULES)["connectors"]


def connector_rule(col: Dict, rules: Dict) -> Optional[Dict]:
    lemma = col.get("lemma", "").strip()
    greek = col.get("greek", "").strip()

    if lemma in rules:
        return rules[lemma]

    if greek in rules:
        return rules[greek]

    return None


def normalized_relationship(rule: Dict) -> Optional[str]:
    category = rule.get("category", "")
    rel = CATEGORY_TO_RELATIONSHIP.get(category)

    if rel not in APPROVED_RELATIONSHIP_TYPES:
        return None

    return rel


def normalized_direction(rule: Dict) -> str:
    return DIRECTION_MAP.get(rule.get("direction", ""), "backward")


def connector_explicit(col: Dict) -> bool:
    nbla = col.get("nbla", "").strip()
    alignment = col.get("alignment", "").strip()

    if not nbla or nbla == "-":
        return False

    if alignment in {"missing", "implicit", "supplied"}:
        return False

    return True


def verb_explicit(col: Dict) -> bool:
    nbla = col.get("nbla", "").strip()
    alignment = col.get("alignment", "").strip()

    if not nbla or nbla == "-":
        return False

    if alignment in {"missing", "implicit", "supplied"}:
        return False

    return True


def visible_columns(columns: List[Dict]) -> List[Dict]:
    return [
        col for col in columns
        if col.get("alignment", "").strip() != "shared"
    ]


def ordered_visible_columns(columns: List[Dict]) -> List[Dict]:
    return sorted(
        visible_columns(columns),
        key=lambda c: (nbla_pos(c), int(c.get("column", 0))),
    )


class Clause:
    def __init__(
        self,
        verse_ref: str,
        local_id: str,
        verb_col: Dict,
        columns: List[Dict],
        start_nbla: Optional[int],
        end_nbla: Optional[int],
    ):
        self.verse_ref = verse_ref
        self.local_id = local_id
        self.verb_col = verb_col
        self.columns = columns

        self.greek = verb_col.get("greek", "")
        self.nbla = verb_col.get("nbla", "")
        self.lemma = verb_col.get("lemma", "")
        self.rmac_display = verb_col.get("rmac", "")

        self.greek_pos = greek_pos(verb_col)
        self.nbla_pos = nbla_pos(verb_col)

        self.start_nbla = start_nbla
        self.end_nbla = end_nbla

        self.owned_tokens: List[Tuple[int, str]] = []

    def kind(self) -> str:
        return finite_kind_label(self.verb_col)

    def is_imperative(self) -> bool:
        return is_imperative_finite(self.verb_col)

    def force_note(self) -> str:
        notes = []

        if self.is_imperative():
            notes.append("griego: imperativo")

        if (
            is_finite(self.verb_col)
            and has_infinitival_surface(self.nbla)
        ):
            notes.append("NBLA: reestructuración infinitival")

        if not notes:
            return ""

        return " [" + "; ".join(notes) + "]"

    def short(self) -> str:
        nbla = self.nbla.strip() or "∅"
        morph = morphgnt_code(self.verb_col)

        extra = []

        note = self.force_note()

        if note:
            extra.append(note)

        if morph:
            extra.append(f"[MorphGNT: {morph}]")

        if self.rmac_display:
            extra.append(f"[RMAC display: {self.rmac_display}]")

        suffix = " " + " ".join(extra) if extra else ""

        return (
            f"{self.local_id}. "
            f"{self.greek} "
            f"({self.kind()}) → "
            f"{nbla}"
            f"{suffix}"
        )

    def assign_token(self, idx: int, word: str) -> None:
        self.owned_tokens.append((idx, word))

    def surface(self) -> str:
        if not self.owned_tokens:
            return self.rendered_body()

        words: List[str] = []
        verb_nbla_idxs = sorted(set(nbla_indices(self.verb_col)))

        verb_chunks: List[List[int]] = []
        current_chunk: List[int] = []

        for idx in verb_nbla_idxs:
            if not current_chunk:
                current_chunk.append(idx)
                continue

            previous = current_chunk[-1]

            if idx == previous + 1:
                current_chunk.append(idx)
            else:
                verb_chunks.append(current_chunk)
                current_chunk = [idx]

        if current_chunk:
            verb_chunks.append(current_chunk)

        chunk_map: Dict[int, Tuple[int, ...]] = {}

        for chunk in verb_chunks:
            chunk_tuple = tuple(chunk)
            for idx in chunk:
                chunk_map[idx] = chunk_tuple

        rendered_chunks: Set[Tuple[int, ...]] = set()
        token_map = {idx: word for idx, word in self.owned_tokens}

        for idx, word in sorted(self.owned_tokens):
            if idx not in chunk_map:
                words.append(word)
                continue

            chunk = chunk_map[idx]

            if chunk in rendered_chunks:
                continue

            rendered_chunks.add(chunk)

            chunk_words = [
                token_map[i]
                for i in chunk
                if i in token_map
            ]

            segment = clean_text(" ".join(chunk_words))

            if verb_explicit(self.verb_col):
                segment = f"=={segment}=="
            else:
                segment = f"==[{segment}]=="

            words.append(segment)

        return clean_text(" ".join(words))

    def rendered_body(self) -> str:
        nbla = self.nbla.strip()

        if not nbla or nbla == "-":
            fallback = self.lemma or self.greek
            return f"==[{fallback}]=="

        if verb_explicit(self.verb_col):
            return f"=={nbla}=="

        return f"==[{nbla}]=="

    def rendered_clause(self) -> str:
        prefix = self.local_id

        if self.is_imperative():
            prefix = f"{self.local_id} [IMP]"

        return f"{prefix}. {self.surface()}"


class Connector:
    def __init__(self, verse_ref: str, local_id: str, col: Dict, rule: Dict):
        self.verse_ref = verse_ref
        self.local_id = local_id
        self.col = col
        self.rule = rule

        self.greek = col.get("greek", "")
        self.lemma = col.get("lemma", "")
        self.nbla = col.get("nbla", "")
        self.greek_pos = greek_pos(col)
        self.nbla_pos = nbla_pos(col)
        self.explicit = connector_explicit(col)

        self.relationship_type = normalized_relationship(rule)
        self.direction = normalized_direction(rule)
        self.priority = PRIORITY.get(self.relationship_type or "", 0)
        self.scope = "unresolved"

    def marker(self) -> str:
        nbla = self.nbla.strip().strip("()[] ")

        if not nbla or nbla == "-":
            nbla = self.rule.get("default_nbla", "∅")

        if self.explicit:
            return f"({self.local_id}: {nbla} — {self.greek})"

        return f"[{self.local_id}: {nbla} — {self.greek}]"

    def hierarchy_effect(self) -> str:
        if self.lemma == "γάρ":
            return "same_level"

        if self.rule.get("indent_b", False):
            return "subordinate"

        return "same_level"

    def short(self) -> str:
        rel = SPANISH_RELATIONSHIP_LABELS.get(
            self.relationship_type,
            self.relationship_type,
        )

        direction = SPANISH_DIRECTION_LABELS.get(
            self.direction,
            self.direction,
        )

        return (
            f"{self.local_id}. "
            f"{self.greek} | "
            f"relación: {rel} | "
            f"dirección: {direction} | "
            f"alcance: {self.scope}"
        )


class RelationshipFact:
    def __init__(
        self,
        local_id: str,
        connector: Connector,
        B: Optional[Clause],
        a_candidates: List[Clause],
        note: str,
    ):
        self.local_id = local_id
        self.connector = connector
        self.B = B
        self.a_candidates = a_candidates
        self.note = note

    def render(self) -> List[str]:
        lines = []

        rel = SPANISH_RELATIONSHIP_LABELS.get(
            self.connector.relationship_type,
            self.connector.relationship_type,
        )
        direction = SPANISH_DIRECTION_LABELS.get(
            self.connector.direction,
            self.connector.direction,
        )
        direction_explanation = SPANISH_DIRECTION_EXPLANATIONS.get(
            self.connector.direction,
            "",
        )
        hierarchy = SPANISH_HIERARCHY_LABELS.get(
            self.connector.hierarchy_effect(),
            self.connector.hierarchy_effect(),
        )
        description = SPANISH_DESCRIPTIONS.get(
            self.connector.relationship_type,
            "",
        )

        lines.append(f"- {self.local_id} | {self.connector.marker()}")
        lines.append(f"  - relación gramatical: {rel}")
        lines.append(f"  - dirección: {direction}")

        if direction_explanation:
            lines.append(f"  - dirección significa: {direction_explanation}")

        lines.append(f"  - jerarquía: {hierarchy}")

        if description:
            lines.append(f"  - descripción: {description}")

        if self.B:
            lines.append(f"  - B confirmada: {self.B.short()}")
        else:
            lines.append("  - B confirmada: no detectada mecánicamente")

        if self.a_candidates:
            lines.append("  - posibles A:")
            for candidate in self.a_candidates:
                lines.append(f"    - {candidate.short()}")
        else:
            lines.append("  - posibles A: no detectadas mecánicamente")

        if self.note:
            lines.append(f"  - nota: {self.note}")

        return lines


def build_clause_boundaries(
    finite_cols: List[Dict],
    columns: List[Dict],
) -> List[Tuple[Optional[int], Optional[int]]]:
    all_nbla: List[int] = []

    for col in visible_columns(columns):
        all_nbla.extend(nbla_indices(col))

    if not all_nbla:
        return [(None, None) for _ in finite_cols]

    verse_start = min(all_nbla)
    verse_end = max(all_nbla)

    finite_positions: List[Optional[int]] = []

    for verb_col in finite_cols:
        verb_idxs = nbla_indices(verb_col)
        finite_positions.append(min(verb_idxs) if verb_idxs else None)

    boundaries: List[Tuple[Optional[int], Optional[int]]] = []
    previous_end: Optional[int] = None

    for i, current_start in enumerate(finite_positions):
        if current_start is None:
            boundaries.append((None, None))
            continue

        if i == 0:
            start = verse_start
        elif previous_end is not None:
            start = previous_end + 1
        else:
            start = current_start

        next_start: Optional[int] = None

        for candidate in finite_positions[i + 1:]:
            if candidate is not None:
                next_start = candidate
                break

        if next_start is not None:
            end = next_start - 1
        else:
            end = verse_end

        if end < start:
            start = current_start
            end = current_start

        boundaries.append((start, end))
        previous_end = end

    return boundaries


def build_clauses(
    verse_ref: str,
    columns: List[Dict],
) -> List[Clause]:

    validate_morph_logic_source(columns)

    finite_cols = [
        col for col in columns
        if is_finite(col)
    ]

    finite_cols.sort(key=greek_pos)

    boundaries = build_clause_boundaries(
        finite_cols,
        columns,
    )

    clauses = []

    for i, col in enumerate(finite_cols, start=1):
        start, end = boundaries[i - 1]

        clause = Clause(
            verse_ref=verse_ref,
            local_id=f"C{i}",
            verb_col=col,
            columns=columns,
            start_nbla=start,
            end_nbla=end,
        )

        clauses.append(clause)

    claimed = set()

    for clause in clauses:
        if clause.start_nbla is None:
            continue

        if clause.end_nbla is None:
            continue

        for col in ordered_visible_columns(columns):
            idxs = nbla_indices(col)
            text = col.get("nbla", "").strip()

            if not text or text == "-":
                continue

            words = text.split()

            for pos, idx in enumerate(idxs):
                if idx in claimed:
                    continue

                if not (clause.start_nbla <= idx <= clause.end_nbla):
                    continue

                word = words[pos] if pos < len(words) else words[-1]

                clause.assign_token(idx, word)
                claimed.add(idx)

    return clauses


def build_connectors(
    verse_ref: str,
    columns: List[Dict],
    rules: Dict,
) -> List[Connector]:
    raw = []

    for col in columns:
        rule = connector_rule(col, rules)

        if not rule:
            continue

        rel = normalized_relationship(rule)

        if not rel:
            continue

        raw.append((col, rule))

    raw.sort(key=lambda item: greek_pos(item[0]))

    return [
        Connector(verse_ref, f"cn{i}", col, rule)
        for i, (col, rule) in enumerate(raw, start=1)
    ]


def previous_clause_before(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    prior = [c for c in clauses if c.greek_pos < pos]
    return prior[-1] if prior else None


def following_clause_after(pos: int, clauses: List[Clause]) -> Optional[Clause]:
    following = [c for c in clauses if c.greek_pos > pos]
    return following[0] if following else None


def next_clause_after(clause: Clause, clauses: List[Clause]) -> Optional[Clause]:
    following = [c for c in clauses if c.greek_pos > clause.greek_pos]
    return following[0] if following else None


def stronger_connector_between(
    connector: Connector,
    B: Clause,
    connectors: List[Connector],
) -> bool:
    for other in connectors:
        if other is connector:
            continue

        if not (connector.greek_pos < other.greek_pos < B.greek_pos):
            continue

        if other.priority > connector.priority:
            return True

    return False


def candidate_B_for_connector(
    connector: Connector,
    clauses: List[Clause],
) -> Optional[Clause]:
    return following_clause_after(connector.greek_pos, clauses)


def classify_connector_scope(
    connector: Connector,
    clauses: List[Clause],
    connectors: List[Connector],
    previous_context_clause: Optional[Clause],
) -> str:
    B = candidate_B_for_connector(connector, clauses)
    rel = connector.relationship_type

    if not clauses:
        return "phrase-level"

    if rel == "comparison":
        return "phrase-level"

    if rel == "coordination":
        A = previous_clause_before(connector.greek_pos, clauses)

        if not A or not B:
            return "phrase-level"

        if stronger_connector_between(connector, B, connectors):
            return "blocked"

        return "clause-level"

    if len(clauses) == 1:
        if rel in {"contrast", "inference", "reason"}:
            return "discourse-level"

        return "intra-clausal"

    if not B:
        return "unresolved"

    if stronger_connector_between(connector, B, connectors):
        return "blocked"

    return "clause-level"


def a_candidates_for(
    connector: Connector,
    B: Clause,
    clauses: List[Clause],
    previous_context_clause: Optional[Clause],
) -> Tuple[List[Clause], str]:
    candidates = []
    rel = connector.relationship_type

    prev_same_verse = previous_clause_before(connector.greek_pos, clauses)
    next_after_B = next_clause_after(B, clauses)

    if rel == "condition":
        if next_after_B:
            candidates.append(next_after_B)
            return candidates, "La condición introduce B; A puede ser la cláusula finita siguiente."
        if previous_context_clause:
            candidates.append(previous_context_clause)
            return candidates, "La condición introduce B; A puede estar en el contexto previo."
        return candidates, "La condición introduce B; A no se detectó mecánicamente."

    if rel in {"purpose", "result", "content", "comparison"}:
        if prev_same_verse:
            candidates.append(prev_same_verse)
            return candidates, "B es la cláusula gobernada por el conector; A se busca antes del conector."
        if previous_context_clause:
            candidates.append(previous_context_clause)
            return candidates, "B es la cláusula gobernada por el conector; A puede estar en el contexto previo."
        return candidates, "B es la cláusula gobernada por el conector; A no se detectó mecánicamente."

    if rel in {"reason", "contrast", "inference"}:
        if prev_same_verse:
            candidates.append(prev_same_verse)
            return candidates, "El conector apunta hacia atrás; A puede ser la cláusula previa."
        if previous_context_clause:
            candidates.append(previous_context_clause)
            return candidates, "El conector apunta hacia atrás; A puede estar en el contexto previo."
        return candidates, "El conector apunta hacia atrás; A no se detectó mecánicamente."

    if rel == "coordination":
        if prev_same_verse:
            candidates.append(prev_same_verse)
            return candidates, "El conector coordina B con una cláusula finita previa."
        return candidates, "La coordinación no tiene cláusula finita previa detectada."

    return candidates, "No se detectó A mecánicamente."


def build_relationship_facts(
    connectors: List[Connector],
    clauses: List[Clause],
    previous_context_clause: Optional[Clause],
) -> List[RelationshipFact]:
    facts: List[RelationshipFact] = []
    eligible_connectors = []

    for connector in connectors:
        connector.scope = classify_connector_scope(
            connector,
            clauses,
            connectors,
            previous_context_clause,
        )

        if connector.scope == "clause-level":
            eligible_connectors.append(connector)

    for i, connector in enumerate(eligible_connectors, start=1):
        B = candidate_B_for_connector(connector, clauses)

        candidates: List[Clause] = []
        note = ""

        if B:
            candidates, note = a_candidates_for(
                connector,
                B,
                clauses,
                previous_context_clause,
            )

        facts.append(
            RelationshipFact(
                local_id=f"R{i}",
                connector=connector,
                B=B,
                a_candidates=candidates,
                note=note,
            )
        )

    incoming = {
        fact.B.local_id
        for fact in facts
        if fact.B is not None
    }

    REPORTING_LEMMAS = {
        "λέγω",
    }

    relationship_counter = len(facts)

    for i in range(len(clauses) - 1):
        A = clauses[i]
        B = clauses[i + 1]

        if B.local_id in incoming:
            continue

        lemma = (A.lemma or "").strip()

        if lemma not in REPORTING_LEMMAS:
            continue

        synthetic_col = {
            "greek": "∅",
            "lemma": "∅",
            "nbla": "(implícito)",
            "alignment": "supplied",
            "greek_tokens": [],
            "nbla_idx": "-",
            "column": 0,
        }

        synthetic_rule = {
            "category": "content_or_reason",
            "direction": "backward",
            "indent_b": True,
            "default_nbla": "(implícito)",
        }

        synthetic_connector = Connector(
            verse_ref=A.verse_ref,
            local_id=f"cn_imp_{i + 1}",
            col=synthetic_col,
            rule=synthetic_rule,
        )

        synthetic_connector.relationship_type = "content"
        synthetic_connector.direction = "backward"
        synthetic_connector.scope = "clause-level"
        synthetic_connector.priority = PRIORITY.get("content", 90)

        relationship_counter += 1

        facts.append(
            RelationshipFact(
                local_id=f"R{relationship_counter}",
                connector=synthetic_connector,
                B=B,
                a_candidates=[A],
                note="Relación de contenido implícita detectada mecánicamente por verbo finito de reporte/escritura seguido por otra cláusula finita sin relación entrante.",
            )
        )

        incoming.add(B.local_id)

    return facts


def render_relationship_graph(facts: List[RelationshipFact]) -> List[str]:
    lines = []

    if not facts:
        lines.append("- ninguna relación finita detectada")
        return lines

    for fact in facts:
        lines.extend(fact.render())
        lines.append("")

    return lines


def render_visible_structure(
    clauses: List[Clause],
    facts: List[RelationshipFact],
) -> List[str]:
    embedded_under: Dict[str, str] = {}

    relationship_notes_by_clause = {
        clause.local_id: []
        for clause in clauses
    }

    for fact in facts:
        if not fact.B:
            continue

        note_lines = [
            f"{fact.local_id} {fact.connector.marker()}",
            f"    B confirmada → {fact.B.local_id}",
        ]

        if fact.a_candidates:
            candidates = ", ".join(c.local_id for c in fact.a_candidates)
            note_lines.append(f"    posibles A → {candidates}")

        relationship_notes_by_clause[fact.B.local_id].extend(note_lines)

        if (
            fact.connector.hierarchy_effect() == "subordinate"
            and fact.a_candidates
        ):
            embedded_under[fact.B.local_id] = fact.a_candidates[0].local_id

    def clause_depth(clause_id: str) -> int:
        depth = 0
        seen = set()
        parent = embedded_under.get(clause_id)

        while parent and parent not in seen:
            seen.add(parent)
            depth += 1
            parent = embedded_under.get(parent)

        return depth

    lines = []

    for clause in clauses:
        depth = clause_depth(clause.local_id)
        indent = "    " * depth

        notes = relationship_notes_by_clause.get(clause.local_id, [])

        for note in notes:
            lines.append(f"{indent}{note}")

        lines.append(f"{indent}{clause.rendered_clause()}")

    return lines


def render_verse(
    verse_ref: str,
    clauses: List[Clause],
    connectors: List[Connector],
    facts: List[RelationshipFact],
) -> str:
    lines = []

    lines.append(f"### {verse_ref}")
    lines.append("")

    lines.append("#### Cláusulas finitas griegas")
    lines.append("")

    if clauses:
        for clause in clauses:
            lines.append(f"- {clause.short()}")
    else:
        lines.append("- ninguna")

    lines.append("")

    lines.append("#### Conectores detectados")
    lines.append("")

    if connectors:
        for connector in connectors:
            lines.append(f"- {connector.short()}")
    else:
        lines.append("- ninguno")

    lines.append("")

    lines.append("#### Relaciones gramaticales observadas")
    lines.append("")
    lines.extend(render_relationship_graph(facts))
    lines.append("")

    lines.append("#### Estructura visible")
    lines.append("")
    lines.append("```text")

    if clauses:
        lines.extend(render_visible_structure(clauses, facts))

    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    rules = load_connector_rules()

    files = sorted(
        JSON_DIR.glob("*.json"),
        key=lambda p: int(p.stem),
    )

    previous_context_clause = None
    output_sections = []

    for path in files:
        data = load_json(path)
        verse_ref = data["reference"]
        columns = data["columns"]

        clauses = build_clauses(verse_ref, columns)
        connectors = build_connectors(verse_ref, columns, rules)

        facts = build_relationship_facts(
            connectors,
            clauses,
            previous_context_clause,
        )

        output_sections.append(
            render_verse(
                verse_ref,
                clauses,
                connectors,
                facts,
            )
        )

        if clauses:
            previous_context_clause = clauses[-1]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        "\n---\n\n".join(output_sections),
        encoding="utf-8",
    )

    print("PASS ROOTS Engine v2 written:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()