#!/usr/bin/env python3
"""
MNA Maintenance — Reset To Stage 2 Threshold

Purpose
-------
Archive drifted implementation files and remove generated book outputs so MNA can
restart from the frozen Stage 1–2 factual threshold.

This script preserves:
- MNA/SOURCES/**
- MNA/docs/**
- Stage 1 and Stage 2 documentation
- source Bible texts

This script archives/removes:
- generated datasets for selected books
- generated audits for selected books
- drifted post-threshold scripts

Default behavior is DRY RUN. Use --apply to make changes.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_BOOKS = ["1corintios", "filipenses", "santiago"]

# Scripts beyond the frozen Stage 1–2 threshold are archived, not destroyed.
SCRIPT_DIRS_TO_ARCHIVE = [
    "scripts/stage3",
    "scripts/stage4",
    "scripts/stage5",
    "scripts/stage6",
    "scripts/stage7",
    "scripts/consolidation",
]

# Generated output directories. Source directories are intentionally excluded.
GENERATED_DIRS_TO_SCAN = [
    "datasets",
    "audits",
    "data/g-tokens",
    "data/s-tokens",
    "data/alignments",
]

PRESERVE_PATH_PARTS = {
    "SOURCES",
    "docs",
}


def mna_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def should_preserve(path: Path, mna_root: Path) -> bool:
    try:
        relative = path.relative_to(mna_root)
    except ValueError:
        return True
    return any(part in PRESERVE_PATH_PARTS for part in relative.parts)


def archive_path(src: Path, archive_root: Path, mna_root: Path) -> Path:
    relative = src.relative_to(mna_root)
    return archive_root / relative


def move_to_archive(src: Path, archive_root: Path, mna_root: Path, apply: bool) -> None:
    dest = archive_path(src, archive_root, mna_root)
    print(f"ARCHIVE: {src} -> {dest}")
    if not apply:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"Archive destination already exists: {dest}")
    shutil.move(str(src), str(dest))


def remove_path(path: Path, apply: bool) -> None:
    print(f"REMOVE: {path}")
    if not apply:
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def find_generated_book_paths(mna_root: Path, books: list[str]) -> list[Path]:
    matches: list[Path] = []
    for rel_dir in GENERATED_DIRS_TO_SCAN:
        root = mna_root / rel_dir
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if should_preserve(path, mna_root):
                continue
            name = path.name.lower()
            path_str = str(path.relative_to(mna_root)).lower()
            for book in books:
                book_l = book.lower()
                if name == book_l or name.startswith(f"{book_l}.") or name.startswith(f"{book_l}-") or f"/{book_l}/" in path_str:
                    matches.append(path)
                    break
    # Remove children before parents when deleting.
    return sorted(set(matches), key=lambda p: len(p.parts), reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive drifted MNA files and remove generated book outputs.")
    parser.add_argument("--books", nargs="*", default=DEFAULT_BOOKS, help="Book slugs to remove generated outputs for.")
    parser.add_argument("--apply", action="store_true", help="Actually modify files. Default is dry run.")
    parser.add_argument("--archive-root", default=None, help="Archive directory. Defaults to ../MNA_CHATGPT_FAIL/<timestamp> from MNA root.")
    args = parser.parse_args()

    mna_root = mna_root_from_script()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_root = Path(args.archive_root).expanduser().resolve() if args.archive_root else (mna_root.parent / "MNA_CHATGPT_FAIL" / timestamp)

    print("MNA Maintenance — Reset To Stage 2 Threshold")
    print(f"MNA_ROOT: {mna_root}")
    print(f"ARCHIVE_ROOT: {archive_root}")
    print(f"BOOKS: {', '.join(args.books)}")
    print(f"MODE: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    print("== Archive drifted script directories ==")
    for rel in SCRIPT_DIRS_TO_ARCHIVE:
        path = mna_root / rel
        if path.exists():
            move_to_archive(path, archive_root, mna_root, args.apply)
        else:
            print(f"SKIP missing: {path}")

    print()
    print("== Remove generated book outputs ==")
    for path in find_generated_book_paths(mna_root, args.books):
        remove_path(path, args.apply)

    print()
    print("PRESERVED:")
    print("- MNA/SOURCES/**")
    print("- MNA/docs/**")
    print("- Source Bible texts")
    print()
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
