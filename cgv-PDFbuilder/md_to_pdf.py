#!/usr/bin/env python3
"""Export plain Markdown study notes to a polished PDF manual."""

from __future__ import annotations

import argparse
import html
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer


VERSE_HEADING_RE = re.compile(r"^[1-3]?\s?[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s+\d+:\d+")
LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[-*+])\s+(?P<text>.+)$")
NUMBERED_LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>\d+[.)])\s+(?P<text>.+)$")
FONT_DIRS = [
    Path("/Users/johnwry/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
]


@dataclass(frozen=True)
class Theme:
    page_width: float = letter[0]
    page_height: float = letter[1]
    margin_x: float = 0.72 * inch
    margin_top: float = 0.66 * inch
    margin_bottom: float = 0.74 * inch
    body_size: float = 12.2
    leading: float = 16.3
    footer_size: float = 8.8
    title: str = "Manual"
    subtitle: str = ""
    footer_left: str = ""
    footer_center: str = "www.discipuladocgv.org"
    footer_right: str = ""


class PageNumberCanvas:
    """Two-pass canvas that draws page numbers and manual footers."""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.pages = []

    def __call__(self, canvas, doc):
        font_regular, _, _, _ = register_fonts()
        canvas.saveState()
        page_number = canvas.getPageNumber()
        canvas.setFont(font_regular, self.theme.footer_size)
        canvas.setFillColor(colors.HexColor("#222222"))
        canvas.drawCentredString(self.theme.page_width / 2, self.theme.page_height - 0.33 * inch, str(page_number))

        y = 0.42 * inch
        canvas.setFont(font_regular, self.theme.footer_size)
        if self.theme.footer_left:
            canvas.drawString(self.theme.margin_x, y, self.theme.footer_left)
        if self.theme.footer_center:
            canvas.drawCentredString(self.theme.page_width / 2, y, self.theme.footer_center)
        if self.theme.footer_right:
            canvas.drawRightString(self.theme.page_width - self.theme.margin_x, y, self.theme.footer_right)
        canvas.restoreState()


def first_existing_font(names: list[str]) -> str | None:
    for directory in FONT_DIRS:
        for name in names:
            path = directory / name
            if path.exists():
                return os.fspath(path)
    return None


def register_fonts() -> tuple[str, str, str, str]:
    regular = first_existing_font(["DejaVuSans.ttf", "NotoSans-Regular.ttf", "Arial Unicode.ttf"])
    bold = first_existing_font(["DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf", "Arial Unicode.ttf"])
    italic = first_existing_font(["DejaVuSans-Oblique.ttf", "NotoSans-Italic.ttf", "Arial Unicode.ttf"])
    bold_italic = first_existing_font(["DejaVuSans-BoldOblique.ttf", "NotoSans-BoldItalic.ttf", "Arial Unicode.ttf"])

    if not regular:
        return ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique")

    pdfmetrics.registerFont(TTFont("CGVSans", regular))
    pdfmetrics.registerFont(TTFont("CGVSans-Bold", bold or regular))
    pdfmetrics.registerFont(TTFont("CGVSans-Italic", italic or regular))
    pdfmetrics.registerFont(TTFont("CGVSans-BoldItalic", bold_italic or bold or italic or regular))
    pdfmetrics.registerFontFamily(
        "CGVSans",
        normal="CGVSans",
        bold="CGVSans-Bold",
        italic="CGVSans-Italic",
        boldItalic="CGVSans-BoldItalic",
    )
    return ("CGVSans", "CGVSans-Bold", "CGVSans-Italic", "CGVSans-BoldItalic")


def build_styles(theme: Theme) -> dict[str, ParagraphStyle]:
    font_regular, font_bold, _, _ = register_fonts()
    sample = getSampleStyleSheet()
    base = ParagraphStyle(
        "ManualBody",
        parent=sample["BodyText"],
        fontName=font_regular,
        fontSize=theme.body_size,
        leading=theme.leading,
        alignment=TA_LEFT,
        spaceBefore=2,
        spaceAfter=5,
    )

    return {
        "title": ParagraphStyle(
            "Title",
            parent=base,
            fontName=font_bold,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceBefore=2.2 * inch,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base,
            fontSize=15,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=2.8 * inch,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base,
            fontName=font_bold,
            fontSize=18.5,
            leading=23,
            spaceBefore=16,
            spaceAfter=9,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base,
            fontName=font_bold,
            fontSize=16,
            leading=20,
            spaceBefore=13,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base,
            fontName=font_bold,
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "Heading4",
            parent=base,
            fontName=font_bold,
            fontSize=13.2,
            leading=17,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h5": ParagraphStyle(
            "Heading5",
            parent=base,
            fontName=font_bold,
            fontSize=12.8,
            leading=16.8,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "h6": ParagraphStyle(
            "Heading6",
            parent=base,
            fontName=font_bold,
            fontSize=12.4,
            leading=16.4,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": base,
        "verse": ParagraphStyle(
            "Verse",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size + 0.3,
            leading=theme.leading + 1,
            leftIndent=0.18 * inch,
            rightIndent=0.18 * inch,
            spaceBefore=8,
            spaceAfter=8,
            borderColor=colors.HexColor("#d8d8d8"),
            borderWidth=0.5,
            borderPadding=7,
            backColor=colors.HexColor("#fbfbfb"),
        ),
        "bullet": ParagraphStyle(
            "BulletText",
            parent=base,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=1,
            spaceAfter=2,
        ),
    }


def escape_inline(text: str) -> str:
    text = html.escape(text.strip(), quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<i>\1</i>", text)
    return text


def make_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape_inline(text), style)


def flush_paragraph(lines: list[str], story: list[Flowable], styles: dict[str, ParagraphStyle]) -> None:
    if not lines:
        return
    text = " ".join(line.strip() for line in lines if line.strip())
    if not text:
        lines.clear()
        return
    style = styles["verse"] if text.startswith(("“", "«")) and text.endswith(("”", "»")) else styles["body"]
    story.append(make_paragraph(text, style))
    lines.clear()


def append_list(
    items: list[tuple[int, str, bool]],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
) -> None:
    if not items:
        return

    counters: dict[int, int] = {}
    for indent, text, ordered in items:
        left_indent = 0.22 * inch + min(indent, 5) * 0.18 * inch
        style = ParagraphStyle(
            f"BulletIndent{indent}{ordered}",
            parent=styles["bullet"],
            leftIndent=left_indent,
            firstLineIndent=-0.16 * inch,
        )
        if ordered:
            counters[indent] = counters.get(indent, 0) + 1
            bullet = f"{counters[indent]}."
        else:
            bullet = "-"
        story.append(
            Paragraph(
                f"{html.escape(bullet)}&nbsp;&nbsp;{escape_inline(text)}",
                style,
            )
        )
    story.append(Spacer(1, 4))


def parse_markdown(markdown: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    story: list[Flowable] = []
    paragraph_lines: list[str] = []
    list_items: list[tuple[int, str, bool]] = []

    def flush_all() -> None:
        flush_paragraph(paragraph_lines, story, styles)
        append_list(list_items, story, styles)
        list_items.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_all()
            story.append(Spacer(1, 3))
            continue

        if stripped == "---":
            flush_all()
            story.append(PageBreak())
            continue

        list_match = LIST_RE.match(line) or NUMBERED_LIST_RE.match(line)
        if list_match:
            flush_paragraph(paragraph_lines, story, styles)
            indent = len(list_match.group("indent").replace("\t", "    ")) // 2
            marker = list_match.group("marker")
            list_items.append((indent, list_match.group("text"), marker[0].isdigit()))
            continue

        flush_all()

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if text:
                style = styles.get(f"h{min(level, 6)}", styles["h6"])
                heading = make_paragraph(text, style)
                if level <= 2 and story:
                    story.append(Spacer(1, 4))
                story.append(heading)
            continue

        if stripped.startswith(">"):
            quote = stripped.lstrip(">").strip()
            story.append(make_paragraph(quote, styles["verse"]))
            continue

        if VERSE_HEADING_RE.match(stripped):
            story.append(KeepTogether([make_paragraph(stripped, styles["h4"])]))
            continue

        paragraph_lines.append(stripped)

    flush_all()
    return story


def build_pdf(markdown_path: Path, output_path: Path, theme: Theme, no_cover: bool) -> None:
    styles = build_styles(theme)
    text = markdown_path.read_text(encoding="utf-8")
    story: list[Flowable] = []

    if not no_cover:
        story.append(make_paragraph(theme.title, styles["title"]))
        if theme.subtitle:
            story.append(make_paragraph(theme.subtitle, styles["subtitle"]))
        story.append(PageBreak())

    story.extend(parse_markdown(text, styles))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=theme.margin_x,
        rightMargin=theme.margin_x,
        topMargin=theme.margin_top,
        bottomMargin=theme.margin_bottom,
        title=theme.title,
        author="Cultivados en Gracia y Verdad",
    )
    page_canvas = PageNumberCanvas(theme)
    doc.build(story, onFirstPage=page_canvas, onLaterPages=page_canvas)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a plain Markdown file to a letter-sized PDF manual.")
    parser.add_argument("input", type=Path, help="Markdown source file")
    parser.add_argument("-o", "--output", type=Path, help="PDF output path")
    parser.add_argument("--title", default="Manual", help="Cover title and PDF title")
    parser.add_argument("--subtitle", default="", help="Cover subtitle")
    parser.add_argument("--footer-left", default="", help="Footer text at bottom left")
    parser.add_argument("--footer-center", default="www.discipuladocgv.org", help="Footer text at bottom center")
    parser.add_argument("--footer-right", default="", help="Footer text at bottom right")
    parser.add_argument("--body-size", type=float, default=12.2, help="Main text size in points")
    parser.add_argument("--no-cover", action="store_true", help="Start the PDF directly from the Markdown content")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output
    if output_path is None:
        output_path = Path("output/pdf") / f"{input_path.stem}.pdf"
    output_path = output_path.expanduser().resolve()

    theme = Theme(
        body_size=args.body_size,
        leading=args.body_size * 1.34,
        title=args.title,
        subtitle=args.subtitle,
        footer_left=args.footer_left,
        footer_center=args.footer_center,
        footer_right=args.footer_right,
    )
    build_pdf(input_path, output_path, theme, args.no_cover)
    print(os.fspath(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
