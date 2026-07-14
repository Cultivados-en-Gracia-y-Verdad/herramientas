#!/usr/bin/env python3
"""Build reader/catalog.json and reader/search-index.json from interlinear exports."""

from __future__ import annotations

import json
import re
from pathlib import Path

from testament_books import ALL_BOOKS_LONGEST_FIRST, NT_BOOKS, OT_BOOKS

ROOT = Path(__file__).resolve().parents[1]
INTERLINEAR = ROOT / "output" / "interlinear"
OUT = ROOT / "reader" / "catalog.json"
SEARCH_OUT = ROOT / "reader" / "search-index.json"

TOKEN_RE = re.compile(r"^(.+)<([^|]*)\|([^|]*)\|([^|]*)\|([^>]*)>$")
# Longest slug first so 1juan / 2reyes are not parsed as juan / reyes.
CHAPTER_RE = re.compile(
    r"^("
    + "|".join(re.escape(b) for b in ALL_BOOKS_LONGEST_FIRST)
    + r")-(\d+)\.interlinear\.txt$"
)

DISPLAY = {
    "genesis": "Génesis",
    "exodo": "Éxodo",
    "levitico": "Levítico",
    "numeros": "Números",
    "deuteronomio": "Deuteronomio",
    "josue": "Josué",
    "jueces": "Jueces",
    "rut": "Rut",
    "1samuel": "1 Samuel",
    "2samuel": "2 Samuel",
    "1reyes": "1 Reyes",
    "2reyes": "2 Reyes",
    "1cronicas": "1 Crónicas",
    "2cronicas": "2 Crónicas",
    "esdras": "Esdras",
    "nehemias": "Nehemías",
    "ester": "Ester",
    "job": "Job",
    "salmos": "Salmos",
    "proverbios": "Proverbios",
    "eclesiastes": "Eclesiastés",
    "cantares": "Cantares",
    "isaias": "Isaías",
    "jeremias": "Jeremías",
    "lamentaciones": "Lamentaciones",
    "ezequiel": "Ezequiel",
    "daniel": "Daniel",
    "oseas": "Oseas",
    "joel": "Joel",
    "amos": "Amós",
    "abdias": "Abdías",
    "jonas": "Jonás",
    "miqueas": "Miqueas",
    "nahum": "Nahúm",
    "habacuc": "Habacuc",
    "sofonias": "Sofonías",
    "hageo": "Hageo",
    "zacarias": "Zacarías",
    "malaquias": "Malaquías",
    "mateo": "Mateo",
    "marcos": "Marcos",
    "lucas": "Lucas",
    "juan": "Juan",
    "hechos": "Hechos",
    "romanos": "Romanos",
    "1corintios": "1 Corintios",
    "2corintios": "2 Corintios",
    "galatas": "Gálatas",
    "efesios": "Efesios",
    "filipenses": "Filipenses",
    "colosenses": "Colosenses",
    "1tesalonicenses": "1 Tesalonicenses",
    "2tesalonicenses": "2 Tesalonicenses",
    "1timoteo": "1 Timoteo",
    "2timoteo": "2 Timoteo",
    "tito": "Tito",
    "filemon": "Filemón",
    "hebreos": "Hebreos",
    "santiago": "Santiago",
    "1pedro": "1 Pedro",
    "2pedro": "2 Pedro",
    "1juan": "1 Juan",
    "2juan": "2 Juan",
    "3juan": "3 Juan",
    "judas": "Judas",
    "apocalipsis": "Apocalipsis",
}


def chapters_for(folder: Path, book: str) -> list[int]:
    """Chapter numbers for a book; filename must start with the full slug."""
    nums = []
    for path in folder.glob(f"{book}-*.interlinear.txt"):
        m = re.fullmatch(rf"{re.escape(book)}-(\d+)\.interlinear\.txt", path.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def build_testament(code: str, books: list[str]) -> dict:
    folder = INTERLINEAR / code
    entries = []
    for slug in books:
        chs = chapters_for(folder, slug)
        if not chs:
            continue
        entries.append(
            {
                "slug": slug,
                "label": DISPLAY.get(slug, slug[:1].upper() + slug[1:]),
                "chapters": chs,
            }
        )
    return {"code": code, "books": entries}


def build_search_index() -> int:
    """Compact verse rows: [testament, book, chapter, verse, es, strongs, surface, morph].

    Verses are emitted in canonical Bible order (OT then NT, book lists, chapter, verse).
    """
    rows: list[list] = []
    for testament, books in (("OT", OT_BOOKS), ("NT", NT_BOOKS)):
        folder = INTERLINEAR / testament
        if not folder.is_dir():
            continue
        for book in books:
            chapter_paths = []
            for path in folder.glob(f"{book}-*.interlinear.txt"):
                m = CHAPTER_RE.match(path.name)
                if not m or m.group(1) != book:
                    continue
                chapter_paths.append((int(m.group(2)), path))
            for chapter, path in sorted(chapter_paths, key=lambda x: x[0]):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if "\t" not in line:
                        continue
                    ref, body = line.split("\t", 1)
                    vs_m = re.search(r":(\d+)\s*$", ref)
                    if not vs_m:
                        continue
                    verse = int(vs_m.group(1))
                    glosses: list[str] = []
                    strongs: list[str] = []
                    surfaces: list[str] = []
                    morphs: list[str] = []
                    for raw in body.split():
                        tm = TOKEN_RE.match(raw)
                        if not tm:
                            continue
                        surfaces.append(tm.group(1))
                        strongs.append(tm.group(3))
                        morphs.append(tm.group(4))
                        glosses.append(tm.group(5).replace("·", " "))
                    rows.append(
                        [
                            testament,
                            book,
                            chapter,
                            verse,
                            " ".join(glosses),
                            " ".join(strongs),
                            " ".join(surfaces),
                            " ".join(morphs),
                        ]
                    )
    SEARCH_OUT.write_text(
        json.dumps({"v": rows}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return len(rows)


def main() -> int:
    catalog = {
        "title": "BLE Interlinear",
        "subtitle": "Biblia Literal en Español — palabra por palabra",
        "testaments": [
            build_testament("OT", OT_BOOKS),
            build_testament("NT", NT_BOOKS),
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ot = len(catalog["testaments"][0]["books"])
    nt = len(catalog["testaments"][1]["books"])
    print(f"wrote {OUT} (OT books={ot}, NT books={nt})")
    n = build_search_index()
    size_mb = SEARCH_OUT.stat().st_size / 1e6
    print(f"wrote {SEARCH_OUT} (verses={n}, {size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
