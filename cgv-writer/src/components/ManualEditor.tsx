import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import HorizontalRule from "@tiptap/extension-horizontal-rule";
import Underline from "@tiptap/extension-underline";
import { useEffect, useRef, useState } from "react";
import type { Editor } from "@tiptap/react";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import {
  anchorBeforeOffset,
  bodyTextCharRatio,
  loadSharedEditorPlace,
  normalizeForAnchor,
  plainTextOffset,
  saveEditorPlace,
  textOffsetFromPos,
  textOffsetToPos,
  type SavedEditorPlace
} from "../lib/editor-position-bridge";
import {
  applyCommentBulletList,
  applyHeadingStyle,
  applyScriptureStyle,
  underlineWordAtCursor
} from "../lib/manual-comments";
import { CgvH5Block } from "../lib/tiptap-cgv-h5-block";
import { CgvSynthesisBlockquote } from "../lib/tiptap-cgv-synthesis";
import { CgvParagraph } from "../lib/tiptap-cgv-paragraph";
import { ensureScriptureParagraphsAfterH3 } from "../lib/manual-scripture-blocks";
import { CgvSearch, cgvSearchPluginKey } from "../lib/tiptap-search";
import type { SearchRequest } from "../lib/search-bridge";
import {
  editorHtmlToMarkdown,
  isLikelyBibleReference,
  markdownToEditorHtml
} from "../lib/markdown-html";
import { replaceAllInText } from "../lib/text-search";
import { isManualCommandVisible } from "../lib/manual-toolbar-config";
import {
  DEFAULT_MANUAL_BLOCK_STYLE,
  getManualBlockStyleAtCursor,
  type ManualBlockStyle
} from "../lib/manual-block-style";
import {
  clearManualEditorDirty,
  isManualEditorDirty,
  MANUAL_SYNC_MS,
  markManualEditorDirty,
  setViewHandoff,
  takeViewHandoff
} from "../lib/manual-sync";
import { useBible } from "../lib/bible-context";
import { formatScriptureLine, type ResolveBibleReferenceResult } from "../lib/bible-client";
import {
  applyScriptureTextAfterH3,
  findH3AtPos
} from "../lib/insert-scripture-from-bible";
import { findH3FromDomClick } from "../lib/h3-reference-click";
import { getInlineReferenceAtDocPos, getInlineReferenceFromClick } from "../lib/inline-reference-click";
import { CgvInlineBibleRefs, inlineBibleRefsPluginKey } from "../lib/tiptap-inline-bible-refs";
import {
  BIBLE_INDEX_UPDATED_EVENT
} from "../lib/bible-index-store";
import { BibleReferencePopup } from "./BibleReferencePopup";
import "./ManualEditor.css";
import "./BibleReferencePopup.css";

interface ManualEditorProps {
  body: string;
  onBodyChange: (body: string) => void;
  reloadKey: string;
  isActive: boolean;
  writingMode?: boolean;
}

function manualDocPlainText(doc: ProseMirrorNode): string {
  return doc.textBetween(0, doc.content.size, "\n", "\n");
}

function manualBodyCharRatio(ed: Editor): number {
  const doc = ed.state.doc;
  const plain = manualDocPlainText(doc);
  const normalized = normalizeForAnchor(plain);
  if (!normalized.length) return 0;
  const offset = textOffsetFromPos(doc, ed.state.selection.from);
  const normOffset = normalizeForAnchor(plain.slice(0, offset)).length;
  return bodyTextCharRatio(normalized.length, normOffset);
}

function manualAnchorBefore(ed: Editor): string {
  const doc = ed.state.doc;
  const plain = manualDocPlainText(doc);
  const offset = textOffsetFromPos(doc, ed.state.selection.from);
  return anchorBeforeOffset(plain, offset);
}

function manualNormalizedOffset(ed: Editor): number {
  const doc = ed.state.doc;
  const plain = manualDocPlainText(doc);
  const offset = textOffsetFromPos(doc, ed.state.selection.from);
  return normalizeForAnchor(plain.slice(0, offset)).length;
}

function manualSavePlace(ed: Editor, scrollEl: HTMLElement | null): SavedEditorPlace {
  const bodyCharRatio = manualBodyCharRatio(ed);
  const anchorBefore = manualAnchorBefore(ed);
  const normalizedOffset = manualNormalizedOffset(ed);
  saveEditorPlace("manual", scrollEl, bodyCharRatio, anchorBefore, normalizedOffset);
  return loadSharedEditorPlace() ?? {
    scrollRatio: 0,
    bodyCharRatio,
    anchorBefore,
    normalizedOffset
  };
}

function scrollManualCursorIntoView(ed: Editor, scrollEl: HTMLElement | null): void {
  if (!scrollEl) return;
  const coords = ed.view.coordsAtPos(ed.state.selection.from);
  const box = scrollEl.getBoundingClientRect();
  scrollEl.scrollTop = Math.max(
    0,
    coords.top - box.top + scrollEl.scrollTop - scrollEl.clientHeight * 0.35
  );
}

function restoreManualPlace(
  ed: Editor,
  scrollEl: HTMLElement | null,
  place: SavedEditorPlace
): void {
  const doc = ed.state.doc;
  const plain = manualDocPlainText(doc);
  const target = plainTextOffset(plain, place);
  const pos = textOffsetToPos(doc, target);
  ed.commands.setTextSelection(pos);
  ed.commands.focus();
  requestAnimationFrame(() => scrollManualCursorIntoView(ed, scrollEl));
}

function scrollToCurrentMatch(editor: Editor, scrollEl: HTMLElement | null): void {
  const state = cgvSearchPluginKey.getState(editor.state);
  if (!state || state.currentIndex < 0) return;
  const match = state.matches[state.currentIndex];
  if (!match) return;

  const coords = editor.view.coordsAtPos(match.from);
  if (!scrollEl) return;
  const box = scrollEl.getBoundingClientRect();
  const target = coords.top - box.top + scrollEl.scrollTop - scrollEl.clientHeight * 0.35;
  scrollEl.scrollTop = Math.max(0, target);
}

export function ManualEditor({ body, onBodyChange, reloadKey, isActive, writingMode = false }: ManualEditorProps) {
  const lastReloadKey = useRef(reloadKey);
  const suppressUpdate = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wasActive = useRef(false);
  const onBodyChangeRef = useRef(onBodyChange);
  const bodyRef = useRef(body);
  const syncTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const lastSyncedFromEditor = useRef<string | null>(null);
  const lastLoadedBody = useRef(body);
  const isActiveRef = useRef(isActive);
  const [blockStyle, setBlockStyle] = useState<ManualBlockStyle>(DEFAULT_MANUAL_BLOCK_STYLE);
  const { resolveReference, status: bibleStatus, loading: bibleLoading, index: bibleIndex } = useBible();
  const [biblePopup, setBiblePopup] = useState<{
    kind: "h3" | "inline";
    reference: string;
    h3Pos: number | null;
    loading: boolean;
    error: string | null;
    result: ResolveBibleReferenceResult | null;
  } | null>(null);
  const openBiblePopupRef = useRef<
    (request: { kind: "h3" | "inline"; reference: string; h3Pos?: number | null }) => void
  >(() => {});
  const bibleIndexRef = useRef(bibleIndex);
  bibleIndexRef.current = bibleIndex;
  onBodyChangeRef.current = onBodyChange;
  bodyRef.current = body;
  isActiveRef.current = isActive;

  const cancelPendingSync = () => {
    if (syncTimer.current) {
      clearTimeout(syncTimer.current);
      syncTimer.current = null;
    }
  };

  const pushBodyMarkdown = (markdown: string) => {
    lastSyncedFromEditor.current = markdown;
    lastLoadedBody.current = markdown;
    clearManualEditorDirty();
    onBodyChangeRef.current(markdown);
  };

  const scheduleSyncToMarkdown = () => {
    cancelPendingSync();
    syncTimer.current = setTimeout(() => {
      syncTimer.current = null;
      const ed = editorRef.current;
      if (!ed || suppressUpdate.current) return;
      const md = editorHtmlToMarkdown(ed.getHTML());
      if (md.trim() === bodyRef.current.trim()) return;
      pushBodyMarkdown(md);
    }, MANUAL_SYNC_MS);
  };

  const flushPending = () => {
    const ed = editorRef.current;
    if (!ed) return;
    if (syncTimer.current) {
      clearTimeout(syncTimer.current);
      syncTimer.current = null;
    }
    if (suppressUpdate.current) return;
    const md = editorHtmlToMarkdown(ed.getHTML());
    lastSyncedFromEditor.current = md;
    lastLoadedBody.current = md;
    onBodyChangeRef.current(md);
  };

  const openBiblePopup = async (
    kind: "h3" | "inline",
    reference: string,
    h3Pos: number | null = null
  ) => {
    setBiblePopup({
      kind,
      reference,
      h3Pos,
      loading: true,
      error: null,
      result: null
    });

    if (bibleLoading || !bibleStatus?.loaded) {
      if (!bibleStatus?.configured) {
        setBiblePopup({
          kind,
          reference,
          h3Pos,
          loading: false,
          error:
            "Configure la biblioteca CGV en el panel lateral (Biblioteca CGV → Elegir carpeta…). Elija la carpeta raíz que contiene bibles/, no la subcarpeta bibles/ sola.",
          result: null
        });
        return;
      }

      if (!bibleStatus.loaded) {
        setBiblePopup({
          kind,
          reference,
          h3Pos,
          loading: false,
          error: bibleStatus.error ?? "No se pudo cargar la biblioteca NBLA.",
          result: null
        });
        return;
      }
    }

    try {
      const result = await resolveReference(reference);
      if (!result) {
        setBiblePopup({
          kind,
          reference,
          h3Pos,
          loading: false,
          error: `No se encontró la referencia: ${reference}`,
          result: null
        });
        return;
      }

      setBiblePopup({
        kind,
        reference,
        h3Pos,
        loading: false,
        error: null,
        result
      });
    } catch (error) {
      setBiblePopup({
        kind,
        reference,
        h3Pos,
        loading: false,
        error: String(error),
        result: null
      });
    }
  };

  openBiblePopupRef.current = ({ kind, reference, h3Pos = null }) => {
    void openBiblePopup(kind, reference, h3Pos);
  };

  const editor = useEditor(
    {
      extensions: [
        StarterKit.configure({
          heading: { levels: [1, 2, 3, 4, 5, 6] },
          horizontalRule: false,
          paragraph: false,
          blockquote: false,
          bulletList: {
            HTMLAttributes: { class: "cgv-h6-bullets" }
          }
        }),
        CgvSynthesisBlockquote,
        CgvParagraph,
        CgvH5Block,
        CgvInlineBibleRefs,
        CgvSearch,
        Underline,
        Placeholder.configure({
          placeholder: () =>
            writingMode ? "" : "⌘O para abrir un manual, o empiece a escribir."
        }),
        HorizontalRule.configure({ HTMLAttributes: { class: "cgv-slide-break" } })
      ],
      content: markdownToEditorHtml(body || ""),
      editorProps: {
        attributes: { class: "manual-prosemirror" },
        handleClick: (_view, pos, event) => {
          const ed = editorRef.current;
          if (!ed) return false;

          const hit = findH3AtPos(ed, pos);
          if (hit && isLikelyBibleReference(hit.text)) {
            event.preventDefault();
            openBiblePopupRef.current({
              kind: "h3",
              reference: hit.text,
              h3Pos: hit.pos
            });
            return true;
          }

          const inline = getInlineReferenceAtDocPos(ed, pos, bibleIndexRef.current);
          if (inline) {
            event.preventDefault();
            openBiblePopupRef.current({
              kind: "inline",
              reference: inline.reference
            });
            return true;
          }

          return false;
        },
        handleKeyDown: (_view, event) => {
          if (
            (event.metaKey || event.ctrlKey) &&
            !event.altKey &&
            !event.shiftKey &&
            event.key.toLowerCase() === "u"
          ) {
            event.preventDefault();
            const ed = editorRef.current;
            if (ed) underlineWordAtCursor(ed);
            return true;
          }
          if (event.key === "Enter" && !event.shiftKey) {
            queueMicrotask(() => {
              const ed = editorRef.current;
              if (ed) ensureScriptureParagraphsAfterH3(ed);
            });
          }
          return false;
        }
      },
      onUpdate: () => {
        if (suppressUpdate.current) return;
        markManualEditorDirty();
        scheduleSyncToMarkdown();
      }
    },
    []
  );

  editorRef.current = editor;

  useEffect(() => {
    if (!editor || !scrollRef.current) return;

    const root = scrollRef.current;

    const onEditorClick = (event: MouseEvent) => {
      if (!isActiveRef.current) return;

      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest(".manual-prosemirror") || !root.contains(target)) return;

      const h3 = target.closest(".manual-prosemirror h3");
      if (h3) {
        const hit = findH3FromDomClick(editor.state.doc, h3.textContent ?? "");
        if (hit) {
          event.preventDefault();
          event.stopPropagation();
          openBiblePopupRef.current({
            kind: "h3",
            reference: hit.text,
            h3Pos: hit.pos
          });
        }
        return;
      }

      const inline = getInlineReferenceFromClick(editor, event, bibleIndexRef.current);
      if (!inline) return;

      event.preventDefault();
      event.stopPropagation();
      openBiblePopupRef.current({
        kind: "inline",
        reference: inline.reference
      });
    };

    root.addEventListener("click", onEditorClick, true);
    return () => root.removeEventListener("click", onEditorClick, true);
  }, [editor]);

  useEffect(() => {
    if (!editor) return;

    const refreshInlineRefs = () => {
      editor.view.dispatch(editor.state.tr.setMeta(inlineBibleRefsPluginKey, true));
    };

    window.addEventListener(BIBLE_INDEX_UPDATED_EVENT, refreshInlineRefs);
    window.addEventListener("cgv-bible-library-changed", refreshInlineRefs);
    refreshInlineRefs();

    return () => {
      window.removeEventListener(BIBLE_INDEX_UPDATED_EVENT, refreshInlineRefs);
      window.removeEventListener("cgv-bible-library-changed", refreshInlineRefs);
    };
  }, [editor]);

  useEffect(() => {
    if (!biblePopup) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setBiblePopup(null);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [biblePopup]);

  useEffect(() => {
    if (!editor) return;

    const updateBlockStyle = () => {
      setBlockStyle(getManualBlockStyleAtCursor(editor));
    };

    updateBlockStyle();
    editor.on("selectionUpdate", updateBlockStyle);
    editor.on("transaction", updateBlockStyle);
    return () => {
      editor.off("selectionUpdate", updateBlockStyle);
      editor.off("transaction", updateBlockStyle);
    };
  }, [editor]);

  useEffect(() => {
    return () => {
      if (syncTimer.current) clearTimeout(syncTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!editor) return;

    const onFlush = () => flushPending();
    const onCancel = () => cancelPendingSync();
    const onExport = () => {
      flushPending();
      const ed = editorRef.current;
      const md = ed ? editorHtmlToMarkdown(ed.getHTML()) : bodyRef.current;
      window.dispatchEvent(
        new CustomEvent("cgv-manual-body-export", {
          detail: { body: md }
        })
      );
    };

    const onHandoff = () => {
      const ed = editorRef.current;
      if (!ed) {
        window.dispatchEvent(
          new CustomEvent("cgv-manual-body-handoff", { detail: { body: bodyRef.current } })
        );
        return;
      }
      cancelPendingSync();
      const md = editorHtmlToMarkdown(ed.getHTML());
      lastLoadedBody.current = md;
      lastSyncedFromEditor.current = md;
      clearManualEditorDirty();
      window.dispatchEvent(new CustomEvent("cgv-manual-body-handoff", { detail: { body: md } }));
    };

    window.addEventListener("cgv-manual-flush-sync", onFlush);
    window.addEventListener("cgv-manual-cancel-sync", onCancel);
    window.addEventListener("cgv-manual-body-export-request", onExport);
    window.addEventListener("cgv-request-manual-body-handoff", onHandoff);
    return () => {
      window.removeEventListener("cgv-manual-flush-sync", onFlush);
      window.removeEventListener("cgv-manual-cancel-sync", onCancel);
      window.removeEventListener("cgv-manual-body-export-request", onExport);
      window.removeEventListener("cgv-request-manual-body-handoff", onHandoff);
    };
  }, [editor]);

  useEffect(() => {
    if (!editor) return;

    const fileChanged = lastReloadKey.current !== reloadKey;
    if (!fileChanged) return;

    lastReloadKey.current = reloadKey;
    lastSyncedFromEditor.current = null;
    lastLoadedBody.current = body;
    clearManualEditorDirty();
    cancelPendingSync();
    suppressUpdate.current = true;
    editor.commands.setContent(markdownToEditorHtml(body), { emitUpdate: false });
    requestAnimationFrame(() => {
      ensureScriptureParagraphsAfterH3(editor);
      suppressUpdate.current = false;
    });
  }, [body, reloadKey, editor]);

  /** Reload when body changes from outside the editor (style correct, Presenter panel, etc.). */
  useEffect(() => {
    if (!editor) return;

    const incoming = body.trim();
    const loaded = lastLoadedBody.current.trim();
    const synced = lastSyncedFromEditor.current?.trim() ?? "";

    if (incoming === loaded) return;
    if (incoming === synced) {
      lastLoadedBody.current = body;
      return;
    }

    cancelPendingSync();
    suppressUpdate.current = true;
    lastLoadedBody.current = body;
    lastSyncedFromEditor.current = body;
    clearManualEditorDirty();
    editor.commands.setContent(markdownToEditorHtml(body), { emitUpdate: false });
    requestAnimationFrame(() => {
      ensureScriptureParagraphsAfterH3(editor);
      suppressUpdate.current = false;
    });
  }, [body, editor]);

  useEffect(() => {
    if (!editor) return;

    const saveIfActive = () => {
      if (!isActiveRef.current) return;

      const place = manualSavePlace(editor, scrollRef.current);
      let bodyMd: string | null = null;

      if (isManualEditorDirty() || syncTimer.current) {
        cancelPendingSync();
        bodyMd = editorHtmlToMarkdown(editor.getHTML());
        lastLoadedBody.current = bodyMd;
        lastSyncedFromEditor.current = bodyMd;
        bodyRef.current = bodyMd;
        clearManualEditorDirty();
        onBodyChangeRef.current(bodyMd);
      }

      setViewHandoff({ place, bodyMd });
    };

    window.addEventListener("cgv-before-view-change", saveIfActive);
    return () => window.removeEventListener("cgv-before-view-change", saveIfActive);
  }, [editor]);

  useEffect(() => {
    if (!editor) return;

    if (!isActive && wasActive.current) {
      cancelPendingSync();
    }

    if (isActive && !wasActive.current) {
      const handoff = takeViewHandoff();
      const place = handoff?.place ?? loadSharedEditorPlace();
      const reloadBody = handoff?.bodyMd ?? bodyRef.current;
      const needsReload = reloadBody.trim() !== lastLoadedBody.current.trim();

      const finishActivate = () => {
        suppressUpdate.current = false;
        if (place) {
          restoreManualPlace(editor, scrollRef.current, place);
        } else {
          editor.commands.focus();
        }
      };

      if (needsReload) {
        cancelPendingSync();
        suppressUpdate.current = true;
        editor.commands.setContent(markdownToEditorHtml(reloadBody), { emitUpdate: false });
        lastLoadedBody.current = reloadBody;
        bodyRef.current = reloadBody;
        requestAnimationFrame(() => {
          ensureScriptureParagraphsAfterH3(editor);
          finishActivate();
        });
      } else if (place) {
        restoreManualPlace(editor, scrollRef.current, place);
      } else {
        editor.commands.focus();
      }
    }

    wasActive.current = isActive;
  }, [isActive, editor]);

  useEffect(() => {
    if (!editor) return;
    editor.setOptions({
      editorProps: {
        attributes: {
          class: writingMode
            ? "manual-prosemirror manual-prosemirror--preview"
            : "manual-prosemirror"
        }
      }
    });
  }, [editor, writingMode]);

  useEffect(() => {
    if (!editor || !isActive || !writingMode) return;
    editor.commands.focus();
  }, [editor, isActive, writingMode]);

  useEffect(() => {
    if (!editor) return;

    const handler = (event: Event) => {
      if (!isActive) return;

      const detail = (event as CustomEvent<{ styleKey: number; viewMode: string }>).detail;
      if (detail.viewMode !== "manual") return;

      const key = detail.styleKey;
      switch (key) {
        case 1:
          editor.chain().focus().toggleHeading({ level: 1 }).run();
          break;
        case 2:
          editor.chain().focus().toggleHeading({ level: 2 }).run();
          break;
        case 3:
          editor.chain().focus().toggleHeading({ level: 3 }).run();
          break;
        case 4:
          applyHeadingStyle(editor, 4);
          break;
        case 5:
          applyHeadingStyle(editor, 5);
          break;
        case 6:
          applyHeadingStyle(editor, 6);
          break;
        case 7:
          applyCommentBulletList(editor);
          break;
        default:
          break;
      }
    };

    window.addEventListener("cgv-apply-style", handler);
    return () => window.removeEventListener("cgv-apply-style", handler);
  }, [editor, isActive]);

  useEffect(() => {
    if (!editor) return;

    const syncQuery = (query: string, caseSensitive: boolean) => {
      const current = cgvSearchPluginKey.getState(editor.state);
      if (
        current &&
        current.query === query &&
        current.caseSensitive === caseSensitive &&
        current.matches.length
      ) {
        return;
      }
      editor.commands.findInDocument(query, caseSensitive);
    };

    const handler = (event: Event) => {
      if (!isActive) return;

      flushPending();

      const detail = (event as CustomEvent<SearchRequest>).detail;
      switch (detail.action) {
        case "clear":
          editor.commands.clearDocumentSearch();
          break;
        case "find":
          editor.commands.findInDocument(detail.query, detail.caseSensitive);
          scrollToCurrentMatch(editor, scrollRef.current);
          break;
        case "next":
          syncQuery(detail.query, detail.caseSensitive);
          editor.commands.findNextInDocument();
          scrollToCurrentMatch(editor, scrollRef.current);
          break;
        case "prev":
          syncQuery(detail.query, detail.caseSensitive);
          editor.commands.findPreviousInDocument();
          scrollToCurrentMatch(editor, scrollRef.current);
          break;
        case "replace":
          syncQuery(detail.query, detail.caseSensitive);
          editor.commands.replaceCurrentMatch(detail.replace);
          scrollToCurrentMatch(editor, scrollRef.current);
          break;
        case "replaceAll": {
          syncQuery(detail.query, detail.caseSensitive);
          const md = editorHtmlToMarkdown(editor.getHTML());
          const nextMd = replaceAllInText(
            md,
            detail.query,
            detail.replace,
            detail.caseSensitive
          );
          if (nextMd === md) break;

          cancelPendingSync();
          suppressUpdate.current = true;
          editor.commands.setContent(markdownToEditorHtml(nextMd), { emitUpdate: false });
          suppressUpdate.current = false;
          onBodyChangeRef.current(nextMd);
          editor.commands.clearDocumentSearch();
          if (detail.query) {
            editor.commands.findInDocument(detail.query, detail.caseSensitive);
          }
          break;
        }
      }
    };

    window.addEventListener("cgv-search", handler);
    return () => window.removeEventListener("cgv-search", handler);
  }, [editor, isActive]);

  const handleUseBibleText = () => {
    if (!editor || biblePopup?.kind !== "h3" || biblePopup.h3Pos == null || !biblePopup.result) {
      return;
    }

    const text = formatScriptureLine(biblePopup.result.verses);
    applyScriptureTextAfterH3(editor, biblePopup.h3Pos, text);
    markManualEditorDirty();
    scheduleSyncToMarkdown();
    setBiblePopup(null);
  };

  if (!editor) return null;

  const insertScripture = () => {
    applyScriptureStyle(editor);
  };

  const insertDefinition = () => {
    editor
      .chain()
      .focus()
      .insertContent(
        `<div class="cgv-definition"><p class="definition-term">término - TERMINO</p><p class="definition-text">: definición en español</p></div>`
      )
      .run();
  };

  const insertSlideBreak = () => {
    editor.chain().focus().setHorizontalRule().run();
  };

  const insertQuiz = () => {
    const id = window.prompt("ID del quiz (ej. santiago-1-1-27)", "santiago-1-1-27");
    if (!id?.trim()) return;
    editor
      .chain()
      .focus()
      .insertContent(
        `<p class="cgv-quiz" data-quiz-id="${id.trim()}">Quiz: ${id.trim()}</p>`
      )
      .run();
  };

  const styleButtonClass = (id: string) =>
    blockStyle.id === id ? "manual-toolbar-btn is-active" : "manual-toolbar-btn";

  const blockStyleIndicator = (
    <span className="manual-style-indicator" aria-live="polite" title="Estilo del bloque actual">
      <span className="manual-style-indicator-mark">{blockStyle.markdown}</span>
      <span className="manual-style-indicator-label">{blockStyle.label}</span>
      {blockStyle.shortcut ? (
        <span className="manual-style-indicator-shortcut">{blockStyle.shortcut}</span>
      ) : null}
    </span>
  );

  return (
    <div
      className={`manual-editor ${writingMode ? "manual-editor--writing" : ""} ${
        bibleIndex || bibleStatus?.loaded ? "manual-editor--bible-ready" : ""
      }`}
    >
      {!writingMode && (
        <div className="manual-toolbar">
        <span className="manual-toolbar-label">Estilo:</span>
        {blockStyleIndicator}
        <span className="manual-toolbar-sep" />
        <button type="button" className={styleButtonClass("h1")} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} title="⌘1">
          Contexto
        </button>
        <button type="button" className={styleButtonClass("h2")} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} title="⌘2">
          Sección
        </button>
        <button type="button" className={styleButtonClass("h3")} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} title="⌘3 — referencia bíblica">
          Referencia
        </button>
        <button type="button" className={`${styleButtonClass("h4")} accent`} onClick={() => applyHeadingStyle(editor, 4)} title="⌘4 — texto ancla (escritura)">
          H4
        </button>
        <button type="button" className={styleButtonClass("h5")} onClick={() => applyHeadingStyle(editor, 5)} title="⌘5 — comentario nivel 1">
          H5
        </button>
        <button type="button" className={styleButtonClass("h6")} onClick={() => applyHeadingStyle(editor, 6)} title="⌘6 — comentario nivel 2">
          H6
        </button>
        <button type="button" className={styleButtonClass("list")} onClick={() => applyCommentBulletList(editor)} title="⌘7 — comentario nivel 3 (lista)">
          Lista
        </button>
        <button type="button" className={styleButtonClass("scripture")} onClick={insertScripture} title="Versículo bajo referencia">
          Versículo
        </button>
        <button type="button" className={styleButtonClass("definition")} onClick={insertDefinition}>
          Definición
        </button>
        <span className="manual-toolbar-sep" />
        <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()} title="En comentarios = escritura">
          Cursiva
        </button>
        <button type="button" onClick={() => underlineWordAtCursor(editor)} title="Espacio en blanco (⌘U)">
          Subrayado
        </button>
        <button type="button" onClick={() => editor.chain().focus().toggleBold().run()}>
          Negrita
        </button>
        {(isManualCommandVisible("slideBreak") || isManualCommandVisible("quiz")) && (
          <>
            <span className="manual-toolbar-sep" />
            {isManualCommandVisible("slideBreak") && (
              <button type="button" onClick={insertSlideBreak}>
                Diapositiva
              </button>
            )}
            {isManualCommandVisible("quiz") && (
              <button type="button" onClick={insertQuiz}>
                Quiz
              </button>
            )}
          </>
        )}
      </div>
      )}

      {writingMode && (
        <div className="manual-style-indicator manual-style-indicator--writing" aria-live="polite">
          <span className="manual-style-indicator-mark">{blockStyle.markdown}</span>
          <span className="manual-style-indicator-label">{blockStyle.label}</span>
        </div>
      )}

      <div className="manual-page-scroll" ref={scrollRef}>
        <div className="manual-page">
          <EditorContent editor={editor} />
        </div>
      </div>

      {writingMode && (
        <p className="writing-mode-keys">
          Escape · ⌘⇧F salir · ⌘/ vista · ⌘S guardar
        </p>
      )}

      <BibleReferencePopup
        open={!!biblePopup}
        reference={biblePopup?.reference ?? ""}
        version={bibleStatus?.version ?? "NBLA"}
        loading={biblePopup?.loading ?? false}
        error={biblePopup?.error ?? null}
        result={biblePopup?.result ?? null}
        showUseText={biblePopup?.kind === "h3"}
        onClose={() => setBiblePopup(null)}
        onUseText={handleUseBibleText}
      />
    </div>
  );
}
