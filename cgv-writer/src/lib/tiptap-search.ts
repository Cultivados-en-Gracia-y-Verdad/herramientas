import { Extension } from "@tiptap/core";
import type { CommandProps } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey, TextSelection } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export interface CgvSearchState {
  query: string;
  caseSensitive: boolean;
  matches: { from: number; to: number }[];
  currentIndex: number;
}

export const cgvSearchPluginKey = new PluginKey<CgvSearchState>("cgvSearch");

/** Flatten document text so matches can span inline mark boundaries. */
function buildDocTextIndex(doc: PMNode): { text: string; map: number[] } {
  const map: number[] = [];
  let text = "";
  let needsBlockGap = false;

  const pushChar = (char: string, pos: number) => {
    text += char;
    map.push(pos);
  };

  doc.descendants((node, pos) => {
    if (node.isBlock && node.type.name !== "doc") {
      if (text.length > 0) needsBlockGap = true;
      return;
    }

    if (!node.isText || !node.text) return;

    if (needsBlockGap) {
      pushChar("\n", -1);
      needsBlockGap = false;
    }

    for (let i = 0; i < node.text.length; i++) {
      pushChar(node.text[i], pos + i);
    }
  });

  return { text, map };
}

function findMatches(
  doc: CommandProps["state"]["doc"],
  query: string,
  caseSensitive: boolean
): { from: number; to: number }[] {
  if (!query) return [];

  const { text, map } = buildDocTextIndex(doc);
  if (!text) return [];

  const matches: { from: number; to: number }[] = [];
  const haystack = caseSensitive ? text : text.toLowerCase();
  const needle = caseSensitive ? query : query.toLowerCase();
  let index = 0;

  while (index <= haystack.length) {
    const hit = haystack.indexOf(needle, index);
    if (hit === -1) break;

    const endIdx = hit + needle.length - 1;
    const from = map[hit];
    const to = map[endIdx];
    if (from >= 0 && to >= 0) {
      matches.push({ from, to: to + 1 });
    }

    index = hit + (needle.length || 1);
  }

  return matches;
}

function reportFromState(state: CgvSearchState | undefined): void {
  const total = state?.matches.length ?? 0;
  const current = total && state && state.currentIndex >= 0 ? state.currentIndex + 1 : 0;
  window.dispatchEvent(
    new CustomEvent("cgv-search-report", { detail: { total, current } })
  );
}

function applySearchMeta(
  tr: CommandProps["tr"],
  next: CgvSearchState,
  selectMatch = false
): CommandProps["tr"] {
  let transaction = tr.setMeta(cgvSearchPluginKey, next);
  if (selectMatch && next.currentIndex >= 0 && next.matches[next.currentIndex]) {
    const match = next.matches[next.currentIndex];
    transaction = transaction
      .setSelection(TextSelection.create(transaction.doc, match.from, match.to))
      .scrollIntoView();
  }
  return transaction;
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    cgvSearch: {
      findInDocument: (query: string, caseSensitive?: boolean) => ReturnType;
      findNextInDocument: () => ReturnType;
      findPreviousInDocument: () => ReturnType;
      replaceCurrentMatch: (replacement: string) => ReturnType;
      replaceAllInDocument: (replacement: string) => ReturnType;
      clearDocumentSearch: () => ReturnType;
    };
  }
}

export const CgvSearch = Extension.create({
  name: "cgvSearch",

  addCommands() {
    return {
      findInDocument:
        (query: string, caseSensitive = false) =>
        ({ tr, dispatch, state }: CommandProps) => {
          const matches = findMatches(state.doc, query, caseSensitive);
          const next: CgvSearchState = {
            query,
            caseSensitive,
            matches,
            currentIndex: matches.length ? 0 : -1
          };
          if (dispatch) {
            dispatch(applySearchMeta(tr, next));
            reportFromState(next);
          }
          return true;
        },

      findNextInDocument:
        () =>
        ({ tr, dispatch, state }: CommandProps) => {
          const current = cgvSearchPluginKey.getState(state);
          if (!current?.matches.length) return false;
          const currentIndex = (current.currentIndex + 1) % current.matches.length;
          const next = { ...current, currentIndex };
          if (dispatch) {
            dispatch(applySearchMeta(tr, next));
            reportFromState(next);
          }
          return true;
        },

      findPreviousInDocument:
        () =>
        ({ tr, dispatch, state }: CommandProps) => {
          const current = cgvSearchPluginKey.getState(state);
          if (!current?.matches.length) return false;
          const currentIndex =
            (current.currentIndex - 1 + current.matches.length) % current.matches.length;
          const next = { ...current, currentIndex };
          if (dispatch) {
            dispatch(applySearchMeta(tr, next));
            reportFromState(next);
          }
          return true;
        },

      replaceCurrentMatch:
        (replacement: string) =>
        ({ tr, dispatch, state }: CommandProps) => {
          const current = cgvSearchPluginKey.getState(state);
          if (!current?.matches.length || current.currentIndex < 0) return false;
          const match = current.matches[current.currentIndex];
          let transaction = tr.insertText(replacement, match.from, match.to);
          const matches = findMatches(transaction.doc, current.query, current.caseSensitive);
          let currentIndex = Math.min(current.currentIndex, Math.max(matches.length - 1, 0));
          if (!matches.length) currentIndex = -1;
          const next: CgvSearchState = {
            ...current,
            matches,
            currentIndex
          };
          if (dispatch) {
            dispatch(applySearchMeta(transaction, next, false));
            reportFromState(next);
          }
          return true;
        },

      replaceAllInDocument:
        (replacement: string) =>
        ({ tr, dispatch, state }: CommandProps) => {
          const current = cgvSearchPluginKey.getState(state);
          if (!current?.matches.length) return false;
          let transaction = tr;
          for (let i = current.matches.length - 1; i >= 0; i--) {
            const match = current.matches[i];
            transaction = transaction.insertText(replacement, match.from, match.to);
          }
          const next: CgvSearchState = {
            query: current.query,
            caseSensitive: current.caseSensitive,
            matches: [],
            currentIndex: -1
          };
          if (dispatch) {
            dispatch(transaction.setMeta(cgvSearchPluginKey, next));
            reportFromState(next);
          }
          return true;
        },

      clearDocumentSearch:
        () =>
        ({ tr, dispatch }: CommandProps) => {
          const next: CgvSearchState = {
            query: "",
            caseSensitive: false,
            matches: [],
            currentIndex: -1
          };
          if (dispatch) {
            dispatch(tr.setMeta(cgvSearchPluginKey, next));
            reportFromState(next);
          }
          return true;
        }
    };
  },

  addProseMirrorPlugins() {
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    return [
      new Plugin<CgvSearchState>({
        key: cgvSearchPluginKey,
        state: {
          init: () => ({
            query: "",
            caseSensitive: false,
            matches: [],
            currentIndex: -1
          }),
          apply(tr, value) {
            const meta = tr.getMeta(cgvSearchPluginKey) as CgvSearchState | undefined;
            if (meta) return meta;
            if (tr.docChanged && value.query) {
              return { ...value, matches: [], currentIndex: -1 };
            }
            return value;
          }
        },
        props: {
          decorations(state) {
            const pluginState = cgvSearchPluginKey.getState(state);
            if (!pluginState?.matches.length) return DecorationSet.empty;

            const decos = pluginState.matches.map((match, index) =>
              Decoration.inline(match.from, match.to, {
                class:
                  index === pluginState.currentIndex
                    ? "cgv-search-match cgv-search-match--current"
                    : "cgv-search-match"
              })
            );
            return DecorationSet.create(state.doc, decos);
          }
        },
        view() {
          return {
            update(view, prevState) {
              const current = cgvSearchPluginKey.getState(view.state);
              if (!current?.query || view.state.doc === prevState.doc) return;

              if (debounceTimer) clearTimeout(debounceTimer);
              debounceTimer = setTimeout(() => {
                debounceTimer = null;
                if (view.isDestroyed) return;
                const state = cgvSearchPluginKey.getState(view.state);
                if (!state?.query) return;

                const matches = findMatches(view.state.doc, state.query, state.caseSensitive);
                let currentIndex = state.currentIndex;
                if (!matches.length) {
                  currentIndex = -1;
                } else if (currentIndex >= matches.length) {
                  currentIndex = matches.length - 1;
                } else if (currentIndex < 0) {
                  currentIndex = 0;
                }
                const next: CgvSearchState = { ...state, matches, currentIndex };
                view.dispatch(view.state.tr.setMeta(cgvSearchPluginKey, next));
                reportFromState(next);
              }, 280);
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
