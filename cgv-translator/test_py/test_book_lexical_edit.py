import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lexical", ROOT / "scripts" / "book_lexical_edit.py")
LEX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEX)


class LexicalEditTests(unittest.TestCase):
    def test_book_scope_is_targeted_and_reopens_changed_phrase(self):
        phrases = [
            {"reference": "Book 1:1", "phraseIndex": 0, "spanish": "bronce", "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]},
            {"reference": "Book 1:2", "phraseIndex": 1, "spanish": "metal", "suggestionSource": "lbf-approved", "approval": {"status": "approved"}, "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]},
            {"reference": "Book 1:3", "phraseIndex": 2, "spanish": "metal", "tokenRows": [{"strongs": "H2", "lemma": "other"}]},
        ]
        plan = LEX.build_plan(phrases, ("H1", "lemma"), "metal", "bronce")
        self.assertTrue(plan["safe"])
        self.assertEqual(plan["totalSourceOccurrences"], 2)
        self.assertEqual(plan["phrasesChanged"], 1)
        updated = LEX.apply_plan({"phrases": phrases}, plan)
        self.assertEqual(updated["phrases"][1]["spanish"], "bronce")
        self.assertEqual(updated["phrases"][1]["suggestionSource"], "lbf-preliminary")
        self.assertEqual(updated["phrases"][1]["approval"]["status"], "invalidated")
        self.assertEqual(updated["phrases"][2]["spanish"], "metal")

    def test_ambiguous_mapping_fails_closed(self):
        phrases = [{"reference": "Book 1:1", "phraseIndex": 0, "spanish": "otra cosa", "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]}]
        plan = LEX.build_plan(phrases, ("H1", "lemma"), "metal", "bronce")
        self.assertFalse(plan["safe"])
        with self.assertRaises(ValueError):
            LEX.apply_plan({"phrases": phrases}, plan)


if __name__ == "__main__":
    unittest.main()
