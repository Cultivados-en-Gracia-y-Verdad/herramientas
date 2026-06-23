import type { EditorState, Extension, Range, Text } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  ViewPlugin,
  type DecorationSet,
  type ViewUpdate
} from "@codemirror/view";
import { findInlineBibleReferenceMatches } from "cgv-bible";
import { BIBLE_INDEX_UPDATED_EVENT, getSharedBibleIndex } from "./bible-index-store";

/** Hide markdown syntax with marks (not replace) so mouse selection keeps working. */

interface ManualLineStyle {
  className: string;
  prefixLength: number;
  suffixLength: number;
  legacyComment?: boolean;
}

const hiddenMark = Decoration.mark({ class: "cm-cgv-manual-hidden" });

function findTableLineNumbers(doc: Text): Set<number> {
  const lines = new Set<number>();
  let lineNumber = 1;

  while (lineNumber <= doc.lines) {
    const text = doc.line(lineNumber).text;
    if (!/^\|.+\|/.test(text.trim()) && !/^\|.*\|/.test(text.trim())) {
      lineNumber += 1;
      continue;
    }

    let index = lineNumber;
    while (index <= doc.lines) {
      const row = doc.line(index).text;
      if (!row.trim()) break;
      if (!row.includes("|")) break;
      lines.add(index);
      index += 1;
    }
    lineNumber = index;
  }

  return lines;
}

function previousNonBlankLine(view: EditorView, lineNumber: number): string {
  for (let number = lineNumber - 1; number >= 1; number -= 1) {
    const text = view.state.doc.line(number).text.trim();
    if (text) return text;
  }
  return "";
}

function frontMatterEndLine(state: EditorState): number {
  if (state.doc.lines < 2 || state.doc.line(1).text.trim() !== "---") return 0;
  for (let number = 2; number <= state.doc.lines; number += 1) {
    if (state.doc.line(number).text.trim() === "---") return number;
  }
  return 0;
}

function headingStyle(level: number, prefixLength: number, suffixLength = 0): ManualLineStyle {
  return {
    className: `cm-cgv-manual-h${level}`,
    prefixLength,
    suffixLength
  };
}

function classifyLine(
  view: EditorView,
  lineNumber: number,
  text: string,
  frontMatterEnd: number,
  tableLines: Set<number>
): ManualLineStyle {
  if (frontMatterEnd && lineNumber <= frontMatterEnd) {
    return { className: "cm-cgv-manual-yaml", prefixLength: 0, suffixLength: 0 };
  }

  if (!text.trim()) {
    return { className: "cm-cgv-manual-blank", prefixLength: 0, suffixLength: 0 };
  }

  if (tableLines.has(lineNumber)) {
    return { className: "cm-cgv-manual-table-row", prefixLength: 0, suffixLength: 0 };
  }

  const wrappedHeading = text.match(/^<!--\s*(#{1,6}\s+)([\s\S]*?)\s*-->$/);
  if (wrappedHeading) {
    const prefix = text.match(/^<!--\s*#{1,6}\s+/)?.[0] ?? "";
    const suffix = text.match(/\s*-->$/)?.[0] ?? "";
    return {
      ...headingStyle(wrappedHeading[1].trim().length, prefix.length, suffix.length),
      className: `cm-cgv-manual-h${wrappedHeading[1].trim().length} cm-cgv-manual-legacy-comment`,
      legacyComment: true
    };
  }

  const heading = text.match(/^(#{1,6})\s+/);
  if (heading) return headingStyle(heading[1].length, heading[0].length);

  const bullet = text.match(/^-\s+/);
  if (bullet) {
    return {
      className: "cm-cgv-manual-bullet",
      prefixLength: bullet[0].length,
      suffixLength: 0
    };
  }

  if (/^:\s*/.test(text)) {
    return { className: "cm-cgv-manual-definition", prefixLength: 0, suffixLength: 0 };
  }

  if (/^<!--\s*@quiz\s+#?([^\s]+)\s*-->$/i.test(text)) {
    return { className: "cm-cgv-manual-quiz", prefixLength: 0, suffixLength: 0 };
  }

  if (/^---\s*$/.test(text)) {
    return { className: "cm-cgv-manual-break", prefixLength: 0, suffixLength: 0 };
  }

  if (text.trim() && /^###\s+/.test(previousNonBlankLine(view, lineNumber))) {
    return { className: "cm-cgv-manual-scripture", prefixLength: 0, suffixLength: 0 };
  }

  return { className: "cm-cgv-manual-paragraph", prefixLength: 0, suffixLength: 0 };
}

function addHidden(
  decorations: Range<Decoration>[],
  from: number,
  to: number
) {
  if (to > from) decorations.push(hiddenMark.range(from, to));
}

function addInlineDecorations(
  text: string,
  lineFrom: number,
  contentStart: number,
  contentEnd: number,
  scriptureLine: boolean,
  decorations: Range<Decoration>[]
) {
  const patterns = [
    { regex: /__<u>([^<\n]+)<\/u>__/g, open: 5, close: 6, className: "cm-cgv-manual-underline" },
    { regex: /<u>([^<\n]+)<\/u>/g, open: 3, close: 4, className: "cm-cgv-manual-underline" },
    { regex: /\*\*([^*\n]+)\*\*/g, open: 2, close: 2, className: "cm-cgv-manual-bold" },
    { regex: /__([^_\n]+)__/g, open: 2, close: 2, className: "cm-cgv-manual-bold" },
    {
      regex: /(^|[^*])\*([^*\n]+)\*(?!\*)/g,
      open: 1,
      close: 1,
      className: scriptureLine ? "cm-cgv-manual-scripture-text" : "cm-cgv-manual-italic",
      leading: true
    }
  ];
  const occupied: Array<{ from: number; to: number }> = [];

  for (const pattern of patterns) {
    pattern.regex.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.regex.exec(text))) {
      const leading = pattern.leading ? match[1]?.length ?? 0 : 0;
      const start = lineFrom + match.index + leading;
      const end = lineFrom + match.index + match[0].length;
      const innerFrom = start + pattern.open;
      const innerTo = end - pattern.close;
      if (start < contentStart || end > contentEnd || innerTo <= innerFrom) continue;
      if (occupied.some(range => start < range.to && end > range.from)) continue;
      occupied.push({ from: start, to: end });

      addHidden(decorations, start, innerFrom);
      decorations.push(Decoration.mark({ class: pattern.className }).range(innerFrom, innerTo));
      addHidden(decorations, innerTo, end);
    }
  }
}

function addInlineBibleRefs(
  text: string,
  lineFrom: number,
  style: ManualLineStyle,
  decorations: Range<Decoration>[]
) {
  const index = getSharedBibleIndex();
  if (!index) return;
  if (style.className.includes("cm-cgv-manual-h3")) return;
  if (style.className.includes("yaml") || style.className.includes("quiz")) return;

  for (const match of findInlineBibleReferenceMatches(text, index)) {
    decorations.push(
      Decoration.mark({ class: "cm-cgv-inline-bible-ref" }).range(
        lineFrom + match.start,
        lineFrom + match.end
      )
    );
  }
}

function buildDecorations(view: EditorView): DecorationSet {
  const decorations: Range<Decoration>[] = [];
  const seen = new Set<number>();
  const frontMatterEnd = frontMatterEndLine(view.state);
  const tableLines = findTableLineNumbers(view.state.doc);

  for (const visible of view.visibleRanges) {
    const first = view.state.doc.lineAt(visible.from).number;
    const last = view.state.doc.lineAt(visible.to).number;

    for (let number = first; number <= last; number += 1) {
      if (seen.has(number)) continue;
      seen.add(number);

      const line = view.state.doc.line(number);
      const style = classifyLine(view, number, line.text, frontMatterEnd, tableLines);

      decorations.push(
        Decoration.line({
          attributes: { class: `cm-cgv-manual-line ${style.className}` }
        }).range(line.from)
      );

      const contentStart = line.from + style.prefixLength;
      const contentEnd = line.to - style.suffixLength;
      addHidden(decorations, line.from, contentStart);
      addHidden(decorations, contentEnd, line.to);

      if (style.legacyComment && contentEnd > contentStart) {
        decorations.push(
          Decoration.mark({ class: "cm-cgv-manual-comment-content" }).range(contentStart, contentEnd)
        );
      }

      const scriptureLine =
        style.className.includes("scripture") || style.className.includes("cm-cgv-manual-h4");

      addInlineDecorations(
        line.text,
        line.from,
        contentStart,
        contentEnd,
        scriptureLine,
        decorations
      );

      addInlineBibleRefs(line.text, line.from, style, decorations);
    }
  }

  return Decoration.set(decorations, true);
}

const manualDecorations = ViewPlugin.fromClass(
  class {
    decorations!: DecorationSet;
    private onBibleIndex = () => {
      this.decorations = buildDecorations(this.view);
    };
    private view!: EditorView;

    constructor(view: EditorView) {
      this.view = view;
      window.addEventListener(BIBLE_INDEX_UPDATED_EVENT, this.onBibleIndex);
      this.decorations = buildDecorations(view);
    }

    destroy() {
      window.removeEventListener(BIBLE_INDEX_UPDATED_EVENT, this.onBibleIndex);
    }

    update(update: ViewUpdate) {
      if (update.docChanged || update.selectionSet || update.viewportChanged) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: plugin => plugin.decorations }
);

export const codemirrorManualMode: Extension = [
  EditorView.editorAttributes.of({ class: "cm-cgv-manual-mode" }),
  manualDecorations
];
