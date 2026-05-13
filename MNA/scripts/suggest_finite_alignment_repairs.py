#!/usr/bin/env python3

"""
Suggest repairs for suspicious finite-verb NBLA alignments.

This script does NOT modify TSV files.

It scans interlinear JSON to identify finite Greek verbs whose current NBLA
surface is missing or suspicious, then inspects the verse's Spanish token file
and alignment TSV to suggest likely NBLA token ownership repairs.

Primary purpose:
  audit -> suggest -> human review -> repair TSV -> regenerate JSON -> re-audit
"""

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


SUSPICIOUS_FINITE_SURFACES = {
    "-", "a", "al", "de", "del", "el", "la", "las", "los", "lo", "en",
    "por", "para", "con", "sin", "que", "qué", "y", "o", "pero", "sino",
    "un", "una", "unos", "unas", "cada", "todo", "toda", "todos", "todas",
    "iglesias", "señor",
}

AUXILIARIES = {
    "he", "has", "ha", "hemos", "han",
    "hube", "hubo", "hubieron", "había", "habían",
    "fui", "fue", "fuimos", "fueron",
    "soy", "eres", "es", "somos", "son",
    "era", "eran", "será", "serán",
    "estoy", "estás", "está", "estamos", "están",
    "estaba", "estaban", "esté", "estén",
}

# Spanish finite-looking endings. This is intentionally broad because this tool
# only proposes candidates; it does not apply repairs.
FINITE_ENDING_RE = re.compile(
    r"(o|as|a|amos|áis|an|es|e|emos|éis|en|í|iste|ió|imos|ieron|aron|"
    r"aba|abas|ábamos|aban|ía|ías|íamos|ían|aré|arás|ará|aremos|arán|"
    r"eré|erás|erá|eremos|erán|iré|irás|irá|iremos|irán|"
    r"aría|arían|ería|erían|iría|irían|ad|ed|id)$",
    re.IGNORECASE,
)

STRONG_VERB_WORDS = {
    "anda", "ande", "anden", "andemos",
    "beba", "beban", "coma", "coman",
    "crea", "creen", "cree", "creemos",
    "diga", "digan", "dice", "dicen", "dijo", "dijeron",
    "edifica", "edifican", "edifique", "edifiquen",
    "escriba", "escriban", "escrito", "escrita", "escritas", "escritos",
    "examine", "examínese", "juzguen", "juzga", "juzgo",
    "llama", "llamó", "llamado", "llamados", "llamadas",
    "muere", "murió", "murieron", "murió",
    "ordeno", "ordena", "ordenen",
    "puede", "pueden", "podrá", "podrán",
    "ruego", "rogué", "saben", "sabemos", "sé",
    "tengo", "tiene", "tienen", "tenemos", "tendrá", "tendrán",
    "vivan", "vive", "viven",
}

ALIGNMENT_HEADER = [
    "BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT",
]

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
    if len(parts) < 2:
        return False
    tvm = parts[1]
    if len(tvm) < 3:
        return False
    return tvm[-1] in {"I", "S", "M", "D"}


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
                continue
        else:
            try:
                values.append(int(part))
            except ValueError:
                continue
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
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader)


def read_s_tokens(path: Path) -> Dict[int, str]:
    tokens: Dict[int, str] = {}
    if not path.exists():
        return tokens
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            left, _, right = line.partition(" ")
            try:
                tokens[int(left)] = right.strip()
            except ValueError:
                continue
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
    return {row.get("G_IDX", "").strip(): row for row in rows}


def used_finite_indexes(data: Dict, suspicious_gidx: str) -> set:
    used = set()
    for col in data.get("columns", []):
        g_tokens = col.get("greek_tokens") or []
        gidx = str(g_tokens[0]).zfill(2) if g_tokens else ""
        if gidx == suspicious_gidx:
            continue
        if is_finite_rmac(col.get("rmac", "")) and not is_suspicious_finite_surface(col.get("nbla", "")):
            used.update(parse_nbla_indexes(col.get("nbla_idx", "")))
    return used


def word_is_verbish(word: str) -> bool:
    w = norm(word)
    if not w:
        return False
    if w in AUXILIARIES or w in STRONG_VERB_WORDS:
        return True
    if FINITE_ENDING_RE.search(w) and len(w) >= 4:
        return True
    return False


def span_text(tokens: Dict[int, str], indexes: List[int]) -> str:
    return " ".join(tokens[i] for i in indexes if i in tokens).strip()


def score_span(
    indexes: List[int],
    tokens: Dict[int, str],
    current_indexes: List[int],
    greek_pos: int,
    tsv_rows: List[Dict[str, str]],
    data: Dict,
    suspicious_gidx: str,
) -> Tuple[int, List[str]]:
    words = [tokens[i] for i in indexes if i in tokens]
    normalized = [norm(w) for w in words]
    text = " ".join(words)
    notes: List[str] = []
    score = 0

    if any(word_is_verbish(w) for w in words):
        score += 35
        notes.append("contains verb-like Spanish token")

    if normalized and normalized[0] in AUXILIARIES and len(indexes) >= 2:
        score += 30
        notes.append("auxiliary + verbal phrase candidate")

    if any(w in STRONG_VERB_WORDS for w in normalized):
        score += 25
        notes.append("strong known verb word")

    if len(indexes) <= 3:
        score += 8
    else:
        score -= len(indexes) * 3

    if current_indexes:
        distance = min(abs(i - current_indexes[0]) for i in indexes)
        if distance <= 4:
            score += 16
            notes.append("near current corrupted NBLA index")
        elif distance <= 8:
            score += 8
        else:
            score -= min(distance, 20)

    # If the candidate is currently owned by a non-verb Greek row, it may be a drift/swap.
    candidate_set = set(indexes)
    finite_good_used = used_finite_indexes(data, suspicious_gidx)
    if candidate_set & finite_good_used:
        score -= 60
        notes.append("candidate overlaps another apparently good finite verb")

    for row in tsv_rows:
        row_indexes = set(parse_nbla_indexes(row.get("NBLA_IDX", "")))
        if not row_indexes or not (candidate_set & row_indexes):
            continue
        if row.get("G_IDX", "").strip() == suspicious_gidx:
            continue
        # Existing non-finite owner of a verbal phrase is a strong drift signal.
        row_text = row.get("NBLA_TEXT", "")
        if any(word_is_verbish(w) for w in row_text.split()):
            score += 18
            notes.append(f"currently owned by neighboring row G{row.get('G_IDX')} with verb-like text")
            break

    if norm(text) in SUSPICIOUS_FINITE_SURFACES:
        score -= 50
        notes.append("candidate is also suspicious")

    return score, notes


def candidate_spans(
    tokens: Dict[int, str],
    current_indexes: List[int],
    greek_pos: int,
    tsv_rows: List[Dict[str, str]],
    data: Dict,
    suspicious_gidx: str,
) -> List[Candidate]:
    if not tokens:
        return []

    max_idx = max(tokens)
    center = current_indexes[0] if current_indexes else min(max(greek_pos, 1), max_idx)

    spans: List[List[int]] = []
    window_start = max(1, center - 10)
    window_end = min(max_idx, center + 10)

    # single-token candidates
    for i in range(window_start, window_end + 1):
        spans.append([i])

    # short phrase candidates, especially useful for "ha asignado", "fue crucificado", etc.
    for length in (2, 3, 4):
        for start in range(window_start, window_end - length + 2):
            spans.append(list(range(start, start + length)))

    candidates: List[Candidate] = []
    seen = set()
    for indexes in spans:
        key = tuple(indexes)
        if key in seen:
            continue
        seen.add(key)
        text = span_text(tokens, indexes)
        if not text:
            continue
        # Keep only spans with at least one verbal-looking element. This avoids flooding the report.
        if not any(word_is_verbish(word) for word in text.split()):
            continue
        score, notes = score_span(indexes, tokens, current_indexes, greek_pos, tsv_rows, data, suspicious_gidx)
        if score < 20:
            continue
        confidence = "high" if score >= 75 else "medium" if score >= 50 else "low"
        candidates.append(Candidate(format_idx(indexes), text, score, confidence, "; ".join(dict.fromkeys(notes))))

    candidates.sort(key=lambda c: (-c.score, len(c.idx), c.idx))
    return candidates[:5]


def finite_columns(data: Dict) -> Iterable[Dict]:
    for col in data.get("columns", []):
        if is_finite_rmac(col.get("rmac", "")):
            yield col


def scan_book(book: str, interlinear_dir: Path, alignments_dir: Path, s_tokens_dir: Path) -> List[List[str]]:
    rows_out: List[List[str]] = []
    book_dir = interlinear_dir / book
    for json_path in sorted(book_dir.glob("*/*.json"), key=verse_sort_key):
        data = read_json(json_path)
        chapter = int(data["chapter"])
        verse = int(data["verse"])
        ref = f"{book} {chapter}:{verse}"
        tsv_path = tsv_path_for(book, chapter, verse, alignments_dir)
        s_path = s_tokens_path_for(book, chapter, verse, s_tokens_dir)
        if not tsv_path.exists():
            continue
        tsv_rows = read_tsv(tsv_path)
        tsv_by_g = tsv_row_by_gidx(tsv_rows)
        tokens = read_s_tokens(s_path)

        for col in finite_columns(data):
            current_text = str(col.get("nbla", "") or "").strip()
            if not is_suspicious_finite_surface(current_text):
                continue
            greek_tokens = col.get("greek_tokens") or []
            gidx = str(greek_tokens[0]).zfill(2) if greek_tokens else ""
            tsv_row = tsv_by_g.get(gidx, {})
            current_idx = tsv_row.get("NBLA_IDX", col.get("nbla_idx", ""))
            current_alignment = tsv_row.get("ALIGNMENT", col.get("alignment", ""))
            current_indexes = parse_nbla_indexes(current_idx)
            reason = "missing finite NBLA" if not current_indexes or current_text == "-" else "suspicious finite NBLA surface"

            candidates = candidate_spans(
                tokens=tokens,
                current_indexes=current_indexes,
                greek_pos=int(gidx or 999999),
                tsv_rows=tsv_rows,
                data=data,
                suspicious_gidx=gidx,
            )

            if not candidates:
                rows_out.append([
                    ref, gidx, col.get("greek", ""), col.get("lemma", ""), col.get("rmac", ""),
                    current_idx, current_text, current_alignment,
                    reason, "", "", "0", "none", "no candidate found", str(tsv_path),
                ])
                continue

            for candidate in candidates:
                rows_out.append([
                    ref, gidx, col.get("greek", ""), col.get("lemma", ""), col.get("rmac", ""),
                    current_idx, current_text, current_alignment,
                    reason, candidate.idx, candidate.text, str(candidate.score), candidate.confidence,
                    candidate.notes, str(tsv_path),
                ])

    return rows_out


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
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path("MNA/outputs/roots-visible") / f"{args.book}-finite-repair-candidates.tsv"
    rows = scan_book(args.book, Path(args.interlinear_dir), Path(args.alignments_dir), Path(args.s_tokens_dir))
    write_report(out_path, rows)

    high = sum(1 for row in rows if len(row) > 12 and row[12] == "high")
    medium = sum(1 for row in rows if len(row) > 12 and row[12] == "medium")
    low = sum(1 for row in rows if len(row) > 12 and row[12] == "low")
    none = sum(1 for row in rows if len(row) > 12 and row[12] == "none")

    print(f"Wrote {len(rows)} candidate row(s) to {out_path}")
    print({"high": high, "medium": medium, "low": low, "none": none})


if __name__ == "__main__":
    main()
