#!/usr/bin/env python3

import sys
import yaml
import shutil
from pathlib import Path

HEADER = ["BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"]

SEARCH_WINDOW = 8
OUTPUT_DIR = Path("data/alignments")


def load_tokens(path):
    tokens = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"{path}:{line_no}: invalid token line: {line}")

            idx, tok = parts
            tokens.append((idx.zfill(2), tok))

    return tokens


def load_rules(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return []

    return data.get("rules", [])


def parse_ref_from_filename(path):
    stem = Path(path).stem
    parts = stem.split("-")

    if len(parts) != 3:
        raise ValueError(
            f"Cannot infer BOOK/CH/VS from filename '{stem}'. "
            "Expected format like 1corintios-7-17.txt"
        )

    return parts[0], parts[1], parts[2]


def rule_nbla_words(rule):
    action = rule.get("action", {})
    nbla = action.get("nbla")

    if nbla is None:
        return []

    if isinstance(nbla, str):
        return [nbla]

    return list(nbla)


def match_rule(greek_tokens, i, rules):
    sorted_rules = sorted(
        rules,
        key=lambda r: (
            -int(r.get("priority", 0)),
            -len(r.get("match", {}).get("greek", [])),
        ),
    )

    for rule in sorted_rules:
        pattern = rule.get("match", {}).get("greek", [])
        if not pattern:
            continue

        if i + len(pattern) > len(greek_tokens):
            continue

        segment = [tok for _, tok in greek_tokens[i : i + len(pattern)]]

        if segment == pattern:
            return rule

    return None


def find_nbla_phrase(s_tokens, start_i, words, window=SEARCH_WINDOW):
    if not words:
        return None

    phrase_len = len(words)
    max_start = min(len(s_tokens) - phrase_len, start_i + window)

    if max_start < start_i:
        return None

    for i in range(start_i, max_start + 1):
        segment = [tok for _, tok in s_tokens[i : i + phrase_len]]
        if segment == words:
            return i

    return None


def span_from_tokens(s_tokens, start_i, count):
    idxs = []
    words = []

    for i in range(start_i, min(start_i + count, len(s_tokens))):
        idxs.append(s_tokens[i][0])
        words.append(s_tokens[i][1])

    return ",".join(idxs) if idxs else "-", " ".join(words) if words else "-"


def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(HEADER) + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")


def suggest(book, ch, vs, g_tokens, s_tokens, rules):
    rows = []
    g_i = 0
    s_i = 0

    while g_i < len(g_tokens):
        rule = match_rule(g_tokens, g_i, rules)

        if rule:
            action = rule.get("action", {})
            alignment_type = action.get("type", "direct")
            pattern = rule.get("match", {}).get("greek", [])
            span_len = len(pattern)

            if alignment_type == "missing":
                for j in range(span_len):
                    g_idx, g_tok = g_tokens[g_i + j]
                    rows.append([book, ch, vs, g_idx, g_tok, "-", "-", "missing"])
                g_i += span_len
                continue

            nbla_words = rule_nbla_words(rule)
            consume = int(action.get("consume", len(nbla_words) if nbla_words else 1))

            # Prevent runaway singleton expansions
            if span_len == 1 and consume > 4:
                rule = None

            if consume <= 0:
                for j in range(span_len):
                    g_idx, g_tok = g_tokens[g_i + j]
                    rows.append([book, ch, vs, g_idx, g_tok, "-", "-", "missing"])
                g_i += span_len
                continue

            anchor_i = find_nbla_phrase(s_tokens, s_i, nbla_words) if nbla_words else None

            if anchor_i is not None:
                s_i = anchor_i

            nbla_idx, nbla_text = span_from_tokens(s_tokens, s_i, consume)

            if nbla_idx == "-" or nbla_text == "-":
                for j in range(span_len):
                    g_idx, g_tok = g_tokens[g_i + j]
                    rows.append([book, ch, vs, g_idx, g_tok, "-", "-", "missing"])
                g_i += span_len
                continue

            s_i += consume

            for j in range(span_len):
                g_idx, g_tok = g_tokens[g_i + j]
                row_alignment = alignment_type if j == 0 else "shared"
                rows.append([book, ch, vs, g_idx, g_tok, nbla_idx, nbla_text, row_alignment])

            g_i += span_len
            continue

        g_idx, g_tok = g_tokens[g_i]

        if s_i < len(s_tokens):
            nbla_idx = s_tokens[s_i][0]
            nbla_text = s_tokens[s_i][1]
            s_i += 1
            rows.append([book, ch, vs, g_idx, g_tok, nbla_idx, nbla_text, "direct"])
        else:
            rows.append([book, ch, vs, g_idx, g_tok, "-", "-", "missing"])

        g_i += 1

    return rows


def main():
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "  python3 scripts/suggest_alignment_v2.py "
            "data/g-tokens/1corintios-8-1.txt "
            "data/s-tokens/1corintios-8-1.txt "
            "data/rules/alignment_rules.yaml",
            file=sys.stderr,
        )
        sys.exit(2)

    greek_path = sys.argv[1]
    spanish_path = sys.argv[2]
    rules_path = sys.argv[3]

    book, ch, vs = parse_ref_from_filename(greek_path)

    g_tokens = load_tokens(greek_path)
    s_tokens = load_tokens(spanish_path)
    rules = load_rules(rules_path)

    rows = suggest(book, ch, vs, g_tokens, s_tokens, rules)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base_name = f"{book}-{ch}-{vs}"
    original_path = OUTPUT_DIR / f"{base_name}.original.tsv"
    corrected_path = OUTPUT_DIR / f"{base_name}.tsv"

    write_tsv(original_path, rows)

    print(f"✔ Wrote: {original_path}")

    if not corrected_path.exists():
        shutil.copy(original_path, corrected_path)
        print(f"✔ Created: {corrected_path}")
    else:
        print(f"ℹ Existing corrected TSV retained: {corrected_path}")


if __name__ == "__main__":
    main()