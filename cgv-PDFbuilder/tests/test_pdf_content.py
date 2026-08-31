"""Tests for PDF-only filtering of the shared presentation/manual source."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cgv_pdf_content import prepare_pdf_markdown  # noqa: E402


class PdfContentPolicyTest(unittest.TestCase):
    def test_gate_surface_is_preserved_byte_for_byte(self) -> None:
        source = (
            "# Unidad\r\n"
            "= **1** Texto LBF\r\n"
            "### Flujo\r\n"
            "Contenido estructural.\r\n"
            "## Convergencia\r\n"
            "Contenido convergente.\r\n"
            "## Apéndice D — Notas técnicas\r\n"
            "[^tech]: conservar\r\n"
        )
        result = prepare_pdf_markdown(source)
        self.assertEqual(result.markdown, source)

    def test_all_removal_counters_stay_zero(self) -> None:
        result = prepare_pdf_markdown("= Escritura\n## Apéndice D\n[^x]: nota\n")
        self.assertEqual(result.removed_scripture_lines, 0)
        self.assertEqual(result.removed_appendix_d_lines, 0)
        self.assertEqual(result.removed_flow_lines, 0)
        self.assertEqual(result.removed_convergence_lines, 0)
        self.assertEqual(result.removed_footnote_citations, 0)
        self.assertFalse(result.appendix_d_footnote_ids)


if __name__ == "__main__":
    unittest.main()
