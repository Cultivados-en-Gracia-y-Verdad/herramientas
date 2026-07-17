# CGV PDF Builder

This is a plain Markdown to PDF exporter for CGV study-manual material. It uses the attached manuals as layout references: letter-sized pages, simple page numbers, a small footer, readable body text, verse callouts, headings, and bullet lists.

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Export

```bash
python3 md_to_pdf.py source.md \
  --title "Manual del Maestro" \
  --subtitle "Tito" \
  --footer-left "Tito (0.8)" \
  --output output/pdf/tito-maestro.pdf
```

By default, output goes to `output/pdf/<source-name>.pdf`.

Useful options:

- `--body-size 13`: make the manual text larger or smaller.
- `--no-cover`: start directly with the Markdown content.
- `--footer-left`, `--footer-center`, `--footer-right`: set footer text.
- `---` on its own line in the Markdown inserts a page break.

## Markdown Supported

- `#` through `######` headings
- paragraphs
- `-`, `*`, and numbered lists
- blockquotes with `>`
- inline `**bold**`, `*italic*`, and `` `code` ``
- quoted paragraphs beginning and ending with Spanish or English curly quotes are styled as verse callouts

