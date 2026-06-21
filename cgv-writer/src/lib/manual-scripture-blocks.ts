import type { Editor } from "@tiptap/react";

function scriptureTagAttrs(attrs: Record<string, unknown>): Record<string, unknown> {
  return { ...attrs, class: "cgv-scripture" };
}

function paragraphNeedsScriptureTag(cls: string, attrs: Record<string, unknown>): boolean {
  const tokens = cls.split(/\s+/);
  return (
    !tokens.includes("cgv-scripture") &&
    !tokens.includes("cgv-quiz") &&
    !attrs.dataQuizId
  );
}

/** Tag the paragraph after an H3 when the cursor is on that pair (cheap on Enter). */
export function ensureScriptureParagraphAfterH3AtCursor(editor: Editor): void {
  const { state } = editor;
  const $pos = state.doc.resolve(state.selection.from);
  let depth = $pos.depth;
  while (depth > 0 && !$pos.node(depth).isBlock) {
    depth -= 1;
  }
  if (depth === 0) return;

  const block = $pos.node(depth);
  if (block.type.name !== "paragraph") return;

  const parent = $pos.node(depth - 1);
  const index = $pos.index(depth - 1);
  if (index === 0) return;

  const prev = parent.child(index - 1);
  if (prev.type.name !== "heading" || prev.attrs.level !== 3) return;

  const cls = String(block.attrs.class || "");
  if (!paragraphNeedsScriptureTag(cls, block.attrs as Record<string, unknown>)) return;

  const blockPos = $pos.before(depth);
  editor.view.dispatch(
    state.tr.setNodeMarkup(blockPos, undefined, scriptureTagAttrs(block.attrs as Record<string, unknown>))
  );
}

/** Tag the first paragraph after each H3 as scripture when it has no class yet. */
export function ensureScriptureParagraphsAfterH3(editor: Editor): void {
  const { state } = editor;
  let changed = false;
  const tr = state.tr;

  state.doc.descendants((node, pos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return true;
    }

    const nextPos = pos + node.nodeSize;
    const next = state.doc.nodeAt(nextPos);
    if (!next || next.type.name !== "paragraph") {
      return false;
    }

    const cls = String(next.attrs.class || "");
    if (!paragraphNeedsScriptureTag(cls, next.attrs as Record<string, unknown>)) {
      return false;
    }

    tr.setNodeMarkup(nextPos, undefined, scriptureTagAttrs(next.attrs as Record<string, unknown>));
    changed = true;
    return false;
  });

  if (changed) {
    editor.view.dispatch(tr);
  }
}
