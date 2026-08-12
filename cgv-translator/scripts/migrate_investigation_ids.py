#!/usr/bin/env python3
"""Migrate investigation IDs to INV-<book number>-<book-local sequence>.

Canonical examples:
  Daniel     -> INV-27-0001
  Zechariah  -> INV-38-0001
  Titus      -> INV-56-0001

Dry-run by default. Use --apply to perform the migration.

This is intentionally narrow and guarded. It:
- renames only the eight known existing investigation directories;
- preserves all investigation contents, including locally generated evidence;
- records each legacy ID in history.md;
- updates active Translator ID parsing/allocation/routing;
- scopes gate-policy lookup to the active book;
- refuses unknown books instead of silently falling back to Titus;
- never reads or writes .DS_Store contents.

The migration does not change translation decisions, Spanish, alignment, G0A, or
G0B state.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVESTIGATIONS = ROOT / "investigations"


@dataclass(frozen=True)
class Move:
    book: str
    old: str
    new: str


MOVES = (
    Move("titus", "INV-0001", "INV-56-0001"),
    Move("titus", "INV-0002", "INV-56-0002"),
    Move("titus", "INV-0003", "INV-56-0003"),
    Move("titus", "INV-0004", "INV-56-0004"),
    Move("titus", "INV-0005", "INV-56-0005"),
    Move("titus", "INV-0006", "INV-56-0006"),
    Move("daniel", "INV-0007", "INV-27-0001"),
    Move("daniel", "INV-0008", "INV-27-0002"),
)


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} exact match(es), found {count}")
    return text.replace(old, new)


def regex_sub(text: str, pattern: str, replacement: str, label: str, expected: int = 1, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=flags)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} regex match(es), found {count}")
    return updated


def patch_create_investigation(text: str) -> str:
    text = replace_exact(
        text,
        'import { join } from "node:path";\n',
        'import { join } from "node:path";\nimport { findBook } from "../data/bookCatalog.js";\n',
        "createInvestigation catalog import",
    )

    old = '''function investigationNumber(id = "") {\n  const match = String(id).match(/^INV-(\\d{4})$/);\n  return match ? Number(match[1]) : 0;\n}\n'''
    new = '''const INVESTIGATION_ID_RE = /^INV-(\\d{2})-(\\d{4})$/;\n\nexport function parseInvestigationId(id = "") {\n  const match = String(id).match(INVESTIGATION_ID_RE);\n  if (!match) return null;\n  return {\n    bookNumber: Number(match[1]),\n    sequence: Number(match[2])\n  };\n}\n\nexport function formatInvestigationId(bookNumber, sequence) {\n  const book = Number(bookNumber);\n  const item = Number(sequence);\n  if (!Number.isInteger(book) || book < 1 || book > 66) {\n    throw new Error("canonical book number must be an integer from 1 through 66");\n  }\n  if (!Number.isInteger(item) || item < 1 || item > 9999) {\n    throw new Error("investigation sequence must be an integer from 1 through 9999");\n  }\n  return `INV-${String(book).padStart(2, "0")}-${String(item).padStart(4, "0")}`;\n}\n\nfunction investigationNumber(id = "") {\n  return parseInvestigationId(id)?.sequence || 0;\n}\n'''
    text = replace_exact(text, old, new, "createInvestigation canonical ID helpers")

    text = replace_exact(
        text,
        '.filter(entry => entry.isDirectory() && /^INV-\\d{4}$/.test(entry.name))',
        '.filter(entry => entry.isDirectory() && INVESTIGATION_ID_RE.test(entry.name))',
        "createInvestigation canonical list filter",
    )

    text = regex_sub(
        text,
        r'''\nasync function listAllInvestigationIds\(investigationsDir\) \{.*?\n\}\n\nexport async function allocateNextInvestigationId\(investigationsDir\) \{\n  const ids = await listAllInvestigationIds\(investigationsDir\);\n  const next = Math\.max\(0, \.\.\.ids\.map\(investigationNumber\)\) \+ 1;\n  return `INV-\$\{String\(next\)\.padStart\(4, "0"\)\}`;\n\}\n''',
        '''\nexport async function allocateNextInvestigationId(bookInvestigationsDir, bookNumber) {\n  const canonicalBookNumber = Number(bookNumber);\n  const ids = await listInvestigationIds(bookInvestigationsDir);\n  const localIds = ids.filter(id => parseInvestigationId(id)?.bookNumber === canonicalBookNumber);\n  const next = Math.max(0, ...localIds.map(investigationNumber)) + 1;\n  return formatInvestigationId(canonicalBookNumber, next);\n}\n''',
        "createInvestigation book-local allocator",
        flags=re.S,
    )

    text = replace_exact(
        text,
        '  const number = id.replace(/^INV-/u, "");\n',
        "",
        "createInvestigation obsolete display number",
    )
    text = replace_exact(
        text,
        '  const readme = `# Investigation ${number}\n',
        '  const readme = `# Investigation ${id}\n',
        "createInvestigation canonical README heading",
    )

    text = replace_exact(
        text,
        '''Preferred Rendering: \nConfidence: \n\n### Reason\n''',
        '''Preferred Rendering: \nConfidence: \nApproval Authority: \nApproved By: \nApproved At: \n\n### Reason\n''',
        "createInvestigation approval provenance scaffold",
    )

    text = replace_exact(
        text,
        'Investigation created from ${reference || "translator request"} for ${subject}.\n',
        'Investigation ${id} created from ${reference || "translator request"} for ${subject}.\n',
        "createInvestigation history identity",
    )

    old = '''  const bookId = String(body.book || "").trim().toLowerCase();\n  if (!/^[a-z0-9][a-z0-9-]*$/.test(bookId)) {\n    throw new Error("book id is required for a book-owned investigation");\n  }\n  const book = String(body.bookLabel || "").trim() || bookFromReference(reference);\n  const investigationsDir = join(rootDir, "investigations");\n  const bookInvestigationsDir = join(investigationsDir, bookId);\n'''
    new = '''  const bookId = String(body.book || "").trim().toLowerCase();\n  if (!/^[a-z0-9][a-z0-9-]*$/.test(bookId)) {\n    throw new Error("book id is required for a book-owned investigation");\n  }\n  const bookInfo = findBook(bookId);\n  if (!bookInfo) {\n    throw new Error(`unknown Translator book: ${bookId}`);\n  }\n  const book = String(body.bookLabel || "").trim() || bookInfo.label;\n  const investigationsDir = join(rootDir, "investigations");\n  const bookInvestigationsDir = join(investigationsDir, bookInfo.id);\n'''
    text = replace_exact(text, old, new, "createInvestigation canonical book validation")

    text = replace_exact(
        text,
        '  const id = await allocateNextInvestigationId(investigationsDir);\n',
        '  const id = await allocateNextInvestigationId(bookInvestigationsDir, bookInfo.number);\n',
        "createInvestigation book-local allocation call",
    )

    text = replace_exact(text, '      book: bookId\n', '      book: bookInfo.id\n', "createInvestigation existing book result")
    text = replace_exact(text, '    book: bookId\n', '    book: bookInfo.id\n', "createInvestigation created book result")

    return text


def patch_main(text: str) -> str:
    expected_counts = {
        "INV-0001": 4,
        "INV-0002": 2,
        "INV-0003": 3,
    }
    replacements = {
        "INV-0001": "INV-56-0001",
        "INV-0002": "INV-56-0002",
        "INV-0003": "INV-56-0003",
    }
    for old, expected in expected_counts.items():
        text = replace_exact(text, old, replacements[old], f"main active reference {old}", expected)

    text = replace_exact(
        text,
        '    reference: phrase.reference,\n    greek: phraseGreekText(phrase),\n',
        '    book: state.bookId,\n    reference: phrase.reference,\n    greek: phraseGreekText(phrase),\n',
        "main pipeline book payload",
    )

    text = replace_exact(
        text,
        '  const match = window.location.hash.match(/^#investigation\\/(INV-\\d{4})$/);\n  return match?.[1] || "INV-56-0001";\n',
        '  const match = window.location.hash.match(/^#investigation\\/(INV-\\d{2}-\\d{4})$/);\n  return match?.[1] || state.investigation;\n',
        "main canonical hash parser",
    )
    return text


def patch_server(text: str) -> str:
    text = replace_exact(
        text,
        '''function resolveBook(bookId) {\n  return findBook(bookId) || findBook("titus");\n}\n''',
        '''function resolveBook(bookId) {\n  const book = findBook(bookId);\n  if (!book) {\n    throw new Error(`Unknown Translator book: ${bookId}`);\n  }\n  return book;\n}\n''',
        "server remove Titus fallback",
    )

    old = '''function safeInvestigationPath(id) {\n  if (!/^INV-\\d{4}$/.test(id)) {\n    throw new Error("Invalid investigation ID");\n  }\n\n  const legacy = join(investigationsDir, id);\n  if (existsSync(legacy)) return legacy;\n\n  const bookDirs = readdirSync(investigationsDir, { withFileTypes: true })\n    .filter(entry => entry.isDirectory() && !/^INV-\\d{4}$/.test(entry.name));\n  for (const entry of bookDirs) {\n    const candidate = join(investigationsDir, entry.name, id);\n    if (existsSync(candidate)) return candidate;\n  }\n\n  throw new Error(`Investigation not found: ${id}`);\n}\n'''
    new = '''function investigationBookFromId(id) {\n  const match = String(id || "").match(/^INV-(\\d{2})-(\\d{4})$/);\n  if (!match) {\n    throw new Error("Invalid investigation ID");\n  }\n  const bookNumber = Number(match[1]);\n  const book = allTranslatorBooks().find(item => Number(item.number) === bookNumber);\n  if (!book) {\n    throw new Error(`Unknown investigation book number: ${match[1]}`);\n  }\n  return book;\n}\n\nfunction safeInvestigationPath(id) {\n  const book = investigationBookFromId(id);\n  const candidate = join(investigationsDir, book.id, id);\n  if (existsSync(candidate)) return candidate;\n  throw new Error(`Investigation not found: ${id}`);\n}\n'''
    text = replace_exact(text, old, new, "server canonical investigation path")

    text = replace_exact(
        text,
        '''      const investigations = entries\n        .filter(entry => entry.isDirectory() && /^INV-\\d{4}$/.test(entry.name))\n        .map(entry => entry.name)\n        .sort();\n''',
        '''      const bookNumber = String(resolveBook(bookId).number).padStart(2, "0");\n      const investigations = entries\n        .filter(entry => entry.isDirectory() && /^INV-\\d{2}-\\d{4}$/.test(entry.name))\n        .filter(entry => entry.name.startsWith(`INV-${bookNumber}-`))\n        .map(entry => entry.name)\n        .sort();\n''',
        "server book-prefix list filter",
    )

    remaining = text.count(r"INV-\d{4}")
    if remaining != 5:
        raise RuntimeError(f"server legacy route regexes: expected 5 remaining occurrences, found {remaining}")
    text = text.replace(r"INV-\d{4}", r"INV-\d{2}-\d{4}")

    text = replace_exact(
        text,
        '''    const evidenceAliasMatch = url.pathname.match(/^\\/(?:investigations\\/(INV-\\d{2}-\\d{4})\\/)?evidence\\/([^/]+)$/);\n    if (request.method === "GET" && evidenceAliasMatch) {\n      const [, id = "INV-0001", fileName] = evidenceAliasMatch;\n''',
        '''    const evidenceAliasMatch = url.pathname.match(/^\\/investigations\\/(INV-\\d{2}-\\d{4})\\/evidence\\/([^/]+)$/);\n    if (request.method === "GET" && evidenceAliasMatch) {\n      const [, id, fileName] = evidenceAliasMatch;\n''',
        "server canonical evidence alias",
    )

    text = replace_exact(
        text,
        '''    const analysis = await analyzePhraseGates({\n      rootDir,\n      reference: payload.reference,\n''',
        '''    const analysis = await analyzePhraseGates({\n      rootDir,\n      bookId: String(payload.book || "").trim().toLowerCase(),\n      reference: payload.reference,\n''',
        "server gate analysis book scope",
        expected=2,
    )
    return text


def patch_analyze_gates(text: str) -> str:
    text = replace_exact(
        text,
        '''      preferredRendering: fields["preferred rendering"] || "",\n      confidence: fields.confidence || "",\n      reason: reasonMatch ? reasonMatch[1].trim() : ""\n''',
        '''      preferredRendering: fields["preferred rendering"] || "",\n      confidence: fields.confidence || "",\n      approvalAuthority: fields["approval authority"] || "",\n      approvedBy: fields["approved by"] || "",\n      approvedAt: fields["approved at"] || "",\n      reason: reasonMatch ? reasonMatch[1].trim() : ""\n''',
        "analyzeGates approval provenance parser",
    )

    old = '''export async function loadLemmaPolicyIndex(rootDir) {\n  const investigationsDir = join(rootDir, "investigations");\n  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);\n  const approved = [];\n  const openInvestigations = [];\n\n  for (const entry of entries) {\n    if (!entry.isDirectory() || !/^INV-\\d{4}$/.test(entry.name)) continue;\n    const markdown = await readFile(join(investigationsDir, entry.name, "decision.md"), "utf8").catch(() => "");\n'''
    new = '''export async function loadLemmaPolicyIndex(rootDir, bookId) {\n  const canonicalBookId = String(bookId || "").trim().toLowerCase();\n  if (!/^[a-z0-9][a-z0-9-]*$/.test(canonicalBookId)) {\n    throw new Error("book id is required for investigation policy lookup");\n  }\n  const investigationsDir = join(rootDir, "investigations", canonicalBookId);\n  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);\n  const approved = [];\n  const openInvestigations = [];\n\n  for (const entry of entries) {\n    if (!entry.isDirectory() || !/^INV-\\d{2}-\\d{4}$/.test(entry.name)) continue;\n    const markdown = await readFile(join(investigationsDir, entry.name, "decision.md"), "utf8").catch(() => "");\n'''
    text = replace_exact(text, old, new, "analyzeGates book-scoped investigation loader")

    text = replace_exact(
        text,
        '''      reason: latest.reason || "",\n      status: latest.status || "Draft"\n    };\n\n    openInvestigations.push(record);\n    if (/^approved$/i.test(record.status) && record.lemma && record.preferredRendering) {\n      approved.push(record);\n    }\n''',
        '''      reason: latest.reason || "",\n      status: latest.status || "Draft",\n      approvalAuthority: latest.approvalAuthority || "",\n      approvedBy: latest.approvedBy || "",\n      approvedAt: latest.approvedAt || ""\n    };\n    record.humanApproved = /^approved$/i.test(record.status)\n      && record.approvalAuthority === "human"\n      && Boolean(record.approvedBy)\n      && Boolean(record.approvedAt);\n\n    openInvestigations.push(record);\n    if (record.humanApproved && record.lemma && record.preferredRendering) {\n      approved.push(record);\n    }\n''',
        "analyzeGates human-approved policy filter",
    )

    text = replace_exact(
        text,
        '''export async function loadApprovedLemmaPolicies(rootDir) {\n  const { approved } = await loadLemmaPolicyIndex(rootDir);\n''',
        '''export async function loadApprovedLemmaPolicies(rootDir, bookId) {\n  const { approved } = await loadLemmaPolicyIndex(rootDir, bookId);\n''',
        "analyzeGates approved policy signature",
    )

    text = replace_exact(
        text,
        '    const openIsDraft = openInv && !/^approved$/i.test(openInv.status || "");\n',
        '    const openIsDraft = openInv && !openInv.humanApproved;\n',
        "analyzeGates unattributed approval remains blocking",
    )

    text = replace_exact(
        text,
        '''export async function analyzePhraseGates({\n  rootDir,\n  reference,\n''',
        '''export async function analyzePhraseGates({\n  rootDir,\n  bookId,\n  reference,\n''',
        "analyzeGates bookId signature",
    )
    text = replace_exact(
        text,
        '  const { approved, openInvestigations } = await loadLemmaPolicyIndex(rootDir);\n',
        '  const { approved, openInvestigations } = await loadLemmaPolicyIndex(rootDir, bookId);\n',
        "analyzeGates book-scoped policy call",
    )
    return text


def migration_history(existing: str, old_id: str, new_id: str) -> str:
    marker = f"Legacy ID: {old_id}"
    if marker in existing:
        raise RuntimeError(f"history already contains migration marker for {old_id}")
    stamp = date.today().isoformat()
    block = (
        f"\n## {stamp} — Investigation ID migration\n\n"
        f"Legacy ID: {old_id}\n\n"
        f"Canonical ID: {new_id}\n\n"
        "The investigation content and decision history were preserved; only its canonical identifier changed.\n"
    )
    return existing.rstrip() + "\n" + block


def prepare_investigation_files(move: Move) -> dict[Path, str]:
    source = INVESTIGATIONS / move.book / move.old
    updates: dict[Path, str] = {}
    for path in source.rglob("*"):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace(move.old, move.new)
        if path.name == "README.md" and path.parent == source:
            legacy_number = move.old.removeprefix("INV-")
            first = f"# Investigation {legacy_number}"
            if text.startswith(first):
                text = f"# Investigation {move.new}" + text[len(first):]
        if path.name == "history.md" and path.parent == source:
            text = migration_history(text, move.old, move.new)
        updates[path.relative_to(source)] = text
    return updates


def validate_moves() -> None:
    for move in MOVES:
        source = INVESTIGATIONS / move.book / move.old
        target = INVESTIGATIONS / move.book / move.new
        if not source.is_dir():
            raise RuntimeError(f"missing expected source investigation: {source.relative_to(ROOT)}")
        if target.exists():
            raise RuntimeError(f"target already exists: {target.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply migration. Default is dry-run.")
    args = parser.parse_args()

    validate_moves()

    code_targets = {
        ROOT / "src" / "investigations" / "createInvestigation.js": patch_create_investigation,
        ROOT / "public" / "main.js": patch_main,
        ROOT / "server.js": patch_server,
        ROOT / "src" / "pipeline" / "analyzeGates.js": patch_analyze_gates,
    }
    originals: dict[Path, str] = {}
    patched: dict[Path, str] = {}
    for path, patcher in code_targets.items():
        original = path.read_text(encoding="utf-8")
        updated = patcher(original)
        if updated == original:
            raise RuntimeError(f"{path.relative_to(ROOT)}: patch produced no change")
        originals[path] = original
        patched[path] = updated

    investigation_updates = {move: prepare_investigation_files(move) for move in MOVES}

    print("CANONICAL INVESTIGATION ID MIGRATION")
    for move in MOVES:
        print(f"{move.book}: {move.old} -> {move.new}")
    for path in code_targets:
        print(f"patch ready: {path.relative_to(ROOT)}")
    print("policy lookup: book-scoped + human-approved only")
    print("unknown book fallback: removed")

    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply to migrate.")
        return 0

    completed_moves: list[Move] = []
    try:
        for move in MOVES:
            source = INVESTIGATIONS / move.book / move.old
            target = INVESTIGATIONS / move.book / move.new
            source.rename(target)
            completed_moves.append(move)
            for relative, text in investigation_updates[move].items():
                (target / relative).write_text(text, encoding="utf-8")

        for path, text in patched.items():
            path.write_text(text, encoding="utf-8")
    except Exception:
        # Best-effort rollback. Restore code first, then directory names.
        for path, text in originals.items():
            try:
                path.write_text(text, encoding="utf-8")
            except Exception:
                pass
        for move in reversed(completed_moves):
            source = INVESTIGATIONS / move.book / move.old
            target = INVESTIGATIONS / move.book / move.new
            try:
                if target.exists() and not source.exists():
                    target.rename(source)
            except Exception:
                pass
        raise

    print("PASS: investigation IDs migrated to canonical book-number identities.")
    print("NOTE: .DS_Store contents were not read or written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
