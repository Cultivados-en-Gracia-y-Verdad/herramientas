import re


BOOK_NUMBERS = {
    "mateo": "01",
    "marcos": "02",
    "lucas": "03",
    "juan": "04",
    "hechos": "05",
    "romanos": "06",
    "1corintios": "07",
    "2corintios": "08",
    "galatas": "09",
    "efesios": "10",
    "filipenses": "11",
    "colosenses": "12",
    "1tesalonicenses": "13",
    "2tesalonicenses": "14",
    "1timoteo": "15",
    "2timoteo": "16",
    "tito": "17",
    "filemon": "18",
    "hebreos": "19",
    "santiago": "20",
    "1pedro": "21",
    "2pedro": "22",
    "1juan": "23",
    "2juan": "24",
    "3juan": "25",
    "judas": "26",
    "apocalipsis": "27",
}


def convert_ref(ref):
    """
    Converts:
      filipenses 1:1 -> 110101
      1corintios 1:10 -> 070110
    """

    ref = ref.strip().lower()

    parts = ref.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid reference format: {ref}")

    book, cv = parts

    if book not in BOOK_NUMBERS:
        raise ValueError(f"Unknown book name in ref_converter: {book}")

    match = re.match(r"^(\d+):(\d+)$", cv)
    if not match:
        raise ValueError(f"Invalid chapter:verse format: {cv}")

    chapter = int(match.group(1))
    verse = int(match.group(2))

    return f"{BOOK_NUMBERS[book]}{chapter:02d}{verse:02d}"