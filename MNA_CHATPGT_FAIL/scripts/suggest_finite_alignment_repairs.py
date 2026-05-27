#!/usr/bin/env python3

"""
Suggest repairs for suspicious finite-verb NBLA alignments.

This script does NOT modify TSV files.

It scans interlinear JSON, alignment TSVs, and Spanish token files. It reports
one best candidate per suspicious/missing finite Greek verb by default.
Use --all-candidates to inspect the top five candidates per verb.
"""

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


SUSPICIOUS_FINITE_SURFACES = {
    "-", "a", "al", "de", "del", "el", "la", "las", "los", "lo", "en",
    "por", "para", "con", "sin", "que", "qué", "y", "o", "pero", "sino",
    "un", "una", "unos", "unas", "cada", "todo", "toda", "todos", "todas",
    "iglesias", "señor",
}

NON_VERB_WORDS = {
    "acaso", "ahora", "al", "alguna", "alimento", "amor", "antes", "ardientemente",
    "bajo", "bien", "bienes", "cada", "cara", "casa", "como", "con", "conocimiento",
    "corazón", "cosas", "cuando", "cual", "cuerpo", "cuyo", "de", "del", "demás",
    "derecho", "dios", "dones", "el", "ellos", "embargo", "en", "entre", "espirituales",
    "espíritu", "esta", "este", "esto", "evangelio", "fe", "fuego", "hermano",
    "hermanos", "hombres", "ídolos", "iglesia", "iglesias", "incompleto", "incrédulo",
    "incrédulos", "injusticia", "intérprete", "la", "las", "lenguas", "ley", "lo",
    "los", "marido", "me", "mismo", "mis", "montañas", "nada", "no", "nombre",
    "nosotros", "nube", "o", "ojo", "para", "parte", "perfecto", "pero", "pie",
    "pobres", "por", "porque", "profecía", "propia", "propio", "que", "qué", "señal",
    "señor", "si", "sino", "su", "tal", "también", "tanto", "toda", "todas",
    "todo", "todos", "tres", "tu", "una", "uno", "ustedes", "verdad", "vida",
    "vírgenes", "y",
}

AUXILIARIES = {
    "he", "has", "ha", "hemos", "han",
    "fui", "fue", "fuimos", "fueron",
    "soy", "eres", "es", "somos", "son",
    "era", "eran", "será", "serán",
    "estoy", "estás", "está", "estamos", "están",
    "estaba", "estaban", "esté", "estén",
}

STRONG_VERB_WORDS = {
    "abundar", "acabará", "adorará", "agradó", "ande", "anhelan", "aprendan",
    "arreglaré", "asignado", "bautizados", "beba", "cantaré", "colocado",
    "coma", "comieron", "cree", "creen", "creemos", "decidido", "deja", "desean",
    "deseen", "dice", "dicen", "dijera", "digo", "duermen", "edifica",
    "entendiera", "entregara", "escrito", "escrita", "escritas", "examine",
    "examínese", "fornicaron", "guarde", "hace", "habla", "hablan", "haya",
    "hice", "juzguen", "llamó", "murió", "oraré", "ordeno", "ordenó",
    "permanezca", "permanecen", "perderá", "procuren", "profetiza", "profetizar",
    "profetizamos", "prohíban", "puede", "pueden", "quedarán", "quedaron",
    "quemado", "regocija", "reúnan", "ruego", "saben", "sabemos", "sujeten",
    "sufrimos", "tendrán", "tengo", "tiene", "tienen", "tenemos", "toma",
    "tuviera", "venga", "vivan", "vuelto",
}

REPORT_HEADER = [
    "REF", "G_IDX", "GREEK", "LEMMA", "RMAC",
    "CURRENT_NBLA_IDX", "CURRENT_NBLA_TEXT", "CURRENT_ALIGNMENT",
    "REASON", "CANDIDATE_NBLA_IDX", "CANDIDATE_NBLA_TEXT",
    "SCORE", "CONFIDENCE", "NOTES", "TSV_PATH",
]


@dataclass
class Candidate:
    idx: str
    text: str
    score: int
    confidence: str
    notes: str


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def norm(text: str) -> str:
    return strip_accents(text).lower().strip(".,;:·⸀⸃[]()¿?¡! ")


def is_finite_rmac(rmac: str) -> bool:
    if not rmac or not rmac.startswith("V-"):
        return False
    parts = rmac.split("-")
    if len(parts) < 2 or len(parts[1]) < 3:
        return False
    return parts[1][-1] in {"I", "S", "M", "D"}


def is_suspicious_finite_surface(text: str) -> bool:
    surface = norm(text)
    return not surface or surface in SUSPICIOUS_FINITE_SURFACES


def parse_nbla_indexes(raw: str) -> List[int]:
    raw = str(raw or "").strip()
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
                values.extend(range(int(left), int(right) + 1))
            except ValueError:
                pass
        else:
            try:
                values.append(int(part))
            except ValueError:
                pass
    return values


def format_idx(indexes: Iterable[int]) -> str:
    values = sorted(set(indexes))
    if not values:
        return "-"
    if len(values) == 1:
        return f"{values[0]:02d}"
    if values == list(range(values[0], values[-1] + 1)):
        return f"{values[0]:02d}-{values[-1]:02d}"
    return ",".join(f"{v:02d}" for v in values)


def read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_s_tokens(path: Path) -> Dict[int, str]:
    tokens: Dict[int, str] = {}
    if not path.exists():
        return tokens
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            left, _, right = raw.strip().partition(" ")
            if not left or not right:
                continue
            try:
                tokens[int(left)] = right.strip()
            except ValueError:
                pass
    return tokens


def verse_sort_key(path: Path) -> Tuple[int, int]:
    try:
        chapter = int(path.parent.name)
    except ValueError:
        chapter = 999999
    try:
        verse = int(path.stem)
    except ValueError:
        verse = 999999
    return chapter, verse


def tsv_path_for(book: str, chapter: int, verse: int, alignments_dir: Path) -> Path:
    return alignments_dir / book / f"{book}-{chapter}-{verse}.tsv"


def s_tokens_path_for(book: str, chapter: int, verse: int, s_tokens_dir: Path) -> Path:
    return s_tokens_dir / book / f"{book}-{chapter}-{verse}.txt"


def tsv_row_by_gidx(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {row.get("G_IDX", "").strip().zfill(2): row for row in rows}


def word_is_strong_verb(word: str) -> bool:
    w = norm(word)
    return w in STRONG_VERB_WORDS or w in AUXILIARIES


def span_text(tokens: Dict[int, str], indexes: List[int]) -> str:
    return " ".join(tokens[i] for i in indexes if i in tokens).strip()


def span_has_strong_verb(tokens: Dict[int, str], indexes: List[int]) -> bool:
    return any(word_is_strong_verb(tokens.get(i, "")) for i in indexes)


def span_is_aux_phrase(tokens: Dict[int, str], indexes: List[int]) -> bool:
    words = [norm(tokens.get(i, "")) for i in indexes]
    return len(words) >= 2 and words[0] in AUXILIARIES and any(w in STRONG_VERB_WORDS for w in words[1:])


def existing_owner_note(indexes: List[int], rows: List[Dict[str, str]], suspicious_gidx: str) -> str:
    candidate_set = set(indexes)
    for row in rows:
        if row.get("G_IDX", "").strip().zfill(2) == suspicious_gidx:
            continue
        row_set = set(parse_nbla_indexes(row.get("NBLA_IDX", "")))
        if candidate_set & row_set:
            return f"currently owned by G{row.get('G_IDX')}"
    return "unowned or no clear current owner"


def score_span(
    indexes: List[int],
    tokens: Dict[int, str],
    current_indexes: List[int],
    greek_pos: int,
    rows: List[Dict[str, str]],
    suspicious_gidx: str,
) -> Tuple[int, List[str]]:
    text = span_text(tokens, indexes)
    words = [norm(w) for w in text.split()]
    notes: List[str] = []
    score = 0

    if not words or not any(w in STRONG_VERB_WORDS or w in AUXILIARIES for w in words):
        return -999, ["no strong verb token"]

    if words[0] in NON_VERB_WORDS and words[0] not in AUXILIARIES:
        score -= 20
        notes.append("starts with non-verb word")

    strong_count = sum(1 for w in words if w in STRONG_VERB_WORDS)
    aux_count = sum(1 for w in words if w in AUXILIARIES)
    score += strong_count * 45
    score += aux_count * 18

    if span_is_aux_phrase(tokens, indexes):
        score += 35
        notes.append("auxiliary + verbal phrase")

    if len(indexes) == 1:
        score += 15
        notes.append("single-token candidate")
    elif len(indexes) == 2:
        score += 18
        notes.append("compact phrase candidate")
    elif len(indexes) == 3:
        score += 5
    else:
        score -= 25
        notes.append("long candidate span")

    if current_indexes:
        distance = min(abs(i - current_indexes[0]) for i in indexes)
        if distance <= 3:
            score += 18
            notes.append("near corrupted NBLA index")
        elif distance <= 8:
            score += 6
        else:
            score -= min(distance, 25)

    owner = existing_owner_note(indexes, rows, suspicious_gidx)
    notes.append(owner)

    if norm(text) in SUSPICIOUS_FINITE_SURFACES:
        score -= 100
        notes.append("candidate itself suspicious")

    return score, notes


def candidate_spans(
    tokens: Dict[int, str],
    current_indexes: List[int],
    greek_pos: int,
    rows: List[Dict[str, str]],
    suspicious_gidx: str,
) -> List[Candidate]:
    if not tokens:
        return []
    max_idx = max(tokens)
    center = current_indexes[0] if current_indexes else min(max(greek_pos, 1), max_idx)
    window_start = max(1, center - 10)
    window_end = min(max_idx, center + 10)

    spans: List[List[int]] = []
    for i in range(window_start, window_end + 1):
        spans.append([i])
    for length in (2, 3):
        for start in range(window_start, window_end - length + 2):
            spans.append(list(range(start, start + length)))

    candidates: List[Candidate] = []
    seen = set()
    for indexes in spans:
        key = tuple(indexes)
        if key in seen:
            continue
        seen.add(key)
        if not span_has_strong_verb(tokens, indexes):
            continue
        score, notes = score_span(indexes, tokens, current_indexes, greek_pos, rows, suspicious_gidx)
        if score < 45:
            continue
        confidence = "high" if score >= 85 else "medium" if score >= 60 else "low"
        candidates.append(Candidate(format_idx(indexes), span_text(tokens, indexes), score, confidence, "; ".join(dict.fromkeys(notes))))

    candidates.sort(key=lambda c: (-c.score, len(parse_nbla_indexes(c.idx)), c.idx))
    return candidates[:5]


def finite_columns(data: Dict) -> Iterable[Dict]:
    for col in data.get("columns", []):
        if is_finite_rmac(col.get("rmac", "")):
            yield col


def scan_book(book: str, interlinear_dir: Path, alignments_dir: Path, s_tokens_dir: Path, all_candidates: bool) -> List[List[str]]:
    out: List[List[str]] = []
    for json_path in sorted((interlinear_dir / book).glob("*/*.json"), key=verse_sort_key):
        data = read_json(json_path)
        chapter = int(data["chapter"])
        verse = int(data["verse"])
        ref = f"{book} {chapter}:{verse}"
        tsv_path = tsv_path_for(book, chapter, verse, alignments_dir)
        s_path = s_tokens_path_for(book, chapter, verse, s_tokens_dir)
        if not tsv_path.exists():
            continue
        rows = read_tsv(tsv_path)
        by_g = tsv_row_by_gidx(rows)
        tokens = read_s_tokens(s_path)

        for col in finite_columns(data):
            current_text = str(col.get("nbla", "") or "").strip()
            if not is_suspicious_finite_surface(current_text):
                continue
            greek_tokens = col.get("greek_tokens") or []
            gidx = str(greek_tokens[0]).zfill(2) if greek_tokens else ""
            row = by_g.get(gidx, {})
            current_idx = row.get("NBLA_IDX", col.get("nbla_idx", ""))
            current_alignment = row.get("ALIGNMENT", col.get("alignment", ""))
            current_indexes = parse_nbla_indexes(current_idx)
            reason = "missing finite NBLA" if not current_indexes or current_text == "-" else "suspicious finite NBLA surface"

            candidates = candidate_spans(tokens, current_indexes, int(gidx or 999999), rows, gidx)
            if not candidates:
                out.append([ref, gidx, col.get("greek", ""), col.get("lemma", ""), col.get("rmac", ""), current_idx, current_text, current_alignment, reason, "", "", "0", "none", "no candidate found", str(tsv_path)])
                continue

            selected = candidates if all_candidates else candidates[:1]
            for cand in selected:
                out.append([ref, gidx, col.get("greek", ""), col.get("lemma", ""), col.get("rmac", ""), current_idx, current_text, current_alignment, reason, cand.idx, cand.text, str(cand.score), cand.confidence, cand.notes, str(tsv_path)])
    return out


def write_report(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(REPORT_HEADER)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest finite-verb alignment repairs for a book.")
    parser.add_argument("book", help="Book folder name, e.g. 1corintios")
    parser.add_argument("--interlinear-dir", default="MNA/data/interlinear")
    parser.add_argument("--alignments-dir", default="MNA/data/alignments")
    parser.add_argument("--s-tokens-dir", default="MNA/data/s-tokens")
    parser.add_argument("--out", default=None)
    parser.add_argument("--all-candidates", action="store_true", help="write top five candidates per finite verb instead of only the best")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("MNA/outputs/roots-visible") / f"{args.book}-finite-repair-candidates.tsv"
    rows = scan_book(args.book, Path(args.interlinear_dir), Path(args.alignments_dir), Path(args.s_tokens_dir), args.all_candidates)
    write_report(out_path, rows)

    counts = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for row in rows:
        if len(row) > 12:
            counts[row[12]] = counts.get(row[12], 0) + 1
    print(f"Wrote {len(rows)} candidate row(s) to {out_path}")
    print(counts)


if __name__ == "__main__":
    main()
