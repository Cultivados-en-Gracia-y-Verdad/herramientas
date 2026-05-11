#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


JSON_DIR = Path("data/interlinear/filemon/1")
CONNECTOR_RULES_PATH = Path("data/rules/connectors.json")

OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "filemon-roots.md"


SPAN_WINDOW = 12


def fail(message: str) -> None:
    print("FAIL\n")
    print(f"- {message}")
    sys.exit(1)


def verse_number(path: Path) -> int:
    return int(path.stem)


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_connector_rules(path: Path) -> Dict:
    if not path.exists():
        fail(f"connector rules file not found: {path}")

    data = load_json(path)

    if "connectors" not in data:
        fail("connector rules file missing 'connectors'")

    return data["connectors"]


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


def parse_index_part(part: str) -> List[int]:
    part = part.strip()

    if not part or part == "-":
        return []

    if "-" in part:
        a, b = part.split("-", 1)
        return list(range(int(a), int(b) + 1))

    return [int(part)]


def parse_indices(value: str) -> List[int]:
    value = str(value or "").strip()

    if not value or value == "-":
        return []

    output = []

    for part in value.split(","):
        output.extend(parse_index_part(part))

    return output


def nbla_indices(col: Dict) -> List[int]:
    return parse_indices(col.get("nbla_idx", ""))


def greek_indices(col: Dict) -> List[int]:
    values = []

    for item in col.get("greek_tokens", []):
        try:
            values.append(int(item))
        except Exception:
            pass

    return values


def ordered_columns(columns: List[Dict]) -> List[Dict]:

    def key(col: Dict):
        idxs = nbla_indices(col)

        if idxs:
            return min(idxs)

        return 999999

    return sorted(columns, key=key)


def get_greek_text(columns: List[Dict]) -> str:
    sortable = []

    for col in columns:
        greek = col.get("greek", "").strip()

        if not greek or greek == "-":
            continue

        idxs = greek_indices(col)

        if not idxs:
            continue

        sortable.append((min(idxs), greek))

    sortable.sort(key=lambda x: x[0])

    return clean_text(" ".join(g for _, g in sortable))


def get_nbla_text(columns: List[Dict]) -> str:
    parts = []

    for col in ordered_columns(columns):
        text = col.get("nbla", "").strip()

        if text and text != "-":
            parts.append(text)

    return clean_text(" ".join(parts))


def is_verb(rmac: str) -> bool:
    return bool(rmac and rmac.startswith("V-"))


def is_finite(rmac: str) -> bool:

    if not is_verb(rmac):
        return False

    parts = rmac.split("-")

    if len(parts) < 3:
        return False

    return parts[-1] in {
        "1S", "2S", "3S",
        "1P", "2P", "3P",
    }


def find_verbs(columns: List[Dict]) -> List[Dict]:

    output = []

    for col in columns:

        rmac = col.get("rmac", "")

        if not is_verb(rmac):
            continue

        output.append({
            "column": int(col.get("column")),
            "finite": is_finite(rmac),
            "status": "[F]" if is_finite(rmac) else "[NF]",
            "greek": col.get("greek", ""),
            "nbla": col.get("nbla", ""),
            "lemma": col.get("lemma", ""),
            "rmac": rmac,
            "alignment": col.get("alignment", ""),
            "nbla_idx": col.get("nbla_idx", ""),
            "greek_tokens": col.get("greek_tokens", []),
        })

    return output


def finite_verbs(verbs: List[Dict]) -> List[Dict]:
    return [v for v in verbs if v["finite"]]


def connector_rule(col: Dict, rules: Dict) -> Optional[Dict]:

    lemma = col.get("lemma", "").strip()
    greek = col.get("greek", "").strip()

    if lemma in rules:
        return rules[lemma]

    if greek in rules:
        return rules[greek]

    return None


def connector_explicit(col: Dict) -> bool:

    nbla = col.get("nbla", "").strip()

    if not nbla or nbla == "-":
        return False

    alignment = col.get("alignment", "").strip()

    if alignment in {"missing", "implicit", "supplied"}:
        return False

    return True


def connector_marker(connector_id: str, connector: Dict) -> str:

    explicit = connector["explicit"]

    nbla = connector["nbla"].strip()
    greek = connector["greek"].strip()

    nbla = nbla.strip("()[] ")

    if not nbla:
        nbla = "∅"

    if explicit:
        return f"( {connector_id}: {nbla} — {greek} )"

    return f"[ {connector_id}: {nbla} — {greek} ]"


def find_connectors(columns: List[Dict], rules: Dict) -> List[Dict]:

    output = []

    for col in columns:

        rule = connector_rule(col, rules)

        if not rule:
            continue

        output.append({
            "id": "",
            "column": int(col.get("column")),
            "greek": col.get("greek", ""),
            "nbla": col.get("nbla", ""),
            "lemma": col.get("lemma", ""),
            "alignment": col.get("alignment", ""),
            "nbla_idx": col.get("nbla_idx", ""),
            "greek_tokens": col.get("greek_tokens", []),
            "rule": rule,
            "explicit": connector_explicit(col),
        })

    output = sorted(
        output,
        key=lambda c: (
            min(parse_indices(c["nbla_idx"]))
            if parse_indices(c["nbla_idx"])
            else 999999
        )
    )

    for i, c in enumerate(output, start=1):
        c["id"] = f"cn{i}"
        c["marker"] = connector_marker(c["id"], c)

    return output


def clause_span(
    columns: List[Dict],
    verb: Dict,
    next_verb: Optional[Dict],
) -> List[Dict]:

    start_idxs = parse_indices(verb["nbla_idx"])

    if start_idxs:
        start = min(start_idxs)
    else:
        start = 999999

    if next_verb:
        next_idxs = parse_indices(next_verb["nbla_idx"])

        if next_idxs:
            end = min(next_idxs) - 1
        else:
            end = start + SPAN_WINDOW
    else:
        end = start + SPAN_WINDOW

    collected = []

    for col in ordered_columns(columns):

        idxs = nbla_indices(col)

        if not idxs:
            continue

        if any(start <= i <= end for i in idxs):
            collected.append(col)

    return collected


def clause_surface(
    span: List[Dict],
    verb: Dict,
) -> Tuple[str, bool]:

    explicit = bool(
        verb["nbla"].strip()
        and verb["nbla"].strip() != "-"
    )

    parts = []
    used: Set[int] = set()

    verb_col = verb["column"]

    for col in span:

        idxs = nbla_indices(col)

        fresh = [
            i for i in idxs
            if i not in used
        ]

        if not fresh:
            continue

        for i in fresh:
            used.add(i)

        text = col.get("nbla", "").strip()

        if not text or text == "-":
            continue

        if int(col.get("column")) == verb_col:

            if explicit:
                text = f"=={text}=="
            else:
                text = f"==[{text}]=="

        parts.append(text)

    if not parts:

        fallback = verb["nbla"].strip()

        if not fallback or fallback == "-":
            fallback = verb["greek"]

        if explicit:
            return f"=={fallback}==", True

        return f"==[{fallback}]==", False

    return clean_text(" ".join(parts)), explicit


def build_clauses(
    columns: List[Dict],
    verbs: List[Dict],
) -> List[Dict]:

    clauses = []

    for i, verb in enumerate(verbs):

        next_verb = None

        if i + 1 < len(verbs):
            next_verb = verbs[i + 1]

        span = clause_span(
            columns,
            verb,
            next_verb,
        )

        surface, explicit = clause_surface(
            span,
            verb,
        )

        idxs = parse_indices(verb["nbla_idx"])

        if idxs:
            start = min(idxs)
        else:
            start = 999999

        clauses.append({
            "label": f"C{i + 1}",
            "verb": verb,
            "surface": surface,
            "explicit": explicit,
            "start": start,
        })

    return clauses


def connector_for_clause(
    clause: Dict,
    connectors: List[Dict],
) -> Optional[Dict]:

    candidates = []

    clause_start = clause["start"]

    for connector in connectors:

        idxs = parse_indices(
            connector["nbla_idx"]
        )

        if not idxs:
            continue

        idx = min(idxs)

        if idx <= clause_start:
            candidates.append(connector)

    if not candidates:
        return None

    return candidates[-1]


def connector_indents(connector: Dict) -> bool:

    rule = connector["rule"]

    if connector["lemma"] == "γάρ":
        return False

    return bool(rule.get("indent_b", False))


def build_context(
    data: Dict,
    rules: Dict,
) -> Dict:

    columns = data.get("columns", [])

    verbs = find_verbs(columns)

    fverbs = finite_verbs(verbs)

    connectors = find_connectors(columns, rules)

    clauses = build_clauses(
        columns,
        fverbs,
    )

    return {
        "reference": data.get("reference", ""),
        "columns": columns,
        "greek_text": get_greek_text(columns),
        "nbla_text": get_nbla_text(columns),
        "verbs": verbs,
        "connectors": connectors,
        "clauses": clauses,
    }


def render_texto(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Texto")
    lines.append("")
    lines.append("##### SBLGNT")
    lines.append("")
    lines.append(context["greek_text"])
    lines.append("")
    lines.append("##### NBLA")
    lines.append("")
    lines.append(context["nbla_text"])
    lines.append("")


def render_verbos(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Verbos")
    lines.append("")

    if not context["verbs"]:
        lines.append("- ninguno detectado")
        lines.append("")
        return

    for v in context["verbs"]:

        tokens = ",".join(v["greek_tokens"])

        nbla = v["nbla"].strip()

        if not nbla or nbla == "-":
            nbla = "∅"

        lines.append(
            f"- {v['status']} | "
            f"col {v['column']} | "
            f"G_IDX {tokens} | "
            f"{v['greek']} → {nbla} | "
            f"RMAC: {v['rmac']}"
        )

    lines.append("")


def render_clausulas(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Cláusulas")
    lines.append("")

    for clause in context["clauses"]:

        lines.append(
            f"- {clause['label']}. {clause['surface']}"
        )

    lines.append("")


def render_conectores(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Conectores")
    lines.append("")

    if not context["connectors"]:
        lines.append("- ninguno detectado")
        lines.append("")
        return

    for c in context["connectors"]:

        tokens = ",".join(c["greek_tokens"])

        rule = c["rule"]

        lines.append(
            f"- {c['id']} | "
            f"G_IDX {tokens} | "
            f"{c['marker']} | "
            f"función: {rule.get('roots_function', '')} | "
            f"tipo: {rule.get('type', '')} | "
            f"dirección: {rule.get('direction', '')} | "
            f"relación: {rule.get('relationship', '')}"
        )

    lines.append("")


def render_relaciones(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Relaciones")
    lines.append("")

    clauses = context["clauses"]

    for i, clause in enumerate(clauses):

        connector = connector_for_clause(
            clause,
            context["connectors"],
        )

        if not connector:
            continue

        lines.append(
            f"- {connector['id']} | "
            f"{connector['marker']}"
        )

        if i > 0:
            a_clause = clauses[i - 1]

            lines.append(
                f"  A → {a_clause['label']}. "
                f"{a_clause['surface']}"
            )

        lines.append(
            f"  B → {clause['label']}. "
            f"{clause['surface']}"
        )

        rule = connector["rule"]

        lines.append(
            f"  relación → "
            f"{rule.get('relationship', '')}"
        )

        lines.append(
            f"  dirección → "
            f"{rule.get('direction', '')}"
        )

    lines.append("")


def render_estructura(
    lines: List[str],
    context: Dict,
) -> None:

    lines.append("#### Estructura")
    lines.append("")
    lines.append("```text")

    for clause in context["clauses"]:

        connector = connector_for_clause(
            clause,
            context["connectors"],
        )

        indent = ""

        if connector and connector_indents(connector):
            indent = "    "

        if connector:
            line = (
                f"{indent}"
                f"{clause['label']}. "
                f"{connector['marker']} "
                f"{clause['surface']}"
            )
        else:
            line = (
                f"{indent}"
                f"{clause['label']}. "
                f"{clause['surface']}"
            )

        lines.append(line)

    lines.append("```")
    lines.append("")


def render_verse(
    context: Dict,
) -> str:

    lines = []

    lines.append(f"### {context['reference']}")
    lines.append("")

    render_texto(lines, context)
    render_verbos(lines, context)
    render_clausulas(lines, context)
    render_conectores(lines, context)
    render_relaciones(lines, context)
    render_estructura(lines, context)

    return "\n".join(lines)


def main() -> None:

    if not JSON_DIR.exists():
        fail(f"JSON directory not found: {JSON_DIR}")

    rules = load_connector_rules(
        CONNECTOR_RULES_PATH
    )

    json_files = sorted(
        JSON_DIR.glob("*.json"),
        key=verse_number,
    )

    if not json_files:
        fail(f"no JSON files found in {JSON_DIR}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    sections = []

    for path in json_files:

        data = load_json(path)

        context = build_context(
            data,
            rules,
        )

        sections.append(
            render_verse(context)
        )

    OUTPUT_FILE.write_text(
        "\n---\n\n".join(sections),
        encoding="utf-8",
    )

    print("PASS ROOTS dataset written:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()