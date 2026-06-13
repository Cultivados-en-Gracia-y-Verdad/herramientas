export type SearchAction = "find" | "next" | "prev" | "replace" | "replaceAll" | "clear";

export interface SearchRequest {
  query: string;
  replace: string;
  caseSensitive: boolean;
  action: SearchAction;
}

export interface SearchReport {
  total: number;
  /** 1-based index of current match; 0 when none. */
  current: number;
}

export function dispatchSearch(request: SearchRequest): void {
  window.dispatchEvent(new CustomEvent("cgv-search", { detail: request }));
}

export function dispatchSearchOpen(showReplace = false, seed = ""): void {
  window.dispatchEvent(
    new CustomEvent("cgv-search-open", { detail: { showReplace, seed } })
  );
}

export function dispatchSearchClose(): void {
  window.dispatchEvent(new CustomEvent("cgv-search-close"));
}

export function reportSearchResult(report: SearchReport): void {
  window.dispatchEvent(new CustomEvent("cgv-search-report", { detail: report }));
}
