import { useCallback, useEffect, useRef, useState } from "react";
import { EmptyWelcome } from "./components/EmptyWelcome";
import { FileMenu } from "./components/FileMenu";
import { SharedDocumentEditor } from "./components/SharedDocumentEditor";
import { SearchReplaceBar } from "./components/SearchReplaceBar";
import { PresentationPanel } from "./components/PresentationPanel";
import { LibrarySettingsPanel } from "./components/LibrarySettingsPanel";
import { BibleProvider } from "./lib/bible-context";
import { analyzeDocument, buildHeadingOutlineTree } from "./lib/analyze";
import { HeadingOutlineTree } from "./components/HeadingOutlineTree";
import { confirmAction, deferNativeDialog } from "./lib/confirm";
import { dispatchSearchOpen } from "./lib/search-bridge";
import {
  duplicateManualFile,
  loadStarterTemplate,
  openManualFile,
  readManualByPath,
  saveManualFile,
  takeOpenedManualPaths
} from "./lib/files";
import { splitYamlBody, joinYamlBody } from "./lib/markdown-html";
import { clearEditorPlaces } from "./lib/editor-position-bridge";
import {
  ANALYSIS_DEBOUNCE_MS,
  exportMarkdownFromEditor,
  flushMarkdownEditorSync,
} from "./lib/manual-sync";
import { clearLastOpenedPath, getLastOpenedPath } from "./lib/recent-files";
import {
  loadWritingModePreference,
  saveWritingModePreference
} from "./lib/writing-mode";
import {
  applyTheme,
  loadThemePreference,
  saveThemePreference,
  toggleTheme,
  type ThemeMode
} from "./lib/theme";
import "./App.css";

type ViewMode = "manual" | "markdown";

export default function App() {
  const [content, setContent] = useState("");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [, setStatus] = useState("Listo");
  const [viewMode, setViewMode] = useState<ViewMode>("manual");
  const [frontMatter, setFrontMatter] = useState("");
  const [body, setBody] = useState("");
  const [writingMode, setWritingMode] = useState(loadWritingModePreference);
  const [theme, setTheme] = useState<ThemeMode>(() => loadThemePreference());
  const [analysis, setAnalysis] = useState(() => analyzeDocument(""));
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchShowReplace, setSearchShowReplace] = useState(false);
  const [documentSession, setDocumentSession] = useState(0);
  const [welcomeOverlay, setWelcomeOverlay] = useState<"startup" | null>("startup");
  const [saving, setSaving] = useState(false);
  const dirtyRef = useRef(false);
  const quitInProgressRef = useRef(false);
  const openRequestRef = useRef(0);
  const externalOpenSeenRef = useRef(false);
  const startupCompleteRef = useRef(false);

  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);

  useEffect(() => {
    applyTheme(theme);
    saveThemePreference(theme);
  }, [theme]);

  const setWritingModeEnabled = useCallback((enabled: boolean) => {
    setWritingMode(enabled);
    saveWritingModePreference(enabled);
  }, []);

  const toggleWritingMode = useCallback(() => {
    setWritingModeEnabled(!writingMode);
  }, [setWritingModeEnabled, writingMode]);

  const toggleColorTheme = useCallback(() => {
    setTheme(current => toggleTheme(current));
  }, []);

  const applyContent = useCallback((text: string) => {
    const split = splitYamlBody(text);
    setFrontMatter(split.frontMatter);
    setBody(split.body);
    setContent(text);
    setDocumentSession(session => session + 1);
    clearEditorPlaces();
    if (text.trim()) {
      setWelcomeOverlay(null);
    }
  }, []);

  const dismissWelcome = useCallback(() => {
    setWelcomeOverlay(null);
  }, []);

  const dismissWelcomeForNativeDialog = useCallback(async () => {
    setWelcomeOverlay(null);
    await deferNativeDialog();
  }, []);

  const markDocumentDirty = useCallback(() => {
    if (dirtyRef.current) return;
    dirtyRef.current = true;
    setDirty(true);
  }, []);

  const attemptViewSwitch = useCallback(
    async (next: ViewMode) => {
      if (next === viewMode) return;
      setViewMode(next);
    },
    [viewMode]
  );

  const cycleViewMode = useCallback(async () => {
    const next: ViewMode = viewMode === "manual" ? "markdown" : "manual";
    await attemptViewSwitch(next);
  }, [attemptViewSwitch, viewMode]);

  const switchViewMode = useCallback(
    async (mode: ViewMode) => {
      await attemptViewSwitch(mode);
    },
    [attemptViewSwitch]
  );

  /** Live document from the single shared editor. */
  const resolveLiveContent = useCallback(async (): Promise<string> => {
    flushMarkdownEditorSync();
    const exported = await exportMarkdownFromEditor();
    return exported.trim() ? exported : content;
  }, [content]);

  const updateFullContent = useCallback((text: string) => {
    applyContent(text);
    setDirty(true);
  }, [applyContent]);

  /** Append markdown to the end of the live document body (flushes Manual editor first). */
  const appendToBody = useCallback(
    async (chunk: string) => {
      const exported = await resolveLiveContent();
      const split = splitYamlBody(exported);
      let currentBody = split.body;

      const trimmedChunk = chunk.trim();
      const nextBody = trimmedChunk
        ? currentBody.trim()
          ? `${currentBody.trim()}\n\n${trimmedChunk}`
          : trimmedChunk
        : currentBody.trim()
          ? `${currentBody.trim()}\n\n`
          : "";

      updateFullContent(joinYamlBody(frontMatter, nextBody));

      const quizMatch = trimmedChunk.match(/^<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->$/);
      if (quizMatch) {
        setStatus(`Marcador @quiz añadido: ${quizMatch[1]}`);
      }
    },
    [frontMatter, resolveLiveContent, updateFullContent]
  );

  const insertQuizAtCursor = useCallback(
    async (quizId: string) => {
      const id = quizId.trim();
      if (!id) return;
      void appendToBody(`<!-- @quiz ${id} -->`);
    },
    [appendToBody]
  );

  const loadFromContent = useCallback(
    (text: string) => {
      applyContent(text);
    },
    [applyContent]
  );

  const handleChangeMarkdown = useCallback((next: string) => {
    const split = splitYamlBody(next);
    setFrontMatter(split.frontMatter);
    setBody(split.body);
    setContent(next);
    setDirty(true);
  }, []);

  const handleNew = useCallback(async () => {
    await dismissWelcomeForNativeDialog();

    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si crea un documento nuevo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Nuevo documento", okLabel: "Descartar cambios" }
      );
      if (!proceed) return;
    }

    loadFromContent("");
    setFilePath(null);
    setDirty(false);
    setStatus("Nuevo documento — ⌘S para guardar");
  }, [dirty, dismissWelcomeForNativeDialog, loadFromContent]);

  const handleOpen = useCallback(async () => {
    await dismissWelcomeForNativeDialog();

    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si abre otro archivo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Abrir otro archivo", okLabel: "Abrir sin guardar" }
      );
      if (!proceed) return;
    }

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
  }, [dirty, dismissWelcomeForNativeDialog, loadFromContent]);

  const handleSave = useCallback(async () => {
    if (saving) return;

    setSaving(true);
    setStatus("Guardando…");

    try {
      const exported = await resolveLiveContent();
      const split = splitYamlBody(exported);
      const toSave = exported;
      setFrontMatter(split.frontMatter);
      setBody(split.body);
      setContent(toSave);

      const saved = await saveManualFile(filePath, toSave);
      if (!saved) {
        setStatus("Guardado cancelado");
        return;
      }
      setFilePath(saved);
      setDirty(false);
      setStatus(`Guardado: ${saved.split(/[/\\]/).pop()}`);
    } catch (error) {
      setStatus(`Error al guardar: ${String(error)}`);
    } finally {
      setSaving(false);
    }
  }, [filePath, resolveLiveContent, saving]);

  const handleDuplicate = useCallback(async () => {
    if (saving) return;

    await dismissWelcomeForNativeDialog();
    await deferNativeDialog();
    setStatus("Duplicando…");

    try {
      const exported = await resolveLiveContent();
      const duplicated = await duplicateManualFile(filePath, exported);
      if (!duplicated) {
        setStatus("Duplicado cancelado");
        return;
      }
      setStatus(`Copia creada: ${duplicated.split(/[/\\]/).pop()}`);
    } catch (error) {
      setStatus(`Error al duplicar: ${String(error)}`);
    }
  }, [dismissWelcomeForNativeDialog, filePath, resolveLiveContent, saving]);

  const openPath = useCallback(
    async (path: string) => {
      const requestId = openRequestRef.current + 1;
      openRequestRef.current = requestId;
      const text = await readManualByPath(path);
      if (requestId !== openRequestRef.current) return false;
      loadFromContent(text);
      setFilePath(path);
      dirtyRef.current = false;
      setDirty(false);
      setStatus(`Abierto: ${path}`);
      return true;
    },
    [loadFromContent]
  );

  const handleExternalOpenPath = useCallback(
    async (path: string) => {
      if (!path) return;

      await dismissWelcomeForNativeDialog();

      if (dirtyRef.current) {
        const proceed = await confirmAction(
          "Tiene cambios sin guardar. Si abre este archivo, perderá esos cambios.\n\n¿Continuar sin guardar?",
          { title: "Abrir archivo", okLabel: "Abrir sin guardar" }
        );
        if (!proceed) return;
      }

      try {
        const opened = await openPath(path);
        if (opened) dismissWelcome();
      } catch (error) {
        setStatus(`Error al abrir: ${String(error)}`);
      }
    },
    [dismissWelcome, dismissWelcomeForNativeDialog, openPath]
  );

  const handleReopenLast = useCallback(async () => {
    const last = getLastOpenedPath();
    if (!last) return;

    await dismissWelcomeForNativeDialog();

    if (dirty) {
      const proceed = await confirmAction(
        "Tiene cambios sin guardar. Si abre el último archivo, perderá esos cambios.\n\n¿Continuar sin guardar?",
        { title: "Reabrir último", okLabel: "Reabrir sin guardar" }
      );
      if (!proceed) return;
    }

    try {
      await openPath(last);
    } catch (error) {
      clearLastOpenedPath();
      setStatus(`No se pudo reabrir: ${String(error)}`);
    }
  }, [dirty, dismissWelcomeForNativeDialog, openPath]);

  const handleStarter = useCallback(async () => {
    await dismissWelcomeForNativeDialog();

    const hasWork = dirty || Boolean(body.trim()) || Boolean(filePath);
    if (hasWork) {
      const proceed = await confirmAction(
        "El documento actual se reemplazará por la plantilla.\n\nGuarde primero (⌘S) si necesita conservar su trabajo.",
        { title: "Nueva plantilla", okLabel: "Reemplazar" }
      );
      if (!proceed) {
        setStatus("Plantilla cancelada");
        return;
      }
    }

    const text = await loadStarterTemplate();
    loadFromContent(text);
    setFilePath(null);
    setDirty(true);
    setStatus("Plantilla nueva (sin guardar)");
  }, [body, dirty, dismissWelcomeForNativeDialog, filePath, loadFromContent]);

  const handleQuit = useCallback(async () => {
    if (quitInProgressRef.current) return;
    quitInProgressRef.current = true;

    try {
      await dismissWelcomeForNativeDialog();

      if (dirtyRef.current) {
        const proceed = await confirmAction(
          "Tiene cambios sin guardar.\n\n¿Salir sin guardar?",
          { title: "Salir", okLabel: "Salir sin guardar" }
        );
        if (!proceed) return;
      }

      await deferNativeDialog();

      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("quit_app");
    } catch {
      window.close();
    } finally {
      quitInProgressRef.current = false;
    }
  }, [dismissWelcomeForNativeDialog]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest(".search-replace-bar")) {
        return;
      }
      if (event.defaultPrevented) return;

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
        void cycleViewMode();
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
      if (event.key === "q") {
        event.preventDefault();
        void handleQuit();
        return;
      }

      const styleKey = event.key >= "1" && event.key <= "7" ? Number(event.key) : 0;
      if (!styleKey) return;

      if (viewMode === "manual" || viewMode === "markdown") {
        event.preventDefault();
        window.dispatchEvent(
          new CustomEvent("cgv-apply-style", {
            detail: { styleKey, viewMode }
          })
        );
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cycleViewMode, handleNew, handleOpen, handleQuit, handleSave, searchOpen, setWritingModeEnabled, toggleWritingMode, viewMode, writingMode]);

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
        await bind("menu-file_duplicate", () => void handleDuplicate());
        await bind("menu-file_reopen", () => void handleReopenLast());
        await bind("menu-file_template", () => void handleStarter());
        await bind("menu-app_quit", () => void handleQuit());
        await bind("app-request-quit", () => void handleQuit());
      } catch {
        /* web-only dev */
      }
    })();

    return () => {
      cancelled = true;
      unsubs.forEach(unsub => unsub());
    };
  }, [handleDuplicate, handleNew, handleOpen, handleQuit, handleReopenLast, handleSave, handleStarter]);

  useEffect(() => {
    let cancelled = false;
    let unlisten: (() => void) | null = null;

    void (async () => {
      let pending: string[] = [];

      try {
        const { listen } = await import("@tauri-apps/api/event");
        if (cancelled) return;

        unlisten = await listen("cgv-open-file-request", () => {
          externalOpenSeenRef.current = true;
          void (async () => {
            const [path] = await takeOpenedManualPaths();
            if (!path) return;
            if (!startupCompleteRef.current) {
              const opened = await openPath(path);
              if (opened) dismissWelcome();
              return;
            }
            await handleExternalOpenPath(path);
          })();
        });

        pending = await takeOpenedManualPaths();
      } catch {
        /* web-only dev */
      }

      if (cancelled) return;
      if (pending[0]) {
        externalOpenSeenRef.current = true;
        const opened = await openPath(pending[0]);
        if (opened) dismissWelcome();
        startupCompleteRef.current = true;
        return;
      }

      await new Promise(resolve => window.setTimeout(resolve, 250));
      if (cancelled) return;

      const latePending = await takeOpenedManualPaths().catch(() => []);
      if (latePending[0]) {
        externalOpenSeenRef.current = true;
        const opened = await openPath(latePending[0]);
        if (opened) dismissWelcome();
        startupCompleteRef.current = true;
        return;
      }

      if (externalOpenSeenRef.current) {
        startupCompleteRef.current = true;
        return;
      }

      const last = getLastOpenedPath();
      if (last) {
        try {
          const opened = await openPath(last);
          if (opened) {
            setWelcomeOverlay(null);
            startupCompleteRef.current = true;
            return;
          }
        } catch {
          clearLastOpenedPath();
        }
      }

      if (cancelled || externalOpenSeenRef.current || openRequestRef.current > 0) return;
      loadFromContent("");
      setFilePath(null);
      dirtyRef.current = false;
      setDirty(false);
      setStatus("Sin archivo — ⌘O para abrir o escriba aquí");
      startupCompleteRef.current = true;
    })();

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [dismissWelcome, handleExternalOpenPath, loadFromContent, openPath]);

  useEffect(() => {
    if (dirty) return;
    const timer = window.setTimeout(() => {
      setAnalysis(analyzeDocument(content));
    }, ANALYSIS_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [content, dirty]);

  const title = filePath
    ? filePath.split(/[/\\]/).pop() ?? "Sin título"
    : "Sin archivo";

  const lastOpenedPath = getLastOpenedPath();
  const headingOutlineTree = buildHeadingOutlineTree(analysis.headingOutline);
  const headingCounts = analysis.headingOutline.reduce(
    (counts, item) => {
      counts[item.level] += 1;
      return counts;
    },
    { 1: 0, 2: 0, 3: 0 }
  );

  const focusWriting =
    writingMode && (viewMode === "manual" || viewMode === "markdown");
  const showWelcome =
    welcomeOverlay === "startup" && !filePath && !body.trim() && !focusWriting;

  useEffect(() => {
    if (!showWelcome) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      dismissWelcome();
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dismissWelcome, showWelcome]);

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
            onDuplicate={() => void handleDuplicate()}
            onReopenLast={() => void handleReopenLast()}
            onTemplate={() => void handleStarter()}
            onQuit={() => void handleQuit()}
          />
          <div className="brand">
            <div className="brand-title-row">
              <span className="brand-name">CGV Writer</span>
              <span
                className={`save-indicator${
                  saving
                    ? " save-indicator--saving"
                    : dirty
                      ? " save-indicator--dirty"
                      : " save-indicator--saved"
                }`}
                title={
                  saving
                    ? "Guardando…"
                    : dirty
                      ? "Cambios sin guardar"
                      : "Guardado"
                }
                aria-live="polite"
              >
                {saving ? "…" : dirty ? "●" : "✓"}
              </span>
            </div>
            <span className="brand-file">{title}</span>
          </div>
          <div className="view-tabs">
            <button
              type="button"
              className={viewMode === "manual" ? "active" : undefined}
              onClick={() => switchViewMode("manual")}
              title="Manual CGV — edición visual con términos del formato — ⌘/"
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
            <button
              type="button"
              className="theme-toggle"
              onClick={toggleColorTheme}
              title={theme === "dark" ? "Modo claro" : "Modo oscuro"}
              aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            >
              {theme === "dark" ? "☀" : "☾"}
            </button>
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

      <main className={`workspace ${viewMode === "markdown" ? "workspace--markdown" : ""}`}>
        {focusWriting && (
          <div className="focus-mode-badge" aria-live="polite">
            {viewMode === "manual" ? "Manual" : "Markdown"}
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
              onDismiss={dismissWelcome}
            />
          )}
          <div className="editor-pane-layer active">
            <SharedDocumentEditor
              value={content}
              onChange={handleChangeMarkdown}
              onDirty={markDocumentDirty}
              reloadKey={`${documentSession}:${filePath ?? "untitled"}`}
              mode={viewMode}
              writingMode={focusWriting}
              onToggleMode={() => void cycleViewMode()}
            />
          </div>
        </section>

        {!focusWriting && viewMode === "manual" && (
          <aside className="sidebar">
          <section className="panel">
            <h2>Esquema</h2>
            <p className="panel-meta">
              {analysis.headingOutline.length
                ? `${headingCounts[1]} contexto${headingCounts[1] === 1 ? "" : "s"} · ${headingCounts[2]} sección${headingCounts[2] === 1 ? "" : "es"} · ${headingCounts[3]} referencia${headingCounts[3] === 1 ? "" : "s"}`
                : "—"}
            </p>
            <HeadingOutlineTree nodes={headingOutlineTree} />
          </section>

          <section className="panel panel-presentation">
            <h2>Presenter</h2>
            <PresentationPanel
              content={content}
              onAppendToBody={appendToBody}
              onInsertQuiz={insertQuizAtCursor}
              variant="sidebar"
            />
          </section>

          <LibrarySettingsPanel />

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
              Buscar — ⌘F, reemplazar — ⌘⌥F. Atajos: ⌘/ Manual ↔ Markdown, ⌘N/O/S, ⌘1–7 estilos CGV.
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
