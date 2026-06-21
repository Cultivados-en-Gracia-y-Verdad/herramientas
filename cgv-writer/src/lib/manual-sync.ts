import type { SavedEditorPlace } from "./editor-position-bridge";

/** TipTap → markdown is expensive on large manuals; debounce while typing. */
export const MANUAL_SYNC_MS = 900;

/** CodeMirror → React state; keep in sync with manual but defer heavy parent work. */
export const MARKDOWN_SYNC_MS = 900;

/** Sidebar outline/checks — refresh after edits are saved/flushed. */
export const ANALYSIS_DEBOUNCE_MS = 800;

export const OUTLINE_DISPLAY_CAP = 200;

let manualEditorDirty = false;

export function markManualEditorDirty(): void {
  manualEditorDirty = true;
}

export function isManualEditorDirty(): boolean {
  return manualEditorDirty;
}

export function clearManualEditorDirty(): void {
  manualEditorDirty = false;
}

export interface ViewHandoff {
  place: SavedEditorPlace;
  /** Updated manual body markdown, or null when already synced. */
  bodyMd: string | null;
}

let pendingViewHandoff: ViewHandoff | null = null;

export function setViewHandoff(handoff: ViewHandoff): void {
  pendingViewHandoff = handoff;
}

export function takeViewHandoff(): ViewHandoff | null {
  const handoff = pendingViewHandoff;
  pendingViewHandoff = null;
  return handoff;
}

export function clearViewHandoff(): void {
  pendingViewHandoff = null;
}

const EXPORT_BODY_TIMEOUT_MS = 8000;

export function exportManualBodyFromEditor(): Promise<string> {
  return new Promise(resolve => {
    let settled = false;

    const finish = (body: string) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("cgv-manual-body-export", onResponse);
      resolve(body);
    };

    const onResponse = (event: Event) => {
      finish(String((event as CustomEvent<{ body: string }>).detail.body ?? ""));
    };

    window.addEventListener("cgv-manual-body-export", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-manual-body-export-request"));

    window.setTimeout(() => finish(""), EXPORT_BODY_TIMEOUT_MS);
  });
}

export function flushManualEditorSync(): void {
  window.dispatchEvent(new CustomEvent("cgv-manual-flush-sync"));
}

export function flushMarkdownEditorSync(): void {
  window.dispatchEvent(new CustomEvent("cgv-markdown-flush-sync"));
}

export function exportMarkdownFromEditor(): Promise<string> {
  return new Promise(resolve => {
    let settled = false;

    const finish = (body: string) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("cgv-markdown-body-export", onResponse);
      resolve(body);
    };

    const onResponse = (event: Event) => {
      finish(String((event as CustomEvent<{ body: string }>).detail.body ?? ""));
    };

    window.addEventListener("cgv-markdown-body-export", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-markdown-body-export-request"));
    window.setTimeout(() => finish(""), EXPORT_BODY_TIMEOUT_MS);
  });
}

/** Drop pending Manual→markdown debounce without pushing stale edits to React state. */
export function cancelManualEditorSync(): void {
  window.dispatchEvent(new CustomEvent("cgv-manual-cancel-sync"));
}

/** Flush Manual editor and return stored body for «Corregir estilo». */
export function requestManualBodyForStyleCorrect(): Promise<{
  body: string;
  storedBody: string;
}> {
  return new Promise(resolve => {
    const onResponse = (event: Event) => {
      window.removeEventListener("cgv-manual-style-correct-prep", onResponse);
      const detail = (event as CustomEvent<{ body: string; storedBody: string }>).detail;
      resolve({
        body: detail.body ?? "",
        storedBody: detail.storedBody ?? detail.body ?? ""
      });
    };
    window.addEventListener("cgv-manual-style-correct-prep", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-request-manual-style-correct-prep"));
    window.setTimeout(
      () => resolve({ body: "", storedBody: "" }),
      EXPORT_BODY_TIMEOUT_MS
    );
  });
}

/** Export current Manual body for Markdown view switch (single turndown, no React flush). */
export function requestManualBodyHandoff(): Promise<string> {
  return new Promise(resolve => {
    const onResponse = (event: Event) => {
      window.removeEventListener("cgv-manual-body-handoff", onResponse);
      resolve((event as CustomEvent<{ body: string }>).detail.body);
    };
    window.addEventListener("cgv-manual-body-handoff", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-request-manual-body-handoff"));
  });
}

/** Save cursor on the active editor before React switches views. */
export function dispatchBeforeViewChange(): void {
  window.dispatchEvent(new CustomEvent("cgv-before-view-change"));
}

const INSERT_QUIZ_TIMEOUT_MS = 2000;

/** Insert @quiz at the Manual editor cursor (or last known selection). */
export function requestInsertQuizAtCursor(quizId: string): Promise<boolean> {
  return new Promise(resolve => {
    let settled = false;

    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("cgv-insert-quiz-result", onResponse);
      resolve(ok);
    };

    const onResponse = (event: Event) => {
      finish(Boolean((event as CustomEvent<{ ok: boolean }>).detail?.ok));
    };

    window.addEventListener("cgv-insert-quiz-result", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-insert-quiz", { detail: { quizId } }));
    window.setTimeout(() => finish(false), INSERT_QUIZ_TIMEOUT_MS);
  });
}
