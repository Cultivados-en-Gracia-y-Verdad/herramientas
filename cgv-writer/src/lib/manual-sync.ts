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

export interface ManualBodyExport {
  body: string;
  blocked: boolean;
  changed: boolean;
}

export function exportManualBodyFromEditor(): Promise<ManualBodyExport> {
  return new Promise(resolve => {
    let settled = false;

    const finish = (result: ManualBodyExport) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("cgv-manual-body-export", onResponse);
      resolve(result);
    };

    const onResponse = (event: Event) => {
      const detail = (event as CustomEvent<ManualBodyExport>).detail;
      finish({
        body: String(detail?.body ?? ""),
        blocked: Boolean(detail?.blocked),
        changed: Boolean(detail?.changed)
      });
    };

    window.addEventListener("cgv-manual-body-export", onResponse, { once: true });
    window.dispatchEvent(new CustomEvent("cgv-manual-body-export-request"));

    window.setTimeout(
      () => finish({ body: "", blocked: true, changed: false }),
      EXPORT_BODY_TIMEOUT_MS
    );
  });
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

let viewChangeBlocked = false;

export function blockPendingViewChange(): void {
  viewChangeBlocked = true;
}

/** Save cursor on the active editor before React switches views. */
export function dispatchBeforeViewChange(): boolean {
  viewChangeBlocked = false;
  window.dispatchEvent(new CustomEvent("cgv-before-view-change"));
  return !viewChangeBlocked;
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
