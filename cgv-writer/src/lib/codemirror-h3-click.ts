import type { RefObject } from "react";
import { EditorView } from "@codemirror/view";
import { getInlineBibleReferenceAtPosition } from "cgv-bible";
import { getSharedBibleIndex } from "./bible-index-store";
import { isLikelyBibleReference } from "./markdown-html";

export function bibleReferenceFromHeadingLine(text: string): string {
  const plain = text.match(/^###\s+(.+)$/);
  const legacy = text.match(/^<!--\s*###\s+([\s\S]*?)\s*-->$/);
  const reference = (plain?.[1] ?? legacy?.[1] ?? "")
    .replace(/<\/?u>/gi, "")
    .replace(/[*_]/g, "")
    .trim();
  return isLikelyBibleReference(reference) ? reference : "";
}

function clickedDocumentPosition(event: MouseEvent, view: EditorView): number | null {
  const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
  return typeof pos === "number" ? pos : null;
}

function referenceFromInlineElement(target: Element): string {
  const element = target.closest(".cm-cgv-inline-bible-ref");
  const text = element?.textContent?.trim() ?? "";
  const index = getSharedBibleIndex();
  if (!text || !index) return "";

  return getInlineBibleReferenceAtPosition(text, 0, index)?.reference ?? "";
}

/** H3 bible popup - only when the click is on a ### referencia line. */
export function resolveH3ReferenceClick(
  event: MouseEvent,
  view: EditorView
): { reference: string; headingFrom: number } | null {
  const target = event.target;
  if (!(target instanceof Element)) return null;

  const lineElement = target.closest(".cm-line.cm-cgv-manual-h3");
  if (!lineElement || !view.dom.contains(lineElement)) return null;

  const pos = clickedDocumentPosition(event, view);
  if (pos === null) return null;

  const line = view.state.doc.lineAt(pos);
  const reference = bibleReferenceFromHeadingLine(line.text);
  if (!reference) return null;

  return { reference, headingFrom: line.from };
}

function resolveInlineReferenceClick(
  event: MouseEvent,
  view: EditorView
): { reference: string } | null {
  const target = event.target;
  if (!(target instanceof Element)) return null;
  if (!target.closest(".cm-line")) return null;

  const elementReference = referenceFromInlineElement(target);
  if (elementReference) return { reference: elementReference };

  const pos = clickedDocumentPosition(event, view);
  if (pos === null) return null;

  const line = view.state.doc.lineAt(pos);
  if (bibleReferenceFromHeadingLine(line.text)) return null;

  const index = getSharedBibleIndex();
  if (!index) return null;

  const match = getInlineBibleReferenceAtPosition(line.text, pos - line.from, index);
  return match ? { reference: match.reference } : null;
}

export function bibleReferenceClickHandlers(
  modeRef: RefObject<"manual" | "markdown">,
  openBible: (reference: string, kind: "h3" | "inline", headingFrom?: number | null) => void
) {
  return EditorView.domEventHandlers({
    click(event, view) {
      if (modeRef.current !== "manual") return false;
      if (!event.metaKey && !event.ctrlKey) return false;

      const h3Hit = resolveH3ReferenceClick(event, view);
      if (h3Hit) {
        event.preventDefault();
        event.stopPropagation();
        openBible(h3Hit.reference, "h3", h3Hit.headingFrom);
        return true;
      }

      const inlineHit = resolveInlineReferenceClick(event, view);
      if (!inlineHit) return false;

      event.preventDefault();
      event.stopPropagation();
      openBible(inlineHit.reference, "inline");
      return true;
    }
  });
}
