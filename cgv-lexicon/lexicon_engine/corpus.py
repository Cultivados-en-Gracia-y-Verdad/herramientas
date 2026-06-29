"""Load NT Greek token corpus from MNA interlinear JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NT_DIR = REPO_ROOT / "MNA" / "datasets" / "interlinear" / "NT"


@dataclass(frozen=True)
class Token:
    book: str
    ch: int
    vs: int
    tok: int
    surface: str
    lemma: str
    morph: str
    es: str = ""


VerseKey = tuple[str, int, int]


def load_nt_tokens(nt_dir: Path | None = None) -> tuple[list[Token], dict[VerseKey, list[Token]]]:
    root = nt_dir or DEFAULT_NT_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"NT token directory not found: {root}")

    tokens: list[Token] = []
    verses: dict[VerseKey, list[Token]] = {}

    for path in sorted(root.glob("*.tokens.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                for field in ("book", "ch", "vs", "tok", "surface", "lemma"):
                    if field not in raw or raw[field] in (None, ""):
                        raise ValueError(f"{path}:{line_no}: missing required field {field!r}")
                tok = Token(
                    book=str(raw["book"]),
                    ch=int(raw["ch"]),
                    vs=int(raw["vs"]),
                    tok=int(raw["tok"]),
                    surface=str(raw["surface"]),
                    lemma=str(raw["lemma"]),
                    morph=str(raw.get("morph") or ""),
                    es=str(raw.get("es") or ""),
                )
                tokens.append(tok)
                key = (tok.book, tok.ch, tok.vs)
                verses.setdefault(key, []).append(tok)

    for key in verses:
        verses[key].sort(key=lambda t: t.tok)

    return tokens, verses


def context_window(
    verse_tokens: list[Token],
    target_tok: int,
    before: int = 6,
    after: int = 6,
) -> tuple[str, str]:
    idx = next((i for i, t in enumerate(verse_tokens) if t.tok == target_tok), None)
    if idx is None:
        return "", ""
    left = verse_tokens[max(0, idx - before) : idx]
    right = verse_tokens[idx + 1 : idx + 1 + after]
    return " ".join(t.surface for t in left), " ".join(t.surface for t in right)


def verse_clause_text(verse_tokens: list[Token], center_idx: int, radius: int = 8) -> str:
    lo = max(0, center_idx - radius)
    hi = min(len(verse_tokens), center_idx + radius + 1)
    return " ".join(t.surface for t in verse_tokens[lo:hi])
