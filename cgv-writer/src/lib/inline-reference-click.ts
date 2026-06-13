import type { Editor } from "@tiptap/react";
import {
  getInlineBibleReferenceAtPosition,
  type BibleIndex,
  type InlineBibleMatch
} from "cgv-bible";

export function isInsideH3Heading(editor: Editor, pos: number): boolean {
  const $pos = editor.state.doc.resolve(pos);

  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    const node = $pos.node(depth);
    if (node.type.name === "heading" && node.attrs.level === 3) {
      return true;
    }
  }

  return false;
}

export function getInlineReferenceAtDocPos(
  editor: Editor,
  pos: number,
  index: BibleIndex | null
): InlineBibleMatch | null {
  if (!index || isInsideH3Heading(editor, pos)) {
    return null;
  }

  const $pos = editor.state.doc.resolve(pos);
  const parent = $pos.parent;

  if (!parent.isTextblock) {
    return null;
  }

  const blockStart = $pos.start();
  const offset = pos - blockStart;

  return getInlineBibleReferenceAtPosition(parent.textContent, offset, index);
}

export function getInlineReferenceFromClick(
  editor: Editor,
  event: MouseEvent,
  index: BibleIndex | null
): InlineBibleMatch | null {
  const pos = editor.view.posAtCoords({ left: event.clientX, top: event.clientY })?.pos;
  if (pos == null) return null;
  return getInlineReferenceAtDocPos(editor, pos, index);
}
