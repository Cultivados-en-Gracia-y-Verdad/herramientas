import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { EditorView } from "@tiptap/pm/view";
import { findInlineBibleReferenceMatches } from "cgv-bible";
import { getSharedBibleIndex } from "./bible-index-store";

const inlineBibleRefsPluginKey = new PluginKey("cgvInlineBibleRefs");

/** Skip inline-ref decoration on very large manuals. */
const MAX_INLINE_BIBLE_DOC_CHARS = 120_000;
const REBUILD_IDLE_MS = 2_000;
const REBUILD_IDLE_MS_LARGE = 5_000;
const LARGE_DOC_CHARS = 60_000;

function rebuildDelayMs(doc: ProseMirrorNode): number {
  return doc.textContent.length > LARGE_DOC_CHARS ? REBUILD_IDLE_MS_LARGE : REBUILD_IDLE_MS;
}

function buildInlineBibleDecorations(doc: ProseMirrorNode) {
  const index = getSharedBibleIndex();
  if (!index) return DecorationSet.empty;
  if (doc.textContent.length > MAX_INLINE_BIBLE_DOC_CHARS) return DecorationSet.empty;

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

function scheduleIdleRebuild(view: EditorView, delayMs: number) {
  const run = () => {
    if (view.isDestroyed || !view.editable) return;
    view.dispatch(view.state.tr.setMeta(inlineBibleRefsPluginKey, true));
  };

  if (typeof requestIdleCallback === "function") {
    requestIdleCallback(run, { timeout: delayMs + 1_500 });
  } else {
    window.setTimeout(run, 0);
  }
}

/** Dotted underline on inline cross-references (not H3). Rebuild is idle-debounced — never on every keystroke. */
export const CgvInlineBibleRefs = Extension.create({
  name: "cgvInlineBibleRefs",

  addProseMirrorPlugins() {
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    const scheduleRebuild = (view: EditorView) => {
      if (!getSharedBibleIndex()) return;
      if (!view.editable || view.composing) return;

      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        debounceTimer = null;
        if (view.isDestroyed || !view.editable || view.composing) return;
        scheduleIdleRebuild(view, rebuildDelayMs(view.state.doc));
      }, rebuildDelayMs(view.state.doc));
    };

    return [
      new Plugin({
        key: inlineBibleRefsPluginKey,
        state: {
          init: () => DecorationSet.empty,
          apply(tr, value, _oldState, newState) {
            if (!getSharedBibleIndex()) return DecorationSet.empty;
            if (tr.getMeta(inlineBibleRefsPluginKey)) {
              return buildInlineBibleDecorations(newState.doc);
            }
            if (tr.docChanged) {
              return DecorationSet.empty;
            }
            return value;
          }
        },
        props: {
          decorations(state) {
            return inlineBibleRefsPluginKey.getState(state);
          }
        },
        view() {
          return {
            update(view, prevState) {
              if (view.state.doc === prevState.doc) return;
              scheduleRebuild(view);
            },
            destroy() {
              if (debounceTimer) clearTimeout(debounceTimer);
            }
          };
        }
      })
    ];
  }
});

export { inlineBibleRefsPluginKey };
