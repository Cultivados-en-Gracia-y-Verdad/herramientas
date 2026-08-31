#!/usr/bin/env python3
"""Export CGV study-manual Markdown (new outline format) to letter-sized PDFs."""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from cgv_pdf_content import prepare_pdf_markdown
from cgv_structure import (
    INCH,
    Annotation,
    IndentLadder,
    StructuralIndentError,
    StructuralItem,
    apply_outline_depths,
    scan_structure,
)


VERSE_HEADING_RE = re.compile(r"^[1-3]?\s?[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s+\d+:\d+")
# Only `+` and `-` are structural, and cgv_structure.scan_structure owns them.
# `*` notes and `>` commentary are annotations, never list items.
NUMBERED_LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>\d+[.)])\s+(?P<text>.+)$")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)$")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^(?P<id>[^\]]+)\]:\s*(?P<text>.+)$")
FOOTNOTE_CITE_RE = re.compile(r"\[\^(?P<id>[^\]]+)\]")
SCRIPTURE_BLOCK_RE = re.compile(r"^[ \t]*=[ \t]+(?P<text>.+)$")
HTML_COMMENT_RE = re.compile(r"^<!--.*?-->$")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
FENCE_RE = re.compile(r"^```(?P<lang>[\w-]*)\s*$")
ACTOR_TRIPLE_RE = re.compile(r"[→⇒➡➜⟶⤷↪]")
ACTORS_LINE_RE = re.compile(r"^Actores\b", re.IGNORECASE)
TONO_LINE_RE = re.compile(r"^Tono\b", re.IGNORECASE)
HEBREW_RUN_RE = re.compile(r"([֐-׿יִ-ﭏ]+(?:\s+[֐-׿יִ-ﭏ]+)*)")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
DEFAULT_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "cgv-logo.png"
DEFAULT_MANUAL_PATH = Path(
    "/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/25.1Pedro/slides/manual.md"
)
COVER_LABEL_LOCATIONS = {
    "top-center": (0.5, 0.94),
    "center": (0.5, 0.5),
    "lower-quarter": (0.5, 0.25),
    "bottom-center": (0.5, 0.12),
}
LOGO_LOCATIONS = {
    "bottom-right": (0.88, 0.09),
    "bottom-left": (0.12, 0.09),
    "top-right": (0.88, 0.91),
    "top-left": (0.12, 0.91),
}
FONT_DIRS = [
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
    # Linux fallbacks so the exporter still runs (and can be tested) off macOS.
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/Users/johnwry/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype"),
]
IOWAN_TTC = Path("/System/Library/Fonts/Supplemental/Iowan Old Style.ttc")
ARROW_SYMBOLS_RE = re.compile(r"([→⇒➡➜⟶⤷↩↪↓⤵↧⇣↳])")
MERMAID_NODE_DEF_RE = re.compile(
    r"(?P<id>[A-Za-z][\w-]*)\s*(?:\[\s*\"(?P<quoted>[^\"]+)\"\s*\]|\[(?P<bracket>[^\]]+)\]|\(\s*\"(?P<round_quoted>[^\"]+)\"\s*\)|\((?P<round>[^)]+)\))"
)
MERMAID_EDGE_RE = re.compile(r"(?P<left>[A-Za-z][\w-]*).*?(?:-->|---|==>|\.-\.)\s*(?P<right>[A-Za-z][\w-]*)")

# One indentation formula for the whole document, in exactly one object.
# 2 spaces of source indentation = one structural depth step.
LADDER = IndentLadder()


def configure_ladder(
    *,
    indent_step: float | None = None,
    indent_base: float | None = None,
    annotation_offset: float | None = None,
) -> IndentLadder:
    """Set the document-wide indent ladder. Values are in points."""
    global LADDER
    fields = {
        "step": indent_step,
        "base_x": indent_base,
        "annotation_offset": annotation_offset,
    }
    LADDER = IndentLadder(**{k: v for k, v in fields.items() if v is not None})
    return LADDER


@dataclass(frozen=True)
class Theme:
    page_width: float = letter[0]
    page_height: float = letter[1]
    margin_x: float = 0.80 * inch
    margin_top: float = 0.72 * inch
    margin_bottom: float = 0.82 * inch
    body_size: float = 12.5
    leading: float = 17.0
    footer_size: float = 8.4
    book: str = ""
    title: str = "Manual"
    subtitle: str = ""
    telos: str = ""
    version: str = ""
    footer_left: str = ""
    footer_center: str = "www.discipuladocgv.org"
    footer_right: str = ""
    logo_path: str = ""
    cover_path: str = ""
    manual_type: str = ""
    cover_label_color: str = "#111111"
    cover_label_location: str = "lower-quarter"
    logo_location: str = "bottom-right"
    logo_background_alpha: float = 0.70
    page_offset: int = 0
    cover_enabled: bool = True


@dataclass
class LayoutContext:
    paragraph_left: float = 0
    paragraph_parent: str = "body"


class DownArrow(Flowable):
    """Draw a down arrow instead of relying on a font glyph."""

    def __init__(self, width: float, height: float = 0.24 * inch):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        center_x = self.width / 2
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#3a555c"))
        canvas.setFillColor(colors.HexColor("#3a555c"))
        canvas.setLineWidth(1.0)
        canvas.line(center_x, self.height - 2, center_x, 7)
        arrow = canvas.beginPath()
        arrow.moveTo(center_x - 4, 9)
        arrow.lineTo(center_x, 2)
        arrow.lineTo(center_x + 4, 9)
        arrow.close()
        canvas.drawPath(arrow, stroke=0, fill=1)
        canvas.restoreState()


class PageNumberCanvas:
    """Two-pass canvas that draws page numbers and manual footers."""

    def __init__(self, theme: Theme):
        self.theme = theme

    def __call__(self, canvas, doc):
        font_regular, _, _, _ = register_fonts()
        canvas.saveState()
        page_number = canvas.getPageNumber()
        if self.theme.cover_enabled and page_number == 1:
            self.draw_cover(canvas)
            canvas.restoreState()
            return

        if self.theme.cover_enabled and page_number == 2:
            canvas.restoreState()
            return

        if self.theme.cover_enabled and page_number == 3:
            self.draw_inside_title_page(canvas)
            canvas.restoreState()
            return

        if self.theme.cover_enabled and page_number <= 3:
            canvas.restoreState()
            return

        display_page = page_number + self.theme.page_offset
        canvas.setFont(font_regular, self.theme.footer_size)
        canvas.setFillColor(colors.HexColor("#222222"))
        canvas.drawCentredString(self.theme.page_width / 2, self.theme.page_height - 0.33 * inch, str(display_page))

        y = 0.42 * inch
        canvas.setFont(font_regular, self.theme.footer_size)
        if self.theme.footer_left:
            canvas.drawString(self.theme.margin_x, y, self.theme.footer_left)
        if self.theme.footer_center:
            canvas.drawCentredString(self.theme.page_width / 2, y, self.theme.footer_center)
        if self.theme.footer_right:
            canvas.drawRightString(self.theme.page_width - self.theme.margin_x, y, self.theme.footer_right)
        canvas.restoreState()

    def draw_cover(self, canvas) -> None:
        if self.theme.cover_path and Path(self.theme.cover_path).exists():
            self.draw_full_page_image(canvas, self.theme.cover_path)

        self.draw_manual_label(canvas)
        self.draw_logo_badge(canvas)

    def draw_inside_title_page(self, canvas) -> None:
        font_regular, font_bold, font_italic, _ = register_fonts()
        page_width = self.theme.page_width
        page_height = self.theme.page_height

        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)

        if self.theme.logo_path and Path(self.theme.logo_path).exists():
            logo_width = 1.48 * inch
            logo_height = 1.48 * inch
            canvas.drawImage(
                self.theme.logo_path,
                (page_width - logo_width) / 2,
                page_height - 2.92 * inch,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask="auto",
            )

        text_width = page_width - 1.75 * inch
        text_x = (page_width - text_width) / 2
        current_y = page_height - 3.48 * inch

        if self.theme.book:
            book_style = ParagraphStyle(
                "InsideTitlePageBook",
                fontName=font_bold,
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#6a635a"),
            )
            book = Paragraph(escape_inline(self.theme.book.upper()), book_style)
            _, book_height = book.wrap(text_width, 0.5 * inch)
            book.drawOn(canvas, text_x, current_y - book_height)
            current_y -= book_height + 0.18 * inch

        title_style = ParagraphStyle(
            "InsideTitlePageTitle",
            fontName=font_bold,
            fontSize=35,
            leading=40,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#080808"),
        )
        title = Paragraph(escape_inline(self.theme.title), title_style)
        _, title_height = title.wrap(text_width, 1.3 * inch)
        title.drawOn(canvas, text_x, current_y - title_height)
        current_y -= title_height + 0.18 * inch

        if self.theme.subtitle:
            subtitle_style = ParagraphStyle(
                "InsideTitlePageSubtitle",
                fontName=font_regular,
                fontSize=21,
                leading=26,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#080808"),
            )
            subtitle = Paragraph(escape_inline(self.theme.subtitle), subtitle_style)
            _, subtitle_height = subtitle.wrap(text_width, 0.9 * inch)
            subtitle.drawOn(canvas, text_x, current_y - subtitle_height)
            current_y -= subtitle_height + 0.16 * inch

        if self.theme.version:
            canvas.setFont(font_regular, 14)
            canvas.setFillColor(colors.HexColor("#444444"))
            canvas.drawCentredString(page_width / 2, current_y - 0.08 * inch, f"Versión {self.theme.version}")
            current_y -= 0.42 * inch

        if self.theme.telos:
            telos_style = ParagraphStyle(
                "InsideTitlePageTelos",
                fontName=font_italic,
                fontSize=11.5,
                leading=15.5,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#3a342c"),
            )
            telos = Paragraph(escape_inline(self.theme.telos), telos_style)
            _, telos_height = telos.wrap(text_width, 1.6 * inch)
            telos.drawOn(canvas, text_x, current_y - telos_height)

        if self.theme.manual_type:
            canvas.setFillColor(colors.HexColor("#080808"))
            canvas.setFont(font_bold, 24)
            canvas.drawCentredString(page_width / 2, 1.45 * inch, self.theme.manual_type)

        canvas.restoreState()

    def draw_full_page_image(self, canvas, image_path: str) -> None:
        image = ImageReader(image_path)
        image_width, image_height = image.getSize()
        page_width = self.theme.page_width
        page_height = self.theme.page_height
        scale = max(page_width / image_width, page_height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2

        canvas.saveState()
        clip = canvas.beginPath()
        clip.rect(0, 0, page_width, page_height)
        canvas.clipPath(clip, stroke=0, fill=0)
        canvas.drawImage(image, x, y, width=draw_width, height=draw_height, mask="auto")
        canvas.restoreState()

    def draw_manual_label(self, canvas) -> None:
        if not self.theme.manual_type:
            return

        _, font_bold, _, _ = register_fonts()
        x_factor, y_factor = COVER_LABEL_LOCATIONS.get(
            self.theme.cover_label_location,
            COVER_LABEL_LOCATIONS["lower-quarter"],
        )
        x = self.theme.page_width * x_factor
        y = self.theme.page_height * y_factor

        canvas.saveState()
        canvas.setFillColor(colors.HexColor(self.theme.cover_label_color))
        canvas.setFont(font_bold, 22)
        canvas.drawCentredString(x, y, self.theme.manual_type)
        canvas.restoreState()

    def draw_logo_badge(self, canvas) -> None:
        if not self.theme.logo_path or not Path(self.theme.logo_path).exists():
            return

        radius = 0.48 * inch
        x_factor, y_factor = LOGO_LOCATIONS.get(self.theme.logo_location, LOGO_LOCATIONS["bottom-right"])
        center_x = self.theme.page_width * x_factor
        center_y = self.theme.page_height * y_factor

        canvas.saveState()
        try:
            canvas.setFillAlpha(self.theme.logo_background_alpha)
        except AttributeError:
            pass
        canvas.setFillColor(colors.white)
        canvas.circle(center_x, center_y, radius, stroke=0, fill=1)
        try:
            canvas.setFillAlpha(1)
        except AttributeError:
            pass
        logo_size = 0.64 * inch
        canvas.drawImage(
            self.theme.logo_path,
            center_x - logo_size / 2,
            center_y - logo_size / 2,
            width=logo_size,
            height=logo_size,
            mask="auto",
        )
        canvas.restoreState()


def first_existing_font(names: list[str]) -> str | None:
    for directory in FONT_DIRS:
        for name in names:
            path = directory / name
            if path.exists():
                return os.fspath(path)
    return None


def register_fonts() -> tuple[str, str, str, str]:
    """Prefer Iowan Old Style (CGV reader face), then Georgia, then DejaVu."""
    if IOWAN_TTC.exists():
        pdfmetrics.registerFont(TTFont("CGVSerif", os.fspath(IOWAN_TTC), subfontIndex=0))
        pdfmetrics.registerFont(TTFont("CGVSerif-Bold", os.fspath(IOWAN_TTC), subfontIndex=1))
        pdfmetrics.registerFont(TTFont("CGVSerif-Italic", os.fspath(IOWAN_TTC), subfontIndex=2))
        pdfmetrics.registerFont(TTFont("CGVSerif-BoldItalic", os.fspath(IOWAN_TTC), subfontIndex=3))
    else:
        regular = first_existing_font(["Georgia.ttf", "DejaVuSerif.ttf"])
        bold = first_existing_font(["Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"])
        italic = first_existing_font(["Georgia Italic.ttf", "DejaVuSerif-Italic.ttf"])
        bold_italic = first_existing_font(["Georgia Bold Italic.ttf", "DejaVuSerif-BoldItalic.ttf"])
        if not regular:
            return ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique")
        pdfmetrics.registerFont(TTFont("CGVSerif", regular))
        pdfmetrics.registerFont(TTFont("CGVSerif-Bold", bold or regular))
        pdfmetrics.registerFont(TTFont("CGVSerif-Italic", italic or regular))
        pdfmetrics.registerFont(TTFont("CGVSerif-BoldItalic", bold_italic or bold or italic or regular))

    pdfmetrics.registerFontFamily(
        "CGVSerif",
        normal="CGVSerif",
        bold="CGVSerif-Bold",
        italic="CGVSerif-Italic",
        boldItalic="CGVSerif-BoldItalic",
    )
    symbol_candidates = [
        # DejaVu reliably contains every outline arrow. SFNS can register while
        # still drawing a missing-glyph box for the ↳ annotation marker.
        Path(
            "/Users/johnwry/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype/DejaVuSans.ttf"
        ),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Apple Symbols.ttf"),
        Path("/System/Library/Fonts/SFNS.ttf"),
        Path("/System/Library/Fonts/SFNSMono.ttf"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]
    for symbol_font in symbol_candidates:
        if not symbol_font.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("CGVSymbols", os.fspath(symbol_font)))
            break
        except TTFError:
            continue

    hebrew_candidates = [
        Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]
    for heb_font in hebrew_candidates:
        if not heb_font.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("CGVHebrew", os.fspath(heb_font)))
            break
        except TTFError:
            continue

    return ("CGVSerif", "CGVSerif-Bold", "CGVSerif-Italic", "CGVSerif-BoldItalic")


def build_styles(theme: Theme) -> dict[str, ParagraphStyle]:
    font_regular, font_bold, font_italic, font_bold_italic = register_fonts()
    sample = getSampleStyleSheet()
    ink = colors.HexColor("#1a1713")
    muted = colors.HexColor("#6a635a")
    soft = colors.HexColor("#857c70")
    accent = colors.HexColor("#3a555c")

    base = ParagraphStyle(
        "ManualBody",
        parent=sample["BodyText"],
        fontName=font_regular,
        fontSize=theme.body_size,
        leading=theme.leading,
        alignment=TA_LEFT,
        textColor=ink,
        spaceBefore=2,
        spaceAfter=4,
    )

    return {
        "title": ParagraphStyle(
            "Title",
            parent=base,
            fontName=font_bold,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceBefore=0.2 * inch,
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
        # H1 — major movement
        "h1": ParagraphStyle(
            "Heading1",
            parent=base,
            fontName=font_bold,
            fontSize=17.0,
            leading=22,
            alignment=TA_CENTER,
            spaceBefore=22,
            spaceAfter=12,
            keepWithNext=True,
        ),
        # H2 — development navigation: top and small
        "h2": ParagraphStyle(
            "Heading2",
            parent=base,
            fontName=font_bold,
            fontSize=14.5,
            leading=18.5,
            alignment=TA_CENTER,
            textColor=muted,
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True,
        ),
        # H3 — section context title (parent of H4)
        "h3": ParagraphStyle(
            "Heading3",
            parent=base,
            fontName=font_bold,
            fontSize=15.5,
            leading=20,
            leftIndent=0,
            spaceBefore=20,
            spaceAfter=9,
            keepWithNext=True,
        ),
        "h3_sintesis": ParagraphStyle(
            "Heading3Sintesis",
            parent=base,
            fontName=font_bold,
            fontSize=16.2,
            leading=20.5,
            textColor=accent,
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True,
        ),
        # H4 — independent clause (Scripture root), child of H3.
        # Deliberate design: H4 keeps its own typography (bold italic, one step
        # larger) AND sits one small step right of H3, so the parent/child
        # relation reads even when an H4 follows an H3 immediately. Structural
        # items then start one further step right, at LADDER.base_x.
        "h4": ParagraphStyle(
            "Heading4",
            parent=base,
            fontName=font_bold_italic,
            fontSize=theme.body_size + 0.8,
            leading=theme.leading + 1.5,
            leftIndent=LADDER.heading_child_indent,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h5": ParagraphStyle(
            "Heading5",
            parent=base,
            fontName=font_bold,
            fontSize=13.5,
            leading=17.5,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h6": ParagraphStyle(
            "Heading6",
            parent=base,
            fontName=font_bold,
            fontSize=13.0,
            leading=17,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": base,
        "writer": ParagraphStyle(
            "WriterComment",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size - 0.2,
            leading=theme.leading - 0.5,
            textColor=colors.HexColor("#2a2620"),
            spaceBefore=2,
            spaceAfter=4,
        ),
        "scripture_phrase": ParagraphStyle(
            "ScripturePhrase",
            parent=base,
            fontName=font_italic,
            fontSize=theme.body_size + 0.2,
            leading=theme.leading + 0.4,
            spaceBefore=4,
            spaceAfter=3,
        ),
        "scripture_block": ParagraphStyle(
            "ScriptureBlock",
            parent=base,
            fontName=font_italic,
            fontSize=theme.body_size + 0.1,
            leading=theme.leading + 0.8,
            leftIndent=0.18 * inch,
            rightIndent=0.12 * inch,
            spaceBefore=5,
            spaceAfter=5,
        ),
        "dependent_clause": ParagraphStyle(
            "DependentClause",
            parent=base,
            fontName=font_italic,
            fontSize=theme.body_size + 0.2,
            leading=theme.leading + 0.4,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "mechanical": ParagraphStyle(
            "MechanicalNote",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size - 1.6,
            leading=theme.leading - 2.2,
            textColor=soft,
            spaceBefore=2,
            spaceAfter=3,
        ),
        "actor_triple": ParagraphStyle(
            "ActorTriple",
            parent=base,
            fontName=font_bold,
            fontSize=theme.body_size - 0.2,
            leading=theme.leading - 0.2,
            textColor=accent,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "actors_line": ParagraphStyle(
            "ActorsLine",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size - 1.8,
            leading=theme.leading - 2.4,
            textColor=muted,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "footnote_def": ParagraphStyle(
            "FootnoteDef",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size - 1.8,
            leading=theme.leading - 2.4,
            leftIndent=0.22 * inch,
            firstLineIndent=-0.22 * inch,
            textColor=colors.HexColor("#2e2a24"),
            spaceBefore=3,
            spaceAfter=4,
        ),
        "sintesis_body": ParagraphStyle(
            "SintesisBody",
            parent=base,
            fontName=font_regular,
            fontSize=theme.body_size,
            leading=theme.leading,
            textColor=colors.HexColor("#2a2620"),
            spaceBefore=1,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "BulletText",
            parent=base,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=2,
            spaceAfter=3,
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


def footnote_cite_html(footnote_id: str) -> str:
    label = html.escape(footnote_id, quote=False)
    return f"<super><font size='7' color='#5c564e'>{label}</font></super>"


def answer_tag_html(match: re.Match[str], variant: str) -> str:
    answer = html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
    if variant == "student":
        width = max(10, round(len(answer) * 2.6))
        return "<u>" + ("&nbsp;" * width) + "</u>"
    return f"<b><u>{render_arrow_symbols(escape_inline(answer))}</u></b>"


def protect_answer_tags(text: str, variant: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        key = f"@@ANSWER{len(replacements)}@@"
        replacements[key] = answer_tag_html(match, variant)
        return key

    protected = re.sub(r"<u>(.*?)</u>", replace, text, flags=re.IGNORECASE | re.DOTALL)
    return protected, replacements


def restore_protected(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def strip_outer_italics(text: str) -> str:
    """Outline Scripture is already italic via style; unwrap a single outer *…*."""
    match = re.fullmatch(r"\*(.+)\*", text.strip(), flags=re.DOTALL)
    if match and match.group(1).count("*") == 0:
        return match.group(1).strip()
    return text.strip()


def protect_footnote_cites(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        key = f"@@FOOTNOTE{len(replacements)}@@"
        replacements[key] = footnote_cite_html(match.group("id"))
        return key

    return FOOTNOTE_CITE_RE.sub(replace, text), replacements


def normalize_outline_symbols(text: str) -> str:
    """Normalize HTML line breaks before inline Markdown rendering."""
    text = BR_RE.sub(" ", text)
    return re.sub(r" {2,}", " ", text)


def render_arrow_symbols(text: str) -> str:
    """Keep source arrows visible by using a font that has those glyphs."""
    try:
        pdfmetrics.getFont("CGVSymbols")
    except KeyError:
        return text

    def replace(match: re.Match[str]) -> str:
        return f"<font name='CGVSymbols'>{match.group(1)}</font>"

    return ARROW_SYMBOLS_RE.sub(replace, text)


def render_hebrew(text: str) -> str:
    """Wrap Hebrew character runs in a font that has Hebrew glyphs."""
    try:
        pdfmetrics.getFont("CGVHebrew")
    except KeyError:
        return text
    return HEBREW_RUN_RE.sub(lambda m: f"<font name='CGVHebrew'>{m.group(1)}</font>", text)


def format_inline(text: str, variant: str = "teacher", *, scripture_style: bool = False) -> str:
    """Format inline Markdown. Scripture stays italic-only — never wrapped in «…»."""
    stripped = normalize_outline_symbols(text.strip())
    if scripture_style:
        stripped = strip_outer_italics(stripped)
    protected, answer_replacements = protect_answer_tags(stripped, variant)
    protected, footnote_replacements = protect_footnote_cites(protected)
    rendered = escape_inline(protected)
    rendered = render_arrow_symbols(rendered)
    rendered = render_hebrew(rendered)
    rendered = restore_protected(rendered, answer_replacements)
    return restore_protected(rendered, footnote_replacements)


def parse_front_matter(markdown: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(markdown)
    if not match:
        return {}, markdown

    metadata: dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        clean_value = value.strip().strip('"').strip("'")
        metadata[key.strip().lower()] = clean_value
    return metadata, markdown[match.end() :]


def resolve_asset_path(value: str, source_path: Path) -> str:
    """Resolve a cover/logo path next to the Markdown file, then parent folders."""
    if not value:
        return ""
    path = Path(value).expanduser()
    if path.is_absolute():
        return os.fspath(path.resolve()) if path.exists() else os.fspath(path)

    candidates = [
        source_path.parent / path,
        source_path.parent.parent / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return os.fspath(candidate.resolve())
    return os.fspath((source_path.parent / path).resolve())


def resolve_markdown_image_path(value: str, source_path: Path | None) -> Path:
    clean = value.strip().strip('"').strip("'")
    path = Path(clean).expanduser()
    if not path.is_absolute() and source_path:
        path = source_path.parent / path
    return path.resolve()


def parse_opacity(value: str | float | None, default: float = 0.70) -> float:
    if value is None:
        return default
    if isinstance(value, (float, int)):
        return max(0, min(1, float(value)))
    raw = str(value).strip()
    try:
        if raw.endswith("%"):
            return max(0, min(1, float(raw[:-1]) / 100))
        return max(0, min(1, float(raw)))
    except ValueError:
        return default


def make_paragraph(text: str, style: ParagraphStyle, variant: str = "teacher", *, scripture_style: bool = False) -> Paragraph:
    return Paragraph(format_inline(text, variant, scripture_style=scripture_style), style)


def make_markdown_image(image_path: Path, max_width: float, max_height: float = 3.35 * inch) -> Image:
    image = ImageReader(os.fspath(image_path))
    image_width, image_height = image.getSize()
    scale = min(max_width / image_width, max_height / image_height, 1)
    flowable = Image(os.fspath(image_path), width=image_width * scale, height=image_height * scale)
    flowable.hAlign = "CENTER"
    return flowable


def append_markdown_image(
    image_match: re.Match[str],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    source_path: Path | None,
    variant: str,
    left_indent: float = 0,
) -> None:
    image_path = resolve_markdown_image_path(image_match.group("path"), source_path)
    if not image_path.exists():
        alt = image_match.group("alt") or image_match.group("path")
        missing_style = ParagraphStyle(
            f"MissingImage{int(left_indent)}",
            parent=styles["body"],
            leftIndent=left_indent,
            textColor=colors.HexColor("#8a1f11"),
        )
        story.append(make_paragraph(f"Imagen no encontrada: {alt}", missing_style, variant))
        return

    story.append(Spacer(1, 6))
    max_width = max(2.2 * inch, (letter[0] - 2 * Theme.margin_x) - left_indent)
    story.append(make_markdown_image(image_path, max_width))
    story.append(Spacer(1, 8))


def strip_diagram_arrow_token(text: str) -> bool:
    clean = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
    return bool(re.fullmatch(r"[↓⤵↧⇣vV]+", clean))


def append_box_diagram(
    boxes: list[str],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
    left_indent: float,
) -> bool:
    if len(boxes) < 2:
        return False

    max_width = max(2.6 * inch, min(4.9 * inch, (letter[0] - 2 * Theme.margin_x) - left_indent))
    box_style = ParagraphStyle(
        f"DiagramBox{int(left_indent * 100)}",
        parent=styles["writer"],
        alignment=TA_CENTER,
        fontSize=styles["writer"].fontSize,
        leading=styles["writer"].leading,
        spaceBefore=0,
        spaceAfter=0,
    )

    flowables: list[Flowable] = []
    for index, box_text in enumerate(boxes):
        table = Table(
            [[Paragraph(format_inline(box_text, variant), box_style)]],
            colWidths=[max_width],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#3a555c")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f8f5")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        flowables.append(table)
        if index < len(boxes) - 1:
            flowables.append(DownArrow(max_width))

    story.append(Spacer(1, 4))
    story.append(KeepTogether(flowables))
    story.append(Spacer(1, 5))
    return True


def append_break_diagram(
    raw_text: str,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
    left_indent: float,
) -> bool:
    if not BR_RE.search(raw_text):
        return False

    parts = [part.strip() for part in BR_RE.split(raw_text) if part.strip()]
    boxes = [part for part in parts if not strip_diagram_arrow_token(part)]
    return append_box_diagram(boxes, story, styles, variant, left_indent)


def clean_mermaid_label(text: str) -> str:
    clean = BR_RE.sub(" ", text.strip())
    clean = clean.strip().strip('"').strip("'")
    return re.sub(r"\s+", " ", clean)


def parse_mermaid_boxes(code: str) -> list[str]:
    labels: dict[str, str] = {}
    order: list[str] = []
    outgoing: dict[str, str] = {}
    incoming: set[str] = set()

    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%") or line.lower().startswith(("flowchart", "graph")):
            continue
        for match in MERMAID_NODE_DEF_RE.finditer(line):
            node_id = match.group("id")
            label = next(
                value
                for value in [
                    match.group("quoted"),
                    match.group("bracket"),
                    match.group("round_quoted"),
                    match.group("round"),
                    node_id,
                ]
                if value
            )
            if node_id not in labels:
                order.append(node_id)
            labels[node_id] = clean_mermaid_label(label)
        edge = MERMAID_EDGE_RE.search(line)
        if edge:
            left = edge.group("left")
            right = edge.group("right")
            outgoing.setdefault(left, right)
            incoming.add(right)
            if left not in labels:
                labels[left] = left
                order.append(left)
            if right not in labels:
                labels[right] = right
                order.append(right)

    if not labels:
        return []
    starts = [node_id for node_id in order if node_id not in incoming]
    current = starts[0] if starts else order[0]
    chain: list[str] = []
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        chain.append(labels[current])
        current = outgoing.get(current, "")
    for node_id in order:
        if node_id not in seen:
            chain.append(labels[node_id])
    return chain


def append_mermaid_diagram(
    code: str,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
    left_indent: float = 0,
) -> bool:
    return append_box_diagram(parse_mermaid_boxes(code), story, styles, variant, left_indent)


def outline_left(depth: int) -> float:
    """Left edge of a structural item at ``depth``.

    The single call point for the indentation formula
    ``item_x = base_x + depth * indent_step``. Marker type is not an input.
    """
    return LADDER.item_x(depth)


def annotation_left(owner_depth: int) -> float:
    """Left edge of a ``*`` note or ``>`` comment owned by an item at ``owner_depth``."""
    return LADDER.annotation_x(owner_depth)


GREEK_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
HANGER_RE = re.compile(r"^↳")


def classify_outline_line(marker: str, text: str) -> str:
    """Role from content first - manuals sometimes overload `-` across roles.

    This decides *typography*, never depth.
    """
    clean = text.strip()
    if ACTORS_LINE_RE.match(clean) or TONO_LINE_RE.match(clean):
        return "actors_line"
    if ACTOR_TRIPLE_RE.search(clean):
        return "actor_triple"
    if HANGER_RE.match(clean) or clean.startswith("↳"):
        return "mechanical"
    if FOOTNOTE_CITE_RE.search(clean) and (GREEK_RE.search(clean) or len(clean) < 90):
        return "mechanical"
    if marker == "*":
        return "mechanical"
    if marker == "+":
        return "scripture_phrase"
    # `-` Scripture outline (phrase or dependent clause)
    if clean.startswith("*") or re.fullmatch(r"\*.+\*", clean, flags=re.DOTALL):
        return "dependent_clause" if marker == "-" else "scripture_phrase"
    if marker == "-":
        return "dependent_clause"
    return "mechanical"


@dataclass
class RenderNode:
    """One laid-out outline line: its role and the x the layout model gave it."""

    role: str  # "item" | "grammar" | "commentary" | "numbered"
    marker: str
    text: str
    left: float
    depth: int
    group_id: int
    #: a blank source line stood between this node and the one before it
    blank_before: bool = False


def indent_style(name: str, parent: ParagraphStyle, left: float, **kwargs) -> ParagraphStyle:
    """Build a style whose x comes from the layout model and nowhere else.

    ``firstLineIndent=0`` is what makes a wrapped line hang under the item's own
    text instead of falling back to the page margin or faking a deeper level.
    """
    key = f"{name}{int(round(left * 100))}"
    return ParagraphStyle(key, parent=parent, leftIndent=left, firstLineIndent=0, **kwargs)


def append_outline_node(
    node: RenderNode,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
) -> LayoutContext:
    left = node.left

    if node.role == "numbered":
        style = indent_style("Numbered", styles["bullet"], left)
        style.firstLineIndent = -0.16 * inch
        story.append(Paragraph(format_inline(node.text, variant), style))
        return LayoutContext(left, "body")

    if node.role == "commentary":
        style = indent_style("Writer", styles["writer"], left, spaceBefore=2, spaceAfter=4)
        story.append(make_paragraph(node.text, style, variant))
        return LayoutContext(left, "writer")

    kind = classify_outline_line(node.marker, node.text)

    if kind in {"scripture_phrase", "dependent_clause"}:
        style = indent_style(kind, styles[kind], left)
        story.append(make_paragraph(node.text, style, variant, scripture_style=True))
        return LayoutContext(left, "scripture")

    if kind == "actor_triple":
        style = indent_style("ActorTriple", styles["actor_triple"], left)
        story.append(make_paragraph(node.text, style, variant, scripture_style=True))
        return LayoutContext(left, "actor_triple")

    if kind == "actors_line":
        style = indent_style("ActorsLine", styles["actors_line"], left)
        story.append(make_paragraph(node.text, style, variant))
        return LayoutContext(left, "actors_line")

    style = indent_style("Mechanical", styles["mechanical"], left)
    story.append(make_paragraph(node.text, style, variant))
    return LayoutContext(left, "mechanical")


#: Biggest item+annotations block still kept unbroken across a page boundary.
#: Larger groups are split, but the item always keeps its first annotation so a
#: line never ends up stranded at the foot of a page without its own commentary.
MAX_KEEP_TOGETHER = 7


def append_outline_group(
    nodes: list[RenderNode],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
) -> LayoutContext | None:
    """Render buffered nodes, keeping each item together with its own annotations."""
    if not nodes:
        return None

    last: LayoutContext | None = None
    block: list[Flowable] = []
    current_group: int | None = None

    def flush_block() -> None:
        nonlocal block
        if not block:
            return
        if len(block) == 1:
            story.extend(block)
        elif len(block) <= MAX_KEEP_TOGETHER:
            story.append(KeepTogether(block))
        else:
            story.append(KeepTogether(block[:2]))
            story.extend(block[2:])
        block = []

    for node in nodes:
        if node.group_id != current_group:
            flush_block()
            current_group = node.group_id
            if node.blank_before:
                story.append(Spacer(1, 3))
        elif node.blank_before:
            # Air inside a group, but still inside the same unbreakable block:
            # a blank line in the source must not strand an item from its notes.
            block.append(Spacer(1, 3))
        last = append_outline_node(node, block, styles, variant)
    flush_block()
    return last


def flush_paragraph(
    lines: list[str],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    context: LayoutContext,
    variant: str,
    *,
    in_sintesis: bool = False,
) -> None:
    """Unmarked prose inherits the position of the line it follows."""
    if not lines:
        return
    text = " ".join(line.strip() for line in lines if line.strip())
    if not text:
        lines.clear()
        return

    if in_sintesis:
        parent = styles["sintesis_body"]
    elif context.paragraph_parent in {"scripture", "actor_triple"}:
        parent = styles["writer"]
    else:
        parent = styles["body"]

    left = context.paragraph_left if context.paragraph_parent != "body" else 0
    style = ParagraphStyle(
        f"ContextPara{context.paragraph_parent}{int(round(left * 100))}{int(in_sintesis)}",
        parent=parent,
        leftIndent=left,
        firstLineIndent=0,
        spaceBefore=1 if in_sintesis else 2,
        spaceAfter=4 if in_sintesis else 5,
    )
    story.append(make_paragraph(text, style, variant))
    lines.clear()


def heading_style_key(level: int, text: str) -> str:
    if level == 3 and text.strip().lower() == "en síntesis":
        return "h3_sintesis"
    if level == 4:
        return "h4"
    return f"h{min(level, 6)}"


def parse_markdown(
    markdown: str,
    styles: dict[str, ParagraphStyle],
    variant: str = "teacher",
    source_path: Path | None = None,
    *,
    line_offset: int = 0,
    indent_strict: bool = True,
    outline_text: str | None = None,
    outline_filename: str = "<outline>",
) -> list[Flowable]:
    """Render Markdown, taking every outline x from the structural layout model."""
    filename = source_path.name if source_path else "<manual>"
    index = scan_structure(markdown, filename, line_offset=line_offset, strict=indent_strict)
    if outline_text:
        apply_outline_depths(
            index,
            markdown,
            outline_text,
            source_line_offset=line_offset,
            outline_filename=outline_filename,
        )
    for problem in index.problems:
        print(f"warning: {problem.message}", file=sys.stderr)

    story: list[Flowable] = []
    paragraph_lines: list[str] = []
    nodes: list[RenderNode] = []
    context = LayoutContext()
    in_sintesis = False
    pending_blank = False
    code_lang: str | None = None
    code_lines: list[str] = []
    extra_group = 0
    pending_gap = False

    def next_extra_group() -> int:
        nonlocal extra_group
        extra_group -= 1
        return extra_group

    def flush_nodes() -> None:
        nonlocal context, pending_gap
        node_context = append_outline_group(nodes, story, styles, variant)
        if node_context:
            context = node_context
        nodes.clear()
        if pending_gap:
            story.append(Spacer(1, 3))
            pending_gap = False

    def take_gap() -> bool:
        nonlocal pending_gap
        gap, pending_gap = pending_gap, False
        return gap

    def flush_all() -> None:
        flush_paragraph(paragraph_lines, story, styles, context, variant, in_sintesis=in_sintesis)
        flush_nodes()

    for offset, raw in enumerate(markdown.splitlines(), 1):
        line_no = offset + line_offset
        line = raw.rstrip()
        stripped = line.strip()
        fence_match = FENCE_RE.match(stripped)

        if code_lang is not None:
            if fence_match:
                if code_lang == "mermaid":
                    append_mermaid_diagram("\n".join(code_lines), story, styles, variant)
                code_lang = None
                code_lines.clear()
            else:
                code_lines.append(line)
            continue

        if fence_match:
            flush_all()
            code_lang = fence_match.group("lang").lower()
            code_lines.clear()
            continue

        if not stripped:
            # Blank lines are slide breaks in the source; give the page a little
            # air. While outline nodes are buffered the gap is remembered rather
            # than flushed, so an item keeps its own notes across a page break.
            flush_paragraph(paragraph_lines, story, styles, context, variant, in_sintesis=in_sintesis)
            if nodes:
                pending_gap = True
            elif not pending_blank:
                story.append(Spacer(1, 3))
                pending_blank = True
            continue

        pending_blank = False

        if HTML_COMMENT_RE.match(stripped):
            flush_all()
            continue

        if stripped.startswith("\\begin{") or stripped.startswith("\\end{"):
            flush_all()
            continue

        if "page-break-after" in stripped:
            flush_all()
            story.append(PageBreak())
            continue

        if stripped == "---":
            flush_all()
            story.append(PageBreak())
            continue

        footnote_def = FOOTNOTE_DEF_RE.match(stripped)
        if footnote_def:
            flush_all()
            fid = footnote_def.group("id")
            body = footnote_def.group("text")
            label = html.escape(fid, quote=False)
            content = format_inline(body, variant)
            story.append(
                Paragraph(
                    f"<b><font color='#3a555c'>{label}</font></b>&nbsp;&nbsp;{content}",
                    styles["footnote_def"],
                )
            )
            context = LayoutContext()
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            flush_all()
            append_markdown_image(image_match, story, styles, source_path, variant)
            continue

        scripture_block = SCRIPTURE_BLOCK_RE.match(line)
        if scripture_block:
            flush_all()
            story.append(
                make_paragraph(
                    scripture_block.group("text"),
                    styles["scripture_block"],
                    variant,
                    scripture_style=True,
                )
            )
            context = LayoutContext(0, "scripture")
            in_sintesis = False
            continue

        node = index.by_line.get(line_no)

        # Structural outline line: depth already decided by source indentation.
        if isinstance(node, StructuralItem):
            in_sintesis = False
            flush_paragraph(paragraph_lines, story, styles, context, variant, in_sintesis=False)
            nodes.append(
                RenderNode(
                    role="item",
                    marker=node.marker,
                    text=node.content,
                    left=outline_left(node.depth),
                    depth=node.depth,
                    group_id=node.group_id,
                    blank_before=take_gap(),
                )
            )
            continue

        # Annotation: hangs off its owning item, never advances the ladder.
        if isinstance(node, Annotation):
            left = annotation_left(node.owner_depth)
            if node.marker == ">":
                quote = node.content
                quote_image = IMAGE_RE.match(quote)
                if quote_image:
                    flush_all()
                    append_markdown_image(quote_image, story, styles, source_path, variant, left)
                    context = LayoutContext(left, "writer")
                    continue
                if quote.lower() == "en síntesis":
                    flush_all()
                    story.append(make_paragraph("En síntesis", styles["h3_sintesis"], variant))
                    context = LayoutContext()
                    in_sintesis = True
                    continue
                if BR_RE.search(quote):
                    flush_all()
                    if append_break_diagram(quote, story, styles, variant, left):
                        context = LayoutContext(left, "writer")
                        in_sintesis = False
                        continue
                if not quote:
                    continue
            in_sintesis = False
            flush_paragraph(paragraph_lines, story, styles, context, variant, in_sintesis=False)
            nodes.append(
                RenderNode(
                    role="commentary" if node.marker == ">" else "grammar",
                    marker=node.marker,
                    text=node.content,
                    left=left,
                    depth=node.owner_depth,
                    group_id=node.group_id,
                    blank_before=take_gap(),
                )
            )
            continue

        numbered = NUMBERED_LIST_RE.match(line)
        if numbered:
            in_sintesis = False
            flush_paragraph(paragraph_lines, story, styles, context, variant, in_sintesis=False)
            depth = len(numbered.group("indent").replace("\t", "  ")) // 2
            nodes.append(
                RenderNode(
                    role="numbered",
                    marker=numbered.group("marker"),
                    text=numbered.group("text"),
                    left=outline_left(depth),
                    depth=depth,
                    group_id=next_extra_group(),
                    blank_before=take_gap(),
                )
            )
            continue

        flush_all()

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if text:
                key = heading_style_key(level, text)
                style = styles.get(key, styles["h6"])
                is_scripture_heading = level == 4
                heading = make_paragraph(text, style, variant, scripture_style=is_scripture_heading)
                if level <= 2 and story:
                    story.append(Spacer(1, 5))
                story.append(heading)
                context = LayoutContext()
                in_sintesis = key == "h3_sintesis"
                # Heading styles already provide spaceAfter. Suppress a source
                # blank line here so keepWithNext reaches the first real block
                # instead of stopping at a Spacer and orphaning the heading.
                pending_blank = True
            continue

        if VERSE_HEADING_RE.match(stripped):
            story.append(KeepTogether([make_paragraph(stripped, styles["h4"], variant)]))
            context = LayoutContext()
            in_sintesis = False
            pending_blank = True
            continue

        paragraph_lines.append(stripped)

    if code_lang == "mermaid":
        append_mermaid_diagram("\n".join(code_lines), story, styles, variant)
    flush_all()
    return story


def toc_entries(markdown: str) -> list[str]:
    entries: list[str] = []
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:].strip()
            text = re.sub(r"\s+—\s+\*.*\*$", "", text).strip()
            text = re.sub(r"\*([^*]+)\*", r"\1", text)
            text = re.sub(r"<u>(.*?)</u>", r"\1", text, flags=re.IGNORECASE)
            entries.append(text)
    return entries


def append_cover(story: list[Flowable], styles: dict[str, ParagraphStyle], theme: Theme) -> None:
    story.append(PageBreak())
    story.append(PageBreak())
    story.append(PageBreak())


def append_toc(story: list[Flowable], styles: dict[str, ParagraphStyle], entries: list[str]) -> None:
    story.append(make_paragraph("Índice", styles["h1"]))
    story.append(Spacer(1, 0.15 * inch))
    toc_style = ParagraphStyle(
        "TocEntry",
        parent=styles["body"],
        leftIndent=0.2 * inch,
        firstLineIndent=0,
        spaceBefore=2,
        spaceAfter=3,
    )
    for entry in entries:
        story.append(Paragraph(escape_inline(entry), toc_style))
    story.append(PageBreak())


def read_body(path: Path) -> str:
    if not path.exists():
        return ""
    _, body = parse_front_matter(path.read_text(encoding="utf-8"))
    # Blank the line instead of dropping it so reported line numbers stay true.
    return "\n".join("" if "page-break-after" in line else line for line in body.splitlines())


def discover_outline_path(markdown_path: Path, metadata: dict[str, str]) -> Path | None:
    """Find the hierarchy source beside a curriculum manual, if one exists."""
    configured = metadata.get("outline", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = markdown_path.parent / candidate
        return candidate.resolve() if candidate.exists() else None

    book = metadata.get("book", "").strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", book).strip("-")
    candidates = [
        markdown_path.parent.parent / "architecture" / f"{slug}-outline.md",
        markdown_path.parent / f"{slug}-outline.md",
    ]
    return next((path.resolve() for path in candidates if slug and path.exists()), None)


def build_pdf(
    markdown_path: Path,
    output_path: Path,
    theme: Theme,
    no_cover: bool,
    variant: str = "teacher",
    *,
    indent_strict: bool = True,
    outline_path: Path | None = None,
) -> None:
    styles = build_styles(theme)
    raw_source = markdown_path.read_text(encoding="utf-8")
    metadata, unfiltered_text = parse_front_matter(raw_source)
    content_result = prepare_pdf_markdown(unfiltered_text)
    text = content_result.markdown
    # Line numbers in indentation errors must point at the real file.
    line_offset = len(raw_source.splitlines()) - len(unfiltered_text.splitlines())
    story: list[Flowable] = []
    authoritative_outline = outline_path or discover_outline_path(markdown_path, metadata)
    outline_text = authoritative_outline.read_text(encoding="utf-8") if authoritative_outline else None

    if not no_cover:
        append_cover(story, styles, theme)

    project_dir = Path(__file__).resolve().parent
    for intro_file in [project_dir / "CGV.md", project_dir / "proposito-del-manual.md"]:
        intro_body = read_body(intro_file)
        if intro_body:
            story.extend(parse_markdown(intro_body, styles, variant, intro_file, indent_strict=indent_strict))
            story.append(PageBreak())

    append_toc(story, styles, toc_entries(text))
    story.extend(
        parse_markdown(
            text,
            styles,
            variant,
            markdown_path,
            line_offset=line_offset,
            indent_strict=indent_strict,
            outline_text=outline_text,
            outline_filename=authoritative_outline.name if authoritative_outline else "<outline>",
        )
    )
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
    parser = argparse.ArgumentParser(description="Export a CGV Markdown manual to letter-sized PDF.")
    parser.add_argument("input", type=Path, nargs="?", help="Markdown source file")
    parser.add_argument("-o", "--output", type=Path, help="PDF output path")
    parser.add_argument("--title", help="Cover title and PDF title")
    parser.add_argument("--subtitle", help="Cover subtitle")
    parser.add_argument("--footer-left", default="", help="Footer text at bottom left")
    parser.add_argument("--footer-center", default="www.discipuladocgv.org", help="Footer text at bottom center")
    parser.add_argument("--footer-right", default="", help="Footer text at bottom right")
    parser.add_argument("--logo", help="Cover logo path. Front matter may also use logo: path/to/logo.png")
    parser.add_argument("--cover", help="Cover image path. Front matter may also use cover: path/to/cover.png")
    parser.add_argument("--label-color", help="Cover manual label color, such as #111111 or #ffffff")
    parser.add_argument(
        "--label-location",
        choices=sorted(COVER_LABEL_LOCATIONS),
        help="Cover manual label location",
    )
    parser.add_argument("--logo-location", choices=sorted(LOGO_LOCATIONS), help="Cover logo badge location")
    parser.add_argument(
        "--logo-background",
        help="Cover logo badge white background opacity from 0 to 1",
    )
    parser.add_argument("--single", choices=["student", "teacher"], help="Export only one version")
    parser.add_argument("--body-size", type=float, default=12.5, help="Main text size in points")
    parser.add_argument(
        "--outline",
        type=Path,
        help="Authoritative hierarchy Markdown (auto-discovered from book metadata when omitted)",
    )
    parser.add_argument("--no-cover", action="store_true", help="Start the PDF directly from the Markdown content")
    parser.add_argument(
        "--indent-step",
        type=float,
        help="Horizontal distance in inches between two structural depths (default 0.30)",
    )
    parser.add_argument(
        "--indent-base",
        type=float,
        help="Inches from the left margin to a depth-0 structural item (default 0.20)",
    )
    parser.add_argument(
        "--annotation-offset",
        type=float,
        help="Inches a `*` note or `>` comment sits right of its item (default 0.14)",
    )
    parser.add_argument(
        "--indent-policy",
        choices=["strict", "warn"],
        default="strict",
        help="strict: stop on malformed structural indentation. warn: report and skip the line.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    configure_ladder(
        indent_step=args.indent_step * INCH if args.indent_step else None,
        indent_base=args.indent_base * INCH if args.indent_base else None,
        annotation_offset=args.annotation_offset * INCH if args.annotation_offset else None,
    )
    default_input = Path("manual.md") if Path("manual.md").exists() else DEFAULT_MANUAL_PATH
    input_path = (args.input or default_input).expanduser().resolve()
    metadata, _ = parse_front_matter(input_path.read_text(encoding="utf-8"))
    book = metadata.get("book", "")
    version = metadata.get("version", "")
    logo_value = args.logo or metadata.get("logo", "")
    logo_path = resolve_asset_path(logo_value, input_path)
    if not logo_path and DEFAULT_LOGO_PATH.exists():
        logo_path = os.fspath(DEFAULT_LOGO_PATH)
    cover_path = resolve_asset_path(args.cover or metadata.get("cover", ""), input_path)
    label_color = args.label_color or metadata.get("label_color") or metadata.get("cover_label_color") or "#111111"
    label_location = args.label_location or metadata.get("label_location") or metadata.get("cover_label_location") or "lower-quarter"
    logo_location = args.logo_location or metadata.get("logo_location") or "bottom-right"
    logo_background = parse_opacity(
        args.logo_background if args.logo_background is not None else metadata.get("logo_background") or metadata.get("logo_background_alpha")
    )

    variants = [args.single] if args.single else ["student", "teacher"]
    labels = {"student": "Manual del Alumno", "teacher": "Manual del Maestro"}
    suffixes = {"student": "alumno", "teacher": "maestro"}
    written: list[Path] = []

    for variant in variants:
        manual_label = labels[variant]
        footer_left = args.footer_left or " ".join(
            part for part in [book, manual_label, f"({version})" if version else ""] if part
        )
        if args.output and len(variants) == 1:
            output_path = args.output.expanduser().resolve()
        else:
            output_path = input_path.parent / f"{suffixes[variant]}.pdf"

        theme = Theme(
            body_size=args.body_size,
            leading=args.body_size * 1.36,
            book=book,
            title=args.title or metadata.get("title") or book or "Manual",
            subtitle=args.subtitle if args.subtitle is not None else metadata.get("subtitle", ""),
            telos=metadata.get("telos", ""),
            version=version,
            footer_left=footer_left,
            footer_center=args.footer_center,
            footer_right=args.footer_right,
            logo_path=logo_path,
            cover_path=cover_path,
            manual_type=manual_label,
            cover_label_color=label_color,
            cover_label_location=label_location,
            logo_location=logo_location,
            logo_background_alpha=logo_background,
            page_offset=-2 if not args.no_cover else 0,
            cover_enabled=not args.no_cover,
        )
        try:
            build_pdf(
                input_path,
                output_path,
                theme,
                args.no_cover,
                variant,
                indent_strict=args.indent_policy == "strict",
                outline_path=args.outline.expanduser().resolve() if args.outline else None,
            )
        except StructuralIndentError as error:
            print(str(error), file=sys.stderr)
            return 2
        written.append(output_path)

    for path in written:
        print(os.fspath(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
