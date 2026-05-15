#!/usr/bin/env python3
"""Regression tests for MNA validation and cleanup helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from clean_mna_extras import removable_extra_lines
from validate_mna import parse_mna_markdown, validate_verse


FIXTURE_DIR = Path(__file__).resolve().parent / "data" / "fixtures"


def load_verses(name: str):
    text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    return parse_mna_markdown(text)


class MnaToolTests(unittest.TestCase):
    def test_known_good_fixtures_pass_validation(self) -> None:
        for fixture_name in [
            "valid-1cor-1-1-10.md",
            "valid-1cor-1-11-20.md",
            "valid-1cor-1-21-30.md",
            "valid-1cor-1-31.md",
            "valid-1cor-2-1-10.md",
            "valid-1cor-2-11-16.md",
            "valid-1cor-3-1-10.md",
            "valid-1cor-3-11-20.md",
            "valid-1cor-3-21-23.md",
            "valid-1cor-4-1-10.md",
            "valid-1cor-4-11-20.md",
            "valid-1cor-4-21.md",
        ]:
            with self.subTest(fixture_name=fixture_name):
                verses = load_verses(fixture_name)
                issues = [issue for verse in verses for issue in validate_verse(verse)]
                self.assertEqual([], issues)

    def test_duplicate_extra_is_validation_error(self) -> None:
        verses = load_verses("invalid-duplicate-extra.md")
        issues = [issue for verse in verses for issue in validate_verse(verse)]
        messages = [issue.message for issue in issues]
        self.assertIn("Covered word(s) not found in NBLA: acerca, de", messages)

    def test_duplicate_extra_is_cleaner_removal(self) -> None:
        verses = load_verses("invalid-duplicate-extra.md")
        removals = removable_extra_lines(verses)
        self.assertEqual(1, len(removals))
        self.assertEqual("1 Corintios 1:6", removals[0].ref)
        self.assertEqual("acerca de", removals[0].span)


if __name__ == "__main__":
    unittest.main()
