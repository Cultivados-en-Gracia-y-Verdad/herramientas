import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLine,
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
  getCmSearchMatch,
  scrollCmMatchIntoView,
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
import { MANUAL_SYNC_MS, setViewHandoff, takeViewHandoff } from "../lib/manual-sync";
import { replaceAllInText } from "../lib/text-search";
import { reportSearchResult, type SearchRequest } from "../lib/search-bridge";
import { joinYamlBody, splitYamlBody } from "../lib/markdown-html";

const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "calc(15px * var(--cgv-type-scale))",
    backgroundColor: "#f8fafc"
  },
  ".cm-scroller": {
    fontFamily: '"IBM Plex Mono", "SF Mono", Menlo, Consolas, monospace',
    lineHeight: "1.55"
  },
  ".cm-gutters": {
    backgroundColor: "#f1f5f9",
    color: "#64748b",
    borderRight: "1px solid #e2e8f0"
  },
  ".cm-activeLineGutter": { backgroundColor: "#e2e8f0" },
  ".cm-activeLine": { backgroundColor: "rgba(56, 189, 248, 0.08)" },
  "&.cm-focused .cm-cursor": { borderLeftColor: "#0369a1" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
    backgroundColor: "rgba(56, 189, 248, 0.22) !important"
  },
  ".cm-searchMatch": {
    backgroundColor: "rgba(250, 204, 21, 0.45)"
  },
  ".cm-searchMatch.cm-searchMatch-selected": {
    backgroundColor: "rgba(251, 146, 60, 0.55)"
  },
  ".cm-content": {
    textDecoration: "none"
  }
});

/** Like defaultHighlightStyle but without underlines (headings/links stay plain in source view). */
const markdownHighlightStyle = HighlightStyle.define([
  { tag: tags.meta, color: "#404740" },
  { tag: tags.link, color: "#0369a1" },
  { tag: tags.heading, color: "#1e3a5f", fontWeight: "bold" },
  { tag: tags.emphasis, fontStyle: "italic" },
  { tag: tags.strong, fontWeight: "bold" },
  { tag: tags.strikethrough, textDecoration: "line-through" },
  { tag: tags.keyword, color: "#708" },
  { tag: [tags.atom, tags.bool, tags.url, tags.contentSeparator, tags.labelName], color: "#219" },
  { tag: [tags.literal, tags.inserted], color: "#164" },
  { tag: [tags.string, tags.deleted], color: "#a11" },
  { tag: [tags.regexp, tags.escape, tags.special(tags.string)], color: "#e40" },
  { tag: tags.definition(tags.variableName), color: "#00f" },
  { tag: tags.local(tags.variableName), color: "#30a" },
  { tag: [tags.typeName, tags.namespace], color: "#085" },
  { tag: tags.className, color: "#167" },
  { tag: [tags.special(tags.variableName), tags.macroName], color: "#256" },
  { tag: tags.definition(tags.propertyName), color: "#00c" },
  { tag: tags.comment, color: "#940" },
  { tag: tags.invalid, color: "#f00" }
]);

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
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
  const prefix = "- ";
  view.dispatch({
    changes: { from: line.from, to: line.to, insert: prefix + text },
    selection: { anchor: line.from + prefix.length }
  });
}

export function MarkdownEditor({ value, onChange, isActive, reloadKey }: MarkdownEditorProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  const lastReloadKey = useRef(reloadKey);
  const wasActive = useRef(false);
  const selfChange = useRef(false);
  const valueRef = useRef(value);
  const isActiveRef = useRef(isActive);
  const changeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipValueSync = useRef(false);
  onChangeRef.current = onChange;
  valueRef.current = value;
  isActiveRef.current = isActive;

  useEffect(() => {
    if (!hostRef.current) return;

    const updateListener = EditorView.updateListener.of(update => {
      if (!update.docChanged) return;
      selfChange.current = true;
      if (changeTimer.current) clearTimeout(changeTimer.current);
      changeTimer.current = setTimeout(() => {
        changeTimer.current = null;
        const viewNow = viewRef.current;
        if (!viewNow) return;
        onChangeRef.current(viewNow.state.doc.toString());
      }, MANUAL_SYNC_MS);
    });

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        drawSelection(),
        history(),
        cmSearchHighlightExtension(),
        markdown({ base: markdownLanguage }),
        syntaxHighlighting(markdownHighlightStyle),
        editorTheme,
        keymap.of([...defaultKeymap, ...historyKeymap]),
        updateListener,
        EditorView.lineWrapping
      ]
    });

    const view = new EditorView({ state, parent: hostRef.current });
    viewRef.current = view;

    return () => {
      if (changeTimer.current) clearTimeout(changeTimer.current);
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
    if (!fileChanged && current === value) {
      return;
    }

    const place = loadSharedEditorPlace();
    const pos = place ? markdownPosForPlace(value, place) : null;
    const selection = view.state.selection.main;
    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
      selection: fileChanged
        ? { anchor: 0, head: 0 }
        : pos != null
          ? { anchor: pos, head: pos }
          : {
              anchor: Math.min(selection.anchor, value.length),
              head: Math.min(selection.head, value.length)
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
      if (changeTimer.current) {
        clearTimeout(changeTimer.current);
        changeTimer.current = null;
        selfChange.current = true;
        valueRef.current = docValue;
        onChangeRef.current(docValue);
      }
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

    window.addEventListener("cgv-before-view-change", saveIfActive);
    return () => window.removeEventListener("cgv-before-view-change", saveIfActive);
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    if (!isActive && wasActive.current) {
      if (changeTimer.current) {
        clearTimeout(changeTimer.current);
        changeTimer.current = null;
        selfChange.current = true;
        onChangeRef.current(view.state.doc.toString());
      }
    }

    if (isActive && !wasActive.current) {
      const handoff = takeViewHandoff();
      const place = handoff?.place ?? loadSharedEditorPlace();
      const { frontMatter } = splitYamlBody(valueRef.current);

      let nextValue = valueRef.current;
      if (handoff?.bodyMd != null) {
        nextValue = joinYamlBody(frontMatter, handoff.bodyMd);
        valueRef.current = nextValue;
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
          const state = applyCmSearchHighlight(view, searchQuery, 0);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) scrollCmMatchIntoView(view, match.from);
          break;
        }
        case "next": {
          const prev = view.state.field(cmSearchHighlightField);
          const nextIndex = (prev?.currentIndex ?? -1) + 1;
          const state = applyCmSearchHighlight(view, searchQuery, nextIndex);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) scrollCmMatchIntoView(view, match.from);
          break;
        }
        case "prev": {
          const prev = view.state.field(cmSearchHighlightField);
          const nextIndex = (prev?.currentIndex ?? 0) - 1;
          const state = applyCmSearchHighlight(view, searchQuery, nextIndex);
          const match = state ? getCmSearchMatch(view, state) : null;
          if (match) scrollCmMatchIntoView(view, match.from);
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
          if (nextMatch) scrollCmMatchIntoView(view, nextMatch.from);
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
