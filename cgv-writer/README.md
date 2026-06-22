# CGV Writer

Desktop editor for CGV **`manual.md`** files — the long-form course text that **CGV Presenter** reads for slides. Writer is a separate app from Presenter; it does not replace PDF publishing in **curriculo** (pandoc/LaTeX).

Built for daily authoring: a calm writing surface, CGV-specific styles, and plain markdown on disk so Presenter and existing scripts keep working unchanged.

## Why Writer (vs a general markdown editor)

| Need | Writer |
|------|--------|
| CGV heading / comment / scripture styles | **Manual** visual mode with toolbar + shortcuts |
| Raw `#` syntax when you want it | **Markdown** tab (CodeMirror) |
| Quizzes, slide breaks | **Presentación** tab (not mixed into writing flow) |
| Large files, cursor/scroll position | One shared document; switching modes cannot rewrite or relocate content |
| Quiet, Typora-like focus | **Modo enfoque** hides chrome; shortcuts still work |

Output is always normal `.md`. No proprietary format.

## Three tabs

### Manual (default)

Word-like editing on a white page, backed directly by the same CodeMirror Markdown document used by the Markdown tab. Styles map to Presenter markdown — see [docs/conventions.md](docs/conventions.md).

Manual and Markdown are presentation modes of one editor state. Switching modes preserves the exact source, cursor, selection, undo history, and scroll context; no Markdown conversion runs during a switch.

- **Contexto / Sección / Referencia** → `#` `##` `###` (H3 = Bible reference, flush left)
- **H4** → `####` anchor text (scripture style with « »)
- **H5 / H6 / Lista** → `#####` / `######` / `-` (comment levels 1–3, each nested visually)
- **Versículo** → verse block under H3 (before first `####`)
- **Definición** → `term` + `: gloss` on the next line
- **Subrayado** → `<u>…</u>` fill-in-the-blank

Quiz and slide-break buttons are hidden on Manual (use Presentación instead). More commands may move there over time.

### Markdown

Full-file source editor with line numbers. Use for paste, bulk edits, or when you prefer typing `#` directly. Heading shortcuts ⌘1–⌘3 apply `#` / `##` / `###` on the current line.

### Presentación

Forms to append Presenter markers: verse units, focus, commentary, quiz (`<!-- @quiz id -->`), blank-line slide breaks. Keeps presentation mechanics out of the writing surface.

## Modo enfoque (quiet writing)

On the **Manual** tab:

| Action | macOS | Windows |
|--------|-------|---------|
| Toggle focus mode | ⌘⇧F | Ctrl⇧F |
| Exit focus mode | Escape or ⌘⇧F | Escape or Ctrl⇧F |
| Button | **Enfoque** in the toolbar | same |

Focus mode hides the style toolbar, sidebar, status bar, and file tabs. A thin filename bar and a one-line shortcut hint remain. Your preference is remembered.

### Keyboard shortcuts (Manual & Markdown unless noted)

| Shortcut | Action |
|----------|--------|
| ⌘/ / Ctrl+/ | Cycle views: Manual → Presentación → Markdown |
| ⌘S / Ctrl+S | Save |
| ⌘O / Ctrl+O | Open |
| ⌘1 | H1 Contexto / `#` |
| ⌘2 | H2 Sección / `##` |
| ⌘3 | H3 Referencia bíblica / `###` |
| ⌘4 | H4 texto ancla / `####` |
| ⌘5 | H5 comentario nivel 1 / `#####` |
| ⌘6 | H6 comentario nivel 2 / `######` |
| ⌘7 | Lista comentario nivel 3 / `-` |
| ⌘B / ⌘I / ⌘U | Bold / italic / underline (Manual, when editor focused) |

## Daily workflow

1. **Abrir** (⌘O) — open `manual.md` or `markdown.md` from a curriculo course folder, or start typing on the blank page.
2. Write in **Manual**; use **Modo enfoque** for long sessions.
3. Switch to **Markdown** occasionally to inspect source; the same cursor and undo history remain active.
4. Add quizzes and slide structure in **Presentación** when needed.
5. **Guardar** (⌘S) — Presenter reads the same file as before.
6. Build PDFs with existing curriculo scripts when ready (`build_manual.sh`, etc.).

## Prerequisites

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://www.rust-lang.org/tools/install) (Tauri desktop builds)
- Platform deps: [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)

## Daily use (macOS)

Install once so CGV Writer lives in **Applications** like any other app:

```bash
cd cgv-writer
npm run install:mac
```

Then open it from **Spotlight** (⌘Space → “CGV Writer”), the **Dock**, or:

```bash
npm run open:mac
```

On launch, Writer reopens your **last manual** automatically. **⌘Q** or **Archivo → Salir** quits (with a prompt if you have unsaved changes). Click the Dock icon again to bring the window back.

## Development

```bash
cd cgv-writer
npm install
npm run tauri:dev
```

Web-only UI (no native open/save dialogs):

```bash
npm run dev
```

## Production build

```bash
npm run tauri:build
```

Installers land under `src-tauri/target/release/bundle/` (`.app` on macOS, installer on Windows).

## Project layout

```
cgv-writer/
  src/
    App.tsx                 Shell, tabs, shortcuts, focus mode
    components/
      SharedDocumentEditor.tsx  One CodeMirror document, Manual + Markdown modes
      PresentationPanel.tsx Slide/quiz append UI
    lib/
      codemirror-manual-mode.ts Visual Manual decorations over exact Markdown
      analyze.ts            Outline + light checks (sidebar)
      manual-comments.ts    H4/H5/H6 structure
      writing-mode.ts       Focus mode preference
  src-tauri/                Tauri 2 shell
  docs/
    conventions.md          Authoring rules for manual.md
    illustrations-example.md  Future @illustration sidecar (v2)
  templates/                Starter manual.md
  public/templates/         Copy used by “Nueva plantilla”
```

## Downstream tools

| Tool | Role |
|------|------|
| **CGV Presenter** | Reads `manual.md` for slides |
| `publish-course.sh` | Publishes a course folder |
| `build_manual.sh` | PDF from markdown (curriculo) |

## Roadmap

- **Now:** Improve through daily use — performance on very large manuals and visual-mode polish. Native saves are atomic and retain recent backups in `.cgv-writer-backups/` beside each changed manual.
- **v2:** Illustration storyboards (`@illustration` + sidecar JSON) — [docs/illustrations-example.md](docs/illustrations-example.md).

## Authoring reference

Full style table and examples: **[docs/conventions.md](docs/conventions.md)**.
