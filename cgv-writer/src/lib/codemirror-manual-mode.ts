import type { EditorState, Extension, Range } from "@codemirror/state";
import {
  Decoration,
  EditorView,
  ViewPlugin,
  WidgetType,
  type DecorationSet,
  type ViewUpdate
} from "@codemirror/view";
import { convertFileSrc } from "@tauri-apps/api/core";
import { findInlineBibleReferenceMatches } from "cgv-bible";
import { BIBLE_INDEX_UPDATED_EVENT, getSharedBibleIndex } from "./bible-index-store";
import { isTableLine, isTableSeparatorRow, renderTableHtml } from "./table-block";

/** Hide markdown syntax with marks (not replace) so mouse selection keeps working. */

interface ManualLineStyle {
  className: string;
  prefixLength: number;
  suffixLength: number;
  legacyComment?: boolean;
  code?: boolean;
}

const hiddenMark = Decoration.mark({ class: "cm-cgv-manual-hidden" });
let manualImageBaseDir = "";

export function setManualImageBasePath(path: string | null | undefined): void {
  const value = String(path || "");
  manualImageBaseDir = value.replace(/[/\\][^/\\]*$/, "");
}

function imageSrcForManual(src: string): string {
  const trimmed = src.trim();
  if (!trimmed) return "";
  if (/^(https?:|data:|blob:|asset:|file:)/i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("/")) return convertFileSrc(trimmed);
  if (!manualImageBaseDir) return trimmed;
  return convertFileSrc(`${manualImageBaseDir}/${trimmed}`);
}

class ImageWidget extends WidgetType {
  constructor(readonly alt: string, readonly src: string) {
    super();
  }

  eq(other: ImageWidget): boolean {
    return other.alt === this.alt && other.src === this.src;
  }

  toDOM(): HTMLElement {
    const figure = document.createElement("figure");
    figure.className = "cm-cgv-manual-image";
    const image = document.createElement("img");
    image.alt = this.alt;
    image.src = imageSrcForManual(this.src);
    image.loading = "lazy";
    figure.appendChild(image);
    if (this.alt.trim()) {
      const caption = document.createElement("figcaption");
      caption.textContent = this.alt.trim();
      figure.appendChild(caption);
    }
    return figure;
  }
}

class TableWidget extends WidgetType {
  constructor(readonly markdown: string) {
    super();
  }

  eq(other: TableWidget): boolean {
    return other.markdown === this.markdown;
  }

  toDOM(): HTMLElement {
    const dom = document.createElement("div");
    dom.className = "cm-cgv-manual-table";
    const inner = document.createElement("div");
    inner.className = "cm-cgv-manual-table-inner";
    inner.innerHTML = renderTableHtml(this.markdown);
    dom.appendChild(inner);
    return dom;
  }
}

interface TableRange {
  from: number;
  to: number;
  startLine: number;
  endLine: number;
  markdown: string;
}

function isTableStartAtLine(state: EditorState, lineNumber: number): boolean {
  if (lineNumber < 1 || lineNumber >= state.doc.lines) return false;
  return isTableLine(state.doc.line(lineNumber).text) && isTableSeparatorRow(state.doc.line(lineNumber + 1).text);
}

function tableStartNearLine(state: EditorState, lineNumber: number): number | null {
  let start = Math.max(1, Math.min(state.doc.lines, lineNumber));
  let guard = 0;

  while (start > 1 && guard < 80 && isTableLine(state.doc.line(start - 1).text)) {
    start -= 1;
    guard += 1;
  }

  return isTableStartAtLine(state, start) ? start : null;
}

function collectTableRange(state: EditorState, startLine: number): TableRange | null {
  if (!isTableStartAtLine(state, startLine)) return null;

  const rows: string[] = [];
  let lineNumber = startLine;
  while (lineNumber <= state.doc.lines && isTableLine(state.doc.line(lineNumber).text)) {
    rows.push(state.doc.line(lineNumber).text.trimEnd());
    lineNumber += 1;
  }

  const start = state.doc.line(startLine);
  const endLineNumber = Math.max(startLine, lineNumber - 1);
  const end = state.doc.line(endLineNumber);
  return {
    from: start.from,
    to: end.to,
    startLine,
    endLine: endLineNumber,
    markdown: rows.join("\n")
  };
}

function findVisibleTableRanges(view: EditorView): TableRange[] {
  const rangesByStart = new Map<number, TableRange>();

  for (const visible of view.visibleRanges) {
    const first = view.state.doc.lineAt(visible.from).number;
    const last = view.state.doc.lineAt(visible.to).number;

    for (let number = first; number <= last; number += 1) {
      const start = tableStartNearLine(view.state, number);
      if (start == null || rangesByStart.has(start)) continue;
      const range = collectTableRange(view.state, start);
      if (range) rangesByStart.set(start, range);
      number = range?.endLine ?? number;
    }
  }

  return Array.from(rangesByStart.values()).sort((a, b) => a.from - b.from);
}

function previousNonBlankLine(view: EditorView, lineNumber: number): string {
  for (let number = lineNumber - 1; number >= 1; number -= 1) {
    const text = view.state.doc.line(number).text.trim();
    if (text) return text;
  }
  return "";
}

function isListContinuation(view: EditorView, lineNumber: number, text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (/^(#{1,6})\s+/.test(trimmed)) return false;
  if (/^-\s+/.test(trimmed)) return false;
  if (/^```/.test(trimmed)) return false;
  if (/^>\s*/.test(trimmed)) return false;
  return /^-\s+/.test(previousNonBlankLine(view, lineNumber));
}

function frontMatterEndLine(state: EditorState): number {
  if (state.doc.lines < 2 || state.doc.line(1).text.trim() !== "---") return 0;
  for (let number = 2; number <= state.doc.lines; number += 1) {
    if (state.doc.line(number).text.trim() === "---") return number;
  }
  return 0;
}

function isCodeFenceLine(text: string): boolean {
  return /^```/.test(String(text || "").trim());
}

function codeFenceLines(state: EditorState): { codeLines: Set<number>; fenceLines: Set<number> } {
  const codeLines = new Set<number>();
  const fenceLines = new Set<number>();
  let openFenceLine = 0;

  for (let number = 1; number <= state.doc.lines; number += 1) {
    if (!isCodeFenceLine(state.doc.line(number).text)) continue;
    fenceLines.add(number);

    if (openFenceLine) {
      for (let codeLine = openFenceLine + 1; codeLine < number; codeLine += 1) {
        codeLines.add(codeLine);
      }
      openFenceLine = 0;
    } else {
      openFenceLine = number;
    }
  }

  if (openFenceLine) {
    for (let codeLine = openFenceLine + 1; codeLine <= state.doc.lines; codeLine += 1) {
      codeLines.add(codeLine);
    }
  }

  return { codeLines, fenceLines };
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
  tableLines: Set<number>,
  codeLines: Set<number>,
  fenceLines: Set<number>
): ManualLineStyle {
  if (frontMatterEnd && lineNumber <= frontMatterEnd) {
    return { className: "cm-cgv-manual-yaml", prefixLength: 0, suffixLength: 0 };
  }

  if (fenceLines.has(lineNumber)) {
    return { className: "cm-cgv-manual-code-fence", prefixLength: 0, suffixLength: 0, code: true };
  }

  if (codeLines.has(lineNumber)) {
    return { className: "cm-cgv-manual-code", prefixLength: 0, suffixLength: 0, code: true };
  }

  if (!text.trim()) {
    return { className: "cm-cgv-manual-blank", prefixLength: 0, suffixLength: 0 };
  }

  if (tableLines.has(lineNumber)) {
    return { className: "cm-cgv-manual-table-row", prefixLength: 0, suffixLength: 0 };
  }

  if (/^!\[[^\]\n]*\]\([^)]+?\)\s*$/.test(text.trim())) {
    return { className: "cm-cgv-manual-image-source", prefixLength: 0, suffixLength: 0, code: true };
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

  if (isListContinuation(view, lineNumber, text)) {
    return {
      className: "cm-cgv-manual-bullet cm-cgv-manual-bullet-continuation",
      prefixLength: 0,
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

function addImageWidget(
  text: string,
  lineFrom: number,
  decorations: Range<Decoration>[]
): boolean {
  const match = text.trim().match(/^!\[([^\]\n]*)\]\(([^)]+?)\)\s*$/);
  if (!match) return false;
  const startOffset = text.indexOf(match[0].trim());
  const from = lineFrom + Math.max(0, startOffset);
  const to = lineFrom + text.length;
  decorations.push(
    Decoration.widget({
      widget: new ImageWidget(match[1] ?? "", match[2] ?? ""),
      side: -1,
      block: true
    }).range(from)
  );
  addHidden(decorations, from, to);
  return true;
}

function addInlineDecorations(
  text: string,
  lineFrom: number,
  contentStart: number,
  contentEnd: number,
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
      className: "cm-cgv-manual-scripture-text",
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

interface ManualDecorationOptions {
  widgets: boolean;
  inline: boolean;
  references: boolean;
}

const fullDecorations: ManualDecorationOptions = { widgets: true, inline: true, references: true };
const scrollDecorations: ManualDecorationOptions = { widgets: false, inline: true, references: false };

function buildDecorations(
  view: EditorView,
  options: ManualDecorationOptions = fullDecorations
): DecorationSet {
  const decorations: Range<Decoration>[] = [];
  const seen = new Set<number>();
  const frontMatterEnd = frontMatterEndLine(view.state);
  const tableRanges = options.widgets ? findVisibleTableRanges(view) : [];
  const tableLines = new Set<number>();
  const { codeLines, fenceLines } = codeFenceLines(view.state);
  for (const range of tableRanges) {
    decorations.push(
      Decoration.widget({
        widget: new TableWidget(range.markdown),
        side: -1
      }).range(range.from)
    );
    for (let number = range.startLine; number <= range.endLine; number += 1) {
      tableLines.add(number);
      decorations.push(
        Decoration.line({
          attributes: {
            class:
              number === range.startLine
                ? "cm-cgv-manual-table-source cm-cgv-manual-table-source-first"
                : "cm-cgv-manual-table-source"
          }
        }).range(view.state.doc.line(number).from)
      );
    }
  }

  for (const visible of view.visibleRanges) {
    const first = view.state.doc.lineAt(visible.from).number;
    const last = view.state.doc.lineAt(visible.to).number;

    for (let number = first; number <= last; number += 1) {
      if (seen.has(number)) continue;
      seen.add(number);

      const line = view.state.doc.line(number);
      if (tableLines.has(number)) continue;

      const style = classifyLine(view, number, line.text, frontMatterEnd, tableLines, codeLines, fenceLines);

      decorations.push(
        Decoration.line({
          attributes: { class: `cm-cgv-manual-line ${style.className}` }
        }).range(line.from)
      );

      const contentStart = line.from + style.prefixLength;
      const contentEnd = line.to - style.suffixLength;
      if (style.className.includes("cm-cgv-manual-image-source")) {
        if (options.widgets) addImageWidget(line.text, line.from, decorations);
        continue;
      }

      addHidden(decorations, line.from, contentStart);
      addHidden(decorations, contentEnd, line.to);

      if (style.legacyComment && contentEnd > contentStart) {
        decorations.push(
          Decoration.mark({ class: "cm-cgv-manual-comment-content" }).range(contentStart, contentEnd)
        );
      }

      if (options.inline && !style.code) {
        addInlineDecorations(
          line.text,
          line.from,
          contentStart,
          contentEnd,
          decorations
        );
      }

      if (options.references && !style.code) {
        addInlineBibleRefs(line.text, line.from, style, decorations);
      }
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
      if (update.docChanged) {
        this.decorations = buildDecorations(update.view);
        return;
      }

      if (update.viewportMoved) {
        this.decorations = buildDecorations(update.view, scrollDecorations);
        return;
      }

      if (update.viewportChanged || update.heightChanged || update.geometryChanged) {
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
