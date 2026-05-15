#!/usr/bin/env python3

import re
import sys
from pathlib import Path


def clean_token(token: str) -> str:
    """
    Remove punctuation and SBLGNT editorial markers.
    Keep Greek accents.
    """

    # Remove SBLGNT editorial apparatus markers
    token = token.replace("⸀", "")
    token = token.replace("⸂", "")
    token = token.replace("⸃", "")

    # Remove punctuation from edges
    token = token.strip(".,;:··!?¿¡“”\"'()[]{}«»")
    token = token.lower()
    
    return token


def tokenize(text: str):
    raw_tokens = text.split()
    tokens = []

    for raw in raw_tokens:
        token = clean_token(raw)
        if token:
            tokens.append(token)

    return tokens


def write_tokens(tokens, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, token in enumerate(tokens, start=1):
            f.write(f"{i:02d} {token}\n")


def parse_source_file(path: Path):
    """
    Expected source format:

    1corintios 1:10 Παρακαλῶ δὲ ὑμᾶς...

    That is:
    BOOK SPACE CHAPTER:VERSE SPACE TEXT
    """

    verses = []

    pattern = re.compile(r"^(\S+)\s+(\d+:\d+)\s+(.+)$")

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            match = pattern.match(line)
            if not match:
                raise ValueError(
                    f"{path}:{line_no}: expected format: book chapter:verse text"
                )

            book = match.group(1)
            chapter_verse = match.group(2)
            text = match.group(3)

            ref = normalize_ref(f"{book} {chapter_verse}")
            verses.append((ref, text))

    return verses


def normalize_ref(ref: str) -> str:
    """
    Converts:
      1corintios 1:20
      1Corintios 1:20
      1corintios-1-20

    into:
      1corintios-1-20
    """

    ref = ref.strip().lower()
    ref = ref.replace(":", "-")
    ref = re.sub(r"\s+", "-", ref)
    ref = re.sub(r"-+", "-", ref)
    return ref


def main():
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "  python3 scripts/extract_tokens.py SOURCE_FILE OUTPUT_DIR LABEL\n\n"
            "Examples:\n"
            "  python3 scripts/extract_tokens.py sources/1corintios-sblgnt.txt data/g-tokens greek\n"
            "  python3 scripts/extract_tokens.py sources/1corintios-nbla.txt data/s-tokens spanish",
            file=sys.stderr,
        )
        sys.exit(2)

    source_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    label = sys.argv[3]

    if label not in {"greek", "spanish"}:
        print("LABEL must be either: greek or spanish", file=sys.stderr)
        sys.exit(2)

    verses = parse_source_file(source_file)

    for ref, text in verses:
        tokens = tokenize(text)
        output_path = output_dir / f"{ref}.txt"
        write_tokens(tokens, output_path)
        print(f"WROTE {output_path} ({len(tokens)} {label} tokens)")


if __name__ == "__main__":
    main()