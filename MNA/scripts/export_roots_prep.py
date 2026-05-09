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


def mark_nbla_tokens(
    spanish_tokens: list[tuple[str, str]],
    verb_marks: dict[str, str],
    connector_marks: dict[str, str],
    hidden_indexes: set[str],
) -> str:
    marked = []

    for idx, token in spanish_tokens:
        if idx in hidden_indexes:
            continue
        if idx in connector_marks:
            marked.append(connector_marks[idx])
        elif idx in verb_marks:
            marked.append(verb_marks[idx])
        else:
            marked.append(token)

    return " ".join(marked)


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


def closest_connector_for_clause(
    clause_start: int,
    finite_idx: int,
    connector_records: list[dict[str, str]],
) -> dict[str, str] | None:
    candidates = [
        c for c in connector_records
        if clause_start <= int(c["g_idx"]) <= finite_idx
    ]

    if not candidates:
        return None

    return sorted(candidates, key=lambda c: int(c["g_idx"]))[-1]


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


def build_clause_candidates(
    greek_tokens: list[tuple[str, str]],
    spanish_tokens: list[tuple[str, str]],
    align_by_gidx: dict[str, dict[str, str]],
    morph_lookup: dict[tuple[str, str], dict[str, str]],
    ref: str,
    marked_by_sidx: dict[str, str],
    connector_records: list[dict[str, str]],
) -> list[dict[str, str]]:
    finite_positions = finite_positions_for_ref(greek_tokens, morph_lookup, ref)

    if not finite_positions:
        return []

    clauses = []
    used_sidx: set[str] = set()

    for i, finite_idx in enumerate(finite_positions):
        finite_int = int(finite_idx)

        if i == 0:
            base_start = int(greek_tokens[0][0])
        else:
            base_start = int(finite_positions[i - 1]) + 1

        connector = closest_connector_for_clause(base_start, finite_int, connector_records)

        if connector:
            g_start = int(connector["g_idx"])
        else:
            g_start = base_start

        if i + 1 < len(finite_positions):
            g_end = int(finite_positions[i + 1]) - 1
        else:
            g_end = int(greek_tokens[-1][0])

        greek_parts = []
        nbla_indexes_set = set()

        for idx, greek in greek_tokens:
            idx_int = int(idx)

            if g_start <= idx_int <= g_end:
                greek_parts.append(greek)

                row = align_by_gidx.get(idx)
                for s_idx in nbla_indexes(row):
                    if s_idx not in used_sidx and s_idx in marked_by_sidx:
                        nbla_indexes_set.add(s_idx)

        ordered_nbla = []
        ordered_marked = []

        for s_idx, token in spanish_tokens:
            if s_idx in nbla_indexes_set:
                ordered_nbla.append(token)
                ordered_marked.append(marked_by_sidx.get(s_idx, token))
                used_sidx.add(s_idx)

        clauses.append({
            "id": f"C{i + 1}",
            "finite_idx": finite_idx,
            "g_start": f"{g_start:02d}",
            "g_end": f"{g_end:02d}",
            "connector_gidx": connector["g_idx"] if connector else "",
            "greek": " ".join(greek_parts),
            "nbla": " ".join(ordered_nbla),
            "nbla_marked": " ".join(ordered_marked),
        })

    return clauses


def clause_text(clause_id: str, clauses: list[dict[str, str]]) -> str:
    for c in clauses:
        if c["id"] == clause_id:
            return c.get("nbla_marked", c["nbla"])
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
    connector_records: list[dict[str, str]],
    previous_last_clause: str | None,
) -> list[dict[str, str]]:
    relationships = []

    connector_by_idx = {
        c["g_idx"]: c
        for c in connector_records
    }

    for clause in clauses:
        cid = clause["id"]
        connector_gidx = clause.get("connector_gidx")

        if not connector_gidx:
            continue

        connector = connector_by_idx.get(connector_gidx)
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

    for c in clauses:
        cid = c["id"]

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

        verbs: list[str] = []
        connectors: list[str] = []
        connector_evidence: list[str] = []

        verb_marks: dict[str, str] = {}
        connector_marks: dict[str, str] = {}
        hidden_indexes: set[str] = set()

        connector_records = build_connector_records(greek_tokens, align_by_gidx)

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

        for connector in connector_records:
            align = connector["align"]
            indexes = nbla_indexes(align)

            if indexes:
                connector_marks[indexes[0]] = connector["marker"]
                hidden_indexes.update(indexes[1:])

            connectors.append(
                f"- {connector['greek']} → {connector['marker']} — {connector['tipo']}"
            )

            connector_evidence.append(
                "\n".join([
                    f"- Griego: {connector['greek']}",
                    f"  Normalizado: {connector['key']}",
                    f"  Marcador: {connector['marker']}",
                    f"  Presente en NBLA: {'sí' if connector['presente'] else 'no; equivalencia añadida'}",
                    f"  Tipo: {connector['tipo']}",
                    f"  Estado: detectado mecánicamente",
                ])
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
            connector_records,
        )

        relationships = build_relationships(
            clauses,
            connector_records,
            previous_last_clause,
        )

        marked_nbla = mark_nbla_tokens(
            spanish_tokens,
            verb_marks,
            connector_marks,
            hidden_indexes,
        )

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
        lines.extend(structure_lines)
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