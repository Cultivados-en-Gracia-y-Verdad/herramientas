"""NT and OT book slugs for BLE assembly.

Canonical Protestant order. Numbered books keep the digit in the slug
(no separator): 1samuel, 2reyes, 1cronicas, 1corintios, 1juan, etc.
When matching filenames, always prefer the longest slug so ``juan`` does
not steal ``1juan`` / ``2juan`` / ``3juan``.
"""

from __future__ import annotations

NT_BOOKS = [
    "mateo",
    "marcos",
    "lucas",
    "juan",
    "hechos",
    "romanos",
    "1corintios",
    "2corintios",
    "galatas",
    "efesios",
    "filipenses",
    "colosenses",
    "1tesalonicenses",
    "2tesalonicenses",
    "1timoteo",
    "2timoteo",
    "tito",
    "filemon",
    "hebreos",
    "santiago",
    "1pedro",
    "2pedro",
    "1juan",
    "2juan",
    "3juan",
    "judas",
    "apocalipsis",
]

OT_BOOKS = [
    "genesis",
    "exodo",
    "levitico",
    "numeros",
    "deuteronomio",
    "josue",
    "jueces",
    "rut",
    "1samuel",
    "2samuel",
    "1reyes",
    "2reyes",
    "1cronicas",
    "2cronicas",
    "esdras",
    "nehemias",
    "ester",
    "job",
    "salmos",
    "proverbios",
    "eclesiastes",
    "cantares",
    "isaias",
    "jeremias",
    "lamentaciones",
    "ezequiel",
    "daniel",
    "oseas",
    "joel",
    "amos",
    "abdias",
    "jonas",
    "miqueas",
    "nahum",
    "habacuc",
    "sofonias",
    "hageo",
    "zacarias",
    "malaquias",
]

# Longest-first for unambiguous filename / reference matching (1juan before juan).
ALL_BOOKS = OT_BOOKS + NT_BOOKS
ALL_BOOKS_LONGEST_FIRST = sorted(ALL_BOOKS, key=len, reverse=True)
