#!/usr/bin/env python3
"""Extract every MACULA clause (Hebrew WLC + Greek SBLGNT lowfat trees)."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from xml.etree.ElementTree import Element, parse

from versification import to_protestant, validate

ROOT = Path(__file__).resolve().parents[1]
HEBREW_DIR = ROOT / "MACULA" / "macula-hebrew-main" / "WLC" / "lowfat"
GREEK_DIR = ROOT / "MACULA" / "macula-greek-SBLGNT" / "SBLGNT" / "lowfat"
OUT_DIR = ROOT / "clauses"

REF_RE = re.compile(r"^([0-9A-Z]+)\s+(\d+):(\d+)")

COORD_RULES = {
    "CLaCL",
    "ClCl",
    "ClCl2",
    "CLandCL",
    "CLandCL2",
}
EMBED_RULES = {
    "sub-CL",
    "cjpCLx",
    "that-VP",
    "DetCL",
    "PtclCL",
    "of-CL",
}
REDUCED_RULES = {"P2CL", "Np2CL", "V2CL", "O2CL"}


def clause_kind(rule: str | None) -> str:
    r = rule or ""
    if r in COORD_RULES or r.startswith("Conj"):
        return "coord"
    if r in EMBED_RULES:
        return "embed"
    if r in REDUCED_RULES:
        return "reduced"
    return "content"


def word_surface(w: Element) -> str:
    text = "".join(w.itertext()).strip()
    return text


def parse_ref(ref: str | None) -> tuple[str | None, int | None, int | None, str | None]:
    if not ref:
        return None, None, None, None
    m = REF_RE.match(ref)
    if not m:
        return None, None, None, ref.split("!")[0]
    book, chapter, verse = m.group(1), int(m.group(2)), int(m.group(3))
    return book, chapter, verse, f"{book} {chapter}:{verse}"


def own_words(cl: Element) -> list[Element]:
    words: list[Element] = []

    def walk(el: Element, inside_nested: bool) -> None:
        for child in list(el):
            nested = inside_nested or (
                child.tag == "wg" and child.get("class") == "cl" and child is not cl
            )
            if child.tag == "w" and not nested:
                words.append(child)
            walk(child, nested)

    walk(cl, False)
    return words


def first_word(el: Element) -> Element | None:
    for w in el.iter("w"):
        return w
    return None


def _own_children_walk(cl: Element, visit):
    """Walk clause children without entering nested class=cl groups."""

    def walk(el: Element) -> None:
        for child in list(el):
            if child.tag == "wg" and child.get("class") == "cl":
                continue
            visit(child)
            walk(child)

    walk(cl)


def _consonants(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def role_lemmas(cl: Element, role: str) -> list[str]:
    lemmas: list[str] = []

    def visit(child: Element) -> None:
        if child.get("role") != role:
            return
        nodes = [child] if child.tag == "w" else list(child.iter("w"))
        for w in nodes:
            if w.tag == "w" and w.get("lemma"):
                lemmas.append(w.get("lemma") or "")

    _own_children_walk(cl, visit)
    return lemmas


def addressee_lemmas(cl: Element) -> list[str]:
    lemmas: list[str] = []

    def visit(child: Element) -> None:
        if not (child.get("role") == "pp" or child.get("class") == "pp"):
            return
        words = [w for w in child.iter("w") if w.get("lemma")]
        if not words:
            return
        if _consonants(words[0].get("lemma") or "") not in {"אל", "ל"}:
            return
        for w in words[1:]:
            lem = w.get("lemma")
            if lem:
                lemmas.append(lem)

    _own_children_walk(cl, visit)
    return lemmas


def verb_info(words: list[Element]) -> dict[str, str | None]:
    verb = next((w for w in words if w.get("role") == "v"), None)
    if verb is None:
        verb = next((w for w in words if w.get("class") == "verb" or w.get("pos") == "verb"), None)
    if verb is None:
        return {
            "verb_lemma": None,
            "verb_gloss": None,
            "verb_english": None,
            "verb_form": None,
        }
    bits = [
        verb.get("stem"),
        verb.get("type"),
        verb.get("tense"),
        verb.get("voice"),
        verb.get("mood"),
        verb.get("person"),
        verb.get("number"),
    ]
    form = " ".join(b for b in bits if b)
    return {
        "verb_lemma": verb.get("lemma"),
        "verb_gloss": verb.get("gloss"),
        "verb_english": verb.get("english"),
        "verb_form": form or None,
    }


def extract_file(path: Path, corpus: str, start_index: int) -> tuple[list[dict], int]:
    tree = parse(path)
    root = tree.getroot()
    records: list[dict] = []
    index = start_index
    sent_n = 0

    def walk(el: Element, ancestors: list[dict], sentence_id: str | None) -> None:
        nonlocal index, sent_n
        tag = el.tag.split("}")[-1]
        if tag.lower() == "sentence":
            sent_n += 1
            sentence_id = el.get("id") or f"{path.stem}:s{sent_n}"
        if el.tag == "wg" and el.get("class") == "cl":
            index += 1
            words = own_words(el)
            fw = words[0] if words else first_word(el)
            book, chapter, verse, ref = parse_ref(fw.get("ref") if fw is not None else None)
            if book is None and root.get("id"):
                # Hebrew chapter files: id="GEN 1"
                chap_id = root.get("id") or ""
                parts = chap_id.split()
                if len(parts) == 2 and parts[1].isdigit():
                    book = parts[0]
                    chapter = int(parts[1])
                    ref = chap_id
            parent = ancestors[-1] if ancestors else None
            rule = el.get("rule") or el.get("Rule")
            rec = {
                "id": f"{corpus}{index:06d}",
                "corpus": "hebrew" if corpus == "H" else "greek",
                "file": path.name,
                "sentence_id": sentence_id,
                "book": book,
                "chapter": chapter,
                "verse": verse,
                "ref": ref,
                **to_protestant(book, chapter, verse),
                "rule": rule,
                "role": el.get("role"),
                "head": el.get("head"),
                "clause_type": el.get("clauseType") or el.get("ClType"),
                "kind": clause_kind(rule),
                "depth": len(ancestors),
                "parent_id": parent["id"] if parent else None,
                "node_id": el.get("nodeId"),
                "own_text": " ".join(word_surface(w) for w in words if word_surface(w)),
                "own_gloss": " ".join(
                    (w.get("gloss") or w.get("english") or "").strip()
                    for w in words
                    if (w.get("gloss") or w.get("english") or "").strip()
                ),
                "lemmas": [w.get("lemma") for w in words if w.get("lemma")],
                "subject_lemmas": role_lemmas(el, "s"),
                "addressee_lemmas": addressee_lemmas(el),
                "word_ids": [w.get("{http://www.w3.org/XML/1998/namespace}id") or w.get("id") for w in words],
                **verb_info(words),
            }
            records.append(rec)
            child_anc = ancestors + [rec]
            for child in list(el):
                walk(child, child_anc, sentence_id)
            return
        for child in list(el):
            walk(child, ancestors, sentence_id)

    walk(root, [], None)
    return records, index


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_tsv(path: Path, rows: list[dict]) -> None:
    cols = [
        "id",
        "corpus",
        "sentence_id",
        "book",
        "chapter",
        "verse",
        "ref",
        "ref_protestant",
        "rule",
        "role",
        "kind",
        "depth",
        "parent_id",
        "verb_lemma",
        "verb_english",
        "own_gloss",
        "own_text",
    ]
    with path.open("w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for row in rows:
            vals = []
            for c in cols:
                v = row.get(c)
                if v is None:
                    vals.append("")
                else:
                    vals.append(str(v).replace("\t", " ").replace("\n", " "))
            fh.write("\t".join(vals) + "\n")


def summarize(rows: list[dict]) -> dict:
    by_book: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for row in rows:
        book = row.get("book") or "?"
        by_book[book] = by_book.get(book, 0) + 1
        kind = row.get("kind") or "?"
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "clause_count": len(rows),
        "books": len(by_book),
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_book": dict(sorted(by_book.items(), key=lambda kv: kv[0])),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    he_files = sorted(HEBREW_DIR.glob("*-lowfat.xml"))
    el_files = sorted(p for p in GREEK_DIR.glob("*.xml") if p.name != "sblgntlowfat.xml")
    if not he_files:
        print(f"No Hebrew lowfat files in {HEBREW_DIR}", file=sys.stderr)
        return 1
    if not el_files:
        print(f"No Greek lowfat files in {GREEK_DIR}", file=sys.stderr)
        return 1

    hebrew: list[dict] = []
    idx = 0
    for i, path in enumerate(he_files, 1):
        recs, idx = extract_file(path, "H", idx)
        hebrew.extend(recs)
        if i % 100 == 0:
            print(f"Hebrew {i}/{len(he_files)} clauses={idx}", flush=True)
    print(f"Hebrew done: {len(he_files)} files, {len(hebrew)} clauses", flush=True)

    greek: list[dict] = []
    gidx = 0
    for i, path in enumerate(el_files, 1):
        recs, gidx = extract_file(path, "G", gidx)
        greek.extend(recs)
        print(f"Greek {i}/{len(el_files)} {path.name} running={gidx}", flush=True)
    print(f"Greek done: {len(el_files)} files, {len(greek)} clauses", flush=True)

    observed: dict[str, set[tuple[int, int]]] = {}
    shifted = 0
    for row in hebrew + greek:
        book, ch, vs = row.get("book"), row.get("chapter"), row.get("verse")
        if book and ch is not None and vs is not None:
            observed.setdefault(book, set()).add((ch, vs))
        if row.get("versification_shift"):
            shifted += 1
    problems = validate(observed)
    if problems:
        print(f"VERSIFICATION PROBLEMS ({len(problems)}):", file=sys.stderr)
        for p in problems[:20]:
            print("  " + p, file=sys.stderr)
        return 2
    print(f"Versification OK: {shifted} clauses renumbered MT -> Protestant", flush=True)

    write_jsonl(OUT_DIR / "hebrew.jsonl", hebrew)
    write_jsonl(OUT_DIR / "greek.jsonl", greek)
    write_tsv(OUT_DIR / "hebrew.tsv", hebrew)
    write_tsv(OUT_DIR / "greek.tsv", greek)

    summary = {
        "hebrew": summarize(hebrew),
        "greek": summarize(greek),
        "total_clauses": len(hebrew) + len(greek),
        "source": {
            "hebrew": "MACULA Hebrew WLC lowfat",
            "greek": "MACULA Greek SBLGNT lowfat",
        },
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"total": summary["total_clauses"], "hebrew": len(hebrew), "greek": len(greek)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
