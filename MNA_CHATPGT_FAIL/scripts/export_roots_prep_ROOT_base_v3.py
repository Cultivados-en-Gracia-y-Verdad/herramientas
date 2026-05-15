#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path


CONNECTOR_MAP = {
    "γαρ": ("γάρ", "porque"),
    "ινα": ("ἵνα", "para que"),
    "και": ("καὶ", "y"),
    "δε": ("δὲ", "pero/y"),
    "αλλα": ("ἀλλά", "sino/pero"),
    "οτι": ("ὅτι", "que/porque"),
    "ωστε": ("ὥστε", "de manera que"),
    "ει": ("εἰ", "si"),
    "ουν": ("οὖν", "pues/por tanto"),
    "διο": ("διό", "por lo cual"),
    "ως": ("ὡς", "como"),
    "μη": ("μὴ", "no"),
    "ου": ("οὐ", "no"),
    "ουκ": ("οὐκ", "no"),
}

COORDINATING = {"και", "δε", "αλλα"}


def normalize_greek(token: str) -> str:
    token = re.sub(r"[·.,;:!?¿¡⸀⸂⸃()\[\]«»“”\"'—]", "", token).lower()
    token = unicodedata.normalize("NFD", token)
    token = "".join(ch for ch in token if unicodedata.category(ch) != "Mn")
    return token.strip()


def read_tokens(path: Path) -> list[tuple[str, str]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            idx, text = line.split("\t", 1)
            rows.append((idx, text))
    return rows


def read_alignment(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_morph(path: Path) -> list[dict[str, str]]:
    rows = []
    counters: dict[str, int] = {}

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            ref_code = parts[0]
            pos = parts[1]
            morph = parts[2]
            greek = parts[3]
            lemma = parts[-1]

            chapter = str(int(ref_code[2:4]))
            verse = str(int(ref_code[4:6]))
            ref = f"{chapter}:{verse}"

            counters.setdefault(ref, 0)
            counters[ref] += 1
            idx = f"{counters[ref]:02d}"

            code = f"{pos}{morph}"
            rmac = to_rmac(code)

            rows.append({
                "ref": ref,
                "idx": idx,
                "greek": greek,
                "lemma": lemma,
                "pos": pos,
                "morph": morph,
                "code": code,
                "rmac": rmac,
            })

    return rows


def to_rmac(code: str) -> str:
    code = code.strip()

    if not code.startswith("V"):
        return code

    code = code.replace("--", "-").strip("-")
    parts = [p for p in code.split("-") if p]

    if len(parts) == 2 and parts[0] == "V":
        body = parts[1]
        if len(body) == 6:
            return f"V-{body[:3]}-{body[3:]}"
        if len(body) == 3:
            return f"V-{body}"
        return code

    if len(parts) == 3 and parts[0] == "V":
        middle = parts[1]
        last = parts[2]
        if len(middle) == 4 and middle[0].isdigit():
            return f"V-{middle[1:]}-{middle[0]}{last}"
        return f"V-{middle}-{last}"

    return code


def is_verb(code: str) -> bool:
    return code.startswith("V")


def is_finite(code: str) -> bool:
    if not code or not code.startswith("V"):
        return False

    rmac = to_rmac(code)
    parts = [p for p in rmac.split("-") if p]

    if len(parts) < 2:
        return False

    tvm = parts[1]
    return len(tvm) == 3 and tvm[2] in {"I", "S", "M", "O", "D"}


def sort_key(path: Path) -> tuple[int, int]:
    stem = path.stem
    parts = stem.split("-")
    return int(parts[-2]), int(parts[-1])


def alignment_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {r["G_IDX"]: r for r in rows}


def nbla_for_row(row: dict[str, str] | None) -> str:
    if not row:
        return "[sin alineación]"
    if row["NBLA_IDX"] == "-" or row["NBLA_TEXT"] == "-":
        return "[sin equivalente]"
    return row["NBLA_TEXT"]


def nbla_indexes(row: dict[str, str] | None) -> list[str]:
    if not row:
        return []
    raw = row.get("NBLA_IDX", "")
    if raw == "-":
        return []
    return [x.strip() for x in re.split(r"[,|-]", raw) if x.strip().isdigit()]


def connector_info(greek: str):
    key = normalize_greek(greek)
    if key not in CONNECTOR_MAP:
        return None

    gr, es = CONNECTOR_MAP[key]
    tipo = "coordinante" if key in COORDINATING else "subordinante"
    return key, gr, es, tipo


def connector_surface(row: dict[str, str] | None, default_es: str, gr: str) -> tuple[str, bool]:
    if row and row["NBLA_IDX"] != "-" and row["NBLA_TEXT"] != "-":
        return f"({row['NBLA_TEXT']} — {gr})", True
    return f"[{default_es} — {gr}]", False


def finite_positions_for_ref(greek_tokens, morph_lookup, ref) -> list[str]:
    positions = []
    for idx, _greek in greek_tokens:
        morph = morph_lookup.get((ref, idx))
        if morph and is_verb(morph["code"]) and is_finite(morph["code"]):
            positions.append(idx)
    return positions


def build_connector_records(greek_tokens, align_by_gidx):
    records = []
    for idx, greek in greek_tokens:
        info = connector_info(greek)
        if not info:
            continue

        key, gr, default_es, tipo = info
        align = align_by_gidx.get(idx)
        marker, presente = connector_surface(align, default_es, gr)

        records.append({
            "g_idx": idx,
            "greek": greek,
            "key": key,
            "gr": gr,
            "default_es": default_es,
            "tipo": tipo,
            "marker": marker,
            "presente": presente,
            "align": align,
        })
    return records


def structural_connector_for_clause(
    finite_idx: str,
    previous_finite_idx: str | None,
    connector_records: list[dict[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    start = int(previous_finite_idx) + 1 if previous_finite_idx else 1
    end = int(finite_idx)

    candidates = [
        c for c in connector_records
        if start <= int(c["g_idx"]) <= end
        and connector_is_before_or_at_verb(c, finite_idx, align_by_gidx)
    ]

    if not candidates:
        return None

    # After filtering by NBLA surface position, choose the closest remaining
    # Greek connector before this finite verb.
    return sorted(candidates, key=lambda c: int(c["g_idx"]))[-1]


def build_structural_connectors(
    finite_positions: list[str],
    connector_records: list[dict[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    structural = {}

    for i, finite_idx in enumerate(finite_positions):
        prev_finite = finite_positions[i - 1] if i > 0 else None
        connector = structural_connector_for_clause(
            finite_idx,
            prev_finite,
            connector_records,
            align_by_gidx,
        )

        if connector:
            structural[finite_idx] = connector

    return structural


def build_marks(
    greek_tokens,
    align_by_gidx,
    morph_lookup,
    ref,
    structural_connectors_by_finite,
) -> tuple[list[str], list[str], list[str], dict[str, str], dict[str, str], set[str], dict[str, str]]:
    verbs: list[str] = []
    connectors: list[str] = []
    connector_evidence: list[str] = []
    verb_marks: dict[str, str] = {}
    connector_marks: dict[str, str] = {}
    hidden_indexes: set[str] = set()
    structural_connector_mark_by_gidx: dict[str, str] = {}

    structural_gidxs = {
        c["g_idx"] for c in structural_connectors_by_finite.values()
    }

    for idx, greek in greek_tokens:
        morph = morph_lookup.get((ref, idx))
        align = align_by_gidx.get(idx)

        if morph and is_verb(morph["code"]):
            code = morph["code"]
            rmac = morph["rmac"]
            spanish = nbla_for_row(align)
            tag = "[F]" if is_finite(code) else "[NF]"

            if is_finite(code):
                display = f"=={spanish}==" if spanish != "[sin equivalente]" else f"[=={morph['lemma']}==]"
                indexes = nbla_indexes(align)
                if indexes:
                    verb_marks[indexes[0]] = display
                    hidden_indexes.update(indexes[1:])
            else:
                display = spanish if spanish != "[sin equivalente]" else f"[{morph['lemma']}]"

            verbs.append(f"- {greek} ({rmac}) {tag} → {display}")

    connector_records = build_connector_records(greek_tokens, align_by_gidx)

    for connector in connector_records:
        connectors.append(
            f"- {connector['greek']} → {connector['marker']} — {connector['tipo']}"
        )

        structural_status = "sí" if connector["g_idx"] in structural_gidxs else "no"

        connector_evidence.append(
            "\n".join([
                f"- Griego: {connector['greek']}",
                f"  Normalizado: {connector['key']}",
                f"  Marcador: {connector['marker']}",
                f"  Presente en NBLA: {'sí' if connector['presente'] else 'no; equivalencia añadida'}",
                f"  Tipo: {connector['tipo']}",
                f"  Estructural: {structural_status}",
                f"  Estado: detectado mecánicamente",
            ])
        )

        if connector["g_idx"] in structural_gidxs:
            indexes = nbla_indexes(connector["align"])
            if indexes:
                connector_marks[indexes[0]] = connector["marker"]
                hidden_indexes.update(indexes[1:])
            structural_connector_mark_by_gidx[connector["g_idx"]] = connector["marker"]

    return (
        verbs,
        connectors,
        connector_evidence,
        verb_marks,
        connector_marks,
        hidden_indexes,
        structural_connector_mark_by_gidx,
    )


def build_marked_token_map(
    spanish_tokens: list[tuple[str, str]],
    verb_marks: dict[str, str],
    connector_marks: dict[str, str],
    hidden_indexes: set[str],
) -> dict[str, str]:
    marked = {}
    for idx, token in spanish_tokens:
        if idx in hidden_indexes:
            continue
        if idx in connector_marks:
            marked[idx] = connector_marks[idx]
        elif idx in verb_marks:
            marked[idx] = verb_marks[idx]
        else:
            marked[idx] = token
    return marked


def mark_nbla_tokens(
    spanish_tokens: list[tuple[str, str]],
    marked_by_sidx: dict[str, str],
) -> str:
    return " ".join(
        marked_by_sidx[idx]
        for idx, _token in spanish_tokens
        if idx in marked_by_sidx
    )



def first_int(values: list[str]) -> int | None:
    nums = [int(v) for v in values if str(v).isdigit()]
    return min(nums) if nums else None


def last_int(values: list[str]) -> int | None:
    nums = [int(v) for v in values if str(v).isdigit()]
    return max(nums) if nums else None


def connector_span(connector: dict[str, str] | None) -> tuple[int, int] | None:
    if not connector:
        return None

    indexes = nbla_indexes(connector.get("align"))

    if not indexes:
        return None

    return min(int(x) for x in indexes), max(int(x) for x in indexes)


def is_never_structural_connector(connector: dict[str, str]) -> bool:
    """
    These are real Greek particles/connectors, but they do not own a ROOTS
    clause boundary by themselves.
    """

    return connector.get("key") in {"μη", "ου", "ουκ"}


def connector_is_before_or_at_verb(
    connector: dict[str, str],
    finite_idx: str,
    align_by_gidx: dict[str, dict[str, str]],
) -> bool:
    """
    A structural connector may introduce a finite clause only when its NBLA
    surface position is before the Spanish finite verb anchor.

    This prevents cases like:
        tu bondad no ==fuera== (como — ὡς) por obligación

    from treating "como" as the clause-level connector for "fuera".
    """

    if is_never_structural_connector(connector):
        return False

    connector_indexes = nbla_indexes(connector.get("align"))
    verb_indexes = nbla_indexes(align_by_gidx.get(finite_idx))

    if not connector_indexes or not verb_indexes:
        return False

    connector_start = min(int(x) for x in connector_indexes)
    verb_start = min(int(x) for x in verb_indexes)

    return connector_start <= verb_start


def greek_range_rows(
    greek_tokens: list[tuple[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
    start_gidx: int,
    end_gidx: int,
) -> list[tuple[str, dict[str, str]]]:
    rows = []

    for g_idx, _greek in greek_tokens:
        g_int = int(g_idx)

        if start_gidx <= g_int <= end_gidx:
            row = align_by_gidx.get(g_idx)

            if row:
                rows.append((g_idx, row))

    return rows


def normalize_spanish_token_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[.,;:!?¿¡()\[\]«»“”\"'—]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_clause_intro_candidate(greek: str, row: dict[str, str]) -> bool:
    """
    A token may pull a later finite clause start backward only if it is
    clause-introducing material in the NBLA surface.

    This prevents ordinary object/pronoun material such as "lo" from becoming
    a new clause boundary before a later verb such as "es".
    """

    greek_key = normalize_greek(greek)
    spanish = normalize_spanish_token_text(row.get("NBLA_TEXT", ""))

    if connector_info(greek):
        return True

    greek_relative_or_subordinator = {
        "ος",
        "ον",
        "η",
        "ην",
        "ο",
        "ω",
        "οι",
        "ους",
        "αι",
        "ας",
        "οτι",
        "οπως",
        "ει",
    }

    spanish_intro_starts = (
        "que",
        "a quien",
        "quien",
        "el cual",
        "la cual",
        "los cuales",
        "las cuales",
        "lo que",
        "de lo que",
        "si",
        "para que",
        "porque",
        "pues",
        "aunque",
        "cuando",
        "como",
        "por lo cual",
        "de manera que",
    )

    if greek_key in greek_relative_or_subordinator:
        return any(
            spanish == intro or spanish.startswith(f"{intro} ")
            for intro in spanish_intro_starts
        )

    return any(
        spanish == intro or spanish.startswith(f"{intro} ")
        for intro in spanish_intro_starts
    )


def detect_clause_intro_start(
    greek_tokens: list[tuple[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
    finite_idx: str,
    finite_span: tuple[int, int],
    previous_finite_idx: str | None,
    structural_connector: dict[str, str] | None,
) -> int:
    """
    Detect the Spanish surface start for the clause.

    Greek/TSV may identify possible clause-introducing material, but only
    Spanish surface anchors that actually introduce a clause may pull the
    clause start backward from the finite verb.

    Ordinary pre-verbal material such as objects/pronouns remains with the
    previous clause.
    """

    verb_start, _verb_end = finite_span

    structural_span = connector_span(structural_connector)

    if structural_span and structural_span[0] <= verb_start:
        return structural_span[0]

    g_start = int(previous_finite_idx) + 1 if previous_finite_idx else 1
    g_end = int(finite_idx) - 1

    candidates: list[int] = []

    for g_idx, row in greek_range_rows(greek_tokens, align_by_gidx, g_start, g_end):
        s_indexes = [int(x) for x in nbla_indexes(row)]

        if not s_indexes:
            continue

        s_start = min(s_indexes)
        s_end = max(s_indexes)

        # Only material before the Spanish finite verb can introduce this clause.
        if s_start >= verb_start:
            continue

        # Do not let ordinary material become a clause boundary.
        # Examples that must NOT pull a clause start backward:
        #   "lo" before "es"
        #   "te" before "ha perjudicado"
        #   object phrases before a later finite verb
        if not is_clause_intro_candidate(greek_tokens[int(g_idx) - 1][1], row):
            continue

        # Keep nearby clause introducers such as "a quien", "que", "si",
        # "para que", without dragging distant material backward.
        if verb_start - s_end <= 4:
            candidates.append(s_start)

    if candidates:
        return min(candidates)

    return verb_start


def build_root_base(
    greek_tokens: list[tuple[str, str]],
    spanish_tokens: list[tuple[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
    morph_lookup: dict[tuple[str, str], dict[str, str]],
    ref: str,
    structural_connectors_by_finite: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    """
    ROOT base is the pivot layer.

    Before this function:
    - Greek + MorphGNT + TSV identify finite verbs and structural connectors.

    After this function:
    - NBLA surface order becomes the authority for clause ownership.
    """

    finite_positions = finite_positions_for_ref(
        greek_tokens,
        morph_lookup,
        ref,
    )

    anchors: list[dict[str, object]] = []

    for i, finite_idx in enumerate(finite_positions):
        row = align_by_gidx.get(finite_idx)
        s_indexes = nbla_indexes(row)

        if not s_indexes:
            continue

        verb_start = min(int(x) for x in s_indexes)
        verb_end = max(int(x) for x in s_indexes)

        previous_finite_idx = finite_positions[i - 1] if i > 0 else None
        structural_connector = structural_connectors_by_finite.get(finite_idx)

        clause_start = detect_clause_intro_start(
            greek_tokens=greek_tokens,
            align_by_gidx=align_by_gidx,
            finite_idx=finite_idx,
            finite_span=(verb_start, verb_end),
            previous_finite_idx=previous_finite_idx,
            structural_connector=structural_connector,
        )

        anchors.append({
            "finite_idx": finite_idx,
            "verb_start": verb_start,
            "verb_end": verb_end,
            "clause_start": clause_start,
            "connector": structural_connector,
            "greek_order": i,
        })

    # This is the key correction:
    # once anchors exist in Spanish, clause ownership follows NBLA order, not Greek order.
    anchors.sort(key=lambda a: (int(a["clause_start"]), int(a["verb_start"])))

    for i, anchor in enumerate(anchors):
        anchor["id"] = f"C{i + 1}"

    return anchors


def build_clause_candidates(
    greek_tokens: list[tuple[str, str]],
    spanish_tokens: list[tuple[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
    morph_lookup: dict[tuple[str, str], dict[str, str]],
    ref: str,
    marked_by_sidx: dict[str, str],
    structural_connectors_by_finite: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    """
    Build clauses from ROOT base anchors in NBLA surface order.

    This function intentionally does NOT slice Greek ranges to determine clause text.
    Greek has already done its job by producing finite verb and connector anchors.
    """

    root_base = build_root_base(
        greek_tokens=greek_tokens,
        spanish_tokens=spanish_tokens,
        align_by_gidx=align_by_gidx,
        morph_lookup=morph_lookup,
        ref=ref,
        structural_connectors_by_finite=structural_connectors_by_finite,
    )

    if not root_base:
        return []

    last_sidx = int(spanish_tokens[-1][0])
    clauses: list[dict[str, str]] = []

    for i, anchor in enumerate(root_base):
        cid = str(anchor["id"])
        start = int(anchor["clause_start"])

        if i + 1 < len(root_base):
            end = int(root_base[i + 1]["clause_start"]) - 1
        else:
            end = last_sidx

        if end < start:
            end = start

        owned_indexes = {
            f"{s_idx:02d}"
            for s_idx in range(start, end + 1)
        }

        ordered_marked: list[str] = []
        ordered_plain: list[str] = []

        for s_idx, token in spanish_tokens:
            if s_idx not in owned_indexes:
                continue

            if s_idx in marked_by_sidx:
                ordered_marked.append(marked_by_sidx[s_idx])
                ordered_plain.append(token)
            else:
                # Hidden indexes are second/third tokens of multi-token verb/connector marks.
                # They are owned, but not rendered twice.
                continue

        connector = anchor.get("connector")

        clauses.append({
            "id": cid,
            "finite_idx": str(anchor["finite_idx"]),
            "s_start": f"{start:02d}",
            "s_end": f"{end:02d}",
            "verb_start": f"{int(anchor['verb_start']):02d}",
            "verb_end": f"{int(anchor['verb_end']):02d}",
            "connector_gidx": str(connector["g_idx"]) if connector else "",
            "greek": f"ROOT base: finite verb {anchor['finite_idx']} projected to NBLA {int(anchor['verb_start']):02d}-{int(anchor['verb_end']):02d}",
            "nbla": " ".join(ordered_plain).strip(),
            "nbla_marked": " ".join(ordered_marked).strip(),
        })

    return clauses


def clause_text(clause_id: str, clauses: list[dict[str, str]]) -> str:
    for c in clauses:
        if c["id"] == clause_id:
            return c.get("nbla_marked") or c.get("nbla", "")
    return ""


def clause_by_id(clause_id: str, clauses: list[dict[str, str]]) -> dict[str, str] | None:
    for c in clauses:
        if c["id"] == clause_id:
            return c
    return None


def previous_clause_id(clause_id: str) -> str | None:
    if not clause_id.startswith("C"):
        return None
    n = int(clause_id[1:])
    if n <= 1:
        return None
    return f"C{n - 1}"


def build_relationships(
    clauses: list[dict[str, str]],
    structural_connectors_by_finite: dict[str, dict[str, str]],
    previous_last_clause: str | None,
) -> list[dict[str, str]]:
    relationships = []

    for clause in clauses:
        cid = clause["id"]
        finite_idx = clause["finite_idx"]
        connector = structural_connectors_by_finite.get(finite_idx)

        if not connector:
            continue

        if cid == "C1":
            a = previous_last_clause or "CONTEXTO_ANTERIOR"
        else:
            a = previous_clause_id(cid) or "CONTEXTO_ANTERIOR"

        relationships.append({
            "gr": connector["gr"],
            "marker": connector["marker"],
            "tipo": connector["tipo"],
            "a": a,
            "b": cid,
            "estado": "candidato mecánico",
        })

    return relationships


def build_structure_lines(
    clauses: list[dict[str, str]],
    relationships: list[dict[str, str]],
) -> list[str]:
    if not clauses:
        return ["- ninguno"]

    parent: dict[str, str] = {}

    for r in relationships:
        if r["tipo"] == "subordinante" and r["a"].startswith("C") and r["b"].startswith("C"):
            parent[r["b"]] = r["a"]

    lines: list[str] = []

    for clause in clauses:
        cid = clause["id"]

        if cid in parent:
            continue

        lines.extend(render_structure_node(cid, clauses, parent, level=0))
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return lines


def render_structure_node(
    cid: str,
    clauses: list[dict[str, str]],
    parent: dict[str, str],
    level: int,
) -> list[str]:
    clause = clause_by_id(cid, clauses)
    if not clause:
        return []

    indent = "    " * level
    lines = [f"{indent}{clause.get('nbla_marked', clause['nbla'])}"]

    children = [child for child, p in parent.items() if p == cid]
    children.sort(key=lambda x: int(x[1:]))

    for child in children:
        lines.extend(render_structure_node(child, clauses, parent, level + 1))

    return lines


def export_book(book: str) -> None:
    g_root = Path("data/g-tokens") / book
    s_root = Path("data/s-tokens") / book
    a_root = Path("data/alignments") / book
    morph_path = Path("data/MorphGNT") / f"{book}-morphgnt.txt"

    out_root = Path("data/exports")
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / f"{book}-roots-prep.md"

    if not morph_path.exists():
        raise FileNotFoundError(f"Missing MorphGNT file: {morph_path}")

    morph_rows = read_morph(morph_path)
    morph_lookup = {(row["ref"], row["idx"]): row for row in morph_rows}

    tsv_files = sorted(
        [p for p in a_root.glob(f"{book}-*.tsv") if not p.name.endswith(".original.tsv")],
        key=sort_key,
    )

    previous_ref = None
    previous_nbla = None
    previous_last_clause = None

    lines: list[str] = []

    lines.append(f"# {book.title()} — Preparación ROOTS")
    lines.append("")
    lines.append("> Fuente: TSVs validados de MNA + MorphGNT")
    lines.append(">")
    lines.append("> Nota: Las cláusulas y relaciones son una vista mecánica inicial basada en verbos finitos, conectores griegos y alineación validada.")
    lines.append("")

    for tsv in tsv_files:
        rows = read_alignment(tsv)
        if not rows:
            continue

        ch = rows[0]["CH"]
        vs = rows[0]["VS"]
        ref = f"{ch}:{vs}"

        g_path = g_root / f"{tsv.stem}.txt"
        s_path = s_root / f"{tsv.stem}.txt"

        greek_tokens = read_tokens(g_path)
        spanish_tokens = read_tokens(s_path)
        align_by_gidx = alignment_lookup(rows)

        greek_line = " ".join(token for _, token in greek_tokens)
        spanish_line = " ".join(token for _, token in spanish_tokens)

        finite_positions = finite_positions_for_ref(greek_tokens, morph_lookup, ref)
        connector_records = build_connector_records(greek_tokens, align_by_gidx)
        structural_connectors_by_finite = build_structural_connectors(finite_positions, connector_records, align_by_gidx)

        (
            verbs,
            connectors,
            connector_evidence,
            verb_marks,
            connector_marks,
            hidden_indexes,
            _structural_connector_mark_by_gidx,
        ) = build_marks(
            greek_tokens,
            align_by_gidx,
            morph_lookup,
            ref,
            structural_connectors_by_finite,
        )

        marked_by_sidx = build_marked_token_map(
            spanish_tokens,
            verb_marks,
            connector_marks,
            hidden_indexes,
        )

        clauses = build_clause_candidates(
            greek_tokens,
            spanish_tokens,
            align_by_gidx,
            morph_lookup,
            ref,
            marked_by_sidx,
            structural_connectors_by_finite,
        )

        relationships = build_relationships(
            clauses,
            structural_connectors_by_finite,
            previous_last_clause,
        )

        marked_nbla = mark_nbla_tokens(spanish_tokens, marked_by_sidx)
        structure_lines = build_structure_lines(clauses, relationships)

        if clauses:
            previous_last_clause = f"{book.title()} {ref} C{len(clauses)}"

        lines.append(f"## {book.title()} {ref}")
        lines.append("")

        if previous_ref and previous_nbla:
            lines.append("### Contexto del Versículo Anterior")
            lines.append("")
            lines.append(f"**{book.title()} {previous_ref}:** {previous_nbla}")
            lines.append("")

        lines.append("### Texto Griego")
        lines.append("")
        lines.append(greek_line)
        lines.append("")

        lines.append("### Texto NBLA")
        lines.append("")
        lines.append(spanish_line)
        lines.append("")

        lines.append("### NBLA Marcado")
        lines.append("")
        lines.append(marked_nbla)
        lines.append("")

        lines.append("### Verbos")
        lines.append("")
        lines.extend(verbs if verbs else ["- ninguno"])
        lines.append("")

        lines.append("### Conectores Detectados")
        lines.append("")
        lines.extend(connectors if connectors else ["- ninguno"])
        lines.append("")

        lines.append("### Evidencia de Conectores")
        lines.append("")
        lines.extend(connector_evidence if connector_evidence else ["- ninguno"])
        lines.append("")

        lines.append("### Cláusulas")
        lines.append("")
        if clauses:
            for c in clauses:
                lines.append(f"- {c['id']}")
                lines.append(f"  Griego: {c['greek']}")
                lines.append(f"  NBLA: {c['nbla_marked']}")
        else:
            lines.append("- ninguno")
        lines.append("")

        lines.append("### Relaciones A–B")
        lines.append("")
        if relationships:
            for r in relationships:
                a_text = clause_text(r["a"], clauses)
                b_text = clause_text(r["b"], clauses)

                if not a_text:
                    a_text = "contexto anterior"

                lines.append(f"- A: {r['a']} — {a_text}")
                lines.append(f"  Conector: {r['marker']}")
                lines.append(f"  B: {r['b']} — {b_text}")
                lines.append(f"  Relación: {r['a']} ({r['gr']}) {r['b']}")
                lines.append(f"  Tipo: {r['tipo']}")
                lines.append(f"  Estado: {r['estado']}")
        else:
            lines.append("- ninguno")
        lines.append("")

        lines.append("### Vista Estructural")
        lines.append("")
        lines.append("```text")
        lines.extend(structure_lines)
        lines.append("```")
        lines.append("")

        lines.append("---")
        lines.append("")

        previous_ref = ref
        previous_nbla = spanish_line

    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("DONE")
    print(f"Book: {book}")
    print(f"Verses exported: {len(tsv_files)}")
    print(f"Output: {out_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/export_roots_prep.py <book>")
        raise SystemExit(1)

    export_book(sys.argv[1])


if __name__ == "__main__":
    main()