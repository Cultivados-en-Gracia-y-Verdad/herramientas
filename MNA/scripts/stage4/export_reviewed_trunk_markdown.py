#!/usr/bin/env python3
"""
MNA Etapa 4 — Exportar Tronco Revisado a Markdown

PROPÓSITO
- Exportar las filas revisadas de suggested-trunk a un archivo Markdown legible.
- Útil para preparación de manuales y revisión rápida de enseñanza.
- No modifica los datos fuente.

Salida:
  MNA/exports/reviewed-trunk/<book>.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


STATUS_ES = {
    "AI_REVIEWED": "REVISADO_POR_IA",
    "NEEDS_EXTERNAL_GREEK_REVIEW": "REQUIERE_REVISIÓN_GRIEGA_EXTERNA",
    "REVIEWED_FOR_MANUAL_USE": "REVISADO_PARA_USO_EN_MANUAL",
}

CONFIDENCE_ES = {
    "HIGH": "ALTA",
    "MEDIUM-HIGH": "MEDIA-ALTA",
    "MEDIUM": "MEDIA",
    "MEDIUM-LOW": "MEDIA-BAJA",
    "LOW": "BAJA",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_jsonl(path: Path):
    metadata = None
    rows = []

    if not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido en {path}:{line_number}: {exc}") from exc

            if obj.get("record_type") == "metadata":
                metadata = obj
            else:
                rows.append(obj)

    return metadata, rows


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (int(r.get("chapter", 0)), int(r.get("verse", 0))))


def should_include(row: dict, include_unreviewed: bool) -> bool:
    if include_unreviewed:
        return True
    return row.get("reviewed_for_manual_use") is True


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Exportar filas revisadas del tronco sugerido a Markdown.")
    parser.add_argument("book", help="Slug del libro, por ejemplo: 1corintios")
    parser.add_argument("--from", dest="from_ref", help="Inicio CAPÍTULO:VERSÍCULO, por ejemplo: 9:1")
    parser.add_argument("--to", dest="to_ref", help="Final CAPÍTULO:VERSÍCULO, por ejemplo: 10:33")
    parser.add_argument("--include-unreviewed", action="store_true", help="Incluir filas no marcadas como reviewed_for_manual_use=true")
    args = parser.parse_args(argv)

    try:
        root = mna_root_from_script()
        book = args.book.strip().lower()
        dataset_path = root / "datasets" / "suggested-trunk" / f"{book}.jsonl"
        output_path = root / "exports" / "reviewed-trunk" / f"{book}.md"

        _metadata, rows = load_jsonl(dataset_path)
        rows = sort_rows(rows)

        def parse_bound(value: Optional[str]) -> Optional[tuple[int, int]]:
            if not value:
                return None
            chapter, verse = value.split(":", 1)
            return int(chapter), int(verse)

        start = parse_bound(args.from_ref)
        end = parse_bound(args.to_ref)

        filtered = []
        for row in rows:
            key = (int(row.get("chapter", 0)), int(row.get("verse", 0)))
            if start and key < start:
                continue
            if end and key > end:
                continue
            if should_include(row, args.include_unreviewed):
                filtered.append(row)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        title_range = ""
        if args.from_ref or args.to_ref:
            title_range = f" ({args.from_ref or 'inicio'}–{args.to_ref or 'fin'})"

        lines = []
        lines.append(f"# Tronco Revisado — {book}{title_range}")
        lines.append("")
        lines.append(f"Filas exportadas: {len(filtered)}")
        lines.append("")

        current_chapter = None
        for row in filtered:
            chapter = int(row.get("chapter", 0))
            if chapter != current_chapter:
                current_chapter = chapter
                lines.append(f"## Capítulo {chapter}")
                lines.append("")

            reference = row.get("reference")
            confidence = CONFIDENCE_ES.get(str(row.get("confidence")), row.get("confidence"))
            status = STATUS_ES.get(str(row.get("status")), row.get("status"))
            trunk = row.get("trunk_greek") or ""
            notes = row.get("review_notes") or row.get("notes") or ""

            lines.append(f"### {reference}")
            lines.append(f"#### Estado: {status} | Confianza: {confidence}")
            lines.append("```text")
            lines.append(trunk)
            lines.append("```")
            if notes:
                lines.append("##### Notas")
                lines.append(notes)
            lines.append("")

        output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        print("MNA Etapa 4 — Exportar Tronco Revisado a Markdown")
        print(f"LIBRO: {book}")
        print(f"DATASET: {dataset_path}")
        print(f"SALIDA: {output_path}")
        print(f"FILAS EXPORTADAS: {len(filtered)}")
        print("STATUS: PASS")
        return 0

    except Exception as exc:
        print("Falló la exportación del tronco revisado de MNA Etapa 4", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
