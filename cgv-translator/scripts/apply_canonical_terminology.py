#!/usr/bin/env python3
"""Apply declared book-wide terminology decisions before workflow/editor startup.

This is intentionally deterministic and idempotent. Canonical terminology decisions
live in translations/canonical-terminology.json. If an old rendering is present, the
existing book_lexical_edit machinery updates every Spanish occurrence and rebases
reverse-link target spans without changing sourceTokenIds. If the book is already
normalized, this script is a no-op.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "translations" / "canonical-terminology.json"


def whole_word_count(text: str, word: str) -> int:
    return len(re.findall(rf"(?<!\w){re.escape(word)}(?!\w)", text))


def phrase_path(book: str) -> Path:
    oshb = ROOT / "translations" / "oshb-spine" / book / f"{book}-phrases.json"
    if oshb.is_file():
        return oshb
    tr = ROOT / "translations" / "tr-spine" / book / f"{book}-phrases-tr.json"
    if tr.is_file():
        return tr
    raise FileNotFoundError(f"phrase artifact missing for {book}")


def main() -> int:
    if not POLICY.is_file():
        return 0
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    for book, rules in (policy.get("books") or {}).items():
        path = phrase_path(book)
        doc = json.loads(path.read_text(encoding="utf-8"))
        spanish = "\n".join(str(row.get("spanish") or "") for row in doc.get("phrases", []))
        for rule in rules:
            old = str(rule["from"])
            new = str(rule["to"])
            old_count = whole_word_count(spanish, old)
            if old_count == 0:
                print(f"TERMINOLOGY {book}: already normalized ({new})")
                continue
            if rule.get("scope") != "book":
                raise SystemExit(f"Unsupported terminology scope for {book}: {rule.get('scope')!r}")
            command = [
                sys.executable,
                str(ROOT / "scripts" / "book_lexical_edit.py"),
                "--book", book,
                "--reference", str(rule["reference"]),
                "--source-surface", str(rule["sourceSurface"]),
                "--from", old,
                "--to", new,
                "--apply",
            ]
            completed = subprocess.run(command, cwd=ROOT)
            if completed.returncode:
                return completed.returncode
            doc = json.loads(path.read_text(encoding="utf-8"))
            spanish = "\n".join(str(row.get("spanish") or "") for row in doc.get("phrases", []))
            remaining = whole_word_count(spanish, old)
            if remaining:
                raise SystemExit(f"TERMINOLOGY {book}: {remaining} {old!r} occurrences remain after apply")
            print(f"TERMINOLOGY {book}: normalized {old!r} -> {new!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
