#!/usr/bin/env python3

import argparse
import csv
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validate_mna import parse_mna_markdown, tokenize_spanish_words  # noqa: E402


HEADER = ["BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"]


@dataclass
class Row:
    book: str
    chapter: str
    verse: str
    g_idx: str
    greek: str
    nbla_indexes: list[str]
    alignment: str


def strip_diacritics(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value)
        if unicodedata.category(ch) != "Mn"
    )


def normalize(value: str) -> str:
    return strip_diacritics(value.strip().lower())


def read_tokens(path: Path) -> list[tuple[str, str]]:
    tokens = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, token = line.split(maxsplit=1)
            tokens.append((idx.zfill(2), token))
    return tokens


def words_for_span(span: str) -> list[str]:
    span = span.strip()
    if span.startswith("(") and span.endswith(")"):
        return []
    return [normalize(word) for word in tokenize_spanish_words(span)]


def find_unused_sequence(words: list[str], nbla_words: list[tuple[str, str]], used: set[str]) -> list[str]:
    if not words:
        return []
    normalized = [normalize(token) for _idx, token in nbla_words]
    for start in range(0, len(normalized) - len(words) + 1):
        indexes = [nbla_words[i][0] for i in range(start, start + len(words))]
        if any(idx in used for idx in indexes):
            continue
        if normalized[start:start + len(words)] == words:
            return indexes
    return []


def compress_indexes(indexes: list[str]) -> str:
    if not indexes:
        return "-"
    nums = sorted({int(idx) for idx in indexes})
    parts = []
    start = prev = nums[0]
    for num in nums[1:]:
        if num == prev + 1:
            prev = num
            continue
        parts.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
        start = prev = num
    parts.append(f"{start:02d}" if start == prev else f"{start:02d}-{prev:02d}")
    return ",".join(parts)


def text_for_indexes(indexes: list[str], nbla_by_idx: dict[str, str]) -> str:
    if not indexes:
        return "-"
    return " ".join(nbla_by_idx[idx] for idx in sorted(indexes, key=int))


def tsv_alignment_type(mna_type: str) -> str:
    if mna_type == "merged-backward":
        return "shared"
    return mna_type


def ref_parts(ref: str) -> tuple[str, str]:
    match = re.search(r"(\d+):(\d+)$", ref)
    if not match:
        raise ValueError(f"Cannot parse verse reference: {ref}")
    return match.group(1), match.group(2)


def attach_unused_tokens(rows: list[Row], nbla_words: list[tuple[str, str]], used: set[str]) -> None:
    unused = [idx for idx, _token in nbla_words if idx not in used]
    for idx in unused:
        idx_num = int(idx)
        candidates = [row for row in rows if row.alignment != "missing" and row.nbla_indexes]
        if not candidates:
            continue
        target = min(
            candidates,
            key=lambda row: min(abs(int(existing) - idx_num) for existing in row.nbla_indexes),
        )
        target.nbla_indexes.append(idx)
        used.add(idx)
        if target.alignment == "direct":
            target.alignment = "expanded"


def convert_verse(verse, g_path: Path, s_path: Path) -> list[Row]:
    greek_tokens = read_tokens(g_path)
    nbla_words = read_tokens(s_path)
    nbla_by_idx = dict(nbla_words)
    used: set[str] = set()
    rows: list[Row] = []
    previous_span_indexes: dict[str, list[str]] = {}
    chapter, verse_no = ref_parts(verse.ref)

    for i, alignment in enumerate(verse.alignments):
        g_idx, greek = greek_tokens[i]
        words = words_for_span(alignment.span)
        indexes: list[str]
        if alignment.atype == "missing" or not words:
            indexes = []
        elif alignment.atype == "merged-backward" and alignment.span in previous_span_indexes:
            indexes = previous_span_indexes[alignment.span]
        else:
            indexes = find_unused_sequence(words, nbla_words, used)
            if not indexes:
                raise ValueError(f"{verse.ref}: could not match NBLA span: {alignment.span}")
            used.update(indexes)
            previous_span_indexes[alignment.span] = indexes

        rows.append(
            Row(
                book="1cor",
                chapter=chapter,
                verse=verse_no,
                g_idx=g_idx,
                greek=greek,
                nbla_indexes=list(indexes),
                alignment=tsv_alignment_type(alignment.atype),
            )
        )

    attach_unused_tokens(rows, nbla_words, used)

    for row in rows:
        row.nbla_indexes = sorted(set(row.nbla_indexes), key=int)

    return rows


def write_tsv(path: Path, rows: list[Row], s_path: Path) -> None:
    nbla_by_idx = dict(read_tokens(s_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow([
                row.book,
                row.chapter,
                row.verse,
                row.g_idx,
                row.greek,
                compress_indexes(row.nbla_indexes),
                text_for_indexes(row.nbla_indexes, nbla_by_idx),
                row.alignment,
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert locked MNA Markdown to alignment TSV files.")
    parser.add_argument("mna_path", type=Path)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "alignments")
    parser.add_argument("--g-dir", type=Path, default=ROOT / "data" / "g-tokens")
    parser.add_argument("--s-dir", type=Path, default=ROOT / "data" / "s-tokens")
    args = parser.parse_args()

    text = args.mna_path.read_text(encoding="utf-8")
    verses = parse_mna_markdown(text)
    for verse in verses:
        chapter, verse_no = ref_parts(verse.ref)
        if chapter != str(args.chapter):
            continue
        stem = f"1corintios-{chapter}-{verse_no}"
        rows = convert_verse(verse, args.g_dir / f"{stem}.txt", args.s_dir / f"{stem}.txt")
        write_tsv(args.out_dir / f"{stem}.tsv", rows, args.s_dir / f"{stem}.txt")
        print(f"WROTE {args.out_dir / f'{stem}.tsv'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
