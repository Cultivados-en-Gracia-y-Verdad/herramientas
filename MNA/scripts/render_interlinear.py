import json
from pathlib import Path


VERSE_PATH = Path("data/interlinear/filemon/1/1.json")


ROWS = [
    ("NBLA", "nbla"),
    ("Greek", "greek"),
    ("Translit", "translit"),
    ("Lemma", "lemma"),
    ("RMAC", "rmac"),
    ("Strong’s", "strongs"),
]


def load_verse(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_widths(columns):
    widths = []

    for column in columns:
        values = [
            str(column.get(field, ""))
            for _, field in ROWS
        ]

        width = max(len(v) for v in values)
        widths.append(width + 2)

    return widths


def render_row(label, field, columns, widths):
    print(label.ljust(12), end="")

    for column, width in zip(columns, widths):
        value = str(column.get(field, ""))
        print(value.ljust(width), end="")

    print()


def render(verse):
    print()
    print(verse["reference"])
    print()

    columns = verse["columns"]

    widths = compute_widths(columns)

    for label, field in ROWS:
        render_row(label, field, columns, widths)

    print()


def main():
    verse = load_verse(VERSE_PATH)
    render(verse)


if __name__ == "__main__":
    main()