#!/usr/bin/env python3
"""Content-preservation policy for CGV PDF manuals.

The Manager's ``manual.md`` gate surface is authoritative. PDF export must pass
every line through unchanged; presentation syntax such as the leading ``=`` on
LBF Scripture is interpreted later by the renderer, never deleted here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfContentResult:
    """Preserved Markdown plus compatibility counters for export reporting."""

    markdown: str
    removed_scripture_lines: int
    removed_appendix_d_lines: int
    removed_flow_lines: int
    removed_convergence_lines: int
    removed_footnote_citations: int
    appendix_d_footnote_ids: frozenset[str]


def prepare_pdf_markdown(markdown: str) -> PdfContentResult:
    """Return the gate surface byte-for-byte with no PDF-only omissions."""
    return PdfContentResult(
        markdown=markdown,
        removed_scripture_lines=0,
        removed_appendix_d_lines=0,
        removed_flow_lines=0,
        removed_convergence_lines=0,
        removed_footnote_citations=0,
        appendix_d_footnote_ids=frozenset(),
    )
