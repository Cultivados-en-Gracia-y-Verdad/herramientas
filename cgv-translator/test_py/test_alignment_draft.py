from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_alignment_draft import build_units, partition  # noqa: E402


class AlignmentDraftTests(unittest.TestCase):
    def test_partition_consumes_both_complete_sequences(self):
        groups = partition([["y", "dio"], ["dios"], ["obj"], ["daniel"]], ["y", "dios", "concedio", "a", "daniel"])
        self.assertEqual(groups[0][0], 0)
        self.assertEqual(groups[0][2], 0)
        self.assertEqual(groups[-1][1], 4)
        self.assertEqual(groups[-1][3], 5)

    def test_units_cover_exact_span_without_overlap(self):
        row = {
            "reference": "Daniel 1:1",
            "phraseIndex": 0,
            "spanish": "En el año tercero.",
            "sourceTokenIds": ["h1", "h2"],
            "tokenRows": [
                {"sourceTokenId": "h1", "ble": "en año"},
                {"sourceTokenId": "h2", "ble": "tercero"},
            ],
        }
        units, _ = build_units(row)
        self.assertEqual(units[0]["charStart"], 0)
        self.assertEqual(units[-1]["charEnd"], len(row["spanish"]))
        self.assertEqual("".join(unit["surface"] for unit in units), row["spanish"])
        self.assertTrue(all(unit["status"] == "DRAFT" for unit in units))


if __name__ == "__main__":
    unittest.main()
