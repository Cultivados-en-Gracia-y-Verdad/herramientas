import type { Editor } from "@tiptap/core";
import {
  removeEmptyParagraphsBetweenH4AndFirstH5,
  tightenPassageLayoutInEditor
} from "./manual-passage-layout";

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

function wordRangeAtDocPos(
  editor: Editor,
  pos: number
): { from: number; to: number } | null {
  const $pos = editor.state.doc.resolve(pos);
  if (!$pos.parent.isTextblock) return null;

  const parentStart = $pos.start();
  const text = $pos.parent.textContent;
  const offset = pos - parentStart;
  const bounds = wordBoundsAt(text, offset);
  if (!bounds) return null;

  return {
    from: parentStart + bounds.from,
    to: parentStart + bounds.to
  };
}

/** Fill-in-the-blank at a document position — returns false when no word there. */
export function underlineWordAtDocPos(editor: Editor, pos: number): boolean {
  const range = wordRangeAtDocPos(editor, pos);
  if (!range) return false;

  const mark = editor.schema.marks.underline;
  if (mark && editor.state.doc.rangeHasMark(range.from, range.to, mark)) {
    return true;
  }

  editor
    .chain()
    .focus()
    .setTextSelection(range)
    .setUnderline()
    .setTextSelection(range.to)
    .run();
  return true;
}

/** Fill-in-the-blank: underline the word at the cursor (or selection). */
export function underlineWordAtCursor(editor: Editor): void {
  const { from, empty } = editor.state.selection;

  if (!empty) {
    editor.chain().focus().toggleUnderline().run();
    return;
  }

  underlineWordAtDocPos(editor, from);
}

/** Verse block immediately under ### (not #### anchor text). */
export function applyScriptureStyle(editor: Editor): void {
  editor.chain().focus().setParagraph().updateAttributes("paragraph", { class: SCRIPTURE_CLASS }).run();
}

export function applyHeadingStyle(editor: Editor, level: 4 | 5 | 6): void {
  editor.chain().focus().toggleHeading({ level }).run();
  if (level === 5) {
    removeEmptyParagraphsBetweenH4AndFirstH5(editor);
  }
  tightenPassageLayoutInEditor(editor);
}

export function applyCommentBulletList(editor: Editor): void {
  editor.chain().focus().toggleBulletList().run();
}
