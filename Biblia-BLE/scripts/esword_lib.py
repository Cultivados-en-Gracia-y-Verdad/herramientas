"""Shared helpers for e-Sword Bible modules (Windows .bblx and Mac .bbli)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


# Standard Protestant e-Sword book numbers (Genesis = 1 … Malachi = 39,
# Matthew = 40 … Revelation = 66).
ESWORD_BOOK_ID: dict[str, int] = {
    "genesis": 1,
    "exodo": 2,
    "levitico": 3,
    "numeros": 4,
    "deuteronomio": 5,
    "josue": 6,
    "jueces": 7,
    "rut": 8,
    "1samuel": 9,
    "2samuel": 10,
    "1reyes": 11,
    "2reyes": 12,
    "1cronicas": 13,
    "2cronicas": 14,
    "esdras": 15,
    "nehemias": 16,
    "ester": 17,
    "job": 18,
    "salmos": 19,
    "proverbios": 20,
    "eclesiastes": 21,
    "cantares": 22,
    "isaias": 23,
    "jeremias": 24,
    "lamentaciones": 25,
    "ezequiel": 26,
    "daniel": 27,
    "oseas": 28,
    "joel": 29,
    "amos": 30,
    "abdias": 31,
    "jonas": 32,
    "miqueas": 33,
    "nahum": 34,
    "habacuc": 35,
    "sofonias": 36,
    "hageo": 37,
    "zacarias": 38,
    "malaquias": 39,
    "mateo": 40,
    "marcos": 41,
    "lucas": 42,
    "juan": 43,
    "hechos": 44,
    "romanos": 45,
    "1corintios": 46,
    "2corintios": 47,
    "galatas": 48,
    "efesios": 49,
    "filipenses": 50,
    "colosenses": 51,
    "1tesalonicenses": 52,
    "2tesalonicenses": 53,
    "1timoteo": 54,
    "2timoteo": 55,
    "tito": 56,
    "filemon": 57,
    "hebreos": 58,
    "santiago": 59,
    "1pedro": 60,
    "2pedro": 61,
    "1juan": 62,
    "2juan": 63,
    "3juan": 64,
    "judas": 65,
    "apocalipsis": 66,
}

# Public study module — traditional interlinear, NOT the official BLE Bible text.
MODULE_TITLE = "BLE Interlinear (estudio)"
MODULE_ABBREV = "BLEi"
MODULE_BASENAME = "BLE-Interlinear"
MODULE_INFO = (
    "<p><b>BLE Interlinear</b> — interlinear de estudio (hebreo/griego + glosa española).</p>"
    "<p>No es la Biblia Literal en Español (BLE) oficial. "
    "Cada versículo muestra el texto original con su glosa literal debajo.</p>"
    "<p>Generado desde MNA/BLE (Cultivados en Gracia y Verdad).</p>"
)


class EswordPlatform(str, Enum):
    WINDOWS = "windows"
    MAC = "mac"


@dataclass(frozen=True)
class EswordModuleSpec:
    platform: EswordPlatform
    extension: str
    details_sql: str
    details_insert_sql: str


WINDOWS_SPEC = EswordModuleSpec(
    platform=EswordPlatform.WINDOWS,
    extension=".bblx",
    details_sql="""
        CREATE TABLE Details (
            Description NVARCHAR(250),
            Abbreviation NVARCHAR(50),
            Information TEXT,
            Version INT,
            Font NVARCHAR(50),
            RightToLeft BOOL,
            OT BOOL,
            NT BOOL,
            Apocrypha BOOL,
            Strong BOOL
        )
    """,
    details_insert_sql="""
        INSERT INTO Details (
            Description, Abbreviation, Information, Version, Font,
            RightToLeft, OT, NT, Apocrypha, Strong
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
)

MAC_SPEC = EswordModuleSpec(
    platform=EswordPlatform.MAC,
    extension=".bbli",
    details_sql="""
        CREATE TABLE Details (
            Title NVARCHAR(100),
            Abbreviation NVARCHAR(50),
            Information TEXT,
            Version INT,
            OldTestament BOOL,
            NewTestament BOOL,
            Apocrypha BOOL,
            Strongs BOOL,
            RightToLeft BOOL
        )
    """,
    details_insert_sql="""
        INSERT INTO Details (
            Title, Abbreviation, Information, Version,
            OldTestament, NewTestament, Apocrypha, Strongs, RightToLeft
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
)

BIBLE_SQL = """
    CREATE TABLE Bible (
        Book INT,
        Chapter INT,
        Verse INT,
        Scripture TEXT
    )
"""


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def details_row(
    spec: EswordModuleSpec,
    *,
    include_ot: bool,
    include_nt: bool,
    strong: bool = True,
) -> tuple:
    # Module-level RTL stays off: verses mix Hebrew RTL columns with Spanish/Greek LTR.
    if spec.platform is EswordPlatform.WINDOWS:
        return (
            MODULE_TITLE,
            MODULE_ABBREV,
            MODULE_INFO,
            6,
            "DEFAULT",
            0,
            1 if include_ot else 0,
            1 if include_nt else 0,
            0,
            1 if strong else 0,
        )
    return (
        MODULE_TITLE,
        MODULE_ABBREV,
        MODULE_INFO,
        6,
        1 if include_ot else 0,
        1 if include_nt else 0,
        0,
        1 if strong else 0,
        0,
    )


def write_module(
    dest: Path,
    verses: list[tuple[int, int, int, str]],
    spec: EswordModuleSpec,
    *,
    include_ot: bool = True,
    include_nt: bool = True,
    strong: bool = True,
    html: bool = True,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    conn = sqlite3.connect(dest)
    try:
        cur = conn.cursor()
        cur.execute(spec.details_sql)
        cur.execute(
            spec.details_insert_sql,
            details_row(
                spec,
                include_ot=include_ot,
                include_nt=include_nt,
                strong=strong,
            ),
        )
        cur.execute(BIBLE_SQL)
        rows = []
        for book, ch, vs, text in verses:
            scripture = text if html else escape_html(text)
            rows.append((book, ch, vs, scripture))
        cur.executemany(
            "INSERT INTO Bible (Book, Chapter, Verse, Scripture) VALUES (?, ?, ?, ?)",
            rows,
        )
        cur.execute("CREATE INDEX BookChapterVerseIndex ON Bible (Book, Chapter, Verse)")
        conn.commit()
    finally:
        conn.close()


def read_bible_rows(path: Path) -> list[tuple[int, int, int, str]]:
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT Book, Chapter, Verse, Scripture FROM Bible ORDER BY Book, Chapter, Verse")
        return [(int(r[0]), int(r[1]), int(r[2]), str(r[3])) for r in cur.fetchall()]
    finally:
        conn.close()


def convert_bblx_to_bbli(source: Path, dest: Path) -> int:
    verses = read_bible_rows(source)
    book_ids = {b for b, _, _, _ in verses}
    include_ot = any(b <= 39 for b in book_ids)
    include_nt = any(b >= 40 for b in book_ids)
    # Preserve HTML already stored in Scripture.
    write_module(
        dest,
        verses,
        MAC_SPEC,
        include_ot=include_ot,
        include_nt=include_nt,
        html=True,
    )
    return len(verses)
