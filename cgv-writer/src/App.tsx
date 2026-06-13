import { useCallback, useEffect, useState } from "react";
import { EmptyWelcome } from "./components/EmptyWelcome";
import { FileMenu } from "./components/FileMenu";
import { ManualEditor } from "./components/ManualEditor";
import { MarkdownEditor } from "./components/MarkdownEditor";
import { SearchReplaceBar } from "./components/SearchReplaceBar";
import { PresentationPanel } from "./components/PresentationPanel";
import { LibrarySettingsPanel } from "./components/LibrarySettingsPanel";
import { BibleProvider } from "./lib/bible-context";
import { analyzeDocument } from "./lib/analyze";
import { confirmAction, deferNativeDialog } from "./lib/confirm";
import { dispatchSearchOpen } from "./lib/search-bridge";
import {
  loadStarterTemplate,
  openManualFile,
  readManualByPath,
  saveManualFile
} from "./lib/files";
import { splitYamlBody, joinYamlBody, normalizeCgvMarkdown } from "./lib/markdown-html";
import { clearEditorPlaces } from "./lib/editor-position-bridge";
import {
  ANALYSIS_DEBOUNCE_MS,
  cancelManualEditorSync,
  clearViewHandoff,
  dispatchBeforeViewChange,
  exportManualBodyFromEditor,
  flushManualEditorSync,
  OUTLINE_DISPLAY_CAP
} from "./lib/manual-sync";
import { correctManualStyle } from "./lib/style-corrector";
import { clearLastOpenedPath, getLastOpenedPath } from "./lib/recent-files";
import {
  loadWritingModePreference,
  saveWritingModePreference
} from "./lib/writing-mode";
import "./App.css";

type ViewMode = "manual" | "markdown";

export default function App() {
  const [content, setContent] = useState("");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState("Listo");
  const [viewMode, setViewMode] = useState<ViewMode>("manual");
  const [frontMatter, setFrontMatter] = useState("");
  const [body, setBody] = useState("");
  const [writingMode, setWritingMode] = useState(loadWritingModePreference);
  const [analysis, setAnalysis] = useState(() => analyzeDocument(""));
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchShowReplace, setSearchShowReplace] = useState(false);
  const [styleCorrectBusy, setStyleCorrectBusy] = useState(false);
  const [styleCorrectMessage, setStyleCorrectMessage] = useState<string | null>(null);

  const setWritingModeEnabled = useCallback((enabled: boolean) => {
    setWritingMode(enabled);
    saveWritingModePreference(enabled);
  }, []);

  const toggleWritingMode = useCallback(() => {
    setWritingModeEnabled(!writingMode);
  }, [setWritingModeEnabled, writingMode]);

  const cycleViewMode = useCallback(() => {
    dispatchBeforeViewChange();
    setViewMode(current => (current === "manual" ? "markdown" : "manual"));
  }, []);

  const switchViewMode = useCallback((mode: ViewMode) => {
    dispatchBeforeViewChange();
    setViewMode(mode);
  }, []);

  const applyContent = useCallback((text: string) => {
    const split = splitYamlBody(text);
    const body = normalizeCgvMarkdown(split.body);
    setFrontMatter(split.frontMatter);
    setBody(body);
    setContent(joinYamlBody(split.frontMatter, body));
    clearEditorPlaces();
    clearViewHandoff();
  }, []);

  /** In-editor sync (typing / view handoff) — preserve cursor bridge. */
  const syncContentFromEditor = useCallback((text: string) => {
    const split = splitYamlBody(text);
    const body = normalizeCgvMarkdown(split.body);
    setFrontMatter(split.frontMatter);
    setBody(body);
    setContent(joinYamlBody(split.frontMatter, body));
  }, []);

  const updateBody = useCallback(
    (nextBody: string) => {
      setBody(nextBody);
      setContent(joinYamlBody(frontMatter, nextBody));
      setDirty(true);
    },
    [frontMatter]
  );

  const updateFullContent = useCallback((text: string) => {
    applyContent(text);
    setDirty(true);
  }, [applyContent]);

  const loadFromContent = useCallback(
    (text: string) => {
      applyContent(text);
    },
    [applyContent]
  );

  const handleChangeMarkdown = useCallback(
    (next: string) => {
      syncContentFromEditor(next);
      setDirty(true);
    },
    [syncContentFromEditor]
  );

  const handleNew = useCallback(async () => {
    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si crea un documento nuevo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Nuevo documento", okLabel: "Descartar cambios" }
      );
      if (!proceed) return;
    }

    cancelManualEditorSync();
    loadFromContent("");
    setFilePath(null);
    setDirty(false);
    setStatus("Nuevo documento — ⌘S para guardar");
  }, [dirty, loadFromContent]);

  const handleOpen = useCallback(async () => {
    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si abre otro archivo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Abrir otro archivo", okLabel: "Abrir sin guardar" }
      );
      if (!proceed) return;
    }

    cancelManualEditorSync();
    await deferNativeDialog();

    try {
      const opened = await openManualFile();
      if (!opened) return;
      loadFromContent(opened.content);
      setFilePath(opened.path);
      setDirty(false);
      setStatus(`Abierto: ${opened.path}`);
    } catch (error) {
      setStatus(`Error al abrir: ${String(error)}`);
    }
  }, [dirty, loadFromContent]);

  const handleSave = useCallback(async () => {
    try {
      let toSave = content;
      if (viewMode === "manual") {
        flushManualEditorSync();
        const bodyMd = await exportManualBodyFromEditor();
        toSave = joinYamlBody(frontMatter, bodyMd);
        setBody(bodyMd);
        setContent(toSave);
      }

      const saved = await saveManualFile(filePath, toSave);
      if (!saved) return;
      setFilePath(saved);
      setDirty(false);
      setStatus(`Guardado: ${saved}`);
    } catch (error) {
      setStatus(`Error al guardar: ${String(error)}`);
    }
  }, [content, filePath, frontMatter, viewMode]);

  const openPath = useCallback(
    async (path: string) => {
      const text = await readManualByPath(path);
      loadFromContent(text);
      setFilePath(path);
      setDirty(false);
      setStatus(`Abierto: ${path}`);
    },
    [loadFromContent]
  );

  const handleReopenLast = useCallback(async () => {
    const last = getLastOpenedPath();
    if (!last) return;

    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si abre el último archivo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Reabrir último", okLabel: "Reabrir sin guardar" }
      );
      if (!proceed) return;
    }

    cancelManualEditorSync();

    try {
      await openPath(last);
    } catch (error) {
      clearLastOpenedPath();
      setStatus(`No se pudo reabrir: ${String(error)}`);
    }
  }, [dirty, openPath]);

  const handleStarter = useCallback(async () => {
    const proceed = await confirmAction(
      "El documento actual se reemplazará por la plantilla.\n\nGuarde primero (⌘S) si necesita conservar su trabajo.",
      { title: "Nueva plantilla", okLabel: "Reemplazar" }
    );
    if (!proceed) {
      setStatus("Plantilla cancelada");
      return;
    }

    cancelManualEditorSync();
    const text = await loadStarterTemplate();
    loadFromContent(text);
    setFilePath(null);
    setDirty(true);
    setStatus("Plantilla nueva (sin guardar)");
  }, [loadFromContent]);

  const hasCorrectableContent = Boolean(body.trim() || splitYamlBody(content).body.trim());

  const handleStyleCorrect = useCallback(async () => {
    if (styleCorrectBusy) return;

    setStyleCorrectBusy(true);
    setStyleCorrectMessage(null);
    setStatus("Corrigiendo estilo CGV…");

    try {
      let sourceBody = body.trim() ? body : splitYamlBody(content).body;

      if (viewMode === "manual") {
        flushManualEditorSync();
        const exported = await exportManualBodyFromEditor();
        if (exported.trim()) {
          sourceBody = exported;
        }
      }

      if (!sourceBody.trim()) {
        const message = "No hay contenido para corregir.";
        setStyleCorrectMessage(message);
        setStatus(message);
        return;
      }

      const result = await correctManualStyle(sourceBody);
      updateBody(result.body);
      setDirty(true);

      if (!result.changed) {
        const message = result.warnings.length
          ? `Sin cambios de estilo. ${result.warnings[0]}`
          : "Sin cambios de estilo — el documento ya cumple las reglas.";
        setStyleCorrectMessage(message);
        setStatus(message);
        return;
      }

      const parts: string[] = [];
      if (result.stats.scriptureUpdated) {
        parts.push(`${result.stats.scriptureUpdated} versículo(s) NBLA`);
      }
      if (result.stats.anchorsSet) {
        parts.push(`${result.stats.anchorsSet} ancla(s) H4`);
      }
      if (result.stats.linesPromotedToH5) {
        parts.push(`${result.stats.linesPromotedToH5} línea(s) H5`);
      }
      if (result.stats.referencesDemoted) {
        parts.push(`${result.stats.referencesDemoted} referencia(s) reubicada(s)`);
      }

      const summary = parts.length ? parts.join(" · ") : "estructura normalizada";
      const warning = result.warnings.length ? ` (${result.warnings.length} aviso(s))` : "";
      const message = `Estilo corregido: ${summary}${warning}. Revise y guarde (⌘S).`;
      setStyleCorrectMessage(message);
      setStatus(message);
    } catch (error) {
      const message = `Error al corregir estilo: ${String(error)}`;
      setStyleCorrectMessage(message);
      setStatus(message);
    } finally {
      setStyleCorrectBusy(false);
    }
  }, [body, content, styleCorrectBusy, updateBody, viewMode]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest(".search-replace-bar")) {
        return;
      }

      const mod = event.metaKey || event.ctrlKey;

      if (event.key === "Escape") {
        if (searchOpen) {
          event.preventDefault();
          setSearchOpen(false);
          setSearchShowReplace(false);
          return;
        }
        if (writingMode) {
          event.preventDefault();
          setWritingModeEnabled(false);
        }
        return;
      }

      if (mod && event.shiftKey && event.key.toLowerCase() === "f") {
        if (viewMode === "manual" || viewMode === "markdown") {
          event.preventDefault();
          toggleWritingMode();
        }
        return;
      }

      if (mod && event.altKey && event.key.toLowerCase() === "f") {
        if (viewMode === "manual" || viewMode === "markdown") {
          event.preventDefault();
          setSearchOpen(true);
          setSearchShowReplace(true);
          dispatchSearchOpen(true, window.getSelection()?.toString().trim() ?? "");
        }
        return;
      }

      if (mod && event.key.toLowerCase() === "f") {
        if (viewMode === "manual" || viewMode === "markdown") {
          event.preventDefault();
          setSearchOpen(true);
          setSearchShowReplace(false);
          dispatchSearchOpen(false, window.getSelection()?.toString().trim() ?? "");
        }
        return;
      }

      if (!mod || event.altKey) return;

      if (event.key === "/" || event.code === "Slash") {
        event.preventDefault();
        cycleViewMode();
        return;
      }

      if (event.key === "s") {
        event.preventDefault();
        void handleSave();
        return;
      }
      if (event.key === "o") {
        event.preventDefault();
        void handleOpen();
        return;
      }
      if (event.key === "n") {
        event.preventDefault();
        void handleNew();
        return;
      }

      const styleKey = event.key >= "1" && event.key <= "7" ? Number(event.key) : 0;
      if (!styleKey) return;

      if (viewMode === "manual" || viewMode === "markdown") {
        event.preventDefault();
        window.dispatchEvent(
          new CustomEvent("cgv-apply-style", { detail: { styleKey, viewMode } })
        );
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cycleViewMode, handleNew, handleOpen, handleSave, searchOpen, setWritingModeEnabled, toggleWritingMode, viewMode, writingMode]);

  useEffect(() => {
    let cancelled = false;
    const unsubs: (() => void)[] = [];

    void (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        if (cancelled) return;

        const bind = async (event: string, handler: () => void) => {
          unsubs.push(await listen(event, handler));
        };

        await bind("menu-file_new", () => void handleNew());
        await bind("menu-file_open", () => void handleOpen());
        await bind("menu-file_save", () => void handleSave());
        await bind("menu-file_reopen", () => void handleReopenLast());
        await bind("menu-file_template", () => void handleStarter());
      } catch {
        /* web-only dev */
      }
    })();

    return () => {
      cancelled = true;
      unsubs.forEach(unsub => unsub());
    };
  }, [handleNew, handleOpen, handleReopenLast, handleSave, handleStarter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAnalysis(analyzeDocument(content));
    }, ANALYSIS_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [content]);

  useEffect(() => {
    loadFromContent("");
    setFilePath(null);
    setDirty(false);
    setStatus("Sin archivo — ⌘O para abrir o escriba aquí");
  }, [loadFromContent]);

  const title = filePath
    ? `${dirty ? "• " : ""}${filePath.split(/[/\\]/).pop()}`
    : dirty
      ? "• Sin título"
      : "Sin archivo";

  const lastOpenedPath = getLastOpenedPath();
  const outlineVisible = analysis.outline.slice(0, OUTLINE_DISPLAY_CAP);
  const outlineHiddenCount = Math.max(0, analysis.outline.length - OUTLINE_DISPLAY_CAP);

  const focusWriting =
    writingMode && (viewMode === "manual" || viewMode === "markdown");
  const showWelcome = !filePath && !body.trim() && !focusWriting;

  return (
    <BibleProvider>
    <div className={`app ${focusWriting ? "writing-mode" : ""}`}>
      {!focusWriting && (
        <header className="toolbar">
          <FileMenu
            lastOpenedPath={lastOpenedPath}
            onNew={() => void handleNew()}
            onOpen={() => void handleOpen()}
            onSave={() => void handleSave()}
            onReopenLast={() => void handleReopenLast()}
            onTemplate={() => void handleStarter()}
          />
          <div className="brand">
            <span className="brand-name">CGV Writer</span>
            <span className="brand-file">{title}</span>
          </div>
          <div className="view-tabs">
            <button
              type="button"
              className={viewMode === "manual" ? "active" : undefined}
              onClick={() => switchViewMode("manual")}
              title="⌘/"
            >
              Manual
            </button>
            <button
              type="button"
              className={viewMode === "markdown" ? "active" : undefined}
              onClick={() => switchViewMode("markdown")}
              title="⌘/"
            >
              Markdown
            </button>
          </div>
          <div className="toolbar-actions">
            {viewMode === "manual" && (
              <button
                type="button"
                className="writing-mode-toggle"
                onClick={toggleWritingMode}
                title="Modo enfoque (⌘⇧F)"
              >
                Enfoque
              </button>
            )}
            <button type="button" className="primary" onClick={() => void handleSave()} title="⌘S">
              Guardar
            </button>
          </div>
        </header>
      )}

      {!focusWriting && <p className="status-bar">{status}</p>}

      <main className="workspace">
        {focusWriting && (
          <div className="focus-mode-badge" aria-live="polite">
            {viewMode === "manual" ? "Vista previa" : "Markdown"}
            <span className="focus-mode-badge-hint">⌘/ cambiar · Escape salir</span>
          </div>
        )}
        <section className="editor-pane">
          {(viewMode === "manual" || viewMode === "markdown") && (
            <SearchReplaceBar
              visible={searchOpen}
              showReplace={searchShowReplace}
              onShowReplaceChange={setSearchShowReplace}
              onClose={() => {
                setSearchOpen(false);
                setSearchShowReplace(false);
              }}
            />
          )}
          {showWelcome && (
            <EmptyWelcome
              lastOpenedPath={lastOpenedPath}
              onOpen={() => void handleOpen()}
              onNew={() => void handleNew()}
              onReopenLast={() => void handleReopenLast()}
              onTemplate={() => void handleStarter()}
            />
          )}
          <div className={`editor-pane-layer ${viewMode === "manual" ? "active" : ""}`}>
            <ManualEditor
              body={body}
              onBodyChange={updateBody}
              reloadKey={filePath ?? "untitled"}
              isActive={viewMode === "manual"}
              writingMode={focusWriting && viewMode === "manual"}
            />
          </div>
          <div className={`editor-pane-layer ${viewMode === "markdown" ? "active" : ""}`}>
            <MarkdownEditor
              value={content}
              onChange={handleChangeMarkdown}
              reloadKey={filePath ?? "untitled"}
              isActive={viewMode === "markdown"}
            />
          </div>
        </section>

        {!focusWriting && (
          <aside className="sidebar">
          <section className="panel">
            <h2>Esquema</h2>
            <p className="panel-meta">
              {analysis.outline.length
                ? `${analysis.outline.length} bloques`
                : "—"}
            </p>
            <ol className="outline-list">
              {outlineVisible.map(slide => (
                <li
                  key={slide.index}
                  className={
                    slide.isQuiz
                      ? "quiz"
                      : slide.isIllustration
                        ? "illustration"
                        : undefined
                  }
                >
                  {slide.index}. {slide.title}
                </li>
              ))}
              {outlineHiddenCount > 0 && (
                <li className="outline-truncated">
                  … {outlineHiddenCount} bloques más (use Markdown para buscar)
                </li>
              )}
            </ol>
          </section>

          <section className="panel panel-presentation">
            <h2>Presenter</h2>
            <PresentationPanel content={content} onContentChange={updateFullContent} variant="sidebar" />
          </section>

          <LibrarySettingsPanel />

          <section className="panel">
            <h2>Estilo CGV</h2>
            <p className="panel-meta">
              Referencias H3 + NBLA, anclas H4, comentarios H5.
            </p>
            <button
              type="button"
              className="style-correct-btn"
              disabled={styleCorrectBusy || !hasCorrectableContent}
              onClick={() => void handleStyleCorrect()}
            >
              {styleCorrectBusy ? "Corrigiendo…" : "Corregir estilo"}
            </button>
            {styleCorrectMessage && (
              <p className="style-correct-result" role="status">
                {styleCorrectMessage}
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Revisión</h2>
            <ul className="check-list">
              {analysis.checks.map((check, i) => (
                <li key={i} className={check.level}>
                  {check.text}
                </li>
              ))}
            </ul>
          </section>

          <section className="panel panel-note">
            <h2>Notas</h2>
            <p>
              <strong>Archivo</strong> — Nuevo, Abrir, Guardar, plantilla. <strong>Enfoque</strong> — ⌘⇧F.
              Buscar — ⌘F, reemplazar — ⌘⌥F. Atajos: ⌘/ Manual ↔ Markdown, ⌘N/O/S, ⌘1–7 estilos.
              Marcadores de Presenter — panel <strong>Presenter</strong> (derecha).
            </p>
          </section>
        </aside>
        )}
      </main>
    </div>
    </BibleProvider>
  );
}
