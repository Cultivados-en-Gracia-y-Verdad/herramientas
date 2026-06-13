import type { Editor } from "@tiptap/core";

const SCRIPTURE_CLASS = "cgv-scripture";
const WORD_CHAR = /[\p{L}\p{N}'’_-]/u;

function wordBoundsAt(text: string, offset: number): { from: number; to: number } | null {
  if (offset < 0 || offset > text.length) return null;

  let from = offset;
  while (from > 0 && WORD_CHAR.test(text[from - 1])) from--;

  let to = offset;
  while (to < text.length && WORD_CHAR.test(text[to])) to++;

  if (from === to) return null;
  return { from, to };
}

/** Fill-in-the-blank: underline the word at the cursor (or selection). */
export function underlineWordAtCursor(editor: Editor): void {
  const { from, empty } = editor.state.selection;

  if (!empty) {
    editor.chain().focus().toggleUnderline().run();
    return;
  }

  const $pos = editor.state.doc.resolve(from);
  const parentStart = $pos.start();
  const text = $pos.parent.textContent;
  const offset = from - parentStart;
  const bounds = wordBoundsAt(text, offset);

  if (!bounds) return;

  const wordFrom = parentStart + bounds.from;
  const wordTo = parentStart + bounds.to;

  editor
    .chain()
    .focus()
    .setTextSelection({ from: wordFrom, to: wordTo })
    .toggleUnderline()
    .setTextSelection(wordTo)
    .run();
}

/** Verse block immediately under ### (not #### anchor text). */
export function applyScriptureStyle(editor: Editor): void {
  editor.chain().focus().setParagraph().updateAttributes("paragraph", { class: SCRIPTURE_CLASS }).run();
}

export function applyHeadingStyle(editor: Editor, level: 4 | 5 | 6): void {
  editor.chain().focus().toggleHeading({ level }).run();
}

export function applyCommentBulletList(editor: Editor): void {
  editor.chain().focus().toggleBulletList().run();
}
