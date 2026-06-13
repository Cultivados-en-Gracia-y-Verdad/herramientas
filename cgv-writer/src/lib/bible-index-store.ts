import type { BibleIndex } from "cgv-bible";

let sharedBibleIndex: BibleIndex | null = null;

export function setSharedBibleIndex(index: BibleIndex | null): void {
  sharedBibleIndex = index;
}

export function getSharedBibleIndex(): BibleIndex | null {
  return sharedBibleIndex;
}

export const BIBLE_INDEX_UPDATED_EVENT = "cgv-bible-index-updated";

export function notifyBibleIndexUpdated(): void {
  window.dispatchEvent(new CustomEvent(BIBLE_INDEX_UPDATED_EVENT));
}
