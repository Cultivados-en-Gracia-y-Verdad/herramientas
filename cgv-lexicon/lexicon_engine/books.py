"""NT book slug → English display name (observation layer references)."""

from __future__ import annotations

BOOK_DISPLAY: dict[str, str] = {
    "mateo": "Matthew",
    "marcos": "Mark",
    "lucas": "Luke",
    "juan": "John",
    "hechos": "Acts",
    "romanos": "Romans",
    "1corintios": "1 Corinthians",
    "2corintios": "2 Corinthians",
    "galatas": "Galatians",
    "efesios": "Ephesians",
    "filipenses": "Philippians",
    "colosenses": "Colossians",
    "1tesalonicenses": "1 Thessalonians",
    "2tesalonicenses": "2 Thessalonians",
    "1timoteo": "1 Timothy",
    "2timoteo": "2 Timothy",
    "tito": "Titus",
    "filemon": "Philemon",
    "hebreos": "Hebrews",
    "santiago": "James",
    "1pedro": "1 Peter",
    "2pedro": "2 Peter",
    "1juan": "1 John",
    "2juan": "2 John",
    "3juan": "3 John",
    "judas": "Jude",
    "apocalipsis": "Revelation",
}


def display_book(slug: str) -> str:
    return BOOK_DISPLAY.get(slug, slug.replace("_", " ").title())


def format_ref(slug: str, ch: int, vs: int) -> str:
    return f"{display_book(slug)} {ch}:{vs}"
