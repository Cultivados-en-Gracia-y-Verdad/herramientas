#!/usr/bin/env python3
"""Apply the narrow Translator Save authority fix to public/main.js.

The GitHub connector can only replace whole existing files. This patcher exists
so the intended two local edits can be applied without reconstructing or
reformatting main.js. It refuses any unexpected source shape.
"""
from __future__ import annotations

from pathlib import Path


OLD_SAVE = '''  const phrase = currentPhrase();
  const previousSavedText = phrase.savedText || "";
  phrase.savedText = phrase.workingText;
  phrase.suggestionSource = phrase.workingText.trim() ? "lbf-approved" : "blank";
'''

NEW_SAVE = '''  const phrase = currentPhrase();
  const previousSavedText = phrase.savedText || "";
  const previousSuggestionSource = phrase.suggestionSource || "";
  const nextSavedText = phrase.workingText;
  const spanishChanged = nextSavedText !== previousSavedText;

  phrase.savedText = nextSavedText;
  if (!nextSavedText.trim()) {
    phrase.suggestionSource = "blank";
  } else if (spanishChanged) {
    phrase.suggestionSource = "lbf-preliminary";
  }
'''

OLD_ROLLBACK = '''    phrase.savedText = previousSavedText;
    renderVersePreview();
'''

NEW_ROLLBACK = '''    phrase.savedText = previousSavedText;
    phrase.suggestionSource = previousSuggestionSource;
    renderVersePreview();
'''


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "public" / "main.js"
    raw = path.read_text(encoding="utf-8")

    if NEW_SAVE in raw and NEW_ROLLBACK in raw and OLD_SAVE not in raw:
        print("UNCHANGED: Save authority patch is already applied")
        return 0

    if raw.count(OLD_SAVE) != 1:
        raise SystemExit(
            "REFUSED: expected Save self-approval snippet was not found exactly once; main.js was not changed"
        )
    if raw.count(OLD_ROLLBACK) != 1:
        raise SystemExit(
            "REFUSED: expected Save rollback snippet was not found exactly once; main.js was not changed"
        )

    candidate = raw.replace(OLD_SAVE, NEW_SAVE, 1).replace(OLD_ROLLBACK, NEW_ROLLBACK, 1)

    if 'phrase.suggestionSource = phrase.workingText.trim() ? "lbf-approved" : "blank";' in candidate:
        raise SystemExit("REFUSED: self-approval assignment still present; main.js was not changed")
    if 'phrase.suggestionSource = "lbf-preliminary";' not in candidate:
        raise SystemExit("REFUSED: preliminary transition missing; main.js was not changed")
    if "previousSuggestionSource" not in candidate:
        raise SystemExit("REFUSED: rollback authority preservation missing; main.js was not changed")

    path.write_text(candidate, encoding="utf-8")
    print("PATCHED: public/main.js")
    print("changed nonblank Spanish -> lbf-preliminary")
    print("unchanged approved Spanish -> approval preserved")
    print("failed save -> prior Spanish/source state restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
