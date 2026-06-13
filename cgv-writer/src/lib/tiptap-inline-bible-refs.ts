import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { findInlineBibleReferenceMatches } from "cgv-bible";
import { getSharedBibleIndex } from "./bible-index-store";

const inlineBibleRefsPluginKey = new PluginKey("cgvInlineBibleRefs");

function buildInlineBibleDecorations(doc: Parameters<typeof DecorationSet.create>[0]) {
  const index = getSharedBibleIndex();
  if (!index) return DecorationSet.empty;

  const decorations: Decoration[] = [];

  doc.descendants((node, pos) => {
    if (node.type.name === "heading" && node.attrs.level === 3) {
      return false;
    }

    if (!node.isTextblock) {
      return true;
    }

    const text = node.textContent;
    if (!text) {
      return false;
    }

    const blockContentStart = pos + 1;

    for (const match of findInlineBibleReferenceMatches(text, index)) {
      decorations.push(
        Decoration.inline(blockContentStart + match.start, blockContentStart + match.end, {
          class: "cgv-inline-bible-ref"
        })
      );
    }

    return false;
  });

  return decorations.length ? DecorationSet.create(doc, decorations) : DecorationSet.empty;
}

/** Dotted underline on inline cross-references (not H3). */
export const CgvInlineBibleRefs = Extension.create({
  name: "cgvInlineBibleRefs",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: inlineBibleRefsPluginKey,
        state: {
          init: (_, state) => buildInlineBibleDecorations(state.doc),
          apply(tr, value, _oldState, newState) {
            if (tr.docChanged || tr.getMeta(inlineBibleRefsPluginKey)) {
              return buildInlineBibleDecorations(newState.doc);
            }
            return value.map(tr.mapping, tr.doc);
          }
        },
        props: {
          decorations(state) {
            return inlineBibleRefsPluginKey.getState(state);
          }
        }
      })
    ];
  }
});

export { inlineBibleRefsPluginKey };
