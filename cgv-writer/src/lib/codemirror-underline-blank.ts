import { Decoration, DecorationSet, EditorView, ViewPlugin, type ViewUpdate } from "@codemirror/view";

const BLANK_TAG = /<u>([^<]*)<\/u>/g;

const blankContentMark = Decoration.mark({ class: "cm-cgv-blank" });

function buildBlankDecorations(view: EditorView): DecorationSet {
  const marks: { from: number; to: number; value: Decoration }[] = [];

  for (const visible of view.visibleRanges) {
    const from = Math.max(0, visible.from - 16);
    const to = Math.min(view.state.doc.length, visible.to + 16);
    const source = view.state.sliceDoc(from, to);

    for (const match of source.matchAll(BLANK_TAG)) {
      const content = match[1] ?? "";
      const index = match.index ?? -1;
      if (index < 0 || !content.length) continue;

      const contentStart = from + index + 3;
      const contentEnd = contentStart + content.length;
      marks.push({ from: contentStart, to: contentEnd, value: blankContentMark });
    }
  }

  if (!marks.length) return Decoration.none;

  marks.sort((a, b) => a.from - b.from || a.to - b.to);
  return Decoration.set(marks, true);
}

/** Bold + underline for `<u>…</u>` fill-in-the-blank spans in Markdown source view. */
export const cgvBlankHighlightExtension = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;

    constructor(view: EditorView) {
      this.decorations = buildBlankDecorations(view);
    }

    update(update: ViewUpdate) {
      if (update.viewportMoved && !update.docChanged) return;
      if (update.docChanged || update.viewportChanged) {
        this.decorations = buildBlankDecorations(update.view);
      }
    }
  },
  { decorations: plugin => plugin.decorations }
);
