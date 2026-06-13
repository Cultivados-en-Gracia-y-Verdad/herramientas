import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

export type EditorViewId = "manual" | "markdown";

const ANCHOR_CHARS = 80;

export interface SavedEditorPlace {
  scrollRatio: number;
  /** 0–1 plain-text position in document body (shared across Manual ↔ Markdown). */
  bodyCharRatio: number;
  /** Normalized plain text immediately before the cursor. */
  anchorBefore: string;
  /** Character offset in normalizeForAnchor(body) space — more stable across views. */
  normalizedOffset: number;
}

const scrollByView: Partial<Record<EditorViewId, number>> = {};
let sharedBodyCharRatio = 0;
let sharedAnchorBefore = "";
let sharedNormalizedOffset = 0;

export function bodyTextCharRatio(totalChars: number, offset: number): number {
  if (totalChars <= 0) return 0;
  return Math.min(1, Math.max(0, offset / totalChars));
}

export function anchorBeforeOffset(text: string, offset: number): string {
  return normalizeForAnchor(text.slice(0, offset)).slice(-ANCHOR_CHARS);
}

/** Strip common markdown/HTML so anchors match Manual plain text. */
export function normalizeForAnchor(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/<\/?u>/gi, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .replace(/\[\^(\d+)\]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function findOffsetByAnchor(text: string, anchorBefore: string, fallbackOffset: number): number {
  const safeFallback = Math.min(text.length, Math.max(0, fallbackOffset));
  if (!anchorBefore || !text) return safeFallback;

  let bestEnd = -1;
  let bestDistance = Infinity;
  let searchFrom = 0;

  while (searchFrom < text.length) {
    const idx = text.indexOf(anchorBefore, searchFrom);
    if (idx < 0) break;
    const end = idx + anchorBefore.length;
    const distance = Math.abs(end - safeFallback);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestEnd = end;
    }
    searchFrom = idx + 1;
  }

  if (bestEnd >= 0) return bestEnd;
  return safeFallback;
}

function normalizedFallbackOffset(
  text: string,
  place: SavedEditorPlace,
  preferSavedOffset = false
): number {
  const normalized = normalizeForAnchor(text);
  if (!normalized.length) return 0;
  if (preferSavedOffset && place.normalizedOffset > 0) {
    return Math.min(normalized.length, place.normalizedOffset);
  }
  return Math.round(place.bodyCharRatio * normalized.length);
}

export function markdownBodyOffset(body: string, place: SavedEditorPlace): number {
  const normalized = normalizeForAnchor(body);
  if (!normalized.length) return 0;
  const fallback = normalizedFallbackOffset(body, place, true);
  const normOffset = findOffsetByAnchor(normalized, place.anchorBefore, fallback);
  return Math.round((normOffset / normalized.length) * body.length);
}

export function plainTextOffset(plain: string, place: SavedEditorPlace): number {
  if (!plain.length) return 0;

  const normalized = normalizeForAnchor(plain);
  const fallbackNorm = normalized.length
    ? normalizedFallbackOffset(plain, place, false)
    : Math.round(place.bodyCharRatio * plain.length);

  const normOffset = place.anchorBefore && normalized.length
    ? findOffsetByAnchor(normalized, place.anchorBefore, fallbackNorm)
    : fallbackNorm;

  if (normalized.length) {
    return Math.min(plain.length, Math.round((normOffset / normalized.length) * plain.length));
  }
  return Math.min(plain.length, Math.round(place.bodyCharRatio * plain.length));
}

export function textOffsetFromPos(doc: ProseMirrorNode, pos: number): number {
  return doc.textBetween(0, pos, "\n", "\n").length;
}

export function textOffsetToPos(doc: ProseMirrorNode, target: number): number {
  if (target <= 0) return 1;

  const maxPos = Math.max(1, doc.content.size - 1);
  let lo = 1;
  let hi = maxPos;

  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (textOffsetFromPos(doc, mid) < target) lo = mid + 1;
    else hi = mid;
  }

  return lo;
}

export function saveEditorPlace(
  view: EditorViewId,
  scrollEl: HTMLElement | null,
  bodyCharRatio: number,
  anchorBefore = "",
  normalizedOffset = 0
): void {
  sharedBodyCharRatio = Math.min(1, Math.max(0, bodyCharRatio));
  sharedAnchorBefore = anchorBefore.slice(-ANCHOR_CHARS);
  sharedNormalizedOffset = Math.max(0, normalizedOffset);

  if (!scrollEl) return;
  const max = scrollEl.scrollHeight - scrollEl.clientHeight;
  scrollByView[view] = max > 0 ? scrollEl.scrollTop / max : 0;
}

/** Cursor position shared across Manual ↔ Markdown (ignore per-view scroll). */
export function loadSharedEditorPlace(): SavedEditorPlace | null {
  if (sharedBodyCharRatio === 0 && !sharedAnchorBefore && sharedNormalizedOffset === 0) {
    return null;
  }
  return {
    scrollRatio: 0,
    bodyCharRatio: sharedBodyCharRatio,
    anchorBefore: sharedAnchorBefore,
    normalizedOffset: sharedNormalizedOffset
  };
}

export function loadEditorPlace(view: EditorViewId): SavedEditorPlace | null {
  const shared = loadSharedEditorPlace();
  if (!shared) return null;
  return {
    ...shared,
    scrollRatio: scrollByView[view] ?? 0
  };
}

export function clearEditorPlaces(): void {
  scrollByView.manual = undefined;
  scrollByView.markdown = undefined;
  sharedBodyCharRatio = 0;
  sharedAnchorBefore = "";
  sharedNormalizedOffset = 0;
}
