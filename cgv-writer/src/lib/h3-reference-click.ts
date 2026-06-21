import type { Editor } from "@tiptap/react";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { isLikelyBibleReference } from "./markdown-html";

export function normalizeReferenceText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function normalizeHeadingText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function findH3PosByReference(
  doc: ProseMirrorNode,
  reference: string
): number | null {
  const target = normalizeReferenceText(reference);
  if (!target) return null;

  let found: number | null = null;

  doc.descendants((node, pos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return true;
    }

    if (normalizeReferenceText(node.textContent) === target) {
      found = pos;
      return false;
    }

    return true;
  });

  return found;
}

export function findH3FromDomClick(
  doc: ProseMirrorNode,
  reference: string
): { pos: number; text: string } | null {
  const text = normalizeHeadingText(reference);
  if (!text || !isLikelyBibleReference(text)) return null;

  const pos = findH3PosByReference(doc, text);
  if (pos === null) return null;

  return { pos, text };
}

/** Last ### bible reference strictly before `pos`. */
export function findH3BeforePos(
  doc: ProseMirrorNode,
  pos: number
): { pos: number; text: string } | null {
  let best: { pos: number; text: string } | null = null;

  doc.nodesBetween(0, pos, (node, nodePos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return;
    }

    const text = normalizeHeadingText(node.textContent);
    if (!text || !isLikelyBibleReference(text)) return;

    best = { pos: nodePos, text };
  });

  return best;
}

/** ### reference at the cursor, or the nearest one before it. */
export function findVerseReferenceAtPos(
  doc: ProseMirrorNode,
  pos: number
): { pos: number; text: string } | null {
  const $pos = doc.resolve(Math.max(0, Math.min(pos, doc.content.size)));

  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    const node = $pos.node(depth);
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      continue;
    }

    const text = normalizeHeadingText(node.textContent);
    if (!text || !isLikelyBibleReference(text)) {
      return null;
    }

    return { pos: $pos.before(depth), text };
  }

  return findH3BeforePos(doc, pos);
}

/** 1-based occurrence index of `reference` at or before `pos`. */
export function countReferenceOccurrenceBeforePos(
  doc: ProseMirrorNode,
  pos: number,
  reference: string
): number {
  const target = normalizeReferenceText(reference);
  if (!target) return 0;

  let count = 0;
  doc.nodesBetween(0, pos, node => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return;
    }

    if (normalizeReferenceText(node.textContent) === target) {
      count += 1;
    }
  });

  return count;
}

/** H3 reference when the cursor/click is on the heading itself (not commentary below). */
export function findH3AtPos(editor: Editor, pos: number): { pos: number; text: string } | null {
  const $pos = editor.state.doc.resolve(Math.max(0, Math.min(pos, editor.state.doc.content.size)));

  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    const node = $pos.node(depth);
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      continue;
    }

    const text = normalizeHeadingText(node.textContent);
    if (!text || !isLikelyBibleReference(text)) {
      return null;
    }

    return { pos: $pos.before(depth), text };
  }

  return null;
}
