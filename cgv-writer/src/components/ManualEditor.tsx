import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import HorizontalRule from "@tiptap/extension-horizontal-rule";
import Underline from "@tiptap/extension-underline";
import { memo, useEffect, useRef, useState } from "react";
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
  underlineWordAtCursor,
  underlineWordAtDocPos
} from "../lib/manual-comments";
import {
  applyReferenceHeading,
  ensureScriptureParagraphAfterH3AtCursor,
  handleManualEnterKey,
  tightenPassageLayoutInEditor
} from "../lib/manual-passage-layout";
import { CgvH5Block } from "../lib/tiptap-cgv-h5-block";
import { CgvTable } from "../lib/tiptap-cgv-table";
import { CgvSynthesisBlockquote } from "../lib/tiptap-cgv-synthesis";
import { CgvParagraph } from "../lib/tiptap-cgv-paragraph";
import { CgvSearch, cgvSearchPluginKey } from "../lib/tiptap-search";
import type { SearchRequest } from "../lib/search-bridge";
import {
  isLikelyBibleReference,
  checkBodyRoundTripLoss,
  markdownToEditorHtml,
  quizMarkerComment,
  sanitizeCgvMarkdown
} from "../lib/markdown-html";
import {
  checkContentPreserved,
  reportContentLossBlocked
} from "../lib/content-preservation";
import { editorDocToMarkdown } from "../lib/blocks/parse-prosemirror";
import { replaceAllInText } from "../lib/text-search";
import { findManualHeadingPos, type OutlineNavigateRequest } from "../lib/outline-bridge";
import { insertQuizIntoEditorMarkdown } from "../lib/manual-quiz-insert";
import { ManualToolbar, ManualStyleChip } from "./ManualToolbar";
import {
  blockPendingViewChange,
  clearManualEditorDirty,
  isManualEditorDirty,
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
  /** View switch — update shared state without marking the document dirty. */
  onBodySync?: (body: string) => void;
  onDirty?: () => void;
  reloadKey: string;
  isActive: boolean;
  /** Read-only layout preview — markdown is the editable source. */
  previewOnly?: boolean;
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

function ManualEditorInner({
  body,
  onBodyChange,
  onBodySync,
  onDirty,
  reloadKey,
  isActive,
  previewOnly = true,
  writingMode = false
}: ManualEditorProps) {
  const lastReloadKey = useRef(reloadKey);
  const suppressUpdate = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wasActive = useRef(false);
  const onBodyChangeRef = useRef(onBodyChange);
  const onBodySyncRef = useRef(onBodySync);
  const onDirtyRef = useRef(onDirty);
  const bodyRef = useRef(body);
  const syncTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const lastSyncedFromEditor = useRef<string | null>(null);
  const lastLoadedBody = useRef(body);
  const lastSelectionPos = useRef(0);
  const isActiveRef = useRef(isActive);
  const previewOnlyRef = useRef(previewOnly);
  const writingModeRef = useRef(writingMode);
  const { resolveReference, status: bibleStatus, index: bibleIndex } = useBible();
  const [biblePopup, setBiblePopup] = useState<{
    kind: "h3" | "inline";
    reference: string;
    h3Pos: number | null;
    loading: boolean;
    error: string | null;
    result: ResolveBibleReferenceResult | null;
  } | null>(null);
  const [underlinePaintMode, setUnderlinePaintMode] = useState(false);
  const [safetyWarning, setSafetyWarning] = useState<string | null>(null);
  const underlinePaintModeRef = useRef(false);
  const openBiblePopupRef = useRef<
    (request: { kind: "h3" | "inline"; reference: string; h3Pos?: number | null }) => void
  >(() => {});
  const bibleIndexRef = useRef(bibleIndex);
  bibleIndexRef.current = bibleIndex;
  onBodyChangeRef.current = onBodyChange;
  onBodySyncRef.current = onBodySync;
  onDirtyRef.current = onDirty;
  bodyRef.current = body;
  isActiveRef.current = isActive;
  previewOnlyRef.current = previewOnly;
  writingModeRef.current = writingMode;

  const setUnderlinePaintModeEnabled = (enabled: boolean) => {
    underlinePaintModeRef.current = enabled;
    setUnderlinePaintMode(enabled);
  };

  const toggleUnderlinePaintMode = () => {
    setUnderlinePaintModeEnabled(!underlinePaintModeRef.current);
  };

  const warnRoundTripLoss = (sourceBody: string) => {
    const loss = checkBodyRoundTripLoss(sourceBody);
    if (loss.missingCount === 0) {
      setSafetyWarning(null);
      return;
    }
    const message =
      `La vista Manual no representa ${loss.missingCount} línea(s) de este archivo. ` +
      "Edite en Markdown hasta corregirlo — no guarde desde Manual.";
    setSafetyWarning(message);
    reportContentLossBlocked(message, loss.missing);
  };

  const cancelPendingSync = () => {
    if (syncTimer.current) {
      clearTimeout(syncTimer.current);
      syncTimer.current = null;
    }
  };

  const scheduleSyncToMarkdown = () => {
    if (previewOnlyRef.current) return;
    if (writingModeRef.current) return;
    markManualEditorDirty();
    onDirtyRef.current?.();
  };

  /** TipTap → markdown; layout tighten only when it preserves all editor text. */
  const exportEditorMarkdown = (ed: Editor, tighten = false): string => {
    const beforeTighten = editorDocToMarkdown(ed);
    if (!tighten) return beforeTighten;

    tightenPassageLayoutInEditor(ed);
    const afterTighten = editorDocToMarkdown(ed);
    const loss = checkContentPreserved(beforeTighten, afterTighten);
    if (loss.missingCount > 0) {
      return beforeTighten;
    }
    return afterTighten;
  };

  const exportIfContentSafe = (ed: Editor, storedBody: string, tighten = false): string | null => {
    const md = exportEditorMarkdown(ed, tighten);
    const loss = checkContentPreserved(storedBody, md);
    if (loss.missingCount === 0) {
      setSafetyWarning(null);
      return md;
    }
    const message =
      `Sincronización bloqueada: se perderían ${loss.missingCount} línea(s). ` +
      "Use vista Markdown.";
    setSafetyWarning(message);
    reportContentLossBlocked(message, loss.missing);
    return null;
  };

  const syncExportedMarkdown = (md: string) => {
    lastSyncedFromEditor.current = md;
    lastLoadedBody.current = md;
    bodyRef.current = md;
  };

  const flushPending = () => {
    if (previewOnlyRef.current) return;
    const ed = editorRef.current;
    if (!ed) return;
    cancelPendingSync();
    if (suppressUpdate.current) return;
    if (!isManualEditorDirty()) return;

    const md = exportIfContentSafe(ed, bodyRef.current, false);
    if (md === null) return;

    syncExportedMarkdown(md);
    clearManualEditorDirty();
    onBodyChangeRef.current(md);
  };

  const applyQuizInsertRef = useRef<(quizId: string, pos?: number) => boolean>(() => false);

  const applyQuizInsert = (quizId: string, pos?: number): boolean => {
    if (previewOnlyRef.current) return false;
    const ed = editorRef.current;
    if (!ed) return false;

    const id = quizId.trim();
    if (!id) return false;

    cancelPendingSync();
    const insertPos = pos ?? lastSelectionPos.current ?? ed.state.selection.from;
    const liveMd = exportEditorMarkdown(ed, true);
    const nextMd = insertQuizIntoEditorMarkdown(ed, id, insertPos, liveMd);
    if (!nextMd || !nextMd.includes(quizMarkerComment(id))) return false;

    suppressUpdate.current = true;
    lastLoadedBody.current = nextMd;
    lastSyncedFromEditor.current = nextMd;
    bodyRef.current = nextMd;
    clearManualEditorDirty();
    ed.commands.setContent(markdownToEditorHtml(nextMd), { emitUpdate: false });
    requestAnimationFrame(() => {
      suppressUpdate.current = false;
    });
    onBodyChangeRef.current(nextMd);
    return true;
  };

  applyQuizInsertRef.current = applyQuizInsert;

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

    try {
      const result = await resolveReference(reference);
      if (!result) {
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

        setBiblePopup({
          kind,
          reference,
          h3Pos,
          loading: false,
          error: bibleStatus?.error ?? `No se encontró la referencia: ${reference}`,
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
        CgvTable,
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
      content: markdownToEditorHtml(sanitizeCgvMarkdown(body || "")),
      onCreate: ({ editor: ed }) => {
        tightenPassageLayoutInEditor(ed);
      },
      editorProps: {
        attributes: { class: "manual-prosemirror" },
        handleDOMEvents: {
          blur: () => {
            const ed = editorRef.current;
            if (ed) {
              lastSelectionPos.current = ed.state.selection.from;
            }
          }
        },
        handleClick: (_view, pos, event) => {
          const ed = editorRef.current;
          if (ed) {
            lastSelectionPos.current = pos;
          }

          if (!ed) return false;

          if (underlinePaintModeRef.current && !previewOnlyRef.current) {
            if (underlineWordAtDocPos(ed, pos)) {
              event.preventDefault();
              markManualEditorDirty();
              scheduleSyncToMarkdown();
              return true;
            }
            return false;
          }

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
          if (event.key === "Escape" && underlinePaintModeRef.current) {
            event.preventDefault();
            setUnderlinePaintModeEnabled(false);
            return true;
          }
          if (
            (event.metaKey || event.ctrlKey) &&
            event.shiftKey &&
            !event.altKey &&
            event.key.toLowerCase() === "u"
          ) {
            event.preventDefault();
            toggleUnderlinePaintMode();
            return true;
          }
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
            const ed = editorRef.current;
            if (ed) {
              if (handleManualEnterKey(ed)) {
                event.preventDefault();
                markManualEditorDirty();
                scheduleSyncToMarkdown();
                return true;
              }
              window.setTimeout(() => ensureScriptureParagraphAfterH3AtCursor(ed), 0);
            }
          }
          return false;
        }
      },
      onUpdate: () => {
        if (previewOnlyRef.current) return;
        if (suppressUpdate.current) return;
        scheduleSyncToMarkdown();
      }
    },
    []
  );

  editorRef.current = editor;

  useEffect(() => {
    if (!editor) return;
    const el = editor.view.dom;
    el.classList.toggle("manual-prosemirror--underline-paint", underlinePaintMode);
    return () => el.classList.remove("manual-prosemirror--underline-paint");
  }, [editor, underlinePaintMode]);

  useEffect(() => {
    if (!editor || !scrollRef.current) return;

    const root = scrollRef.current;

    const onEditorClick = (event: MouseEvent) => {
      if (!isActiveRef.current) return;
      if (underlinePaintModeRef.current) return;

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
      if (!isActiveRef.current) return;
      const run = () => {
        if (editor.isDestroyed) return;
        editor.view.dispatch(editor.state.tr.setMeta(inlineBibleRefsPluginKey, true));
      };
      if (typeof requestIdleCallback === "function") {
        requestIdleCallback(run, { timeout: 2_500 });
      } else {
        window.setTimeout(run, 0);
      }
    };

    window.addEventListener(BIBLE_INDEX_UPDATED_EVENT, refreshInlineRefs);
    window.addEventListener("cgv-bible-library-changed", refreshInlineRefs);

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

    const onSelection = () => {
      if (isActiveRef.current) {
        lastSelectionPos.current = editor.state.selection.from;
      }
    };

    editor.on("selectionUpdate", onSelection);
    return () => {
      editor.off("selectionUpdate", onSelection);
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
    const exportBodyForRequest = (): { body: string; blocked: boolean; changed: boolean } => {
      const ed = editorRef.current;
      if (!ed) return { body: bodyRef.current, blocked: false, changed: false };

      cancelPendingSync();
      if (!isManualEditorDirty()) {
        return { body: bodyRef.current, blocked: false, changed: false };
      }

      const md = exportIfContentSafe(ed, bodyRef.current, false);
      if (md === null) return { body: bodyRef.current, blocked: true, changed: false };
      syncExportedMarkdown(md);
      clearManualEditorDirty();
      return { body: md, blocked: false, changed: true };
    };

    const onExport = () => {
      window.dispatchEvent(
        new CustomEvent("cgv-manual-body-export", {
          detail: exportBodyForRequest()
        })
      );
    };

    const onInsertQuiz = (event: Event) => {
      const quizId = String((event as CustomEvent<{ quizId: string }>).detail?.quizId || "").trim();
      if (!quizId) {
        window.dispatchEvent(new CustomEvent("cgv-insert-quiz-result", { detail: { ok: false } }));
        return;
      }

      const ok = applyQuizInsertRef.current(quizId);
      window.dispatchEvent(new CustomEvent("cgv-insert-quiz-result", { detail: { ok } }));
    };

    window.addEventListener("cgv-manual-flush-sync", onFlush);
    window.addEventListener("cgv-manual-cancel-sync", onCancel);
    window.addEventListener("cgv-manual-body-export-request", onExport);
    window.addEventListener("cgv-insert-quiz", onInsertQuiz);
    return () => {
      window.removeEventListener("cgv-manual-flush-sync", onFlush);
      window.removeEventListener("cgv-manual-cancel-sync", onCancel);
      window.removeEventListener("cgv-manual-body-export-request", onExport);
      window.removeEventListener("cgv-insert-quiz", onInsertQuiz);
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
    editor.commands.setContent(
      markdownToEditorHtml(sanitizeCgvMarkdown(body)),
      { emitUpdate: false }
    );
    tightenPassageLayoutInEditor(editor);
    bodyRef.current = body;
    warnRoundTripLoss(body);
    requestAnimationFrame(() => {
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

    if (!isActiveRef.current) {
      bodyRef.current = body;
      return;
    }

    if (isManualEditorDirty()) {
      return;
    }

    cancelPendingSync();
    suppressUpdate.current = true;
    lastLoadedBody.current = body;
    lastSyncedFromEditor.current = body;
    clearManualEditorDirty();
    bodyRef.current = body;
    editor.commands.setContent(markdownToEditorHtml(sanitizeCgvMarkdown(body)), {
      emitUpdate: false
    });
    tightenPassageLayoutInEditor(editor);
    warnRoundTripLoss(body);
    requestAnimationFrame(() => {
      suppressUpdate.current = false;
    });
  }, [body, editor]);

  useEffect(() => {
    if (!editor) return;

    const saveIfActive = () => {
      if (!isActiveRef.current) return;

      const place = manualSavePlace(editor, scrollRef.current);
      cancelPendingSync();

      let bodyMd = bodyRef.current;
      if (!previewOnlyRef.current && isManualEditorDirty()) {
        const exported = exportIfContentSafe(editor, bodyRef.current, false);
        if (exported === null) {
          blockPendingViewChange();
          return;
        }
        bodyMd = exported;
        syncExportedMarkdown(bodyMd);
        clearManualEditorDirty();
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
          tightenPassageLayoutInEditor(editor);
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
    editor.setEditable(isActive && !previewOnly);
  }, [editor, isActive, previewOnly]);

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
          applyReferenceHeading(editor);
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

    const handler = (event: Event) => {
      if (!isActive) return;

      const detail = (event as CustomEvent<OutlineNavigateRequest>).detail;
      const pos = findManualHeadingPos(editor.state.doc, detail.level, detail.ordinal);
      if (pos == null) return;

      editor.commands.setTextSelection(pos + 1);
      editor.commands.focus();
      requestAnimationFrame(() => scrollManualCursorIntoView(editor, scrollRef.current));
    };

    window.addEventListener("cgv-outline-navigate", handler);
    return () => window.removeEventListener("cgv-outline-navigate", handler);
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
          tightenPassageLayoutInEditor(editor);
          const md = editorDocToMarkdown(editor);
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
          tightenPassageLayoutInEditor(editor);
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
    if (previewOnly) {
      setBiblePopup(null);
      return;
    }
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

  return (
    <div
      className={`manual-editor ${writingMode ? "manual-editor--writing" : ""} ${
        previewOnly ? "manual-editor--preview-only" : ""
      } ${bibleIndex || bibleStatus?.loaded ? "manual-editor--bible-ready" : ""}`}
    >
      {!writingMode && (
        <ManualToolbar
          editor={editor}
          underlinePaintMode={underlinePaintMode}
          onToggleUnderlinePaintMode={toggleUnderlinePaintMode}
        />
      )}

      {safetyWarning && (
        <div className="manual-safety-banner" role="alert">
          {safetyWarning}
        </div>
      )}

      {writingMode && (
        <ManualStyleChip editor={editor} className="manual-style-indicator--writing" />
      )}

      <div className="manual-page-scroll" ref={scrollRef}>
        <div className="manual-page">
          <EditorContent editor={editor} />
        </div>
      </div>

      {writingMode && (
        <p className="writing-mode-keys">
          {underlinePaintMode
            ? "Espacio en blanco — clic en palabras · Escape salir · ⌘S guardar"
            : "Escape · ⌘⇧F salir · ⌘/ vista · ⌘S guardar"}
        </p>
      )}

      <BibleReferencePopup
        open={!!biblePopup}
        reference={biblePopup?.reference ?? ""}
        version={bibleStatus?.version ?? "NBLA"}
        loading={biblePopup?.loading ?? false}
        error={biblePopup?.error ?? null}
        result={biblePopup?.result ?? null}
        showUseText={biblePopup?.kind === "h3" && !previewOnly}
        onClose={() => setBiblePopup(null)}
        onUseText={handleUseBibleText}
      />
    </div>
  );
}

export const ManualEditor = memo(ManualEditorInner, (prev, next) =>
  prev.body === next.body &&
  prev.reloadKey === next.reloadKey &&
  prev.isActive === next.isActive &&
  prev.writingMode === next.writingMode &&
  prev.previewOnly === next.previewOnly
);
