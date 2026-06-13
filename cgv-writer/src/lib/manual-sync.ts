import type { SavedEditorPlace } from "./editor-position-bridge";

/** TipTap → markdown is expensive on large manuals; debounce while typing. */
export const MANUAL_SYNC_MS = 450;

/** Sidebar outline/checks can wait longer than body sync. */
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

/** Drop pending Manual→markdown debounce without pushing stale edits to React state. */
export function cancelManualEditorSync(): void {
  window.dispatchEvent(new CustomEvent("cgv-manual-cancel-sync"));
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
