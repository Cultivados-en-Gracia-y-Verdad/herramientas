import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lexical", ROOT / "scripts" / "book_lexical_edit.py")
LEX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEX)


class BookScopeLexicalEditRegression(unittest.TestCase):
    def test_book_scope_does_not_silently_narrow_to_matching_token_metadata(self):
        phrases = [
            {"reference": "Book 1:1", "phraseIndex": 0, "spanish": "bronce", "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]},
            {"reference": "Book 1:2", "phraseIndex": 1, "spanish": "metal", "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]},
            {"reference": "Book 1:3", "phraseIndex": 2, "spanish": "metal", "tokenRows": [{"strongs": "H2", "lemma": "other"}]},
        ]
        plan = LEX.build_plan(phrases, ("H1", "lemma"), "metal", "bronce")
        self.assertEqual(plan["terminologyOccurrences"], 3)
        self.assertEqual(plan["phrasesChanged"], 2)
        updated = LEX.apply_plan({"phrases": phrases}, plan)
        self.assertEqual([row["spanish"] for row in updated["phrases"]], ["bronce", "bronce", "bronce"])

    def test_wording_change_rebases_reverse_link_spans_without_relinking_tokens(self):
        phrases = [{"reference": "Book 1:1", "phraseIndex": 0, "spanish": "a metal z", "tokenRows": [{"strongs": "H1", "lemma": "lemma"}]}]
        plan = LEX.build_plan(phrases, ("H1", "lemma"), "metal", "bronce")
        reverse = {"links": [{"reference": "Book 1:1", "units": [
            {"unitId": "0:0", "surface": "a metal", "charStart": 0, "charEnd": 7, "sourceTokenIds": ["t1"]},
            {"unitId": "0:1", "surface": "z", "charStart": 8, "charEnd": 9, "sourceTokenIds": ["t2"]},
        ]}]}
        updated, _changed = LEX.synchronize_reverse_links(reverse, plan, "metal", "bronce")
        units = updated["links"][0]["units"]
        self.assertEqual(units[0]["surface"], "a bronce")
        self.assertEqual((units[0]["charStart"], units[0]["charEnd"]), (0, 8))
        self.assertEqual((units[1]["charStart"], units[1]["charEnd"]), (9, 10))
        self.assertEqual(units[0]["sourceTokenIds"], ["t1"])
        self.assertEqual(units[1]["sourceTokenIds"], ["t2"])


if __name__ == "__main__":
    unittest.main()
