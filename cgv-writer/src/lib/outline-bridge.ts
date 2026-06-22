export interface OutlineNavigateRequest {
  level: 1 | 2 | 3;
  bodyOffset: number;
  ordinal: number;
}

export function dispatchOutlineNavigate(request: OutlineNavigateRequest): void {
  window.dispatchEvent(new CustomEvent("cgv-outline-navigate", { detail: request }));
}

export { findManualHeadingPos } from "./outline-nav";
