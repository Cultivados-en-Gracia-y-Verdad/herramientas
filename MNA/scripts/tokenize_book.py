#!/usr/bin/env python3

import re
import sys
from pathlib import Path

SCRIPT_VERSION = "tokenize_book.py v0.1"


def clean_text(s):
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def parse_line(line):
    """
    Expected format:

    romanos 1:1<TAB>text
    OR
    romanos 1:1 text
    """

    line = clean_text(line)

    if "\t" in line:
        ref, text = line.split("\t", 1)
    else:
        m = re.match(r"^(.+?\d+:\d+)\s+(.*)$", line)
        if not m:
            raise ValueError(f"Cannot parse line: {line}")

        ref = m.group(1)
        text = m.group(2)

    ref = clean_text(ref)
    text = clean_text(text)

    return ref, text


def tokenize(text):
    return text.split()


def write_tokens(output_dir, ref, tokens):
    book, cv = ref.rsplit(" ", 1)
    chapter, verse = cv.split(":")

    filename = f"{book.lower()}-{chapter}-{verse}.txt"

    output_dir.mkdir(parents=True, exist_ok=True)

    outpath = output_dir / filename

    with outpath.open("w", encoding="utf-8") as f:
        for i, tok in enumerate(tokens, start=1):
            f.write(f"{i:02d}\t{tok}\n")

    return outpath


def process_file(input_path, output_dir):
    count = 0

    with input_path.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()

            if not raw:
                continue

            ref, text = parse_line(raw)

            tokens = tokenize(text)

            write_tokens(output_dir, ref, tokens)

            count += 1

    return count


def main():
    print(SCRIPT_VERSION)

    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python3 scripts/tokenize_book.py "
            "<greek_txt> <spanish_txt> <bookname>"
        )
        sys.exit(1)

    greek_path = Path(sys.argv[1])
    spanish_path = Path(sys.argv[2])
    bookname = sys.argv[3].lower()

    g_out = Path("data/g-tokens")
    s_out = Path("data/s-tokens")

    g_count = process_file(greek_path, g_out)
    s_count = process_file(spanish_path, s_out)

    print()
    print(f"Greek token files:   {g_count}")
    print(f"Spanish token files: {s_count}")
    print(f"Book: {bookname}")
    print("DONE")


if __name__ == "__main__":
    main()