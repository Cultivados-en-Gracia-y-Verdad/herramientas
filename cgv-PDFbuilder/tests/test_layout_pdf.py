"""Layout-level regression tests: real PDF text coordinates.

These render a small manual through the exporter and read the x positions back
out of the PDF, so they catch a regression that unit-testing the parser alone
would miss.

Run with:  python3 -m unittest discover -s tests -t .
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import md_to_pdf as exporter  # noqa: E402
from cgv_structure import IndentLadder  # noqa: E402

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

#: x tolerance in points. ReportLab places a line's first glyph exactly, so this
#: only absorbs glyph side bearings.
TOLERANCE = 0.75

FIXTURE = """---
book: Apocalipsis
title: Fixture
---

# APOCALIPSIS 1:1-3:22 LA REVELACION DADA A LAS SIETE IGLESIAS

## Apocalipsis 1:1-8 Revelacion, profecia y gracia

### Apocalipsis 1:3:1 - Dichoso el que lee la profecia

#### *Revelacion de Jesus Cristo que Dios le dio*

+ *Revelacion de Jesus Cristo*
  > Comentario del escritor sobre la primera frase, escrito lo bastante largo como para que la linea se parta en varias lineas de texto y podamos comprobar la alineacion colgante del parrafo completo.

- *que Dios le dio para mostrar a sus siervos*
  * *que* introduce la relativa.

+ *Revelacion*

  - *las cosas que deben suceder pronto*
    * *las cosas* apunta a *deben*

- *y la dio a conocer, enviandola por medio de su angel a su siervo Juan*

+ *Revelacion*

+ *Dios*

  - *quien dio testimonio de la palabra de Dios y del testimonio de Jesus Cristo*

  + *Juan*

    - *de todo lo que vio*

+ *Frase larga que debe partirse en varias lineas para comprobar que las lineas continuadas cuelgan bajo el texto del elemento y no vuelven al margen de la pagina ni fingen un nivel nuevo del bosquejo*

---

+ *Despues del salto de pagina*

  - *hijo despues del salto*
"""


def render(source: str) -> list[dict]:
    """Export ``source`` and return every rendered line as {page, x, text}."""
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "fixture.md"
        md.write_text(source, encoding="utf-8")
        pdf_path = Path(tmp) / "fixture.pdf"
        theme = exporter.Theme(cover_enabled=False, title="Fixture")
        exporter.build_pdf(md, pdf_path, theme, no_cover=True, variant="teacher")
        lines: list[dict] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_no, page in enumerate(pdf.pages, 1):
                buckets: dict[int, list] = {}
                for word in page.extract_words():
                    buckets.setdefault(round(word["top"]), []).append(word)
                for top in sorted(buckets):
                    words = sorted(buckets[top], key=lambda w: w["x0"])
                    lines.append(
                        {
                            "page": page_no,
                            "top": top,
                            "x": words[0]["x0"],
                            "text": " ".join(w["text"] for w in words),
                        }
                    )
    return lines


@unittest.skipIf(pdfplumber is None, "pdfplumber is required for layout tests")
class RenderedLayoutTest(unittest.TestCase):
    lines: list[dict]

    @classmethod
    def setUpClass(cls) -> None:
        cls.lines = render(FIXTURE)

    def find(self, needle: str, *, exact: bool = True) -> dict:
        for line in self.lines:
            text = line["text"]
            if text == needle if exact else text.startswith(needle):
                return line
        raise AssertionError(f"not rendered: {needle!r}")

    def x(self, needle: str, *, exact: bool = True) -> float:
        return self.find(needle, exact=exact)["x"]

    # --- equal depth, equal x -------------------------------------------
    def test_all_depth_zero_items_share_one_x(self) -> None:
        roots = [
            "Revelacion de Jesus Cristo",
            "que Dios le dio para mostrar a sus siervos",
            "y la dio a conocer, enviandola por medio de su angel a su siervo Juan",
            "Dios",
        ]
        xs = [self.x(text) for text in roots]
        for value in xs[1:]:
            self.assertAlmostEqual(value, xs[0], delta=TOLERANCE)

    def test_all_depth_one_items_share_one_x(self) -> None:
        ones = [
            "las cosas que deben suceder pronto",
            "Juan",
        ]
        xs = [self.x(text) for text in ones]
        xs.append(self.x("quien dio testimonio de la palabra", exact=False))
        for value in xs[1:]:
            self.assertAlmostEqual(value, xs[0], delta=TOLERANCE)

    def test_marker_change_does_not_move_an_item(self) -> None:
        # `+ Revelacion` (plus) and `- que Dios le dio` (minus) are both depth 0.
        self.assertAlmostEqual(
            self.x("Revelacion de Jesus Cristo"),
            self.x("que Dios le dio para mostrar a sus siervos"),
            delta=TOLERANCE,
        )
        # `- quien dio testimonio` and `+ Juan` are both depth 1.
        self.assertAlmostEqual(
            self.x("quien dio testimonio de la palabra", exact=False),
            self.x("Juan"),
            delta=TOLERANCE,
        )

    # --- the ladder itself ----------------------------------------------
    def test_depth_steps_match_the_configured_indent_step(self) -> None:
        ladder = exporter.LADDER
        zero = self.x("Dios")
        one = self.x("Juan")
        two = self.x("de todo lo que vio")
        self.assertAlmostEqual(one - zero, ladder.step, delta=TOLERANCE)
        self.assertAlmostEqual(two - one, ladder.step, delta=TOLERANCE)

    def test_indentation_returns_to_the_left_after_a_deep_branch(self) -> None:
        deep = self.x("de todo lo que vio")
        after = self.x("Frase larga que debe partirse", exact=False)
        self.assertLess(after, deep)
        self.assertAlmostEqual(after, self.x("Revelacion de Jesus Cristo"), delta=TOLERANCE)

    # --- annotations -----------------------------------------------------
    def test_annotation_hangs_off_its_item_without_reaching_the_next_level(self) -> None:
        item = self.x("que Dios le dio para mostrar a sus siervos")
        note = self.x("que introduce la relativa.")
        nested_item = self.x("las cosas que deben suceder pronto")
        self.assertGreater(note, item)
        self.assertLess(note, nested_item)

    def test_annotation_does_not_push_the_following_item(self) -> None:
        before = self.x("Revelacion de Jesus Cristo")  # has a long `>` comment under it
        after = self.x("que Dios le dio para mostrar a sus siervos")
        self.assertAlmostEqual(before, after, delta=TOLERANCE)

    def test_commentary_stays_with_its_item(self) -> None:
        item = self.find("Revelacion de Jesus Cristo")
        comment = self.find("Comentario del escritor", exact=False)
        self.assertEqual(item["page"], comment["page"])
        self.assertGreater(comment["top"], item["top"])

    # --- wrapping --------------------------------------------------------
    def test_wrapped_lines_hang_under_the_item_text(self) -> None:
        first = self.find("Frase larga que debe partirse", exact=False)
        continuation = [
            line
            for line in self.lines
            if line["page"] == first["page"]
            and 0 < line["top"] - first["top"] < 60
        ]
        self.assertGreaterEqual(len(continuation), 1, "fixture line did not wrap")
        for line in continuation[:2]:
            self.assertAlmostEqual(line["x"], first["x"], delta=TOLERANCE)

    def test_wrapped_commentary_hangs_under_its_own_left_edge(self) -> None:
        first = self.find("Comentario del escritor", exact=False)
        continuation = [
            line
            for line in self.lines
            if line["page"] == first["page"] and 0 < line["top"] - first["top"] < 60
        ]
        self.assertGreaterEqual(len(continuation), 1, "comment did not wrap")
        self.assertAlmostEqual(continuation[0]["x"], first["x"], delta=TOLERANCE)

    # --- page breaks ------------------------------------------------------
    def test_indentation_is_consistent_across_a_page_break(self) -> None:
        after_break = self.find("Despues del salto de pagina")
        child = self.find("hijo despues del salto")
        self.assertGreater(after_break["page"], self.find("de todo lo que vio")["page"])
        self.assertAlmostEqual(
            after_break["x"], self.x("Revelacion de Jesus Cristo"), delta=TOLERANCE
        )
        self.assertAlmostEqual(child["x"], self.x("Juan"), delta=TOLERANCE)

    # --- margins and headings --------------------------------------------
    def test_nothing_collides_with_the_right_margin(self) -> None:
        right_edge = exporter.Theme.page_width - exporter.Theme.margin_x
        for line in self.lines:
            self.assertLess(line["x"], right_edge - IndentLadder().min_text_width + 1)

    def test_h3_and_h4_are_distinguishable(self) -> None:
        h3 = self.find("Apocalipsis 1:3:1 - Dichoso el que lee la profecia")
        h4 = self.find("Revelacion de Jesus Cristo que Dios le dio")
        self.assertGreater(h4["x"], h3["x"])
        self.assertLess(h4["x"], self.x("Revelacion de Jesus Cristo"))


if __name__ == "__main__":
    unittest.main()
