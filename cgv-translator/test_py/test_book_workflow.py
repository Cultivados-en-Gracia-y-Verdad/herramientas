from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from book_workflow import (  # noqa: E402
    WorkflowError,
    alignment_audit,
    gate_state,
    load_book,
    prepare,
    record,
    record_book,
    record_chapter,
    resolve_paths,
    translation_audit,
)
from release_readiness import make_report  # noqa: E402
from release_book import build_candidate, record_book_review  # noqa: E402


class BookWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = "titus"
        paths = resolve_paths(self.root, self.book)
        base = self.root / "translations" / "tr-spine" / self.book
        base.mkdir(parents=True)
        self.spine = {
            "book": "Titus",
            "verses": {
                "1:1": {
                    "tokens": [
                        {"sourceTokenId": "n1", "greek": "Παῦλος", "lemma": "Παῦλος", "robinson": "N-NSM"},
                        {"sourceTokenId": "n2", "greek": "δοῦλος", "lemma": "δοῦλος", "robinson": "N-NSM"},
                    ]
                }
            },
        }
        # Titus's real translation artifact is a root-level array. This must remain supported.
        self.translation = [
            {
                "reference": "Titus 1:1",
                "phraseIndex": 0,
                "spanish": "Pablo, siervo",
                "sourceTokenIds": ["n1", "n2"],
            }
        ]
        self.alignment = {
            "bookId": "titus",
            "links": [
                {
                    "reference": "Titus 1:1",
                    "phraseIndex": 0,
                    "units": [
                        {"unitId": "0:0", "surface": "Pablo", "charStart": 0, "charEnd": 5, "sourceTokenIds": ["n1"]},
                        {"unitId": "0:1", "surface": "siervo", "charStart": 7, "charEnd": 13, "sourceTokenIds": ["n2"]},
                    ],
                }
            ],
        }
        self.paths = {
            "spine": base / "titus-tr-spine.json",
            "translation": base / "titus-phrases-tr.json",
            "alignment": base / "titus-reverse-links.json",
        }
        self.write_artifacts()
        roles = resolve_paths(self.root, self.book)["roles"]
        roles.parent.mkdir(parents=True, exist_ok=True)
        roles.write_text(
            json.dumps(
                {
                    "assignments": {
                        "translationProducer": {"name": "Producer A", "status": "ASSIGNED"},
                        "translationReviewer": {"name": "Reviewer A", "status": "ASSIGNED"},
                        "alignmentProducer": {"name": "Draft Builder", "status": "ASSIGNED"},
                        "alignmentReviewer": {"name": "Reviewer B", "status": "ASSIGNED"},
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_artifacts(self):
        self.paths["spine"].write_text(json.dumps(self.spine), encoding="utf-8")
        self.paths["translation"].write_text(json.dumps(self.translation), encoding="utf-8")
        self.paths["alignment"].write_text(json.dumps(self.alignment), encoding="utf-8")

    def data(self):
        return load_book(self.root, self.book)

    def test_titus_array_format_passes_deterministic_checks(self):
        self.assertEqual(translation_audit(self.data()), [])
        self.assertEqual(alignment_audit(self.data()), [])

    def test_translation_omission_is_a_hard_failure(self):
        self.translation[0]["sourceTokenIds"] = ["n1"]
        self.write_artifacts()
        errors = translation_audit(self.data())
        self.assertTrue(any("omitted" in error for error in errors), errors)

    def test_unaligned_spanish_is_a_hard_failure(self):
        self.alignment["links"][0]["units"] = self.alignment["links"][0]["units"][:1]
        self.write_artifacts()
        errors = alignment_audit(self.data())
        self.assertTrue(any("Spanish text is left unaligned" in error for error in errors), errors)

    def test_whole_verse_link_cannot_manufacture_completeness(self):
        self.alignment["links"][0]["units"] = [
            {
                "unitId": "0:0",
                "surface": "Pablo, siervo",
                "charStart": 0,
                "charEnd": 13,
                "sourceTokenIds": ["n1", "n2"],
            }
        ]
        self.write_artifacts()
        errors = alignment_audit(self.data())
        self.assertTrue(any("manufactures alignment completeness" in error for error in errors), errors)

    def test_prepare_never_creates_a_pass(self):
        data = self.data()
        prepare(data)
        self.assertEqual(gate_state(data, "translation")[0], "PENDING")
        self.assertEqual(gate_state(data, "alignment")[0], "PENDING")

    def test_missing_alignment_does_not_block_g0a_preparation(self):
        self.paths["alignment"].unlink()
        data = self.data()
        self.assertEqual(translation_audit(data), [])
        self.assertTrue(any("not been submitted" in item for item in alignment_audit(data)))
        prepare(data)
        self.assertTrue(data["paths"]["translation_review"].is_file())
        self.assertFalse(data["paths"]["alignment_review"].is_file())
        self.assertEqual(gate_state(data, "translation")[0], "PENDING")
        record(data, "translation", "Titus 1:1", "PASS", "Reviewer A", "faithful", True)
        self.assertEqual(gate_state(data, "translation")[0], "PASS")

    def test_release_report_keeps_g0b_pending_until_g0a_passes(self):
        data = self.data()
        prepare(data)
        report = make_report(self.root, self.book)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["humanGates"]["G0A"]["status"], "PENDING")
        self.assertEqual(report["humanGates"]["G0B"]["status"], "PENDING")
        self.assertFalse(report["aiVerificationPermitted"])

    def test_alignment_review_requires_translation_pass_for_that_verse(self):
        data = self.data()
        prepare(data)
        with self.assertRaises(WorkflowError):
            record(data, "alignment", "Titus 1:1", "PASS", "Reviewer B", "", True)
        record(data, "translation", "Titus 1:1", "PASS", "Reviewer A", "faithful", True)
        record(data, "alignment", "Titus 1:1", "PASS", "Reviewer B", "links correct", True)
        self.assertEqual(gate_state(data, "translation")[0], "PASS")
        self.assertEqual(gate_state(data, "alignment")[0], "PASS")

    def test_chapter_record_creates_human_verse_decisions(self):
        data = self.data()
        prepare(data)
        record_chapter(data, "translation", 1, "PASS", "Reviewer A", "reviewed", True)
        review = json.loads(data["paths"]["translation_review"].read_text(encoding="utf-8"))
        self.assertEqual(review["verses"][0]["decision"], "PASS")
        self.assertTrue(review["verses"][0]["decisionId"].startswith("G0A-titus-"))

    def test_book_record_is_one_reading_not_many_reviews(self):
        data = self.data()
        prepare(data)
        record_book(data, "translation", "PASS", "Reviewer A", "read the book", True)
        review = json.loads(data["paths"]["translation_review"].read_text(encoding="utf-8"))
        ids = {item["decisionId"] for item in review["verses"]}
        self.assertEqual(len(ids), 1)
        self.assertTrue(all(item["decision"] == "PASS" for item in review["verses"]))
        self.assertEqual(gate_state(data, "translation")[0], "PASS")

    def test_release_build_requires_separate_human_book_review(self):
        data = self.data()
        prepare(data)
        record(data, "translation", "Titus 1:1", "PASS", "Reviewer A", "faithful", True)
        record(data, "alignment", "Titus 1:1", "PASS", "Reviewer B", "defensible", True)
        with self.assertRaises(WorkflowError):
            build_candidate(data, "LBF", "1.0.0")
        review = record_book_review(data, "Book Reviewer", "complete-book review", True)
        candidate = build_candidate(data, "LBF", "1.0.0")
        self.assertEqual(review["result"], "PASS")
        self.assertEqual(candidate["bookReviewId"], review["recordId"])
        self.assertEqual(candidate["status"], "PENDING")

    def test_ai_or_unattested_review_cannot_record_pass(self):
        data = self.data()
        prepare(data)
        with self.assertRaises(WorkflowError):
            record(data, "translation", "Titus 1:1", "PASS", "Reviewer A", "", False)
        path = data["paths"]["translation_review"]
        review = json.loads(path.read_text(encoding="utf-8"))
        review["verses"][0].update(
            {
                "decision": "PASS",
                "reviewer": "AI reviewer",
                "authority": "AI",
                "reviewMethod": "AI_REVIEW",
                "aiUsed": True,
                "reviewedAt": "2026-08-14T00:00:00+00:00",
            }
        )
        path.write_text(json.dumps(review), encoding="utf-8")
        self.assertEqual(gate_state(data, "translation")[0], "BLOCKED")

    def test_changed_verse_becomes_pending_then_resets_on_prepare(self):
        data = self.data()
        prepare(data)
        record(data, "translation", "Titus 1:1", "PASS", "Reviewer A", "", True)
        self.translation[0]["spanish"] = "Pablo, un siervo"
        self.alignment["links"][0]["units"][1].update({"surface": "un siervo", "charStart": 7, "charEnd": 16})
        self.write_artifacts()
        changed = self.data()
        self.assertEqual(gate_state(changed, "translation")[0], "PENDING")
        prepare(changed)
        self.assertEqual(gate_state(changed, "translation")[0], "PENDING")


if __name__ == "__main__":
    unittest.main()
