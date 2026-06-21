import Blockquote from "@tiptap/extension-blockquote";
import { Plugin } from "@tiptap/pm/state";

function emptyBlockquoteBulletListRanges(doc: {
  descendants: (
    f: (
      node: { type: { name: string }; nodeSize: number; textContent: string; forEach: (cb: (item: { textContent: string }) => void) => void },
      pos: number
    ) => void
  ) => void;
  resolve: (pos: number) => { depth: number; node: (depth: number) => { type: { name: string } } };
}): { from: number; to: number }[] {
  const ranges: { from: number; to: number }[] = [];

  doc.descendants((node, pos) => {
    if (node.type.name !== "bulletList") return;

    const $pos = doc.resolve(pos);
    let inBlockquote = false;
    for (let depth = $pos.depth; depth > 0; depth -= 1) {
      if ($pos.node(depth).type.name === "blockquote") {
        inBlockquote = true;
        break;
      }
    }
    if (!inBlockquote) return;

    let hasText = false;
    node.forEach(item => {
      if (item.textContent.trim()) hasText = true;
    });

    if (!hasText) {
      ranges.push({ from: pos, to: pos + node.nodeSize });
    }
  });

  return ranges;
}

/** En Síntesis review — one blockquote unit for round-trip with Presenter. */
export const CgvSynthesisBlockquote = Blockquote.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: "cgv-synthesis synthesis-box",
        parseHTML: element =>
          element.getAttribute("class") || "cgv-synthesis synthesis-box",
        renderHTML: attributes => ({
          class: attributes.class || "cgv-synthesis synthesis-box"
        })
      }
    };
  },

  addProseMirrorPlugins() {
    const parent = this.parent?.() ?? [];

    return [
      ...parent,
      new Plugin({
        appendTransaction(transactions, _oldState, newState) {
          if (!transactions.some(tr => tr.docChanged)) return null;

          const ranges = emptyBlockquoteBulletListRanges(newState.doc);
          if (!ranges.length) return null;

          const tr = newState.tr;
          ranges
            .sort((a, b) => b.from - a.from)
            .forEach(({ from, to }) => tr.delete(from, to));

          return tr.docChanged ? tr : null;
        }
      })
    ];
  }
});
