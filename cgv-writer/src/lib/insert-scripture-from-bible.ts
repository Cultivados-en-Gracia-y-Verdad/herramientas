import type { Editor } from "@tiptap/react";
import { ensureScriptureParagraphsAfterH3 } from "./manual-scripture-blocks";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function applyScriptureTextAfterH3(
  editor: Editor,
  h3Pos: number,
  text: string
): void {
  const trimmed = text.trim();
  if (!trimmed) return;

  const { state } = editor;
  const h3Node = state.doc.nodeAt(h3Pos);
  if (!h3Node || h3Node.type.name !== "heading" || h3Node.attrs.level !== 3) {
    return;
  }

  const afterH3 = h3Pos + h3Node.nodeSize;
  const next = state.doc.nodeAt(afterH3);

  if (next?.type.name === "paragraph") {
    const from = afterH3 + 1;
    const to = afterH3 + next.nodeSize - 1;
    editor
      .chain()
      .focus()
      .setTextSelection({ from, to })
      .insertContent(trimmed)
      .run();
  } else {
    editor
      .chain()
      .focus()
      .insertContentAt(afterH3, `<p class="cgv-scripture">${escapeHtml(trimmed)}</p>`)
      .run();
  }

  ensureScriptureParagraphsAfterH3(editor);
}

export function findH3AtPos(editor: Editor, pos: number): { pos: number; text: string } | null {
  const $pos = editor.state.doc.resolve(pos);

  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    const node = $pos.node(depth);
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      continue;
    }

    const text = node.textContent.trim();
    if (!text) return null;

    return { pos: $pos.before(depth), text };
  }

  return null;
}
