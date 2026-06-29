import { useEffect, useRef, useState } from "react";
import { Compartment, EditorState, Prec } from "@codemirror/state";
import { EditorView, drawSelection, keymap, lineNumbers } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { markdown, markdownLanguage } from "@codemirror/lang-markdown";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { SearchQuery } from "@codemirror/search";
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
import { cgvBlankHighlightExtension } from "../lib/codemirror-underline-blank";
import { bibleReferenceClickHandlers } from "../lib/codemirror-h3-click";
import { codemirrorManualMode, setManualImageBasePath } from "../lib/codemirror-manual-mode";
import { bodyStartInContent, CGV_BULLET_LINE_PREFIX, stripMarkdownBlockPrefix } from "../lib/markdown-html";
import { useBible } from "../lib/bible-context";
import { formatScriptureLine, type ResolveBibleReferenceResult } from "../lib/bible-client";
import type { OutlineNavigateRequest } from "../lib/outline-bridge";
import { reportSearchResult, type SearchRequest } from "../lib/search-bridge";
import { replaceAllInText } from "../lib/text-search";
import { BibleReferencePopup } from "./BibleReferencePopup";
import "./ManualEditor.css";
import "./SharedDocumentEditor.css";

export type SharedEditorMode = "manual" | "markdown";

interface SharedDocumentEditorProps {
  value: string;
  onChange: (value: string) => void;
  onDirty?: () => void;
  reloadKey: string;
  mode: SharedEditorMode;
  writingMode?: boolean;
  filePath?: string | null;
  onToggleMode: () => void;
}

const LARGE_MARKDOWN_CHARS = 80_000;

const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "calc(19px * var(--cgv-type-scale))",
    backgroundColor: "var(--cm-bg)",
    color: "var(--text)"
  },
  ".cm-scroller": {
    fontFamily: "var(--cm-font-family)",
    fontWeight: "var(--cm-font-weight)",
    lineHeight: "1.62"
  },
  ".cm-content": { caretColor: "var(--cm-cursor)" },
  ".cm-gutters": {
    backgroundColor: "var(--cm-gutter-bg)",
    color: "var(--cm-gutter-fg)",
    borderRight: "1px solid var(--border)"
  },
  ".cm-activeLineGutter": { backgroundColor: "var(--cm-active-gutter)" },
  ".cm-activeLine": { backgroundColor: "var(--cm-active-line)" },
  "&.cm-focused .cm-cursor": { borderLeftColor: "var(--cm-cursor)" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
    backgroundColor: "var(--cm-selection) !important"
  },
  ".cm-searchMatch": { backgroundColor: "var(--cm-search)" },
  ".cm-searchMatch.cm-searchMatch-selected": { backgroundColor: "var(--cm-search-selected)" },
  ".cm-cgv-blank": {
    fontWeight: "var(--cm-strong-weight)",
    textDecoration: "underline",
    textDecorationThickness: "2px",
    textUnderlineOffset: "2px"
  }
});

const markdownHighlightStyle = HighlightStyle.define([
  { tag: tags.meta, color: "var(--cm-meta)" },
  { tag: tags.link, color: "var(--cm-link)" },
  { tag: tags.heading, color: "var(--cm-heading)", fontWeight: "var(--cm-heading-weight)" },
  { tag: tags.emphasis, fontStyle: "italic" },
  { tag: tags.strong, fontWeight: "var(--cm-strong-weight)" },
  { tag: tags.comment, color: "var(--cm-comment)" },
  { tag: tags.string, color: "var(--cm-string)" },
  { tag: tags.keyword, color: "var(--cm-keyword)" }
]);

function applyHeading(view: EditorView, level: 1 | 2 | 3 | 4 | 5 | 6) {
  const line = view.state.doc.lineAt(view.state.selection.main.from);
  const text = stripMarkdownBlockPrefix(line.text);
  const prefix = `${"#".repeat(level)} `;
  view.dispatch({
    changes: { from: line.from, to: line.to, insert: prefix + text },
    selection: { anchor: line.from + prefix.length }
  });
  view.focus();
}

function applyBullet(view: EditorView) {
  const line = view.state.doc.lineAt(view.state.selection.main.from);
  const text = stripMarkdownBlockPrefix(line.text);
  view.dispatch({
    changes: { from: line.from, to: line.to, insert: CGV_BULLET_LINE_PREFIX + text },
    selection: { anchor: line.from + CGV_BULLET_LINE_PREFIX.length }
  });
  view.focus();
}

function insertManualH5Line(view: EditorView, mode: SharedEditorMode): boolean {
  if (mode !== "manual") return false;

  const selection = view.state.selection.main;
  if (!selection.empty) return false;

  const line = view.state.doc.lineAt(selection.head);
  const offset = selection.head - line.from;
  const before = line.text.slice(0, offset);
  const after = line.text.slice(offset);

  const heading = line.text.match(/^(#{1,3}\s+)/);
  if (heading) {
    if (offset <= heading[0].length) {
      view.dispatch({
        changes: { from: line.from, insert: "##### \n" },
        selection: { anchor: line.from + 6 }
      });
      return true;
    }

    view.dispatch({
      changes: { from: line.to, insert: "\n##### " },
      selection: { anchor: line.to + 7 }
    });
    return true;
  }

  if (after.trim()) return false;

  if (!line.text.trim()) {
    view.dispatch({
      changes: { from: line.from, to: line.to, insert: "##### " },
      selection: { anchor: line.from + 6 }
    });
    return true;
  }

  if (!before.trim()) return false;

  view.dispatch({
    changes: { from: selection.head, insert: "\n##### " },
    selection: { anchor: selection.head + 7 }
  });
  return true;
}

function wrapSelection(view: EditorView, before: string, after = before) {
  const range = view.state.selection.main;
  if (range.empty) return;

  const selected = view.state.sliceDoc(range.from, range.to);
  const beforeFrom = range.from - before.length;
  const afterTo = range.to + after.length;
  const hasOuterWrap =
    beforeFrom >= 0 &&
    afterTo <= view.state.doc.length &&
    view.state.sliceDoc(beforeFrom, range.from) === before &&
    view.state.sliceDoc(range.to, afterTo) === after;

  if (hasOuterWrap) {
    preserveScrollDuring(view, () => {
      view.dispatch({
        changes: [
          { from: range.to, to: afterTo, insert: "" },
          { from: beforeFrom, to: range.from, insert: "" }
        ],
        selection: {
          anchor: beforeFrom,
          head: range.to - before.length
        },
        scrollIntoView: false
      });
    });
    return;
  }

  if (selected.startsWith(before) && selected.endsWith(after) && selected.length >= before.length + after.length) {
    const inner = selected.slice(before.length, selected.length - after.length);
    preserveScrollDuring(view, () => {
      view.dispatch({
        changes: { from: range.from, to: range.to, insert: inner },
        selection: { anchor: range.from, head: range.from + inner.length },
        scrollIntoView: false
      });
    });
    return;
  }

  preserveScrollDuring(view, () => {
    view.dispatch({
      changes: { from: range.from, to: range.to, insert: before + selected + after },
      selection: selected
        ? { anchor: range.from + before.length, head: range.to + before.length }
        : { anchor: range.from + before.length },
      scrollIntoView: false
    });
  });
}

function insertBlock(view: EditorView, text: string) {
  const line = view.state.doc.lineAt(view.state.selection.main.from);
  const insert = `${line.to === line.from ? "" : "\n"}${text}\n`;
  view.dispatch({ changes: { from: line.to, insert }, selection: { anchor: line.to + insert.length } });
  view.focus();
}

function preserveScrollDuring(view: EditorView, run: () => void) {
  const scrollTop = view.scrollDOM.scrollTop;
  const scrollLeft = view.scrollDOM.scrollLeft;
  run();
  requestAnimationFrame(() => {
    view.scrollDOM.scrollTop = scrollTop;
    view.scrollDOM.scrollLeft = scrollLeft;
  });
}

function blockStyleAtSelection(state: EditorState): string {
  const line = state.doc.lineAt(state.selection.main.head).text;
  const legacyHeading = line.match(/^<!--\s*(#{1,6})\s+/);
  if (legacyHeading) return `h${legacyHeading[1].length}`;
  const heading = line.match(/^(#{1,6})\s+/);
  if (heading) return `h${heading[1].length}`;
  if (/^-\s+/.test(line)) return "list";
  return "paragraph";
}

function headingPositionByOrdinal(state: EditorState, level: 1 | 2 | 3, ordinal: number): number | null {
  let count = 0;
  for (let number = 1; number <= state.doc.lines; number += 1) {
    const line = state.doc.line(number);
    const match = line.text.match(/^(#{1,3})\s+/);
    if (!match || match[1].length !== level) continue;
    count += 1;
    if (count === ordinal) return line.from + match[0].length;
  }
  return null;
}

function SharedToolbar({
  viewRef,
  activeStyle
}: {
  viewRef: React.RefObject<EditorView | null>;
  activeStyle: string;
}) {
  const run = (fn: (view: EditorView) => void) => {
    const view = viewRef.current;
    if (view) fn(view);
  };

  return (
    <div className="manual-toolbar" aria-label="Estilos del manual">
      <div className="manual-toolbar-group">
        {([
          [1, "Contexto"],
          [2, "Sección"],
          [3, "Referencia"],
          [4, "Ancla"],
          [5, "Comentario"],
          [6, "Detalle"]
        ] as const).map(([level, label]) => (
          <button
            key={level}
            type="button"
            className={`manual-toolbar-btn${activeStyle === `h${level}` ? " is-active" : ""}`}
            onClick={() => run(view => applyHeading(view, level))}
            title={`${label} (⌘${level})`}
          >
            {label}
          </button>
        ))}
        <button
          type="button"
          className={`manual-toolbar-btn${activeStyle === "list" ? " is-active" : ""}`}
          onClick={() => run(applyBullet)}
          title="Lista (⌘7)"
        >
          Lista
        </button>
      </div>
      <span className="manual-toolbar-sep" aria-hidden="true" />
      <div className="manual-toolbar-group">
        <button type="button" className="manual-toolbar-btn" onClick={() => run(view => wrapSelection(view, "*"))}><em>I</em></button>
        <button type="button" className="manual-toolbar-btn" onClick={() => run(view => wrapSelection(view, "**"))}><strong>B</strong></button>
        <button type="button" className="manual-toolbar-btn" onClick={() => run(view => wrapSelection(view, "<u>", "</u>"))}><u>U</u></button>
        <button type="button" className="manual-toolbar-btn" onClick={() => run(view => insertBlock(view, "término - TERMINO\n: definición en español"))}>Def</button>
        <button type="button" className="manual-toolbar-btn" onClick={() => run(view => insertBlock(view, "---"))}>Diap.</button>
      </div>
    </div>
  );
}

export function SharedDocumentEditor({
  value,
  onChange,
  onDirty,
  reloadKey,
  mode,
  writingMode = false,
  filePath = null,
  onToggleMode
}: SharedDocumentEditorProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const mountRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const modeCompartment = useRef(new Compartment());
  const syntaxCompartment = useRef(new Compartment());
  const onChangeRef = useRef(onChange);
  const onDirtyRef = useRef(onDirty);
  const valueRef = useRef(value);
  const selfChange = useRef(false);
  const syncingFromProps = useRef(false);
  const lastReloadKey = useRef(reloadKey);
  const modeRef = useRef(mode);
  const openBibleRef = useRef<(
    reference: string,
    kind: "h3" | "inline",
    headingFrom?: number | null
  ) => void>(() => {});
  const biblePopupRequestId = useRef(0);
  const onToggleModeRef = useRef(onToggleMode);
  const { resolveReference, status: bibleStatus } = useBible();
  const [biblePopup, setBiblePopup] = useState<{
    kind: "h3" | "inline";
    reference: string;
    headingFrom: number | null;
    loading: boolean;
    error: string | null;
    result: ResolveBibleReferenceResult | null;
  } | null>(null);
  const [activeStyle, setActiveStyle] = useState("paragraph");

  onChangeRef.current = onChange;
  onDirtyRef.current = onDirty;
  valueRef.current = value;
  modeRef.current = mode;
  onToggleModeRef.current = onToggleMode;

  useEffect(() => {
    setManualImageBasePath(filePath);
  }, [filePath]);

  const closeBiblePopup = () => {
    biblePopupRequestId.current += 1;
    setBiblePopup(null);
  };

  openBibleRef.current = (reference, kind, headingFrom = null) => {
    const requestId = biblePopupRequestId.current + 1;
    biblePopupRequestId.current = requestId;
    setBiblePopup({ kind, reference, headingFrom, loading: true, error: null, result: null });
    void resolveReference(reference)
      .then(result => {
        if (requestId !== biblePopupRequestId.current) return;
        setBiblePopup({
          kind,
          reference,
          headingFrom,
          loading: false,
          error: result
            ? null
            : bibleStatus?.error ?? "Configure la biblioteca CGV para consultar referencias.",
          result
        });
      })
      .catch(error => {
        if (requestId !== biblePopupRequestId.current) return;
        setBiblePopup({
          kind,
          reference,
          headingFrom,
          loading: false,
          error: String(error),
          result: null
        });
      });
  };

  const flush = () => {
    const doc = viewRef.current?.state.doc.toString() ?? valueRef.current;
    if (doc !== valueRef.current) {
      valueRef.current = doc;
      selfChange.current = true;
      onChangeRef.current(doc);
    }
    return doc;
  };

  useEffect(() => {
    if (!mountRef.current) return;
    const updateListener = EditorView.updateListener.of(update => {
      if (update.selectionSet || update.docChanged) {
        setActiveStyle(blockStyleAtSelection(update.state));
      }
      if (!update.docChanged) return;
      const doc = update.state.doc.toString();
      valueRef.current = doc;
      if (syncingFromProps.current) return;
      selfChange.current = true;
      onChangeRef.current(doc);
      onDirtyRef.current?.();
    });
    const viewSwitchKeymap = Prec.highest(
      keymap.of([
        {
          key: "Mod-b",
          preventDefault: true,
          run: view => {
            wrapSelection(view, "**");
            return true;
          }
        },
        {
          key: "Mod-i",
          preventDefault: true,
          run: view => {
            wrapSelection(view, "*");
            return true;
          }
        },
        {
          key: "Enter",
          preventDefault: true,
          run: view => insertManualH5Line(view, modeRef.current)
        },
        {
          key: "Mod-/",
          preventDefault: true,
          run: () => {
            onToggleModeRef.current();
            return true;
          }
        }
      ])
    );
    const useSyntaxHighlight = value.length <= LARGE_MARKDOWN_CHARS;
    const syntaxExtensions =
      mode !== "manual" && useSyntaxHighlight
        ? [syntaxHighlighting(markdownHighlightStyle)]
        : [];
    const bibleReferenceClicks = bibleReferenceClickHandlers(modeRef, (reference, kind, headingFrom = null) => {
      openBibleRef.current(reference, kind, headingFrom);
    });
    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        drawSelection(),
        history(),
        cmSearchHighlightExtension(),
        cgvBlankHighlightExtension,
        markdown({ base: markdownLanguage }),
        syntaxCompartment.current.of(syntaxExtensions),
        editorTheme,
        viewSwitchKeymap,
        keymap.of([...defaultKeymap, ...historyKeymap]),
        EditorView.lineWrapping,
        bibleReferenceClicks,
        updateListener,
        modeCompartment.current.of(mode === "manual" ? codemirrorManualMode : [])
      ]
    });
    const view = new EditorView({ state, parent: mountRef.current });
    viewRef.current = view;
    setActiveStyle(blockStyleAtSelection(view.state));
    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const useSyntaxHighlight = valueRef.current.length <= LARGE_MARKDOWN_CHARS;
    preserveScrollDuring(view, () => {
      view.dispatch({
        effects: [
          modeCompartment.current.reconfigure(mode === "manual" ? codemirrorManualMode : []),
          syntaxCompartment.current.reconfigure(
            mode !== "manual" && useSyntaxHighlight ? [syntaxHighlighting(markdownHighlightStyle)] : []
          )
        ]
      });
    });
  }, [mode]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const fileChanged = lastReloadKey.current !== reloadKey;
    if (fileChanged) lastReloadKey.current = reloadKey;
    if (selfChange.current && !fileChanged) {
      selfChange.current = false;
      return;
    }
    selfChange.current = false;
    const current = view.state.doc.toString();
    if (!fileChanged && current === value) return;
    const selection = view.state.selection.main;
    syncingFromProps.current = true;
    const syncEditorValue = () => {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
        selection: fileChanged
          ? { anchor: modeRef.current === "manual" ? bodyStartInContent(value) : 0 }
          : {
              anchor: Math.min(selection.anchor, value.length),
              head: Math.min(selection.head, value.length)
            }
      });
    };
    try {
      if (fileChanged) {
        syncEditorValue();
      } else {
        preserveScrollDuring(view, syncEditorValue);
      }
      valueRef.current = value;
    } finally {
      syncingFromProps.current = false;
    }
  }, [value, reloadKey]);

  useEffect(() => {
    const onExport = () => {
      window.dispatchEvent(new CustomEvent("cgv-markdown-body-export", { detail: { body: flush() } }));
    };
    window.addEventListener("cgv-markdown-flush-sync", flush);
    window.addEventListener("cgv-markdown-body-export-request", onExport);
    return () => {
      window.removeEventListener("cgv-markdown-flush-sync", flush);
      window.removeEventListener("cgv-markdown-body-export-request", onExport);
    };
  }, []);

  const handleUseBibleText = () => {
    const view = viewRef.current;
    if (
      !view ||
      biblePopup?.kind !== "h3" ||
      biblePopup.headingFrom == null ||
      !biblePopup.result
    ) {
      return;
    }

    const text = formatScriptureLine(biblePopup.result.verses).trim();
    if (!text) return;

    const heading = view.state.doc.lineAt(
      Math.max(0, Math.min(biblePopup.headingFrom, view.state.doc.length))
    );
    const insert = `\n${text}`;
    view.dispatch({
      changes: { from: heading.to, insert },
      selection: { anchor: heading.to + insert.length }
    });
    setBiblePopup(null);
    view.focus();
  };

  useEffect(() => {
    const handler = (event: Event) => {
      const view = viewRef.current;
      if (!view) return;
      const detail = (event as CustomEvent<{ styleKey: number }>).detail;
      if (detail.styleKey >= 1 && detail.styleKey <= 6) {
        applyHeading(view, detail.styleKey as 1 | 2 | 3 | 4 | 5 | 6);
      } else if (detail.styleKey === 7) {
        applyBullet(view);
      }
    };
    window.addEventListener("cgv-apply-style", handler);
    return () => window.removeEventListener("cgv-apply-style", handler);
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const view = viewRef.current;
      if (!view) return;
      const detail = (event as CustomEvent<OutlineNavigateRequest>).detail;
      const directPos = headingPositionByOrdinal(view.state, detail.level, detail.ordinal);
      const fallbackPos = Math.min(view.state.doc.length, bodyStartInContent(view.state.doc.toString()) + detail.bodyOffset);
      const pos = directPos ?? fallbackPos;
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
      if (!view) return;
      const detail = (event as CustomEvent<SearchRequest>).detail;
      const query = new SearchQuery({
        search: detail.query,
        caseSensitive: detail.caseSensitive,
        replace: detail.replace,
        literal: true
      });
      if (detail.action === "clear") {
        view.dispatch({ effects: setCmSearchHighlight.of(null) });
        reportSearchResult({ total: 0, current: 0 });
        return;
      }
      if (detail.action === "replaceAll") {
        const current = view.state.doc.toString();
        const next = replaceAllInText(current, detail.query, detail.replace, detail.caseSensitive);
        if (next !== current) view.dispatch({ changes: { from: 0, to: current.length, insert: next } });
        return;
      }
      const previous = view.state.field(cmSearchHighlightField);
      if (detail.action === "replace") {
        const match = previous ? getCmSearchMatch(view, previous) : null;
        if (match) view.dispatch({ changes: { from: match.from, to: match.to, insert: detail.replace } });
      }
      const startIndex = detail.action === "prev"
        ? (previous?.currentIndex ?? 0) - 1
        : detail.action === "next"
          ? (previous?.currentIndex ?? -1) + 1
          : firstMatchIndexAtOrAfter(query, view.state.doc, view.state.selection.main.head);
      const result = applyCmSearchHighlight(view, query, startIndex);
      const match = result ? getCmSearchMatch(view, result) : null;
      if (match) revealCmSearchMatch(view, match);
    };
    window.addEventListener("cgv-search", handler);
    return () => window.removeEventListener("cgv-search", handler);
  }, []);

  return (
    <>
      <div
        className={`shared-document-editor shared-document-editor--${mode}${writingMode ? " shared-document-editor--writing" : ""}`}
        onKeyDownCapture={event => {
          const mod = event.metaKey || event.ctrlKey;
          if (!mod || event.altKey || (event.key !== "/" && event.code !== "Slash")) return;
          event.preventDefault();
          event.stopPropagation();
          onToggleModeRef.current();
        }}
      >
        {mode === "manual" && <SharedToolbar viewRef={viewRef} activeStyle={activeStyle} />}
        <div className="editor-host" ref={hostRef}>
          <div className="editor-mount" ref={mountRef} />
        </div>
      </div>
      <BibleReferencePopup
        open={Boolean(biblePopup)}
        reference={biblePopup?.reference ?? ""}
        version={bibleStatus?.version ?? "NBLA"}
        loading={Boolean(biblePopup?.loading)}
        error={biblePopup?.error ?? null}
        result={biblePopup?.result ?? null}
        showUseText={biblePopup?.kind === "h3"}
        onClose={closeBiblePopup}
        onUseText={handleUseBibleText}
      />
    </>
  );
}
