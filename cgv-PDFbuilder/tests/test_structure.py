"""Parser tests for the CGV structural outline model.

Run with:  python3 -m unittest discover -s tests -t .
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cgv_structure import (  # noqa: E402
    IndentLadder,
    StructuralIndentError,
    scan_structure,
)


def depths(text: str) -> list[int]:
    return [item.depth for item in scan_structure(text, "fixture.md").items]


def pairs(text: str) -> list[tuple[str, int]]:
    return [(item.marker, item.depth) for item in scan_structure(text, "fixture.md").items]


REVELATION_1_1 = """### Apocalipsis 1:3:1 — Dichoso el que lee la profecía

+ *Revelación de Jesús Cristo*

- *que Dios le dio para mostrar a sus siervos*

+ *Revelación*

  - *las cosas que deben suceder pronto*

- *y la dio a conocer, enviándola por medio de su ángel a su siervo Juan*

+ *Revelación*

+ *Dios*

  - *quien dio testimonio de la palabra de Dios y del testimonio de Jesús Cristo*

  + *Juan*

    - *de todo lo que vio*
"""


class MixedMarkersTest(unittest.TestCase):
    """1. Mixed markers at the same level."""

    def test_marker_change_never_changes_depth(self) -> None:
        text = "+ item\n- item\n+ item\n- item\n"
        self.assertEqual(depths(text), [0, 0, 0, 0])

    def test_marker_change_at_depth_two(self) -> None:
        text = "+ root\n    - a\n    + b\n    - c\n"
        self.assertEqual(pairs(text), [("+", 0), ("-", 2), ("+", 2), ("-", 2)])


class NestingTest(unittest.TestCase):
    """2. Multiple nested levels."""

    def test_two_space_ladder(self) -> None:
        text = "+ l0\n  - l1\n    + l2\n      - l3\n        + l4\n"
        self.assertEqual(depths(text), [0, 1, 2, 3, 4])

    def test_parent_links_follow_indentation(self) -> None:
        index = scan_structure("+ a\n  - b\n    + c\n", "fixture.md")
        a, b, c = index.items
        self.assertIsNone(a.parent_line)
        self.assertEqual(b.parent_line, a.line_no)
        self.assertEqual(c.parent_line, b.line_no)


class ReturnToRootTest(unittest.TestCase):
    """3. A return from a deep level to level 0."""

    def test_new_root_returns_to_zero(self) -> None:
        text = "+ parent\n  - child\n    + grandchild\n+ new root\n"
        self.assertEqual(depths(text), [0, 1, 2, 0])

    def test_new_root_has_no_parent(self) -> None:
        index = scan_structure("+ parent\n  - child\n    + grandchild\n+ new root\n", "f.md")
        self.assertIsNone(index.items[-1].parent_line)


class SiblingBranchesTest(unittest.TestCase):
    """4. Several sibling branches."""

    def test_three_branches_reset_each_time(self) -> None:
        text = (
            "+ branch one\n"
            "  - one a\n"
            "    + one a i\n"
            "- branch two\n"
            "  + two a\n"
            "+ branch three\n"
            "  - three a\n"
            "  - three b\n"
        )
        self.assertEqual(depths(text), [0, 1, 2, 0, 1, 0, 1, 1])


class BlankLineTest(unittest.TestCase):
    """5. Blank lines between structural items."""

    def test_blank_lines_do_not_break_the_ladder(self) -> None:
        text = "+ a\n\n\n  - b\n\n+ c\n\n  - d\n"
        self.assertEqual(depths(text), [0, 1, 0, 1])


class WrappedContentTest(unittest.TestCase):
    """6. Wrapped inline content."""

    def test_long_content_is_captured_whole_at_its_own_depth(self) -> None:
        long_text = "palabra " * 40
        text = f"+ short\n  - *{long_text.strip()}*\n+ back to root\n"
        index = scan_structure(text, "fixture.md")
        self.assertEqual([i.depth for i in index.items], [0, 1, 0])
        self.assertIn("palabra palabra", index.items[1].content)
        self.assertTrue(index.items[1].content.endswith("*"))

    def test_inline_emphasis_and_footnotes_survive(self) -> None:
        text = "- *que Dios le dio*[^rel] y <u>mostrar</u>\n"
        self.assertEqual(scan_structure(text, "f.md").items[0].content,
                         "*que Dios le dio*[^rel] y <u>mostrar</u>")


class MalformedIndentTest(unittest.TestCase):
    """7. Malformed odd-number indentation."""

    def test_odd_indent_raises_with_file_line_and_count(self) -> None:
        text = "+ a\n   - three spaces\n"
        with self.assertRaises(StructuralIndentError) as ctx:
            scan_structure(text, "apocalipsis-manual.md")
        message = str(ctx.exception)
        self.assertIn("apocalipsis-manual.md:2", message)
        self.assertIn("3 leading space(s)", message)
        self.assertIn("odd structural indentation", message)

    def test_odd_indent_is_not_silently_rounded(self) -> None:
        index = scan_structure("+ a\n   - three\n  - two\n", "f.md", strict=False)
        self.assertEqual([i.content for i in index.items], ["a", "two"])
        self.assertEqual(len(index.problems), 1)
        self.assertEqual(index.problems[0].leading_spaces, 3)

    def test_line_offset_points_at_the_real_file_line(self) -> None:
        with self.assertRaises(StructuralIndentError) as ctx:
            scan_structure("+ a\n   - bad\n", "manual.md", line_offset=8)
        self.assertIn("manual.md:10", str(ctx.exception))


class TabIndentTest(unittest.TestCase):
    """8. Tabs in indentation — documented policy is rejection."""

    def test_tab_is_rejected(self) -> None:
        with self.assertRaises(StructuralIndentError) as ctx:
            scan_structure("+ a\n\t- tabbed\n", "manual.md")
        message = str(ctx.exception)
        self.assertIn("manual.md:2", message)
        self.assertIn("tab in structural indentation", message)
        self.assertIn("tab(s)", message)

    def test_tab_is_never_expanded_into_a_depth(self) -> None:
        index = scan_structure("+ a\n\t- tabbed\n", "manual.md", strict=False)
        self.assertEqual([i.content for i in index.items], ["a"])

    def test_mixed_space_tab_is_rejected(self) -> None:
        index = scan_structure("+ a\n  \t- mixed\n", "manual.md", strict=False)
        self.assertEqual(len(index.problems), 1)
        self.assertIn("tab", index.problems[0].reason)


class PageBreakTest(unittest.TestCase):
    """9. Hierarchy continuing across a page break."""

    def test_depths_continue_across_a_rule(self) -> None:
        text = "+ parent\n  - child\n\n---\n\n  - child after break\n+ root after break\n"
        self.assertEqual(depths(text), [0, 1, 1, 0])

    def test_page_break_class_does_not_reset_depth(self) -> None:
        text = '+ parent\n  - child\n<div class="page-break-after"></div>\n  - after\n'
        self.assertEqual(depths(text), [0, 1, 1])

    def test_heading_does_reset_ownership_but_not_depth(self) -> None:
        text = "+ parent\n  - child\n\n#### Nueva unidad\n\n  - child of nothing\n"
        index = scan_structure(text, "f.md")
        self.assertEqual([i.depth for i in index.items], [0, 1, 1])
        self.assertIsNone(index.items[-1].parent_line)


class AnnotationTest(unittest.TestCase):
    """`*` notes and `>` commentary never advance the structural ladder."""

    def test_annotations_are_not_items(self) -> None:
        text = "- clause\n  * *porque* (ὅτι)\n  > commentary\n- next clause\n"
        index = scan_structure(text, "f.md")
        self.assertEqual([i.content for i in index.items], ["clause", "next clause"])
        self.assertEqual(depths(text), [0, 0])
        self.assertEqual(len(index.annotations), 2)

    def test_annotation_owner_is_the_enclosing_item(self) -> None:
        text = "- clause\n  * note\n  - nested\n    > deep comment\n"
        index = scan_structure(text, "f.md")
        note, comment = index.annotations
        self.assertEqual(note.owner_depth, 0)
        self.assertEqual(comment.owner_depth, 1)

    def test_annotation_before_any_item_belongs_to_the_section_root(self) -> None:
        text = "#### heading\n* *y* (καὶ)\n  > comment\n"
        index = scan_structure(text, "f.md")
        self.assertTrue(all(a.owner_line is None for a in index.annotations))
        self.assertTrue(all(a.owner_depth == 0 for a in index.annotations))

    def test_extra_annotation_indent_does_not_invent_a_level(self) -> None:
        text = "- clause\n      * ↳ *hanger*\n"
        index = scan_structure(text, "f.md")
        self.assertEqual(index.annotations[0].owner_depth, 0)

    def test_flush_annotation_keeps_its_x_but_travels_with_the_item(self) -> None:
        text = "- clause\n\n* *quien* → *fue matado*\n  > comment\n"
        index = scan_structure(text, "f.md")
        note, comment = index.annotations
        # x is unchanged: the manual's convention is owner indent + 2.
        self.assertEqual(note.owner_depth, 0)
        self.assertIsNone(note.owner_line)
        # ...but it shares the item's group, so a page break cannot separate them.
        self.assertEqual(note.group_id, index.items[0].group_id)
        self.assertEqual(comment.group_id, index.items[0].group_id)

    def test_annotation_after_a_heading_starts_its_own_group(self) -> None:
        text = "- clause\n\n#### heading\n\n* note\n"
        index = scan_structure(text, "f.md")
        self.assertNotEqual(index.annotations[0].group_id, index.items[0].group_id)

    def test_bold_line_is_not_read_as_an_annotation(self) -> None:
        index = scan_structure("**Actores y tono**\n- clause\n", "f.md")
        self.assertEqual(len(index.annotations), 0)
        self.assertEqual(len(index.items), 1)

    def test_fenced_code_is_skipped(self) -> None:
        text = "+ real\n```mermaid\n- not an item\n```\n- also real\n"
        self.assertEqual([i.content for i in scan_structure(text, "f.md").items],
                         ["real", "also real"])


class RevelationFixtureTest(unittest.TestCase):
    """10. The opening hierarchy of Revelation 1:1 as a regression fixture."""

    EXPECTED = [
        ("Revelación de Jesús Cristo", 0),
        ("que Dios le dio para mostrar a sus siervos", 0),
        ("Revelación", 0),
        ("las cosas que deben suceder pronto", 1),
        ("y la dio a conocer, enviándola por medio de su ángel a su siervo Juan", 0),
        ("Revelación", 0),
        ("Dios", 0),
        ("quien dio testimonio de la palabra de Dios y del testimonio de Jesús Cristo", 1),
        ("Juan", 1),
        ("de todo lo que vio", 2),
    ]

    def test_depths_match_the_outline(self) -> None:
        index = scan_structure(REVELATION_1_1, "apocalipsis-outline.md")
        actual = [(item.content.strip("*"), item.depth) for item in index.items]
        self.assertEqual(actual, self.EXPECTED)

    def test_markers_are_preserved_without_affecting_depth(self) -> None:
        index = scan_structure(REVELATION_1_1, "apocalipsis-outline.md")
        self.assertEqual(
            [i.marker for i in index.items],
            ["+", "-", "+", "-", "-", "+", "+", "-", "+", "-"],
        )

    def test_juan_and_quien_are_siblings(self) -> None:
        index = scan_structure(REVELATION_1_1, "apocalipsis-outline.md")
        by_text = {i.content.strip("*"): i for i in index.items}
        self.assertEqual(by_text["Juan"].depth,
                         by_text["quien dio testimonio de la palabra de Dios y del testimonio de Jesús Cristo"].depth)
        self.assertEqual(by_text["Juan"].parent_line, by_text["Dios"].line_no)


class LadderTest(unittest.TestCase):
    """The single indentation formula."""

    def test_item_x_is_base_plus_depth_times_step(self) -> None:
        ladder = IndentLadder(base_x=10.0, step=20.0)
        self.assertEqual([ladder.item_x(d) for d in range(4)], [10.0, 30.0, 50.0, 70.0])

    def test_equal_depth_means_equal_x(self) -> None:
        ladder = IndentLadder()
        index = scan_structure(REVELATION_1_1, "f.md")
        by_depth: dict[int, set[float]] = {}
        for item in index.items:
            by_depth.setdefault(item.depth, set()).add(ladder.item_x(item.depth))
        for depth, xs in by_depth.items():
            self.assertEqual(len(xs), 1, f"depth {depth} rendered at {xs}")

    def test_annotation_sits_between_its_item_and_the_next_level(self) -> None:
        ladder = IndentLadder()
        for depth in range(5):
            self.assertGreater(ladder.annotation_x(depth), ladder.item_x(depth))
            self.assertLess(ladder.annotation_x(depth), ladder.item_x(depth + 1))

    def test_deep_items_are_clamped_off_the_right_margin(self) -> None:
        ladder = IndentLadder()
        self.assertGreaterEqual(
            ladder.content_width - ladder.annotation_x(99),
            ladder.min_text_width - 1e-6,
        )
        self.assertEqual(ladder.item_x(99), ladder.item_x(ladder.max_depth))

    def test_step_is_configurable_in_one_place(self) -> None:
        wide = IndentLadder(step=0.5 * 72)
        self.assertAlmostEqual(wide.item_x(2) - wide.item_x(1), 36.0, places=6)


if __name__ == "__main__":
    unittest.main()
