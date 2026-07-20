# CGV PDF Builder

This is a plain Markdown to PDF exporter for CGV study-manual material. It uses the attached manuals as layout references: letter-sized pages, simple page numbers, a small footer, readable body text, scripture formatting, headings, and semantic list markers.

## Install

```bash
python3 -m pip install -r requirements.txt
```

## Export

Terminal-style local app:

```bash
python3 app.py
```

Then open `http://127.0.0.1:8765`.

Command-line export:

```bash
python3 md_to_pdf.py
```

By default, the exporter reads `manual.md` and writes two PDFs beside the source Markdown:

- `manual-del-alumno.pdf`
- `manual-del-maestro.pdf`

If there is no local `manual.md`, it reads `/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/17.Tito/manual.md`.

Useful options:

- `--body-size 13`: make the manual text larger or smaller.
- `--no-cover`: start directly with the Markdown content.
- `--logo assets/cgv-logo.png`: place a logo on the cover. If `assets/cgv-logo.png` exists, it is used by default.
- `--cover images/portada.png`: use a full-page cover image, with no margin.
- `--label-color "#111111"`: set the cover manual label color.
- `--label-location lower-quarter`: set the cover manual label position. Options: `top-center`, `center`, `lower-quarter`, `bottom-center`.
- `--logo-location bottom-right`: set the logo badge position. Options: `bottom-right`, `bottom-left`, `top-right`, `top-left`.
- `--logo-background 70%`: set the white logo badge opacity. You can also use `0.7`.
- the interior title page uses the YAML `title`, `subtitle`, and `version`, plus the exported manual type.
- `--single student` or `--single teacher`: export only `Manual del Alumno` or `Manual del Maestro`.
- `--footer-left`, `--footer-center`, `--footer-right`: set footer text.
- `---` on its own line in the Markdown inserts a page break.

Front matter can also set cover metadata:

```yaml
---
book: Tito
title: tito
subtitle: subtítulo
version: 0.2
logo: assets/cgv-logo.png
cover: images/portada.png
label_color: "#111111"
label_location: lower-quarter
logo_location: bottom-right
logo_background: 70%
---
```

## Markdown Supported

- `#` and `##` centered headings; `###` and `####` left-aligned headings
- paragraphs
- `-`, `*`, `+`, and numbered lists. Unordered markers are semantic and render without visible bullet glyphs: `-` starts an indented clause, `*` starts a more deeply indented mechanical observation comment, and `+` starts a more deeply indented human observation comment.
- only H1 headings are included in the table of contents
- `<u>word</u>` marks fill-in answers. In `Manual del Alumno`, the word is removed and replaced with an underlined blank twice as wide. In `Manual del Maestro`, the word is rendered bold and underlined.
- unmarked lines inherit the indentation of the item immediately above them
- blockquotes with `>`
- inline `**bold**`, `*italic*`, and `` `code` ``
- whole scripture quotes written with Spanish or English curly quotes are normalized to Spanish quotes and italic text
