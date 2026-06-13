import type { Editor } from "@tiptap/react";

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

    if (next.attrs.class === "cgv-scripture") {
      return false;
    }

    tr.setNodeMarkup(nextPos, undefined, {
      ...next.attrs,
      class: "cgv-scripture"
    });
    changed = true;
    return false;
  });

  if (changed) {
    editor.view.dispatch(tr);
  }
}
