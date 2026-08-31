#!/usr/bin/env python3
"""Merge missing Writer `>` commentary from apocalipsis-manual-editor.md into manual.md.

Line-preserving: only inserts `>` lines after matching Scripture nodes.
Never rewrites headings, `=`, `###`, or outline structure.
"""
from __future__ import annotations

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

STOCK_SKIP = re.compile(
    r"|".join(
        [
            r"une esta cláusula con la anterior",
            r"no abre otra \w+ suelto",
            r"no abre otra salvación",
            r"no sigue el que\b",
            r"describe a \*",
            r"Primer slot|lo alcanzado|la flecha",
        ]
    ),
    re.I,
)

BODY_START = re.compile(r"^# APOCALIPSIS", re.M)
APPENDIX_START = re.compile(r"^# Apéndice", re.M)
H2_RE = re.compile(r"^(## Apocalipsis .+)$", re.M)


def norm_scripture(line: str) -> str:
    s = re.sub(r"\[\^[^\]]+\]", "", line)
    parts = re.findall(r"\*([^*]+)\*", s)
    if not parts:
        s = re.sub(r"^#+\s*", "", s.strip())
        s = re.sub(r"^[-+]\s*", "", s)
        return re.sub(r"\s+", " ", s).strip().lower()
    return re.sub(r"\s+", " ", " ".join(parts)).strip().lower()


def line_kind(line: str) -> str:
    s = line.lstrip()
    if s.startswith("#### "):
        return "h4"
    if s.startswith("- "):
        return "bullet"
    if s.startswith("+ "):
        return "phrase"
    if s.startswith(">"):
        return "comment"
    if s.startswith("### "):
        return "h3"
    if s.startswith("= "):
        return "eq"
    if s.startswith("* "):
        return "star"
    if s.startswith("## "):
        return "h2"
    return "other"


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def is_banned(comment: str) -> bool:
    body = comment.lstrip().lstrip(">").strip()
    if not body:
        return True
    if STOCK_SKIP.search(body):
        return True
    if body.startswith("* ") and "→" in body:
        return True
    return False


def similar(a: str, b: str, threshold: float = 0.82) -> bool:
    na = re.sub(r"<[^>]+>", "", a.lower())
    nb = re.sub(r"<[^>]+>", "", b.lower())
    na = re.sub(r"\[\^[^\]]+\]", "", na)
    nb = re.sub(r"\[\^[^\]]+\]", "", nb)
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def format_comment(raw: str, indent: int) -> str:
    body = raw.lstrip()
    if body.startswith(">"):
        body = body[1:].lstrip()
    return " " * indent + "> " + body


def scripture_comments_after(lines: list[str], idx: int) -> list[str]:
    """Comments immediately following scripture line at idx (before next outline node)."""
    base_indent = indent_of(lines[idx])
    out: list[str] = []
    j = idx + 1
    while j < len(lines):
        line = lines[j]
        kind = line_kind(line)
        if kind == "comment":
            out.append(line.rstrip())
            j += 1
            continue
        if kind == "star":
            j += 1
            continue
        if kind in ("h4", "bullet", "phrase"):
            if indent_of(line) <= base_indent:
                break
            break
        if kind in ("h3", "h2", "eq"):
            break
        if kind == "other" and line.strip() == "":
            j += 1
            continue
        break
    return out


def build_anchor_list(lines: list[str]) -> list[tuple[int, str, int]]:
    """(line_index, key, indent) for each scripture anchor in order."""
    anchors: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        if line_kind(line) in ("h4", "bullet", "phrase"):
            anchors.append((i, norm_scripture(line), indent_of(line)))
    return anchors


def align_anchor_comments(
    manual_lines: list[str], editor_lines: list[str], stats: dict
) -> list[str]:
    m_anchors = build_anchor_list(manual_lines)
    e_anchors = build_anchor_list(editor_lines)

    # Greedy sequence alignment by key
    insertions: dict[int, list[str]] = {}
    ei = 0
    for mi, mkey, mind in m_anchors:
        best_ei = None
        best_score = 0.0
        for k in range(ei, min(ei + 8, len(e_anchors))):
            ekey = e_anchors[k][1]
            score = SequenceMatcher(None, mkey, ekey).ratio()
            if score > best_score:
                best_score = score
                best_ei = k
        if best_ei is None or best_score < 0.72:
            continue
        ei = best_ei
        eidx, _, eind = e_anchors[ei]
        ed_comments = scripture_comments_after(editor_lines, eidx)
        mn_comments = scripture_comments_after(manual_lines, mi)
        new_comments: list[str] = []
        for ec in ed_comments:
            if is_banned(ec):
                stats["skipped_banned"] += 1
                continue
            if any(similar(ec, mc) for mc in mn_comments + new_comments):
                stats["skipped_dup"] += 1
                continue
            new_comments.append(format_comment(ec, mind + 2))
            stats["inserted"] += 1
        if new_comments:
            insertions[mi] = new_comments
        ei += 1

    out: list[str] = []
    skip_until = -1
    for i, line in enumerate(manual_lines):
        if i <= skip_until:
            continue
        out.append(line)
        if i in insertions:
            j = i + 1
            while j < len(manual_lines) and line_kind(manual_lines[j]) == "comment":
                out.append(manual_lines[j])
                j += 1
            skip_until = j - 1
            out.extend(insertions[i])
    return out


def split_h2_sections(text: str) -> tuple[str, list[tuple[str, str]], str]:
    m = BODY_START.search(text)
    if not m:
        return text, [], ""
    pre = text[: m.start()]
    rest = text[m.start() :]
    m2 = APPENDIX_START.search(rest)
    if m2:
        body = rest[: m2.start()]
        post = rest[m2.start() :]
    else:
        body = rest
        post = ""

    sections: list[tuple[str, str]] = []
    matches = list(H2_RE.finditer(body))
    for i, hm in enumerate(matches):
        title = hm.group(1)
        start = hm.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((title, body[start:end]))

    h1_prefix = body[: matches[0].start()] if matches else ""
    return pre + h1_prefix, sections, post


def merge_section(manual_chunk: str, editor_chunk: str, stats: dict) -> str:
    manual_lines = manual_chunk.splitlines()
    editor_lines = editor_chunk.splitlines()
    merged = align_anchor_comments(manual_lines, editor_lines, stats)
    text = "\n".join(merged)
    if manual_chunk.endswith("\n"):
        text += "\n"
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", type=Path, required=True)
    ap.add_argument("--editor", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manual_text = args.manual.read_text(encoding="utf-8")
    editor_text = args.editor.read_text(encoding="utf-8")

    pre, m_sections, post = split_h2_sections(manual_text)
    _, e_sections, _ = split_h2_sections(editor_text)
    e_map = {title: chunk for title, chunk in e_sections}

    stats = {"inserted": 0, "skipped_banned": 0, "skipped_dup": 0, "sections": 0, "missing_editor": 0}

    merged_parts = [pre]
    for title, m_chunk in m_sections:
        e_chunk = e_map.get(title)
        if not e_chunk:
            key = title.split(" ", 2)[-1][:30] if " " in title else title
            for et, ec in e_sections:
                if key in et:
                    e_chunk = ec
                    break
        if e_chunk:
            merged_parts.append(merge_section(m_chunk, e_chunk, stats))
            stats["sections"] += 1
        else:
            merged_parts.append(m_chunk)
            stats["missing_editor"] += 1

    merged_parts.append(post)
    out_text = "".join(merged_parts)

    if args.dry_run:
        print(f"Would insert {stats['inserted']} comments")
        print(f"Skipped banned: {stats['skipped_banned']}, dup: {stats['skipped_dup']}")
        return 0

    out_path = args.out or args.manual
    out_path.write_text(out_text, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Inserted {stats['inserted']} comments across {stats['sections']} H2 sections")
    print(f"Skipped banned: {stats['skipped_banned']}, near-dup: {stats['skipped_dup']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
