import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { isLikelyBibleReference } from "./markdown-html";

function normalizeHeadingText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function findH3PosByReference(
  doc: ProseMirrorNode,
  reference: string
): number | null {
  const target = normalizeHeadingText(reference);
  if (!target) return null;

  let found: number | null = null;

  doc.descendants((node, pos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return true;
    }

    if (normalizeHeadingText(node.textContent) === target) {
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
