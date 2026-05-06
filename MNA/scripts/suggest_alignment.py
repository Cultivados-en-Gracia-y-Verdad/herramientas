#!/usr/bin/env python3

import sys
import yaml
from pathlib import Path

HEADER = ["BOOK", "CH", "VS", "G_IDX", "GREEK", "NBLA_IDX", "NBLA_TEXT", "ALIGNMENT"]


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


def match_rule(greek_tokens, i, rules):
    sorted_rules = sorted(
        rules,
        key=lambda r: (-int(r.get("priority", 0)), -len(r.get("match", {}).get("greek", []))),
    )

    for rule in sorted_rules:
        pattern = rule.get("match", {}).get("greek", [])
        if not pattern:
            continue
        if i + len(pattern) > len(greek_tokens):
            continue

        segment = [tok for _, tok in greek_tokens[i:i + len(pattern)]]
        if segment == pattern:
            return rule

    return None


def consume_span(s_tokens, s_i, count):
    idxs = []
    words = []

    for _ in range(count):
        if s_i < len(s_tokens):
            idxs.append(s_tokens[s_i][0])
            words.append(s_tokens[s_i][1])
            s_i += 1

    return s_i, ",".join(idxs) if idxs else "-", " ".join(words) if words else "-"


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

            consume = int(action.get("consume", 1))
            s_i, nbla_idx, nbla_text = consume_span(s_tokens, s_i, consume)

            for j in range(span_len):
                g_idx, g_tok = g_tokens[g_i + j]

                if j == 0:
                    row_alignment = alignment_type
                else:
                    row_alignment = "shared"

                rows.append([book, ch, vs, g_idx, g_tok, nbla_idx, nbla_text, row_alignment])

            g_i += span_len
            continue

        # fallback
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
            "  python3 scripts/suggest_alignment.py "
            "data/g-tokens/1corintios-7-17.txt "
            "data/s-tokens/1corintios-7-17.txt "
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

    print("\t".join(HEADER))
    for row in suggest(book, ch, vs, g_tokens, s_tokens, rules):
        print("\t".join(row))


if __name__ == "__main__":
    main()