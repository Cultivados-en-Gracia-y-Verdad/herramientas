#!/usr/bin/env python3
"""Migrate legacy Translator investigations into book-owned directories.

This command is intentionally conservative:
- dry-run by default;
- patches the investigation API/UI only by exact known replacements;
- refuses ambiguous or mixed legacy ownership;
- preserves every investigation file byte-for-byte while moving directories;
- keeps investigation IDs globally unique;
- does not resolve, approve, or otherwise alter investigation conclusions.

Usage:
    python3 scripts/migrate_investigations_by_book.py
    python3 scripts/migrate_investigations_by_book.py --apply
"""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.js"
MAIN = ROOT / "public" / "main.js"
CREATE = ROOT / "src" / "investigations" / "createInvestigation.js"
INVESTIGATIONS = ROOT / "investigations"

OWNERSHIP = {
    "INV-0001": "titus",
    "INV-0002": "titus",
    "INV-0003": "titus",
    "INV-0004": "titus",
    "INV-0005": "titus",
    "INV-0006": "titus",
    "INV-0007": "daniel",
    "INV-0008": "daniel",
}
BOOK_LABELS = {"titus": "Titus", "daniel": "Daniel"}


class MigrationError(RuntimeError):
    pass


def replace_exact(text: str, old: str, new: str, label: str, *, count: int = 1) -> str:
    found = text.count(old)
    if found == 0 and new in text:
        return text
    if found != count:
        raise MigrationError(f"{label}: expected {count} exact old snippet(s), found {found}")
    return text.replace(old, new)


def patch_main(text: str) -> str:
    text = replace_exact(
        text,
        'const { investigations } = await api("/api/investigations");',
        'const { investigations } = await api(translationApiPath("/api/investigations"));',
        "main.js book-scoped investigation listing",
        count=2,
    )
    text = replace_exact(
        text,
        'const result = await api("/api/investigations", {',
        'const result = await api(translationApiPath("/api/investigations"), {',
        "main.js book-scoped investigation creation",
    )
    text = replace_exact(
        text,
        '      book: payload.book || ""',
        '      book: payload.book || state.bookId || ""',
        "main.js active book ownership",
    )
    return text


def patch_server(text: str) -> str:
    text = replace_exact(
        text,
        'import { createServer } from "node:http";\n',
        'import { createServer } from "node:http";\nimport { existsSync, readdirSync } from "node:fs";\n',
        "server.js sync filesystem helpers",
    )
    text = replace_exact(
        text,
        '''function safeInvestigationPath(id) {\n  if (!/^INV-\\d{4}$/.test(id)) {\n    throw new Error("Invalid investigation ID");\n  }\n  return join(investigationsDir, id);\n}\n''',
        '''function safeInvestigationPath(id) {\n  if (!/^INV-\\d{4}$/.test(id)) {\n    throw new Error("Invalid investigation ID");\n  }\n\n  const legacy = join(investigationsDir, id);\n  if (existsSync(legacy)) return legacy;\n\n  const bookDirs = readdirSync(investigationsDir, { withFileTypes: true })\n    .filter(entry => entry.isDirectory() && !/^INV-\\d{4}$/.test(entry.name));\n  for (const entry of bookDirs) {\n    const candidate = join(investigationsDir, entry.name, id);\n    if (existsSync(candidate)) return candidate;\n  }\n\n  throw new Error(`Investigation not found: ${id}`);\n}\n''',
        "server.js nested investigation lookup",
    )
    text = replace_exact(
        text,
        '''    if (request.method === "GET") {\n      const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);\n      const investigations = entries\n        .filter(entry => entry.isDirectory() && /^INV-\\d{4}$/.test(entry.name))\n        .map(entry => entry.name)\n        .sort();\n      sendJson(response, 200, { investigations });\n      return;\n    }\n\n    if (request.method === "POST") {\n      try {\n        const body = await readJsonBody(request);\n        const result = await createInvestigationFromLemma(rootDir, body);\n        sendJson(response, result.created ? 201 : 200, result);\n''',
        '''    if (request.method === "GET") {\n      const bookId = bookIdFromRequest(url);\n      const bookDir = join(investigationsDir, bookId);\n      const entries = await readdir(bookDir, { withFileTypes: true }).catch(() => []);\n      const investigations = entries\n        .filter(entry => entry.isDirectory() && /^INV-\\d{4}$/.test(entry.name))\n        .map(entry => entry.name)\n        .sort();\n      sendJson(response, 200, { book: bookId, investigations });\n      return;\n    }\n\n    if (request.method === "POST") {\n      try {\n        const body = await readJsonBody(request);\n        const bookId = bookIdFromRequest(url, body);\n        const book = resolveBook(bookId);\n        const result = await createInvestigationFromLemma(rootDir, {\n          ...body,\n          book: bookId,\n          bookLabel: book.label\n        });\n        sendJson(response, result.created ? 201 : 200, result);\n''',
        "server.js book-scoped list/create endpoint",
    )
    return text


def patch_create(text: str) -> str:
    text = replace_exact(
        text,
        '''export async function allocateNextInvestigationId(investigationsDir) {\n  const ids = await listInvestigationIds(investigationsDir);\n  const next = Math.max(0, ...ids.map(investigationNumber)) + 1;\n  return `INV-${String(next).padStart(4, "0")}`;\n}\n''',
        '''async function listAllInvestigationIds(investigationsDir) {\n  const ids = new Set(await listInvestigationIds(investigationsDir));\n  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);\n  for (const entry of entries) {\n    if (!entry.isDirectory() || /^INV-\\d{4}$/.test(entry.name)) continue;\n    for (const id of await listInvestigationIds(join(investigationsDir, entry.name))) {\n      ids.add(id);\n    }\n  }\n  return [...ids].sort();\n}\n\nexport async function allocateNextInvestigationId(investigationsDir) {\n  const ids = await listAllInvestigationIds(investigationsDir);\n  const next = Math.max(0, ...ids.map(investigationNumber)) + 1;\n  return `INV-${String(next).padStart(4, "0")}`;\n}\n''',
        "createInvestigation.js global unique ID allocation",
    )
    text = replace_exact(
        text,
        '''  const reference = String(body.reference || "").trim() || "Titus 1:1";\n  const clause = String(body.clause || "").trim();\n  const ble = String(body.ble || body.rendering || "").trim();\n  const book = String(body.book || "").trim() || bookFromReference(reference);\n  const investigationsDir = join(rootDir, "investigations");\n\n  const existing = await findInvestigationByLemma(investigationsDir, { lemma, strongs, language });\n''',
        '''  const reference = String(body.reference || "").trim() || "Titus 1:1";\n  const clause = String(body.clause || "").trim();\n  const ble = String(body.ble || body.rendering || "").trim();\n  const bookId = String(body.book || "").trim().toLowerCase();\n  if (!/^[a-z0-9][a-z0-9-]*$/.test(bookId)) {\n    throw new Error("book id is required for a book-owned investigation");\n  }\n  const book = String(body.bookLabel || "").trim() || bookFromReference(reference);\n  const investigationsDir = join(rootDir, "investigations");\n  const bookInvestigationsDir = join(investigationsDir, bookId);\n\n  const existing = await findInvestigationByLemma(bookInvestigationsDir, { lemma, strongs, language });\n''',
        "createInvestigation.js book ownership",
    )
    text = replace_exact(
        text,
        '''      status: existing.status || "Draft"\n    };\n  }\n\n  const id = await allocateNextInvestigationId(investigationsDir);\n  const investigationDir = join(investigationsDir, id);\n''',
        '''      status: existing.status || "Draft",\n      book: bookId\n    };\n  }\n\n  const id = await allocateNextInvestigationId(investigationsDir);\n  const investigationDir = join(bookInvestigationsDir, id);\n''',
        "createInvestigation.js nested target directory",
    )
    text = replace_exact(
        text,
        '''    status: "Draft",\n    reference\n  };\n}\n''',
        '''    status: "Draft",\n    reference,\n    book: bookId\n  };\n}\n''',
        "createInvestigation.js returned book identity",
    )
    return text


def read_declared_book(readme: Path) -> str:
    text = readme.read_text(encoding="utf-8")
    match = re.search(r"## Origin\s+.*?\bBook\s+([^\n]+)", text, flags=re.S)
    if not match:
        raise MigrationError(f"Cannot determine declared Book in {readme}")
    return match.group(1).strip()


def preflight_moves() -> list[tuple[Path, Path]]:
    moves: list[tuple[Path, Path]] = []
    for inv_id, book_id in OWNERSHIP.items():
        source = INVESTIGATIONS / inv_id
        target = INVESTIGATIONS / book_id / inv_id
        if source.exists() and target.exists():
            raise MigrationError(f"Both legacy and book-owned paths exist for {inv_id}")
        if target.exists():
            continue
        if not source.is_dir():
            raise MigrationError(f"Missing legacy investigation directory: {source}")
        declared = read_declared_book(source / "README.md")
        if declared.casefold() != BOOK_LABELS[book_id].casefold():
            raise MigrationError(
                f"{inv_id} ownership mismatch: expected {BOOK_LABELS[book_id]}, README declares {declared}"
            )
        moves.append((source, target))

    decision_source = INVESTIGATIONS / "daniel-hebrew-translation-decisions.md"
    decision_target = INVESTIGATIONS / "daniel" / "daniel-hebrew-translation-decisions.md"
    if decision_source.exists() and decision_target.exists():
        raise MigrationError("Both legacy and Daniel-scoped translation decision files exist")
    if decision_source.exists():
        moves.append((decision_source, decision_target))
    return moves


def atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline=""
    ) as handle:
        handle.write(content)
        temp = Path(handle.name)
    temp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply code patches and move legacy investigation paths")
    args = parser.parse_args()

    originals = {
        MAIN: MAIN.read_text(encoding="utf-8"),
        SERVER: SERVER.read_text(encoding="utf-8"),
        CREATE: CREATE.read_text(encoding="utf-8"),
    }
    patched = {
        MAIN: patch_main(originals[MAIN]),
        SERVER: patch_server(originals[SERVER]),
        CREATE: patch_create(originals[CREATE]),
    }
    moves = preflight_moves()

    print("BOOK-SCOPED INVESTIGATION MIGRATION")
    for path in (MAIN, SERVER, CREATE):
        state = "already patched" if patched[path] == originals[path] else "patch ready"
        print(f"{path.relative_to(ROOT)}: {state}")
    for source, target in moves:
        print(f"MOVE {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")

    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply to migrate.")
        return 0

    for path, content in patched.items():
        if content != originals[path]:
            atomic_write(path, content)

    for source, target in moves:
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)

    # Postconditions.
    for inv_id, book_id in OWNERSHIP.items():
        target = INVESTIGATIONS / book_id / inv_id
        if not target.is_dir():
            raise MigrationError(f"Postcondition failed: {target} is missing")
        if (INVESTIGATIONS / inv_id).exists():
            raise MigrationError(f"Postcondition failed: legacy path remains for {inv_id}")

    print("PASS: investigations are book-scoped; conclusions/statuses were not changed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"BLOCKED: {exc}")
        raise SystemExit(2)
