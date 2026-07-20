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
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer


VERSE_HEADING_RE = re.compile(r"^[1-3]?\s?[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\s+\d+:\d+")
LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[-*+])\s+(?P<text>.+)$")
NUMBERED_LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>\d+[.)])\s+(?P<text>.+)$")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)$")
SCRIPTURE_QUOTE_PAIRS = {
    "“": "”",
    "«": "»",
}
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
DEFAULT_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "cgv-logo.png"
DEFAULT_MANUAL_PATH = Path("/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/17.Tito/manual.md")
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


class PageNumberCanvas:
    """Two-pass canvas that draws page numbers and manual footers."""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.pages = []

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
        font_regular, font_bold, _, _ = register_fonts()
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
    regular = first_existing_font(["STIXGeneral.otf", "STIXTwoText.ttf", "Georgia.ttf", "DejaVuSerif.ttf"])
    bold = first_existing_font(["STIXGeneralBol.otf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"])
    italic = first_existing_font(["STIXGeneralItalic.otf", "STIXTwoText-Italic.ttf", "Georgia Italic.ttf", "DejaVuSerif-Italic.ttf"])
    bold_italic = first_existing_font(["STIXGeneralBolIta.otf", "Georgia Bold Italic.ttf", "DejaVuSerif-BoldItalic.ttf"])

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
    font_regular, font_bold, font_italic, _ = register_fonts()
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
        "h1": ParagraphStyle(
            "Heading1",
            parent=base,
            fontName=font_bold,
            fontSize=18.5,
            leading=23,
            alignment=TA_CENTER,
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
            alignment=TA_CENTER,
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
        ),
        "bullet": ParagraphStyle(
            "BulletText",
            parent=base,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=1,
            spaceAfter=2,
        ),
        "human_observation": ParagraphStyle(
            "HumanObservationText",
            parent=base,
            fontName=font_italic,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=1,
            spaceAfter=2,
        ),
    }


LIST_ROLE_STYLES = {
    "-": {
        "name": "Clause",
        "left": 0.28 * inch,
        "first": 0,
        "space_before": 5,
        "space_after": 4,
    },
    "*": {
        "name": "MechanicalObservation",
        "left": 0.62 * inch,
        "first": 0,
        "space_before": 1,
        "space_after": 3,
    },
    "+": {
        "name": "HumanObservation",
        "left": 0.62 * inch,
        "first": 0,
        "space_before": 1,
        "space_after": 3,
        "font_style": "italic",
    },
}


def escape_inline(text: str) -> str:
    text = html.escape(text.strip(), quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<i>\1</i>", text)
    return text


def answer_tag_html(match: re.Match[str], variant: str) -> str:
    answer = html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
    if variant == "student":
        width = max(10, round(len(answer) * 2.6))
        return "<u>" + ("&nbsp;" * width) + "</u>"
    return f"<b><u>{escape_inline(answer)}</u></b>"


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


def format_inline(text: str, variant: str = "teacher") -> str:
    stripped = text.strip()
    protected, replacements = protect_answer_tags(stripped, variant)
    if len(stripped) >= 2:
        closing = SCRIPTURE_QUOTE_PAIRS.get(protected[0])
        if closing and protected.endswith(closing):
            inner = protected[1:-1].strip()
            return restore_protected(f"« <i>{escape_inline(inner)}</i> »", replacements)
    italic_match = re.fullmatch(r"\*([^*]+)\*", protected)
    if italic_match:
        return restore_protected(f"« <i>{escape_inline(italic_match.group(1))}</i> »", replacements)
    return restore_protected(escape_inline(protected), replacements)


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
    if not value:
        return ""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = source_path.parent / path
    return os.fspath(path.resolve())


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


def make_paragraph(text: str, style: ParagraphStyle, variant: str = "teacher") -> Paragraph:
    return Paragraph(format_inline(text, variant), style)


def scripture_line_text(text: str) -> str | None:
    match = re.fullmatch(r"\*([^*]+)\*", text.strip())
    if not match:
        return None
    return match.group(1).strip()


def make_scripture_paragraph(text: str, style: ParagraphStyle, variant: str) -> Paragraph:
    protected, replacements = protect_answer_tags(text.strip(), variant)
    return Paragraph(restore_protected(f"« <i>{escape_inline(protected)}</i> »", replacements), style)


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


def flush_paragraph(lines: list[str], story: list[Flowable], styles: dict[str, ParagraphStyle], variant: str) -> None:
    if not lines:
        return
    text = " ".join(line.strip() for line in lines if line.strip())
    if not text:
        lines.clear()
        return
    style = styles["verse"] if text.startswith(("“", "«")) and text.endswith(("”", "»")) else styles["body"]
    story.append(make_paragraph(text, style, variant))
    lines.clear()


def flush_context_paragraph(
    lines: list[str],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    context: LayoutContext,
    variant: str,
) -> None:
    if not lines:
        return
    text = " ".join(line.strip() for line in lines if line.strip())
    if not text:
        lines.clear()
        return

    if context.paragraph_parent == "scripture":
        story.append(make_scripture_paragraph(text, styles["verse"], variant))
        lines.clear()
        return

    if text.startswith(("“", "«")) and text.endswith(("”", "»")):
        parent = styles["verse"]
    elif context.paragraph_parent == "human_observation":
        parent = styles["human_observation"]
    else:
        parent = styles["body"]

    style = ParagraphStyle(
        f"ContextParagraph{context.paragraph_parent}{int(context.paragraph_left)}",
        parent=parent,
        leftIndent=context.paragraph_left,
        firstLineIndent=0,
        spaceBefore=1,
        spaceAfter=3,
    )
    story.append(make_paragraph(text, style, variant))
    lines.clear()


def append_list(
    items: list[tuple[int, str, str]],
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    variant: str,
) -> LayoutContext | None:
    if not items:
        return None

    counters: dict[int, int] = {}
    last_context: LayoutContext | None = None
    for indent, marker, text in items:
        ordered = marker[0].isdigit()
        role = LIST_ROLE_STYLES.get(marker, {})
        left_indent = role.get("left", 0.22 * inch) + min(indent, 5) * 0.18 * inch
        parent_key = "human_observation" if marker == "+" else "bullet"
        style = ParagraphStyle(
            f"{role.get('name', 'ListItem')}{indent}",
            parent=styles[parent_key],
            leftIndent=left_indent,
            firstLineIndent=role.get("first", -0.16 * inch if ordered else 0),
            spaceBefore=role.get("space_before", 1),
            spaceAfter=role.get("space_after", 2),
        )
        if ordered:
            counters[indent] = counters.get(indent, 0) + 1
            prefix = f"{counters[indent]}.&nbsp;&nbsp;"
        else:
            prefix = ""
        content = format_inline(text, variant)
        story.append(
            Paragraph(
                f"{prefix}{content}",
                style,
            )
        )
        last_context = LayoutContext(left_indent, "human_observation" if marker == "+" else "body")
    story.append(Spacer(1, 4))
    return last_context


def parse_markdown(
    markdown: str,
    styles: dict[str, ParagraphStyle],
    variant: str = "teacher",
    source_path: Path | None = None,
) -> list[Flowable]:
    story: list[Flowable] = []
    paragraph_lines: list[str] = []
    list_items: list[tuple[int, str, str]] = []
    context = LayoutContext()
    expecting_h3_scripture = False

    def flush_all() -> None:
        nonlocal context
        flush_context_paragraph(paragraph_lines, story, styles, context, variant)
        list_context = append_list(list_items, story, styles, variant)
        if list_context:
            context = list_context
        list_items.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_all()
            story.append(Spacer(1, 3))
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

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            expecting_h3_scripture = False
            flush_all()
            append_markdown_image(image_match, story, styles, source_path, variant)
            continue

        list_match = LIST_RE.match(line) or NUMBERED_LIST_RE.match(line)
        if list_match:
            expecting_h3_scripture = False
            flush_context_paragraph(paragraph_lines, story, styles, context, variant)
            indent = len(list_match.group("indent").replace("\t", "    ")) // 2
            marker = list_match.group("marker")
            list_items.append((indent, marker, list_match.group("text")))
            continue

        scripture_text = scripture_line_text(stripped)
        if scripture_text and (expecting_h3_scripture or context.paragraph_parent == "scripture"):
            append_list(list_items, story, styles, variant)
            list_items.clear()
            context = LayoutContext(styles["verse"].leftIndent, "scripture")
            paragraph_lines.append(scripture_text)
            expecting_h3_scripture = False
            continue

        flush_all()

        if stripped.startswith("#"):
            expecting_h3_scripture = False
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if text:
                style = styles.get(f"h{min(level, 6)}", styles["h6"])
                heading = make_paragraph(text, style, variant)
                if level <= 2 and story:
                    story.append(Spacer(1, 4))
                story.append(heading)
                context = LayoutContext()
                expecting_h3_scripture = level == 3
            continue

        if stripped.startswith(">"):
            expecting_h3_scripture = False
            quote = stripped.lstrip(">").strip()
            image_match = IMAGE_RE.match(quote)
            if image_match:
                flush_all()
                append_markdown_image(image_match, story, styles, source_path, variant, context.paragraph_left)
                continue
            parent_key = "human_observation" if context.paragraph_parent == "human_observation" else "body"
            quote_style = ParagraphStyle(
                f"ContextQuote{context.paragraph_parent}{int(context.paragraph_left)}",
                parent=styles[parent_key],
                leftIndent=context.paragraph_left,
                firstLineIndent=0,
                spaceBefore=2,
                spaceAfter=4,
            )
            story.append(make_paragraph(quote, quote_style, variant))
            continue

        if VERSE_HEADING_RE.match(stripped):
            expecting_h3_scripture = False
            story.append(KeepTogether([make_paragraph(stripped, styles["h4"], variant)]))
            context = LayoutContext()
            continue

        expecting_h3_scripture = False
        paragraph_lines.append(stripped)

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
    return "\n".join(line for line in body.splitlines() if "page-break-after" not in line)


def build_pdf(markdown_path: Path, output_path: Path, theme: Theme, no_cover: bool, variant: str = "teacher") -> None:
    styles = build_styles(theme)
    _, text = parse_front_matter(markdown_path.read_text(encoding="utf-8"))
    story: list[Flowable] = []

    if not no_cover:
        append_cover(story, styles, theme)

    project_dir = Path(__file__).resolve().parent
    for intro_file in [project_dir / "CGV.md", project_dir / "proposito-del-manual.md"]:
        intro_body = read_body(intro_file)
        if intro_body:
            story.extend(parse_markdown(intro_body, styles, variant, intro_file))
            story.append(PageBreak())

    append_toc(story, styles, toc_entries(text))
    story.extend(parse_markdown(text, styles, variant, markdown_path))
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
    parser.add_argument("--body-size", type=float, default=12.2, help="Main text size in points")
    parser.add_argument("--no-cover", action="store_true", help="Start the PDF directly from the Markdown content")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
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
    suffixes = {"student": "manual-del-alumno", "teacher": "manual-del-maestro"}
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
            leading=args.body_size * 1.34,
            title=args.title or metadata.get("title") or book or "Manual",
            subtitle=args.subtitle if args.subtitle is not None else metadata.get("subtitle", ""),
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
        build_pdf(input_path, output_path, theme, args.no_cover, variant)
        written.append(output_path)

    for path in written:
        print(os.fspath(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
