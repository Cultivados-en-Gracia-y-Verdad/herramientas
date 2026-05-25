#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "desarrollo-trace-renderer-v1"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def estado_marker(estado: str) -> str:
    estado = (estado or "").strip().lower()
    if estado == "activo":
        return "ACTIVO"
    if estado == "retomado":
        return "RETOMADO"
    if estado == "distinguido":
        return "DISTINGUIDO"
    if estado == "posible cierre":
        return "POSIBLE CIERRE"
    if estado == "cerrado":
        return "CERRADO"
    return estado.upper() or "REVISAR"


def flow_connector(index: int, total: int) -> str:
    if index == 0:
        return "INICIO"
    if index == total - 1:
        return "ULTIMO PUNTO VISIBLE"
    return "CONTINUA"


def render_signal(signal: dict[str, Any]) -> list[str]:
    puntos = signal.get("trace_points", [])
    lines: list[str] = []

    lines.append(f"## {signal.get('label', signal.get('signal_id', 'desarrollo'))}")
    lines.append("")
    lines.append(f"**Pregunta guía:** {signal.get('pregunta', '')}")
    lines.append("")
    lines.append("```text")
    lines.append("TRAZO DEL DESARROLLO")
    lines.append("")

    if not puntos:
        lines.append("No hay puntos de desarrollo registrados.")
        lines.append("```")
        lines.append("")
        return lines

    for i, punto in enumerate(puntos):
        connector = flow_connector(i, len(puntos))
        estado = estado_marker(str(punto.get("estado", "REVISAR")))
        ref = punto.get("ref", "?")
        funcion = punto.get("funcion", "")
        observacion = punto.get("observacion", "")
        evidencia = punto.get("evidencia", [])

        if i > 0:
            lines.append("   │")
            lines.append("   ▼")

        lines.append(f"[{connector}] {ref} — {estado}")
        lines.append(f"Función: {funcion}")
        lines.append(f"Observación: {observacion}")
        lines.append("Evidencia visible:")
        for item in evidencia:
            lines.append(f"  - {item}")
        lines.append("")

    lines.append("```")
    lines.append("")
    lines.append("### Preguntas de revisión")
    lines.append("")
    lines.append("- ¿El trazo muestra desarrollo real o solo palabras relacionadas?")
    lines.append("- ¿Qué sigue activo?")
    lines.append("- ¿Qué se retoma?")
    lines.append("- ¿Dónde parece cambiar la presión del discurso?")
    lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Renderiza trazos de desarrollo en español.")
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    args = parser.parse_args()

    book = args.book.strip().lower()
    mna = root()
    seed_path = mna / "data" / "developmental-signals" / book / f"desarrollo-{args.chapter}.json"
    out_dir = mna / "datasets" / "developmental" / book
    out_dir.mkdir(parents=True, exist_ok=True)

    seed = load_json(seed_path)

    md: list[str] = []
    md.append(f"# Trazo de Desarrollo — {book} {args.chapter}")
    md.append("")
    md.append("Este archivo muestra el proceso de observación. No crea secciones ni conclusiones finales.")
    md.append("")

    for signal in seed.get("signals", []):
        md.extend(render_signal(signal))

    output = {
        "record_type": "developmental_trace_render",
        "version": VERSION,
        "book": book,
        "chapter": args.chapter,
        "source": str(seed_path),
        "signals": seed.get("signals", []),
    }

    md_path = out_dir / f"chapter-{args.chapter}-desarrollo-trace.md"
    json_path = out_dir / f"chapter-{args.chapter}-desarrollo-trace.json"

    md_path.write_text("\n".join(md), encoding="utf-8")
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Trazo de desarrollo")
    print(f"LIBRO: {book}")
    print(f"CAPÍTULO: {args.chapter}")
    print(f"MD: {md_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
