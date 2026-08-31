#!/usr/bin/env python3
"""Structural outline model for CGV study manuals.

This module owns exactly one job: turning manual Markdown source lines into a
structural AST and a layout model.  It knows nothing about ReportLab, so it can
be unit tested on its own.

The pipeline the exporter follows is::

    source parsing  ->  structural AST  ->  layout model  ->  PDF rendering
    (scan_structure)    (StructuralItem)   (IndentLadder)    (md_to_pdf.py)

Hierarchy rules
---------------
Structural depth comes *only* from the number of spaces in front of the ``+`` or
``-`` marker:

===============  =====
leading spaces   depth
===============  =====
0                0
2                1
4                2
6                3
...              ...
===============  =====

The marker itself is never allowed to change depth.  ``+`` and ``-`` keep their
semantic and typographic differences (phrase vs. dependent clause) but both sit
on the same ladder, so this::

    + item
    - item
    + item

is three siblings at depth 0, and this::

    + parent
      - child
        + grandchild
    + new root

puts ``new root`` back on exactly the same x as ``parent``.

Annotations
-----------
``*`` grammar/mechanical notes and ``>`` writer commentary are *not* structural.
They attach to the nearest preceding structural item whose indentation is
strictly smaller, and they are laid out at a small fixed offset from that item.
They never advance the structural ladder, so a comment can never be mistaken for
a nested outline level and can never push the tree to the right.  An annotation
that appears before any structural item in its section belongs to the section
root (the heading) and is laid out from depth 0.

Tabs
----
Tabs are **rejected** in structural indentation.  A tab has no defined width in
the source, so silently expanding it would invent a depth.  Any tab produces an
actionable :class:`StructuralIndentError` naming the file, the line and the
indentation found.  Odd space counts are rejected the same way rather than being
rounded into a neighbouring depth.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import Iterable, Literal

INCH = 72.0

#: Markers that create structural outline depth.
STRUCTURAL_MARKERS = ("+", "-")
#: Markers that hang off a structural item without creating depth.
ANNOTATION_MARKERS = ("*", ">")

_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.*\S.*)$")
_STRUCT_RE = re.compile(r"^(?P<lead>[ \t]*)(?P<marker>[-+])(?P<gap>[ \t]+)(?P<content>.*\S.*)$")
_GRAMMAR_RE = re.compile(r"^(?P<lead>[ \t]*)(?P<marker>\*)(?P<gap>[ \t]+)(?P<content>.*\S.*)$")
_QUOTE_RE = re.compile(r"^(?P<lead>[ \t]*)(?P<marker>>)[ \t]?(?P<content>.*)$")
_FENCE_RE = re.compile(r"^[ \t]*```[\w-]*[ \t]*$")
_RULE_RE = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$")

LineKind = Literal["item", "grammar", "commentary"]


class StructuralIndentError(ValueError):
    """Raised when manual indentation cannot be mapped onto a depth."""

    def __init__(self, problems: list["IndentProblem"]) -> None:
        self.problems = problems
        shown = problems[:20]
        body = "\n".join(f"  {problem.message}" for problem in shown)
        if len(problems) > len(shown):
            body += f"\n  ... and {len(problems) - len(shown)} more"
        super().__init__(
            f"{len(problems)} malformed structural indentation line(s):\n{body}\n"
            "Structural indentation must be a multiple of two spaces, and tabs are not allowed."
        )


@dataclass(frozen=True)
class IndentProblem:
    """One actionable indentation complaint."""

    filename: str
    line_no: int
    leading: str
    marker: str
    reason: str

    @property
    def leading_spaces(self) -> int:
        return len(self.leading)

    @property
    def message(self) -> str:
        if "\t" in self.leading:
            found = f"{self.leading.count(chr(9))} tab(s) in the indentation"
        else:
            found = f"{self.leading_spaces} leading space(s)"
        return (
            f"{self.filename}:{self.line_no}: {self.reason} — "
            f"marker '{self.marker}' has {found}; "
            f"use a multiple of two spaces (0, 2, 4, 6, ...)"
        )


@dataclass
class Annotation:
    """A ``*`` grammar note or ``>`` commentary line hanging off an item."""

    kind: LineKind  # "grammar" | "commentary"
    marker: str
    content: str
    line_no: int
    leading_spaces: int
    owner_line: int | None  # line number of the owning structural item
    owner_depth: int  # depth used for layout; 0 when owned by the section root
    group_id: int


@dataclass
class StructuralItem:
    """A ``+`` or ``-`` outline line."""

    marker: str
    depth: int
    content: str
    line_no: int
    leading_spaces: int
    parent_line: int | None = None
    group_id: int = 0
    annotations: list[Annotation] = field(default_factory=list)


@dataclass
class StructureIndex:
    """Everything the renderer needs, addressable by source line number."""

    filename: str
    items: list[StructuralItem] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    problems: list[IndentProblem] = field(default_factory=list)
    by_line: dict[int, StructuralItem | Annotation] = field(default_factory=dict)

    def item_at(self, line_no: int) -> StructuralItem | None:
        node = self.by_line.get(line_no)
        return node if isinstance(node, StructuralItem) else None

    def annotation_at(self, line_no: int) -> Annotation | None:
        node = self.by_line.get(line_no)
        return node if isinstance(node, Annotation) else None

    @property
    def depths(self) -> list[int]:
        return [item.depth for item in self.items]

    @property
    def max_depth(self) -> int:
        return max((item.depth for item in self.items), default=0)


@dataclass(frozen=True)
class OutlineResolution:
    """Summary of depths overlaid from an authoritative outline."""

    matched: int
    unresolved: int
    ambiguous: int


@dataclass(frozen=True)
class IndentLadder:
    """The single indentation formula for the whole document.

    ``item_x = base_x + depth * step`` — nothing else in the exporter is allowed
    to add or subtract horizontal offsets for outline depth.
    """

    base_x: float = 0.20 * INCH
    step: float = 0.30 * INCH
    annotation_offset: float = 0.14 * INCH
    heading_child_indent: float = 0.10 * INCH
    # Letter width minus two 0.80in margins minus the two 6pt frame paddings
    # ReportLab adds inside the text frame.
    content_width: float = 6.90 * INCH - 12.0
    min_text_width: float = 2.90 * INCH

    @property
    def max_depth(self) -> int:
        """Deepest depth that still leaves a readable measure on the page."""
        room = self.content_width - self.min_text_width - self.base_x - self.annotation_offset
        return max(0, int(room // self.step))

    def clamp(self, depth: int) -> int:
        return max(0, min(int(depth), self.max_depth))

    def item_x(self, depth: int) -> float:
        """Left edge of a structural item's text. Marker type never enters here."""
        return self.base_x + self.clamp(depth) * self.step

    def annotation_x(self, owner_depth: int) -> float:
        """Left edge of an annotation, tied to its owning item."""
        return self.item_x(owner_depth) + self.annotation_offset

    def text_width(self, left: float) -> float:
        return max(self.min_text_width, self.content_width - left)


def _validate(filename: str, line_no: int, lead: str, marker: str) -> IndentProblem | None:
    if "\t" in lead:
        return IndentProblem(filename, line_no, lead, marker, "tab in structural indentation")
    if len(lead) % 2:
        return IndentProblem(filename, line_no, lead, marker, "odd structural indentation")
    return None


def scan_structure(
    text: str,
    filename: str = "<manual>",
    *,
    line_offset: int = 0,
    strict: bool = True,
) -> StructureIndex:
    """Parse manual source into a structural AST.

    ``line_offset`` is added to reported line numbers so that errors point at the
    original file even when front matter has already been stripped.  With
    ``strict=False`` malformed lines are collected in ``index.problems`` and the
    line is skipped instead of being coerced into a depth.
    """

    index = StructureIndex(filename=filename)
    stack: list[StructuralItem] = []
    in_fence = False
    group_id = 0
    open_root_group: int | None = None
    last_item: StructuralItem | None = None

    for offset, raw in enumerate(text.splitlines(), 1):
        line_no = offset + line_offset
        line = raw.rstrip()

        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue

        if _HEADING_RE.match(line):
            # A heading opens a new section: nothing above it can own a line below it.
            stack.clear()
            open_root_group = None
            last_item = None
            continue

        if _RULE_RE.match(line):
            # A `---` is a page break, not a section boundary: the outline
            # hierarchy (and every depth in it) continues across it unchanged.
            continue

        struct = _STRUCT_RE.match(line)
        if struct:
            lead = struct.group("lead")
            problem = _validate(filename, line_no, lead, struct.group("marker"))
            if problem:
                index.problems.append(problem)
                continue
            leading = len(lead)
            while stack and stack[-1].leading_spaces >= leading:
                stack.pop()
            group_id += 1
            open_root_group = None
            item = StructuralItem(
                marker=struct.group("marker"),
                depth=leading // 2,
                content=struct.group("content").strip(),
                line_no=line_no,
                leading_spaces=leading,
                parent_line=stack[-1].line_no if stack else None,
                group_id=group_id,
            )
            stack.append(item)
            last_item = item
            index.items.append(item)
            index.by_line[line_no] = item
            continue

        grammar = _GRAMMAR_RE.match(line)
        quote = None if grammar else _QUOTE_RE.match(line)
        if grammar or quote:
            match = grammar or quote
            assert match is not None
            lead = match.group("lead")
            marker = match.group("marker")
            problem = _validate(filename, line_no, lead, marker)
            if problem:
                index.problems.append(problem)
                continue
            leading = len(lead)
            owner: StructuralItem | None = None
            for candidate in reversed(stack):
                if candidate.leading_spaces < leading:
                    owner = candidate
                    break
            if owner is not None:
                annotation_group = owner.group_id
            elif (
                last_item is not None
                and open_root_group is None
                and leading == last_item.leading_spaces
            ):
                # Written flush with the item right above it. Under the manual's
                # `owner + 2` convention that is not enough to make the item its
                # owner, so its x stays put - but it is plainly commentary on
                # that line, so it travels with it across a page break.
                open_root_group = last_item.group_id
                annotation_group = open_root_group
            else:
                # Section-root annotation: a `*` opens a group, a `>` joins it.
                if marker == "*" or open_root_group is None:
                    group_id += 1
                    open_root_group = group_id
                annotation_group = open_root_group
            annotation = Annotation(
                kind="grammar" if marker == "*" else "commentary",
                marker=marker,
                content=match.group("content").strip(),
                line_no=line_no,
                leading_spaces=leading,
                owner_line=owner.line_no if owner else None,
                owner_depth=owner.depth if owner else 0,
                group_id=annotation_group,
            )
            if owner is not None:
                owner.annotations.append(annotation)
            index.annotations.append(annotation)
            index.by_line[line_no] = annotation
            continue

        # Any other content line closes nothing; prose simply inherits the
        # position of whatever was emitted last (handled by the renderer).

    if strict and index.problems:
        raise StructuralIndentError(index.problems)
    return index


def _normal(text: str) -> str:
    """Normalize a heading/item only for cross-file identity matching."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("*", "").replace("_", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip().casefold()


def _heading_paths(text: str, *, line_offset: int = 0) -> dict[int, tuple[str, ...]]:
    """Return the active level 1-4 heading path for every source line."""
    active: dict[int, str] = {}
    paths: dict[int, tuple[str, ...]] = {}
    in_fence = False
    for offset, raw in enumerate(text.splitlines(), 1):
        line_no = offset + line_offset
        line = raw.rstrip()
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            paths[line_no] = tuple(active.get(level, "") for level in range(1, 5))
            continue
        if not in_fence:
            heading = _HEADING_RE.match(line)
            if heading:
                level = len(heading.group("hashes"))
                if level <= 4:
                    active[level] = _normal(heading.group("text"))
                    for deeper in range(level + 1, 5):
                        active.pop(deeper, None)
        paths[line_no] = tuple(active.get(level, "") for level in range(1, 5))
    return paths


def apply_outline_depths(
    source: StructureIndex,
    source_text: str,
    outline_text: str,
    *,
    source_line_offset: int = 0,
    outline_filename: str = "<outline>",
) -> OutlineResolution:
    """Overlay structural depth from a separate authoritative outline.

    The shared editor Markdown still supplies every word and annotation. Exact
    content plus heading context identifies the corresponding outline item; its
    source indentation supplies the PDF depth. Items that do not exist in the
    outline (for example generated appendix analytics) retain their own depth.
    """
    outline = scan_structure(outline_text, outline_filename)
    source_paths = _heading_paths(source_text, line_offset=source_line_offset)
    outline_paths = _heading_paths(outline_text)

    # Exact sequence blocks disambiguate repeated short labels such as ``voz``
    # and ``ángel`` even when editorial heading text differs between files.
    matcher = SequenceMatcher(
        None,
        [_normal(item.content) for item in source.items],
        [_normal(item.content) for item in outline.items],
        autojunk=False,
    )
    sequence_depths = {
        source.items[source_start + offset].line_no: outline.items[outline_start + offset].depth
        for source_start, outline_start, size in matcher.get_matching_blocks()
        for offset in range(size)
    }

    by_path: dict[tuple[tuple[str, ...], str], list[int]] = {}
    by_nearest: dict[tuple[str, str], list[int]] = {}
    by_content: dict[str, set[int]] = {}
    for item in outline.items:
        content = _normal(item.content)
        path = outline_paths.get(item.line_no, ("", "", "", ""))
        nearest = next((heading for heading in reversed(path) if heading), "")
        by_path.setdefault((path, content), []).append(item.depth)
        by_nearest.setdefault((nearest, content), []).append(item.depth)
        by_content.setdefault(content, set()).add(item.depth)

    matched = 0
    unresolved = 0
    ambiguous = 0
    path_occurrences: dict[tuple[tuple[str, ...], str], int] = {}
    nearest_occurrences: dict[tuple[str, str], int] = {}
    for item in source.items:
        content = _normal(item.content)
        path = source_paths.get(item.line_no, ("", "", "", ""))
        if path[0] in {"apéndices", "appendices"}:
            # The outline governs the book body. Generated appendix analytics
            # are independent material and keep their own source indentation.
            unresolved += 1
            continue
        nearest = next((heading for heading in reversed(path) if heading), "")
        path_key = (path, content)
        nearest_key = (nearest, content)
        resolved_depth: int | None = sequence_depths.get(item.line_no)

        path_sequence = by_path.get(path_key, [])
        path_index = path_occurrences.get(path_key, 0)
        path_occurrences[path_key] = path_index + 1
        nearest_sequence = by_nearest.get(nearest_key, [])
        nearest_index = nearest_occurrences.get(nearest_key, 0)
        nearest_occurrences[nearest_key] = nearest_index + 1
        if resolved_depth is None and path_index < len(path_sequence):
            resolved_depth = path_sequence[path_index]
        elif resolved_depth is None and nearest_index < len(nearest_sequence):
            resolved_depth = nearest_sequence[nearest_index]

        choices = by_content.get(content, set())
        if resolved_depth is None and len(choices) == 1:
            resolved_depth = next(iter(choices))
        elif resolved_depth is None and item.depth in choices:
            # The content exists at more than one outline depth, but the shared
            # source already uses one of those valid positions.
            resolved_depth = item.depth

        if resolved_depth is not None:
            item.depth = resolved_depth
            matched += 1
        elif choices:
            ambiguous += 1
        else:
            unresolved += 1

    items_by_line = {item.line_no: item for item in source.items}
    for annotation in source.annotations:
        owner = items_by_line.get(annotation.owner_line or -1)
        annotation.owner_depth = owner.depth if owner else 0

    stack: list[StructuralItem] = []
    active_path: tuple[str, ...] | None = None
    for item in source.items:
        path = source_paths.get(item.line_no, ("", "", "", ""))
        if path != active_path:
            stack.clear()
            active_path = path
        while stack and stack[-1].depth >= item.depth:
            stack.pop()
        item.parent_line = stack[-1].line_no if stack else None
        stack.append(item)

    return OutlineResolution(matched=matched, unresolved=unresolved, ambiguous=ambiguous)


def depth_report(index: StructureIndex) -> list[tuple[int, str, int, str]]:
    """(line, marker, depth, content) tuples — handy in tests and diagnostics."""
    return [(item.line_no, item.marker, item.depth, item.content) for item in index.items]


def iter_groups(index: StructureIndex) -> Iterable[list[StructuralItem | Annotation]]:
    """Yield each item together with the annotations that belong to it."""
    buckets: dict[int, list[StructuralItem | Annotation]] = {}
    order: list[int] = []
    for node in sorted(index.items + index.annotations, key=lambda n: n.line_no):
        gid = node.group_id
        if gid not in buckets:
            buckets[gid] = []
            order.append(gid)
        buckets[gid].append(node)
    for gid in order:
        yield buckets[gid]
