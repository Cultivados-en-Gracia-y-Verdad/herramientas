import { SearchQuery } from "@codemirror/search";
import type { Text } from "@codemirror/state";
import { RangeSetBuilder, StateEffect, StateField } from "@codemirror/state";
import { Decoration, DecorationSet, EditorView, ViewPlugin } from "@codemirror/view";
import { reportSearchResult } from "./search-bridge";

export interface CmSearchHighlightState {
  query: SearchQuery;
  currentIndex: number;
}

export const setCmSearchHighlight = StateEffect.define<CmSearchHighlightState | null>();

function countMatches(query: SearchQuery, doc: Text): number {
  let total = 0;
  const cursor = query.getCursor(doc);
  let result = cursor.next();
  while (!result.done) {
    total++;
    result = cursor.next();
  }
  return total;
}

function matchAt(
  query: SearchQuery,
  doc: Text,
  index: number
): { from: number; to: number } | null {
  const cursor = query.getCursor(doc);
  let result = cursor.next();
  let i = 0;
  while (!result.done) {
    if (i === index) return result.value;
    i++;
    result = cursor.next();
  }
  return null;
}

function buildDecorations(view: EditorView): DecorationSet {
  const state = view.state.field(cmSearchHighlightField);
  if (!state?.query.valid || !state.query.search) {
    return Decoration.none;
  }

  const builder = new RangeSetBuilder<Decoration>();
  const cursor = state.query.getCursor(view.state.doc);
  let index = 0;
  let result = cursor.next();
  while (!result.done) {
    const { from, to } = result.value;
    const selected = index === state.currentIndex;
    builder.add(
      from,
      to,
      Decoration.mark({
        class: selected ? "cm-searchMatch cm-searchMatch-selected" : "cm-searchMatch"
      })
    );
    index++;
    result = cursor.next();
  }
  return builder.finish();
}

export const cmSearchHighlightField = StateField.define<CmSearchHighlightState | null>({
  create: () => null,
  update(value, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setCmSearchHighlight)) return effect.value;
    }
    if (value && tr.docChanged && value.query.search) {
      const total = countMatches(value.query, tr.newDoc);
      const currentIndex =
        total === 0 ? -1 : Math.min(Math.max(value.currentIndex, 0), total - 1);
      const next = { ...value, currentIndex };
      queueMicrotask(() =>
        reportSearchResult({
          total,
          current: currentIndex >= 0 ? currentIndex + 1 : 0
        })
      );
      return next;
    }
    return value;
  }
});

const cmSearchHighlightPlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet = Decoration.none;

    constructor(view: EditorView) {
      this.decorations = buildDecorations(view);
    }

    update(update: {
      view: EditorView;
      docChanged: boolean;
      state: EditorView["state"];
      startState: EditorView["state"];
    }) {
      const changed =
        update.state.field(cmSearchHighlightField) !==
          update.startState.field(cmSearchHighlightField) || update.docChanged;
      if (changed) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: plugin => plugin.decorations }
);

export function cmSearchHighlightExtension() {
  return [cmSearchHighlightField, cmSearchHighlightPlugin];
}

export function applyCmSearchHighlight(
  view: EditorView,
  query: SearchQuery,
  currentIndex: number
): CmSearchHighlightState | null {
  if (!query.search) {
    view.dispatch({ effects: setCmSearchHighlight.of(null) });
    reportSearchResult({ total: 0, current: 0 });
    return null;
  }

  const total = countMatches(query, view.state.doc);
  const normalizedIndex = total === 0 ? -1 : ((currentIndex % total) + total) % total;
  const next: CmSearchHighlightState = { query, currentIndex: normalizedIndex };
  view.dispatch({ effects: setCmSearchHighlight.of(next) });
  reportSearchResult({
    total,
    current: normalizedIndex >= 0 ? normalizedIndex + 1 : 0
  });
  return next;
}

export function scrollCmMatchIntoView(view: EditorView, from: number): void {
  const coords = view.coordsAtPos(from);
  if (!coords) return;
  const scroller = view.scrollDOM;
  const box = scroller.getBoundingClientRect();
  const target = coords.top - box.top + scroller.scrollTop - scroller.clientHeight * 0.35;
  scroller.scrollTop = Math.max(0, target);
}

export function getCmSearchMatch(
  view: EditorView,
  state: CmSearchHighlightState
): { from: number; to: number } | null {
  if (state.currentIndex < 0) return null;
  return matchAt(state.query, view.state.doc, state.currentIndex);
}
