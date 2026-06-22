import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

/** Find the document position of the Nth heading at a given level. */
export function findManualHeadingPos(
  doc: ProseMirrorNode,
  level: number,
  ordinal: number
): number | null {
  let count = 0;
  let found: number | null = null;

  doc.descendants((node, pos) => {
    if (node.type.name === "heading" && Number(node.attrs.level) === level) {
      count += 1;
      if (count === ordinal) {
        found = pos;
        return false;
      }
    }
  });

  return found;
}
