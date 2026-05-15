#!/usr/bin/env python3

import html
import json
import sys
from pathlib import Path


JSON_DIR = Path("data/interlinear/filemon/1")
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "filemon-interlinear.html"


ROWS = [
    ("NBLA", "nbla"),
    ("Greek", "greek"),
    ("Translit", "translit"),
    ("Lemma", "lemma"),
    ("MorphGNT", "morphgnt"),
    ("RMAC", "rmac"),
    ("Strong’s", "strongs"),
]


def fail(message: str) -> None:
    print("FAIL")
    print()
    print(f"- {message}")
    sys.exit(1)


def verse_number(path: Path) -> int:
    return int(path.stem)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def esc(value) -> str:
    return html.escape(str(value or ""))


def render_verse(data: dict) -> str:
    reference = esc(data["reference"])
    columns = data["columns"]

    out = []

    out.append(f'<section class="verse" id="{reference.replace(" ", "-")}">')
    out.append(f"<h2>{reference}</h2>")
    out.append('<div class="scroll">')
    out.append('<table class="interlinear">')

    for label, field in ROWS:
        out.append("<tr>")
        out.append(f'<th class="row-label">{esc(label)}</th>')

        for col in columns:
            value = esc(col.get(field, ""))

            classes = ["cell", field]

            if col.get("alignment") == "shared":
                classes.append("shared")

            out.append(
                f'<td class="{" ".join(classes)}" '
                f'data-column="{esc(col.get("column", ""))}" '
                f'data-greek="{esc(col.get("greek", ""))}" '
                f'data-lemma="{esc(col.get("lemma", ""))}" '
                f'data-rmac="{esc(col.get("rmac", ""))}" '
                f'data-morphgnt="{esc(col.get("morphgnt", ""))}">'
                f"{value}</td>"
            )

        out.append("</tr>")

    out.append("</table>")
    out.append("</div>")
    out.append("</section>")

    return "\n".join(out)


def render_page(verses: list[dict]) -> str:
    body = "\n\n".join(render_verse(v) for v in verses)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Filemón — Interlinear</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem;
      background: #fafafa;
      color: #222;
    }}

    h1 {{
      margin-bottom: 2rem;
    }}

    h2 {{
      margin-top: 2.5rem;
      margin-bottom: 0.75rem;
      font-size: 1.2rem;
    }}

    .verse {{
      margin-bottom: 2.5rem;
    }}

    .scroll {{
      overflow-x: auto;
      border: 1px solid #ddd;
      background: white;
      padding: 0.75rem;
      border-radius: 8px;
    }}

    table.interlinear {{
      border-collapse: collapse;
      white-space: nowrap;
      font-size: 15px;
    }}

    th.row-label {{
      position: sticky;
      left: 0;
      background: #f0f0f0;
      text-align: right;
      padding: 0.35rem 0.75rem;
      border-right: 2px solid #ccc;
      font-weight: 700;
      z-index: 2;
    }}

    td.cell {{
      padding: 0.35rem 0.8rem;
      border-bottom: 1px solid #eee;
      vertical-align: top;
      text-align: center;
    }}

    td.greek {{
      font-family: "Times New Roman", serif;
      font-size: 18px;
    }}

    td.lemma {{
      font-family: "Times New Roman", serif;
    }}

    td.rmac,
    td.morphgnt,
    td.strongs {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      color: #555;
    }}

    td.shared {{
      color: #777;
      background: #fafafa;
    }}

    td.cell:hover {{
      background: #fff3bf;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <h1>Filemón — Interlinear</h1>

{body}

</body>
</html>
"""


def main() -> None:
    if not JSON_DIR.exists():
        fail(f"JSON directory not found: {JSON_DIR}")

    json_files = sorted(JSON_DIR.glob("*.json"), key=verse_number)

    if not json_files:
        fail(f"no JSON files found in {JSON_DIR}")

    verses = [load_json(p) for p in json_files]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_text = render_page(verses)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write(html_text)

    print("PASS HTML written:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()