#!/usr/bin/env python3

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


VALID_ALIGNMENT_TYPES = {
    "direct",
    "expanded",
    "merged-forward",
    "merged-backward",
    "missing",
    "shared",
}


REQUIRED_COLUMNS = [
    "BOOK",
    "CH",
    "VS",
    "G_IDX",
    "GREEK",
    "NBLA_IDX",
    "NBLA_TEXT",
    "ALIGNMENT",
]


def read_tsv(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    if reader.fieldnames is None:
        raise ValueError(f"{path}: empty file")

    missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")

    return rows


def read_token_list(path):
    """
    Expected format:

    01<TAB>Παρακαλῶ
    02<TAB>δὲ

    or:

    01 Παρακαλῶ
    02 δὲ
    """

    tokens = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            if "\t" in line:
                idx, token = line.split("\t", 1)
            else:
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    raise ValueError(f"{path}:{line_no}: invalid token line: {line}")
                idx, token = parts

            idx = idx.strip()
            token = token.strip()

            if not idx.isdigit():
                raise ValueError(f"{path}:{line_no}: invalid index: {idx}")

            if idx in tokens:
                raise ValueError(f"{path}:{line_no}: duplicate token index: {idx}")

            tokens[idx.zfill(2)] = token

    return tokens


def expand_nbla_indexes(value):
    """
    Supports:
    - empty / -
    - 03
    - 01-02
    - 12,13
    - 12,13-16
    """

    value = value.strip()

    if value in {"", "-"}:
        return []

    indexes = []

    for part in value.split(","):
        part = part.strip()

        if "-" in part:
            start, end = part.split("-", 1)
            start_i = int(start)
            end_i = int(end)

            if end_i < start_i:
                raise ValueError(f"invalid NBLA range: {part}")

            for i in range(start_i, end_i + 1):
                indexes.append(str(i).zfill(2))
        else:
            if not part.isdigit():
                raise ValueError(f"invalid NBLA index: {part}")
            indexes.append(part.zfill(2))

    return indexes


def expected_nbla_text(nbla_tokens, indexes):
    return " ".join(nbla_tokens[i] for i in indexes)


def validate(greek_path, nbla_path, alignment_path):
    greek_tokens = read_token_list(greek_path)
    nbla_tokens = read_token_list(nbla_path)
    records = read_tsv(alignment_path)

    errors = []

    greek_seen = Counter()
    nbla_usage = defaultdict(list)

    # 1. Validate each alignment record
    for row_no, row in enumerate(records, start=2):
        g_idx = row["G_IDX"].strip().zfill(2)
        greek = row["GREEK"].strip()
        nbla_idx_raw = row["NBLA_IDX"].strip()
        nbla_text = row["NBLA_TEXT"].strip()
        alignment = row["ALIGNMENT"].strip()

        # Alignment type check
        if alignment not in VALID_ALIGNMENT_TYPES:
            errors.append(
                f"line {row_no}: invalid ALIGNMENT '{alignment}'"
            )

        # Greek index validity
        if g_idx not in greek_tokens:
            errors.append(
                f"line {row_no}: G_IDX {g_idx} outside Greek token list"
            )
        else:
            greek_seen[g_idx] += 1

            # Greek token match
            expected_greek = greek_tokens[g_idx]
            if greek.lower() != expected_greek.lower():
                errors.append(
                    f"line {row_no}: Greek mismatch at {g_idx}: "
                    f"expected '{expected_greek}', got '{greek}'"
                )

        # Missing check
        if alignment == "missing":
            if nbla_idx_raw not in {"", "-"}:
                errors.append(
                    f"line {row_no}: missing record must not have NBLA_IDX"
                )
            if nbla_text not in {"", "-"}:
                errors.append(
                    f"line {row_no}: missing record must not have NBLA_TEXT"
                )
            continue

        # Non-missing records must have NBLA index
        if nbla_idx_raw in {"", "-"}:
            errors.append(
                f"line {row_no}: non-missing record has empty NBLA_IDX"
            )
            continue

        # Parse NBLA indexes
        try:
            nbla_indexes = expand_nbla_indexes(nbla_idx_raw)
        except ValueError as e:
            errors.append(f"line {row_no}: {e}")
            continue

        # NBLA index validity
        valid_indexes = []
        for idx in nbla_indexes:
            if idx not in nbla_tokens:
                errors.append(
                    f"line {row_no}: NBLA_IDX {idx} outside NBLA token list"
                )
            else:
                valid_indexes.append(idx)
                nbla_usage[idx].append((row_no, alignment, g_idx))

        # NBLA text match
        if valid_indexes:
            expected_text = expected_nbla_text(nbla_tokens, valid_indexes)
            if nbla_text != expected_text:
                errors.append(
                    f"line {row_no}: NBLA text mismatch for {nbla_idx_raw}: "
                    f"expected '{expected_text}', got '{nbla_text}'"
                )

    # 2. Greek coverage check
    for g_idx in greek_tokens:
        if greek_seen[g_idx] == 0:
            errors.append(f"Greek token {g_idx} unused: {greek_tokens[g_idx]}")
        elif greek_seen[g_idx] > 1:
            errors.append(
                f"Greek token {g_idx} used {greek_seen[g_idx]} times"
            )

    # 3. NBLA coverage check
    for n_idx in nbla_tokens:
        if n_idx not in nbla_usage:
            errors.append(f"NBLA token {n_idx} unused: {nbla_tokens[n_idx]}")

    # 4. Duplication check
    for n_idx, uses in nbla_usage.items():
        if len(uses) <= 1:
            continue

        # First use may be normal.
        # Later repeated uses must be marked shared.
        repeated_uses = uses[1:]

        for row_no, alignment, g_idx in repeated_uses:
            if alignment != "shared":
                errors.append(
                    f"NBLA token {n_idx} reused on line {row_no} "
                    f"without ALIGNMENT=shared"
                )

    return errors


def main():
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "  python scripts/validate_alignment.py "
            "greek_tokens.txt nbla_tokens.txt alignment.tsv",
            file=sys.stderr,
        )
        sys.exit(2)

    greek_path = Path(sys.argv[1])
    nbla_path = Path(sys.argv[2])
    alignment_path = Path(sys.argv[3])

    errors = validate(greek_path, nbla_path, alignment_path)

    if errors:
        print("FAIL")
        print()
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("PASS")


if __name__ == "__main__":
    main()