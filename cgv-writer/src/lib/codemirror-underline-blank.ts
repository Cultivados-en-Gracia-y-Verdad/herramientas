import type { Text } from "@codemirror/state";
import { Decoration, DecorationSet, EditorView, ViewPlugin } from "@codemirror/view";

const BLANK_TAG = /<u>([^<]*)<\/u>/g;

const blankContentMark = Decoration.mark({ class: "cm-cgv-blank" });

function buildBlankDecorations(doc: Text): DecorationSet {
  const source = doc.toString();
  const marks: { from: number; to: number; value: Decoration }[] = [];

  for (const match of source.matchAll(BLANK_TAG)) {
    const content = match[1] ?? "";
    const index = match.index ?? -1;
    if (index < 0 || !content.length) continue;

    const contentStart = index + 3;
    const contentEnd = contentStart + content.length;
    marks.push({ from: contentStart, to: contentEnd, value: blankContentMark });
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
      this.decorations = buildBlankDecorations(view.state.doc);
    }

    update(update: { docChanged: boolean; view: EditorView }) {
      if (update.docChanged) {
        this.decorations = buildBlankDecorations(update.view.state.doc);
      }
    }
  },
  { decorations: plugin => plugin.decorations }
);
