"""Shared helpers for e-Sword Bible modules (Windows .bblx and Mac .bbli)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Windows .bblx (Spanish e-Sword ecosystem): Version=2 means RTF Scripture,
# matching working modules such as RV1960+ / iNA27+.
# Mac/mobile .bbli: HTML Scripture (Version=4).
WINDOWS_CONTENT_VERSION = 2
MAC_CONTENT_VERSION = 4


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

# Public study module — traditional interlinear with Strong's/morph links.
# The "+" suffix follows e-Sword convention (KJV+, NAS95+, OGNT+, …).
# NOT the official assembled BLE Bible text.
MODULE_TITLE = "BLE+ Interlinear (estudio)"
MODULE_ABBREV = "BLE+"
MODULE_BASENAME = "BLE+"
MODULE_INFO_HTML = (
    "<p><b>BLE+</b> — interlinear de estudio (hebreo/griego + Strong's + morfología + glosa española).</p>"
    "<p>Usa etiquetas nativas de e-Sword: <num>Strong's</num>, <tvm>morfología</tvm>.</p>"
    "<p><b>No es la Biblia Literal en Español (BLE) oficial.</b> "
    "Esa publicación queda para más adelante.</p>"
    "<p>Generado desde MNA/BLE (Cultivados en Gracia y Verdad).</p>"
)

# RTF cover/description for Windows .bblx (Version=2). Font/color tables mirror
# Spanish Biblioteca Hispana interlinears so verse fragments can use \f0/\f1/\cf*.
MODULE_INFO_RTF = (
    r"{\rtf1\ansi\ansicpg1252\deff0"
    r"{\fonttbl"
    r"{\f0\froman\fcharset0 Times New Roman;}"
    r"{\f1\froman\fcharset161 Greek;}"
    r"{\f2\froman\fcharset177 Hebrew;}"
    r"}"
    r"{\colortbl ;"
    r"\red0\green0\blue0;"
    r"\red0\green0\blue255;"
    r"\red0\green255\blue255;"
    r"\red0\green255\blue0;"
    r"\red255\green0\blue255;"
    r"\red255\green0\blue0;"
    r"\red255\green255\blue0;"
    r"\red255\green255\blue255;"
    r"\red0\green0\blue128;"
    r"\red0\green128\blue128;"
    r"\red0\green128\blue0;"
    r"\red128\green0\blue128;"
    r"\red128\green0\blue0;"
    r"\red128\green128\blue0;"
    r"\red128\green128\blue128;"
    r"\red192\green192\blue192;"
    r"}"
    r"\viewkind4\uc1\pard\qc\f0\fs28\b BLE+\b0\par"
    r"\fs20 Interlinear de estudio (hebreo/griego + Strong's + morfolog\'eda + glosa espa\'f1ola)\par"
    r"\pard\fs18 No es la Biblia Literal en Espa\'f1ol (BLE) oficial.\par"
    r"Generado desde MNA/BLE (Cultivados en Gracia y Verdad).\par}"
)

# Back-compat alias used by older call sites.
MODULE_INFO = MODULE_INFO_HTML


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
            Comments TEXT,
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
            Description, Abbreviation, Comments, Version, Font,
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


def escape_rtf(text: str) -> str:
    """Encode text for e-Sword Version=2 RTF verse fragments (Unicode-safe)."""
    parts: list[str] = []
    for ch in text:
        code = ord(ch)
        if ch in ("\\", "{", "}"):
            parts.append("\\" + ch)
        elif code < 128:
            parts.append(ch)
        elif code <= 0xFF:
            parts.append(f"\\'{code:02x}")
        elif code <= 0xFFFF:
            signed = code if code <= 32767 else code - 65536
            parts.append(f"\\u{signed}?")
        else:
            parts.append("?")
    return "".join(parts)


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
            MODULE_INFO_RTF,
            WINDOWS_CONTENT_VERSION,
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
        MODULE_INFO_HTML,
        MAC_CONTENT_VERSION,
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
            # Callers pass already-formatted HTML or RTF; only escape when plain.
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
    """Copy Scripture rows into a Mac .bbli shell.

    Only valid when the source .bblx already stores HTML (legacy). Newer
    Windows BLE+ modules store RTF — rebuild with ble_to_esword.py --platform mac.
    """
    verses = read_bible_rows(source)
    if verses and ("\\cf" in verses[0][3] or "\\f1" in verses[0][3]):
        raise ValueError(
            f"{source.name} looks like RTF (Windows Version=2). "
            "Rebuild the Mac module with: python3 scripts/ble_to_esword.py --platform mac"
        )
    book_ids = {b for b, _, _, _ in verses}
    include_ot = any(b <= 39 for b in book_ids)
    include_nt = any(b >= 40 for b in book_ids)
    write_module(
        dest,
        verses,
        MAC_SPEC,
        include_ot=include_ot,
        include_nt=include_nt,
        html=True,
    )
    return len(verses)
