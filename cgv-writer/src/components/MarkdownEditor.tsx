import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import {
  EditorView,
  keymap,
  lineNumbers,
  drawSelection
} from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import {
  SearchQuery
} from "@codemirror/search";
import { markdown, markdownLanguage } from "@codemirror/lang-markdown";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { tags } from "@lezer/highlight";
import {
  applyCmSearchHighlight,
  cmSearchHighlightExtension,
  cmSearchHighlightField,
  firstMatchIndexAtOrAfter,
  getCmSearchMatch,
  revealCmSearchMatch,
  setCmSearchHighlight
} from "../lib/codemirror-search-highlight";
import {
  anchorBeforeOffset,
  bodyTextCharRatio,
  loadSharedEditorPlace,
  markdownBodyOffset,
  normalizeForAnchor,
  saveEditorPlace,
  type SavedEditorPlace
} from "../lib/editor-position-bridge";
import { setViewHandoff, takeViewHandoff } from "../lib/manual-sync";
import { replaceAllInText } from "../lib/text-search";
import { reportSearchResult, type SearchRequest } from "../lib/search-bridge";
import { type OutlineNavigateRequest } from "../lib/outline-bridge";
import { joinYamlBody, splitYamlBody, bodyStartInContent, CGV_BULLET_LINE_PREFIX, tightenCgvDefaultSpacing } from "../lib/markdown-html";
import { cgvBlankHighlightExtension } from "../lib/codemirror-underline-blank";

/** Full-doc Lezer highlighting is costly on long manuals. */
const LARGE_MARKDOWN_CHARS = 80_000;

const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "calc(15px * var(--cgv-type-scale))",
    backgroundColor: "var(--cm-bg)",
    color: "var(--text)"
  },
  ".cm-scroller": {
    fontFamily: "var(--cm-font-family)",
    fontWeight: "var(--cm-font-weight)",
    lineHeight: "1.62",
    WebkitFontSmoothing: "antialiased",
    MozOsxFontSmoothing: "grayscale"
  },
  ".cm-content": {
    fontFamily: "var(--cm-font-family)",
    fontWeight: "var(--cm-font-weight)",
    textDecoration: "none",
    caretColor: "var(--cm-cursor)"
  },
  ".cm-line": {
    fontWeight: "var(--cm-font-weight)"
  },
  ".cm-gutters": {
    backgroundColor: "var(--cm-gutter-bg)",
    color: "var(--cm-gutter-fg)",
    borderRight: "1px solid var(--border)",
    fontFamily: '"IBM Plex Mono", "SF Mono", Menlo, Consolas, monospace',
    fontSize: "0.88em",
    fontWeight: "400"
  },
  ".cm-activeLineGutter": { backgroundColor: "var(--cm-active-gutter)" },
  ".cm-activeLine": { backgroundColor: "var(--cm-active-line)" },
  "&.cm-focused .cm-cursor": { borderLeftColor: "var(--cm-cursor)" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
    backgroundColor: "var(--cm-selection) !important"
  },
  ".cm-searchMatch": {
    backgroundColor: "var(--cm-search)"
  },
  ".cm-searchMatch.cm-searchMatch-selected": {
    backgroundColor: "var(--cm-search-selected)"
  },
  ".cm-cgv-blank": {
    fontWeight: "var(--cm-strong-weight)",
    textDecoration: "underline",
    textDecorationThickness: "2px",
    textUnderlineOffset: "2px",
    backgroundColor: "transparent"
  }
});

/** Prose-oriented highlighting — body and headings use light weight; color marks headings. */
const markdownHighlightStyle = HighlightStyle.define([
  { tag: tags.meta, color: "var(--cm-meta)", fontWeight: "var(--cm-font-weight)" },
  { tag: tags.link, color: "var(--cm-link)", fontWeight: "var(--cm-font-weight)" },
  { tag: tags.heading, color: "var(--cm-heading)", fontWeight: "var(--cm-heading-weight)" },
  { tag: tags.emphasis, fontStyle: "italic", fontWeight: "var(--cm-font-weight)" },
  { tag: tags.strong, fontWeight: "var(--cm-strong-weight)" },
  { tag: tags.strikethrough, textDecoration: "line-through" },
  {
    tag: tags.monospace,
    color: "var(--cm-meta)",
    fontFamily: '"IBM Plex Mono", "SF Mono", Menlo, Consolas, monospace',
    fontWeight: "400"
  },
  { tag: tags.comment, color: "var(--cm-comment)", fontWeight: "var(--cm-font-weight)" },
  { tag: tags.string, color: "var(--cm-string)", fontWeight: "var(--cm-font-weight)" },
  { tag: tags.keyword, color: "var(--cm-keyword)", fontWeight: "var(--cm-font-weight)" }
]);

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** View switch — update shared state without marking the document dirty. */
  onContentSync?: (value: string) => void;
  onDirty?: () => void;
  isActive: boolean;
  reloadKey: string;
}

function markdownBodyCharRatio(view: EditorView, value: string): number {
  const { body } = splitYamlBody(value);
  if (!body.length) return 0;
  const bodyStart = value.length - body.length;
  const head = view.state.selection.main.head;
  const offset = Math.max(0, Math.min(body.length, head - bodyStart));
  const normalized = normalizeForAnchor(body);
  if (!normalized.length) return 0;
  const normOffset = normalizeForAnchor(body.slice(0, offset)).length;
  return bodyTextCharRatio(normalized.length, normOffset);
}

function markdownAnchorBefore(view: EditorView, value: string): string {
  const { body } = splitYamlBody(value);
  const bodyStart = value.length - body.length;
  const head = view.state.selection.main.head;
  const offset = Math.max(0, Math.min(body.length, head - bodyStart));
  return anchorBeforeOffset(body, offset);
}

function markdownNormalizedOffset(view: EditorView, value: string): number {
  const { body } = splitYamlBody(value);
  const bodyStart = value.length - body.length;
  const head = view.state.selection.main.head;
  const offset = Math.max(0, Math.min(body.length, head - bodyStart));
  return normalizeForAnchor(body.slice(0, offset)).length;
}

function markdownPosForPlace(value: string, place: SavedEditorPlace): number {
  const { body } = splitYamlBody(value);
  const bodyStart = value.length - body.length;
  const offsetInBody = body.length ? markdownBodyOffset(body, place) : 0;
  return Math.max(0, Math.min(value.length, bodyStart + offsetInBody));
}

function restoreMarkdownPlace(view: EditorView, value: string, place: SavedEditorPlace): void {
  const pos = markdownPosForPlace(value, place);
  view.dispatch({
    selection: { anchor: pos, head: pos },
    effects: EditorView.scrollIntoView(pos, { y: "center" }),
    scrollIntoView: false
  });
  view.focus();
}

function applyMarkdownHeading(view: EditorView, level: 1 | 2 | 3 | 4 | 5 | 6) {
  const { from } = view.state.selection.main;
  const line = view.state.doc.lineAt(from);
  const text = line.text.replace(/^#+\s*/, "").replace(/^-\s+/, "");
  const prefix = "#".repeat(level) + " ";
  view.dispatch({
    changes: { from: line.from, to: line.to, insert: prefix + text },
    selection: { anchor: line.from + prefix.length }
  });
}

function applyMarkdownBullet(view: EditorView) {
  const { from } = view.state.selection.main;
  const line = view.state.doc.lineAt(from);
  const text = line.text.replace(/^#+\s*/, "").replace(/^-\s+/, "");
  const prefix = CGV_BULLET_LINE_PREFIX;
  view.dispatch({
    changes: { from: line.from, to: line.to, insert: prefix + text },
    selection: { anchor: line.from + prefix.length }
  });
}

export function MarkdownEditor({ value, onChange, onContentSync, onDirty, isActive, reloadKey }: MarkdownEditorProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  const onContentSyncRef = useRef(onContentSync);
  const onDirtyRef = useRef(onDirty);
  const lastReloadKey = useRef(reloadKey);
  const wasActive = useRef(false);
  const selfChange = useRef(false);
  const valueRef = useRef(value);
  const isActiveRef = useRef(isActive);
  const skipValueSync = useRef(false);

  const syncDocToParent = (doc: string) => {
    selfChange.current = true;
    valueRef.current = doc;
    onChangeRef.current(doc);
  };

  const flushPending = (): string => {
    const view = viewRef.current;
    if (!view) return valueRef.current;
    const docValue = view.state.doc.toString();
    if (docValue !== valueRef.current) {
      syncDocToParent(docValue);
    }
    return docValue;
  };

  onChangeRef.current = onChange;
  onContentSyncRef.current = onContentSync;
  onDirtyRef.current = onDirty;
  valueRef.current = value;
  isActiveRef.current = isActive;

  useEffect(() => {
    if (!hostRef.current) return;

    const updateListener = EditorView.updateListener.of(update => {
      if (!update.docChanged) return;
      selfChange.current = true;
      onDirtyRef.current?.();
    });

    const useSyntaxHighlight = value.length <= LARGE_MARKDOWN_CHARS;

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        drawSelection(),
        history(),
        cmSearchHighlightExtension(),
        cgvBlankHighlightExtension,
        markdown({ base: markdownLanguage }),
        ...(useSyntaxHighlight ? [syntaxHighlighting(markdownHighlightStyle)] : []),
        editorTheme,
        keymap.of([...defaultKeymap, ...historyKeymap]),
        updateListener,
        EditorView.lineWrapping
      ]
    });

    const view = new EditorView({ state, parent: hostRef.current });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const fileChanged = lastReloadKey.current !== reloadKey;
    if (fileChanged) {
      lastReloadKey.current = reloadKey;
    }

    if (selfChange.current) {
      selfChange.current = false;
      return;
    }

    if (skipValueSync.current) {
      skipValueSync.current = false;
      return;
    }

    const current = view.state.doc.toString();
    const split = splitYamlBody(value);
    const displayValue = joinYamlBody(split.frontMatter, tightenCgvDefaultSpacing(split.body));

    if (!fileChanged && current === displayValue) {
      return;
    }

    if (!fileChanged && isActiveRef.current && current !== displayValue) {
      syncDocToParent(current);
      return;
    }

    if (fileChanged && displayValue !== value) {
      skipValueSync.current = true;
      selfChange.current = true;
      valueRef.current = displayValue;
      onContentSyncRef.current?.(displayValue);
    }

    const place = loadSharedEditorPlace();
    const pos = place ? markdownPosForPlace(displayValue, place) : null;
    const selection = view.state.selection.main;
    view.dispatch({
      changes: { from: 0, to: current.length, insert: displayValue },
      selection: fileChanged
        ? { anchor: 0, head: 0 }
        : pos != null
          ? { anchor: pos, head: pos }
          : {
              anchor: Math.min(selection.anchor, displayValue.length),
              head: Math.min(selection.head, displayValue.length)
            },
      effects: pos != null ? EditorView.scrollIntoView(pos, { y: "center" }) : undefined,
      scrollIntoView: false
    });
  }, [value, reloadKey]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const saveIfActive = () => {
      if (!isActiveRef.current) return;
      const docValue = view.state.doc.toString();
      selfChange.current = true;
      valueRef.current = docValue;
      onContentSyncRef.current?.(docValue);
      const { body } = splitYamlBody(docValue);
      const place = {
        scrollRatio: 0,
        bodyCharRatio: markdownBodyCharRatio(view, docValue),
        anchorBefore: markdownAnchorBefore(view, docValue),
        normalizedOffset: markdownNormalizedOffset(view, docValue)
      };
      saveEditorPlace(
        "markdown",
        view.scrollDOM,
        place.bodyCharRatio,
        place.anchorBefore,
        place.normalizedOffset
      );
      setViewHandoff({ place: loadSharedEditorPlace() ?? place, bodyMd: body });
    };

    const onExport = () => {
      const docValue = flushPending();
      window.dispatchEvent(
        new CustomEvent("cgv-markdown-body-export", {
          detail: { body: docValue }
        })
      );
    };

    window.addEventListener("cgv-before-view-change", saveIfActive);
    window.addEventListener("cgv-markdown-flush-sync", flushPending);
    window.addEventListener("cgv-markdown-body-export-request", onExport);
    return () => {
      window.removeEventListener("cgv-before-view-change", saveIfActive);
      window.removeEventListener("cgv-markdown-flush-sync", flushPending);
      window.removeEventListener("cgv-markdown-body-export-request", onExport);
    };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    if (!isActive && wasActive.current) {
      flushPending();
    }

    if (isActive && !wasActive.current) {
      const handoff = takeViewHandoff();
      const place = handoff?.place ?? loadSharedEditorPlace();
      const { frontMatter } = splitYamlBody(valueRef.current);

      let nextValue = valueRef.current;
      if (handoff?.bodyMd != null) {
        nextValue = joinYamlBody(frontMatter, handoff.bodyMd);
      }

      const current = view.state.doc.toString();
      const pos = place ? markdownPosForPlace(nextValue, place) : null;

      if (current !== nextValue) {
        view.dispatch({
          changes: { from: 0, to: current.length, insert: nextValue },
          selection: pos != null ? { anchor: pos, head: pos } : undefined,
          effects: pos != null ? EditorView.scrollIntoView(pos, { y: "center" }) : undefined,
          scrollIntoView: false
        });
        skipValueSync.current = true;
        selfChange.current = true;
        valueRef.current = nextValue;
        onContentSyncRef.current?.(nextValue);
      } else if (place) {
        restoreMarkdownPlace(view, nextValue, place);
      } else {
        view.focus();
      }
    }

    wasActive.current = isActive;
  }, [isActive]);

  useEffect(() => {
    const handler = (event: Event) => {
      const view = viewRef.current;
      if (!view || !isActive) return;

      const detail = (event as CustomEvent<{ styleKey: number; viewMode: string }>).detail;
      if (detail.viewMode !== "markdown") return;

      if (detail.styleKey >= 1 && detail.styleKey <= 6) {
        applyMarkdownHeading(view, detail.styleKey as 1 | 2 | 3 | 4 | 5 | 6);
        view.focus();
        return;
      }
      if (detail.styleKey === 7) {
        applyMarkdownBullet(view);
        view.focus();
      }
    };

    window.addEventListener("cgv-apply-style", handler);
    return () => window.removeEventListener("cgv-apply-style", handler);
  }, [isActive]);

  useEffect(() => {
    const handler = (event: Event) => {
      const view = viewRef.current;
      if (!view || !isActiveRef.current) return;

      const detail = (event as CustomEvent<OutlineNavigateRequest>).detail;
      const docValue = view.state.doc.toString();
      const pos = bodyStartInContent(docValue) + detail.bodyOffset;

      view.dispatch({
        selection: { anchor: pos, head: pos },
        effects: EditorView.scrollIntoView(pos, { y: "center" }),
        scrollIntoView: false
      });
      view.focus();
    };

    window.addEventListener("cgv-outline-navigate", handler);
    return () => window.removeEventListener("cgv-outline-navigate", handler);
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const view = viewRef.current;
      if (!view || !isActive) return;

      const detail = (event as CustomEvent<SearchRequest>).detail;
      const searchQuery = new SearchQuery({
        search: detail.query,
        caseSensitive: detail.caseSensitive,
        replace: detail.replace,
        literal: true
      });

      switch (detail.action) {
        case "clear":
          view.dispatch({ effects: setCmSearchHighlight.of(null) });
          reportSearchResult({ total: 0, current: 0 });
          break;
        case "find": {
          const cursorPos = view.state.selection.main.head;
          const startIndex = firstMatchIndexAtOrAfter(searchQuery, view.state.doc, cursorPos);
          const state = applyCmSearchHighlight(view, searchQuery, startIndex);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) revealCmSearchMatch(view, match);
          break;
        }
        case "next": {
          const prev = view.state.field(cmSearchHighlightField);
          const startIndex =
            prev?.query.search === detail.query &&
            prev.query.caseSensitive === detail.caseSensitive
              ? prev.currentIndex + 1
              : firstMatchIndexAtOrAfter(searchQuery, view.state.doc, view.state.selection.main.head);
          const state = applyCmSearchHighlight(view, searchQuery, startIndex);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) revealCmSearchMatch(view, match);
          break;
        }
        case "prev": {
          const prev = view.state.field(cmSearchHighlightField);
          const startIndex =
            prev?.query.search === detail.query &&
            prev.query.caseSensitive === detail.caseSensitive
              ? prev.currentIndex - 1
              : firstMatchIndexAtOrAfter(searchQuery, view.state.doc, view.state.selection.main.head);
          const state = applyCmSearchHighlight(view, searchQuery, startIndex);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) revealCmSearchMatch(view, match);
          break;
        }
        case "replace": {
          const prev = view.state.field(cmSearchHighlightField);
          const match = prev ? getCmSearchMatch(view, prev) : null;
          if (!match) break;
          view.dispatch({
            changes: { from: match.from, to: match.to, insert: detail.replace }
          });
          const state = applyCmSearchHighlight(view, searchQuery, prev?.currentIndex ?? 0);
          const nextMatch = state ? getCmSearchMatch(view, state) : null;
          if (nextMatch) revealCmSearchMatch(view, nextMatch);
          break;
        }
        case "replaceAll": {
          const current = view.state.doc.toString();
          const next = replaceAllInText(
            current,
            detail.query,
            detail.replace,
            detail.caseSensitive
          );
          if (next === current) break;
          view.dispatch({
            changes: { from: 0, to: current.length, insert: next }
          });
          view.dispatch({ effects: setCmSearchHighlight.of(null) });
          reportSearchResult({ total: 0, current: 0 });
          break;
        }
      }
    };

    window.addEventListener("cgv-search", handler);
    return () => window.removeEventListener("cgv-search", handler);
  }, [isActive]);

  return <div className="editor-host" ref={hostRef} />;
}
