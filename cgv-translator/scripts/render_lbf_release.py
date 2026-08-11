#!/usr/bin/env python3
"""Render an approved cgv-translator phrase artifact in cgv-data LBF format.

This is the canonical release renderer. It does not approve translation or alignment.
It only renders phrase records that are already marked lbf-approved.

For safety, an existing release file is never replaced with different bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


BOOK_CONFIG = {
    # Preserve the established cgv-data release header so Daniel regression can
    # prove byte-for-byte identity with the historical approved artifact.
    "daniel": {
        "release_slug": "daniel",
        "source_comment": "cgv-reader/data/lbf/ot/daniel.md",
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
            f"No canonical cgv-data release configuration for book {book_id!r}. "
            "Add it deliberately before publishing that book."
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
                f"Refusing release: phrase {phrase.get('reference') or index} "
                f"has suggestionSource={status!r}, not 'lbf-approved'."
            )
        reference = str(phrase.get("reference") or "").strip()
        spanish = str(phrase.get("spanish") or "").strip()
        if not reference or not spanish:
            raise ValueError(f"Refusing release: blank reference/text at phrase {index}.")
        if reference in seen:
            raise ValueError(f"Refusing release: duplicate reference {reference}.")
        seen.add(reference)
        lines.append(f"{reference} {spanish}")

    # Existing cgv-data LBF files do not require a terminal newline; byte identity
    # is intentional and covered by the Daniel regression hash.
    return "\n".join(lines).encode("utf-8")


def default_output(root: Path, book_id: str) -> Path:
    config = BOOK_CONFIG[book_id]
    return root.parent / "cgv-data" / "bibles" / "LBF" / f"{config['release_slug']}.lbf.md"


def write_release(path: Path, payload: bytes) -> str:
    if path.exists():
        current = path.read_bytes()
        if current == payload:
            return "UNCHANGED"
        raise RuntimeError(
            f"Refusing to mutate released artifact with different bytes: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return "CREATED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrases", required=True, help="Approved phrase JSON")
    parser.add_argument(
        "--output",
        help="Release path. Defaults to sibling cgv-data/bibles/LBF/<book>.lbf.md",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Render to stdout instead of writing a release file.",
    )
    args = parser.parse_args()

    phrase_path = Path(args.phrases).expanduser().resolve()
    phrase_doc = load_phrase_doc(phrase_path)
    book_id = str(phrase_doc.get("bookId") or "").strip().lower()
    if book_id not in BOOK_CONFIG:
        raise SystemExit(f"Unsupported release book: {book_id!r}")

    payload = render_release_bytes(phrase_doc)
    if args.stdout:
        import sys
        sys.stdout.buffer.write(payload)
        return 0

    translator_root = Path(__file__).resolve().parents[1]
    output = Path(args.output).expanduser().resolve() if args.output else default_output(translator_root, book_id)
    result = write_release(output, payload)
    print(f"{result}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
