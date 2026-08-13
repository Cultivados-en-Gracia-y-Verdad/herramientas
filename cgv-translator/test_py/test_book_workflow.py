from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_core import (
    APPROVED, PRELIMINARY, investigation_status, preserve_review, resolve_paths,
    save_yaml, sha256_file,
)
from workflow_queues import alignment_errors, make_g0a, make_g0b
from workflow_state import g0a_status, g0b_status


class BookWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = "zechariah"
        self.paths = resolve_paths(self.root, self.book)
        base = Path(self.paths["spine"]).parent
        base.mkdir(parents=True, exist_ok=True)
        self.spine = {
            "bookId": self.book,
            "textualBasis": "OSHB/WLC",
            "verses": {
                "1:1": {"tokens": [
                    {"sourceTokenId": "h38001001001", "surface": "זכריה", "lemma": "H2148", "morph": "HNp", "lang": "he"},
                    {"sourceTokenId": "h38001001002", "surface": "אמר", "lemma": "H559", "morph": "HV", "lang": "he"},
                ]}
            },
        }
        self.phrases = {
            "bookId": self.book,
            "phrases": [{
                "reference": "Zechariah 1:1",
                "mtChapter": 1,
                "mtVerse": 1,
                "spanish": "Zacarías dijo",
                "suggestionSource": PRELIMINARY,
                "sourceTokenIds": ["h38001001001", "h38001001002"],
            }],
        }
        Path(self.paths["spine"]).write_text(json.dumps(self.spine), encoding="utf-8")
        Path(self.paths["phrases"]).write_text(json.dumps(self.phrases), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def reverse(self, producer_verified=False):
        return {
            "bookId": self.book,
            "links": [{
                "reference": "Zechariah 1:1",
                "status": "verified" if producer_verified else "needs-review",
                "units": [
                    {"unitId": "0:0", "surface": "Zacarías", "charStart": 0, "charEnd": 8,
                     "sourceTokenIds": ["h38001001001"], "status": "verified" if producer_verified else "needs-review", "method": "producer"},
                    {"unitId": "0:1", "surface": "dijo", "charStart": 9, "charEnd": 13,
                     "sourceTokenIds": ["h38001001002"], "status": "verified" if producer_verified else "needs-review", "method": "producer"},
                ],
            }],
        }

    def test_non_daniel_g0a_reference_never_falls_back_to_daniel(self):
        queue = make_g0a(self.root, self.book, self.spine, self.phrases, Path(self.paths["spine"]), Path(self.paths["phrases"]))
        self.assertEqual(queue["items"][0]["mt_reference"], "Zechariah 1:1")

    def test_g0b_queues_every_unit_even_when_producer_marks_verified(self):
        reverse = self.reverse(producer_verified=True)
        Path(self.paths["reverse"]).write_text(json.dumps(reverse), encoding="utf-8")
        queue = make_g0b(self.root, self.book, self.spine, self.phrases, reverse,
                         Path(self.paths["spine"]), Path(self.paths["phrases"]), Path(self.paths["reverse"]))
        self.assertEqual(len(queue["items"]), 2)
        self.assertTrue(all(item["review"]["decision"] == "PENDING" for item in queue["items"]))

    def test_alignment_requires_source_token_accounting(self):
        reverse = self.reverse()
        reverse["links"][0]["units"][1]["sourceTokenIds"] = ["h38001001001"]
        errors = alignment_errors(self.book, self.spine, self.phrases, reverse)
        self.assertTrue(any("unaccounted source tokens" in error for error in errors))

    def test_exact_reviews_are_preserved_but_changed_evidence_resets(self):
        reverse = self.reverse()
        Path(self.paths["reverse"]).write_text(json.dumps(reverse), encoding="utf-8")
        queue = make_g0b(self.root, self.book, self.spine, self.phrases, reverse,
                         Path(self.paths["spine"]), Path(self.paths["phrases"]), Path(self.paths["reverse"]))
        old = {"items": json.loads(json.dumps(queue["items"]))}
        for item in old["items"]:
            item["review"]["decision"] = "VERIFIED"
        same = json.loads(json.dumps(queue["items"]))
        preserved, reset = preserve_review(same, old)
        self.assertEqual((preserved, reset), (2, 0))
        changed = json.loads(json.dumps(queue["items"]))
        changed[0]["item_checksum"] = "changed"
        preserved, reset = preserve_review(changed, old)
        self.assertEqual((preserved, reset), (1, 1))

    def test_g0a_pass_requires_promotion_report_bound_to_exact_artifacts(self):
        self.phrases["phrases"][0]["suggestionSource"] = APPROVED
        Path(self.paths["phrases"]).write_text(json.dumps(self.phrases), encoding="utf-8")
        report = {
            "mode": "APPLY", "book": self.book, "gate": "G0A_TRANSLATION_APPROVAL",
            "validation": {
                "all_queue_items_approved": True,
                "queue_phrase_checksum_matches_current_artifact": True,
                "queue_spine_checksum_matches_current_artifact": True,
                "all_item_checksums_match": True,
            },
            "artifacts": {
                "phrases_sha256_after": sha256_file(Path(self.paths["phrases"])),
                "spine_sha256": sha256_file(Path(self.paths["spine"])),
            },
        }
        save_yaml(Path(self.paths["g0a_report"]), report)
        ok, errors = g0a_status(self.root, self.book, self.paths)
        self.assertTrue(ok, errors)
        self.phrases["phrases"][0]["spanish"] += " cambiado"
        Path(self.paths["phrases"]).write_text(json.dumps(self.phrases), encoding="utf-8")
        ok, errors = g0a_status(self.root, self.book, self.paths)
        self.assertFalse(ok)
        self.assertTrue(any("stale" in error for error in errors))

    def test_draft_investigation_blocks_book_finalization(self):
        inv = Path(self.paths["investigations"]) / "INV-38-0001"
        inv.mkdir(parents=True)
        (inv / "decision.md").write_text("# Decision\n\n## Version 0.1\n\nStatus: Draft\n", encoding="utf-8")
        ok, summary = investigation_status(self.paths)
        self.assertFalse(ok)
        self.assertEqual(summary["open"], ["INV-38-0001:Draft"])


if __name__ == "__main__":
    unittest.main()
