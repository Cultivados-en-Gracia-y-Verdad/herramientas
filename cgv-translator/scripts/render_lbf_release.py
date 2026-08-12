#!/usr/bin/env python3
"""Render an approved cgv-translator phrase artifact in LBF markdown format.

This renderer does not approve a translation, complete a book-level release gate, or
publish a canonical Bible edition. It only renders phrase records already marked
``lbf-approved`` into a deterministic candidate artifact.

Direct publication into ``cgv-data`` is intentionally blocked until the release
manifest enforces the complete RELEASE_GATE.md requirements (edition/version,
book-level final review, human approval, exact revisions, and artifact identity).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


BOOK_CONFIG = {
    "daniel": {
        "release_slug": "daniel",
        # The rendered LBF is produced from the Translator-owned phrase artifact.
        # Keep provenance upstream; cgv-reader is a downstream consumer.
        "source_comment": "cgv-translator/translations/oshb-spine/daniel/daniel-phrases.json",
    },
}


def load_phrase_doc(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        doc = json.load(handle)
    if not isinstance(doc, dict) or not isinstance(doc.get("phrases"), list):
        raise ValueError(f"Invalid phrase artifact: {path}")
    return doc


def render_release_bytes(phrase_doc: dict) -> bytes:
    book_id = str(phrase_doc.get("bookId") or "").strip().lower()
    config = BOOK_CONFIG.get(book_id)
    if not config:
        raise ValueError(
            f"No LBF render configuration for book {book_id!r}. "
            "Add it deliberately before rendering that book."
        )

    phrases = phrase_doc["phrases"]
    if not phrases:
        raise ValueError("Phrase artifact is empty.")

    lines = [
        "<!-- LBF — La Biblia Fiel",
        f"     book: {config['release_slug']}",
        f"     source: {config['source_comment']}",
        "-->",
    ]

    seen = set()
    for index, phrase in enumerate(phrases, start=1):
        if not isinstance(phrase, dict):
            raise ValueError(f"Phrase {index} is not an object.")
        status = str(phrase.get("suggestionSource") or "")
        if status != "lbf-approved":
            raise ValueError(
                f"Refusing render: phrase {phrase.get('reference') or index} "
                f"has suggestionSource={status!r}, not 'lbf-approved'."
            )
        reference = str(phrase.get("reference") or "").strip()
        spanish = str(phrase.get("spanish") or "").strip()
        if not reference or not spanish:
            raise ValueError(f"Refusing render: blank reference/text at phrase {index}.")
        if reference in seen:
            raise ValueError(f"Refusing render: duplicate reference {reference}.")
        seen.add(reference)
        lines.append(f"{reference} {spanish}")

    # Canonical text files end with one terminal newline. Daniel's legacy export
    # used this representation; matching it is continuity evidence, not approval.
    return ("\n".join(lines) + "\n").encode("utf-8")


def path_is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def write_candidate(path: Path, payload: bytes, translator_root: Path) -> str:
    cgv_data_root = translator_root.parent.parent / "cgv-data"
    if path_is_inside(path, cgv_data_root):
        raise RuntimeError(
            "Refusing direct publication to cgv-data. The complete book release "
            "manifest/gate is not implemented yet; render the candidate outside "
            "cgv-data and complete RELEASE_GATE.md first."
        )

    if path.exists():
        current = path.read_bytes()
        if current == payload:
            return "UNCHANGED"
        raise RuntimeError(f"Refusing to replace candidate with different bytes: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return "CREATED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrases", required=True, help="Approved phrase JSON")
    parser.add_argument(
        "--output",
        help="Candidate output path outside cgv-data. Omit with --stdout.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Render candidate bytes to stdout without writing a file.",
    )
    args = parser.parse_args()

    if bool(args.stdout) == bool(args.output):
        raise SystemExit("Choose exactly one: --stdout or --output <candidate-path>.")

    phrase_path = Path(args.phrases).expanduser().resolve()
    phrase_doc = load_phrase_doc(phrase_path)
    book_id = str(phrase_doc.get("bookId") or "").strip().lower()
    if book_id not in BOOK_CONFIG:
        raise SystemExit(f"Unsupported render book: {book_id!r}")

    payload = render_release_bytes(phrase_doc)
    if args.stdout:
        import sys
        sys.stdout.buffer.write(payload)
        return 0

    translator_root = Path(__file__).resolve().parents[1]
    output = Path(args.output).expanduser().resolve()
    result = write_candidate(output, payload, translator_root)
    print(f"{result}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())