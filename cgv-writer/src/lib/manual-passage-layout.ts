import type { Editor } from "@tiptap/core";

const SCRIPTURE_CLASS = "cgv-scripture";
const SPACER_CLASS = "cgv-md-spacer";

function scriptureTagAttrs(attrs: Record<string, unknown>): Record<string, unknown> {
  return { ...attrs, class: SCRIPTURE_CLASS };
}

function paragraphNeedsScriptureTag(cls: string, attrs: Record<string, unknown>): boolean {
  const tokens = cls.split(/\s+/).filter(Boolean);
  return (
    !tokens.includes(SCRIPTURE_CLASS) &&
    !tokens.includes("cgv-quiz") &&
    !attrs.dataQuizId
  );
}

function isMdSpacerParagraph(node: {
  type: { name: string };
  attrs: Record<string, unknown>;
}): boolean {
  if (node.type.name !== "paragraph") return false;
  return String(node.attrs.class || "")
    .split(/\s+/)
    .includes(SPACER_CLASS);
}

function isEmptyParagraph(node: {
  type: { name: string };
  textContent: string;
  attrs: Record<string, unknown>;
}): boolean {
  if (node.type.name !== "paragraph") return false;
  if (node.textContent.trim()) return false;
  return !isMdSpacerParagraph(node);
}

/** Blank or markdown spacer paragraph — removable when tightening heading pairs. */
function isRemovableGapParagraph(node: {
  type: { name: string };
  textContent: string;
  attrs: Record<string, unknown>;
}): boolean {
  return isEmptyParagraph(node) || isMdSpacerParagraph(node);
}

function findH3AtSelection(editor: Editor): number | null {
  const { state } = editor;
  const $from = state.selection.$from;
  for (let depth = $from.depth; depth > 0; depth--) {
    const node = $from.node(depth);
    if (node.type.name === "heading" && node.attrs.level === 3) {
      return $from.before(depth);
    }
  }
  return null;
}

function findCurrentTextblock(editor: Editor): {
  node: { type: { name: string }; attrs: Record<string, unknown> };
  end: number;
} | null {
  const { $from } = editor.state.selection;
  for (let depth = $from.depth; depth > 0; depth -= 1) {
    const node = $from.node(depth);
    if (node.isTextblock) {
      return {
        node: node as { type: { name: string }; attrs: Record<string, unknown> },
        end: $from.after(depth)
      };
    }
  }
  return null;
}

function isAtEndOfTextblock(editor: Editor): boolean {
  const { $from } = editor.state.selection;
  return $from.parent.isTextblock && $from.parentOffset === $from.parent.content.size;
}

/** Default writing flow: Enter after body text opens a fresh H5 comment line. */
export function handleManualDefaultH5Enter(editor: Editor): boolean {
  if (!editor.state.selection.empty || !isAtEndOfTextblock(editor)) return false;

  const block = findCurrentTextblock(editor);
  if (!block) return false;

  if (block.node.type.name === "heading") {
    const level = Number(block.node.attrs.level);
    if (level <= 3) return false;
  }

  const { state } = editor;
  const next = state.doc.nodeAt(block.end);
  if (next?.type.name === "heading" && next.attrs.level === 5) {
    editor.chain().focus().setTextSelection(block.end + 1).run();
    return true;
  }

  editor
    .chain()
    .focus()
    .insertContentAt(block.end, { type: "heading", attrs: { level: 5 } })
    .setTextSelection(block.end + 1)
    .run();
  return true;
}

/** Tag the paragraph after an H3 when the cursor is on that pair (Enter right under referencia). */
export function ensureScriptureParagraphAfterH3AtCursor(editor: Editor): void {
  const { state } = editor;
  const $pos = state.doc.resolve(state.selection.from);
  let depth = $pos.depth;
  while (depth > 0 && !$pos.node(depth).isBlock) {
    depth -= 1;
  }
  if (depth === 0) return;

  const block = $pos.node(depth);
  if (block.type.name !== "paragraph") return;

  const parent = $pos.node(depth - 1);
  const index = $pos.index(depth - 1);
  if (index === 0) return;

  const prev = parent.child(index - 1);
  if (prev.type.name !== "heading" || prev.attrs.level !== 3) return;

  const cls = String(block.attrs.class || "");
  if (!paragraphNeedsScriptureTag(cls, block.attrs as Record<string, unknown>)) return;

  const blockPos = $pos.before(depth);
  editor.view.dispatch(
    state.tr.setNodeMarkup(blockPos, undefined, scriptureTagAttrs(block.attrs as Record<string, unknown>))
  );
}

/** Tag the first paragraph after each H3 as versículo when it has no class yet. */
export function ensureScriptureParagraphsAfterH3(editor: Editor): void {
  const { state } = editor;
  let changed = false;
  const tr = state.tr;

  state.doc.descendants((node, pos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return true;
    }

    let scan = pos + node.nodeSize;
    while (true) {
      const next = tr.doc.nodeAt(scan);
      if (!next) return false;
      if (isEmptyParagraph(next as typeof node)) {
        scan += next.nodeSize;
        continue;
      }
      if (next.type.name !== "paragraph") return false;

      const cls = String(next.attrs.class || "");
      if (!paragraphNeedsScriptureTag(cls, next.attrs as Record<string, unknown>)) {
        return false;
      }

      tr.setNodeMarkup(scan, undefined, scriptureTagAttrs(next.attrs as Record<string, unknown>));
      changed = true;
      return false;
    }
  });

  if (changed) {
    editor.view.dispatch(tr);
  }
}

/** Remove blank paragraphs between ### and the versículo paragraph. */
export function removeEmptyParagraphsBetweenH3AndScripture(editor: Editor): void {
  const { state } = editor;
  const tr = state.tr;
  const toDelete: { from: number; to: number }[] = [];

  state.doc.descendants((node, pos) => {
    if (node.type.name !== "heading" || node.attrs.level !== 3) {
      return true;
    }

    let scan = pos + node.nodeSize;
    while (true) {
      const next = tr.doc.nodeAt(scan);
      if (!next) break;
      if (next.type.name === "heading") break;
      if (next.type.name === "paragraph" && String(next.attrs.class || "").includes(SCRIPTURE_CLASS)) {
        break;
      }
      if (isRemovableGapParagraph(next as typeof node)) {
        toDelete.push({ from: scan, to: scan + next.nodeSize });
        scan += next.nodeSize;
        continue;
      }
      break;
    }

    return false;
  });

  if (!toDelete.length) return;

  toDelete.sort((a, b) => b.from - a.from).forEach(({ from, to }) => {
    tr.delete(from, to);
  });

  if (tr.docChanged) {
    editor.view.dispatch(tr);
  }
}

type TopLevelBlock = {
  pos: number;
  nodeSize: number;
  node: {
    type: { name: string };
    attrs: Record<string, unknown>;
    textContent: string;
  };
};

function collectTopLevelBlocks(editor: Editor): TopLevelBlock[] {
  const blocks: TopLevelBlock[] = [];
  editor.state.doc.forEach((node, offset) => {
    blocks.push({ pos: offset, nodeSize: node.nodeSize, node });
  });
  return blocks;
}

/** True when this H4 follows a ### passage versículo. */
function h4FollowsVerseBlock(blocks: TopLevelBlock[], h4Index: number): boolean {
  let j = h4Index - 1;
  while (j >= 0 && isRemovableGapParagraph(blocks[j].node)) {
    j -= 1;
  }
  if (j < 0) return false;

  const prev = blocks[j].node;
  if (prev.type.name === "heading") return false;
  if (prev.type.name !== "paragraph" || !prev.textContent.trim()) return false;

  let k = j - 1;
  while (k >= 0) {
    const node = blocks[k].node;
    if (node.type.name === "heading") {
      if (node.attrs.level === 4) return false;
      return node.attrs.level === 3;
    }
    k -= 1;
  }
  return false;
}

function hasGapParagraphAbove(blocks: TopLevelBlock[], startIndex: number): boolean {
  for (let j = startIndex - 1; j >= 0; j--) {
    const node = blocks[j].node;
    if (isRemovableGapParagraph(node)) return true;
    if (node.type.name === "paragraph" && node.textContent.trim()) return false;
    if (node.type.name === "heading") return false;
  }
  return false;
}

/** Versículo → #### ancla: one blank line (curriculum layout). */
export function ensureBlankLineBetweenVerseAndH4(editor: Editor): void {
  const { state } = editor;
  const blocks = collectTopLevelBlocks(editor);
  const inserts: number[] = [];

  for (let i = 0; i < blocks.length; i++) {
    const { node } = blocks[i];
    if (node.type.name !== "heading" || node.attrs.level !== 4) continue;
    if (!h4FollowsVerseBlock(blocks, i)) continue;
    if (hasGapParagraphAbove(blocks, i)) continue;
    inserts.push(blocks[i].pos);
  }

  if (!inserts.length) return;

  const tr = state.tr;
  inserts
    .sort((a, b) => b - a)
    .forEach(pos => {
      tr.insert(pos, state.schema.nodes.paragraph.create({ class: SPACER_CLASS }));
    });

  if (tr.docChanged) {
    editor.view.dispatch(tr);
  }
}

function isInsideBlockquote(doc: Editor["state"]["doc"], pos: number): boolean {
  const $pos = doc.resolve(pos);
  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    if ($pos.node(depth).type.name === "blockquote") return true;
  }
  return false;
}

/** Blockquotes with no bullet text should not show an empty list marker. */
function removeEmptySynthesisBulletLists(editor: Editor): void {
  const { state } = editor;
  const tr = state.tr;
  const toDelete: number[] = [];

  state.doc.descendants((node, pos) => {
    if (node.type.name !== "bulletList" || !isInsideBlockquote(state.doc, pos)) return;

    let hasText = false;
    node.forEach(item => {
      if (item.textContent.trim()) hasText = true;
    });

    if (!hasText) {
      toDelete.push(pos);
    }
  });

  toDelete
    .sort((a, b) => b - a)
    .forEach(pos => {
      const node = tr.doc.nodeAt(pos);
      if (node) tr.delete(pos, pos + node.nodeSize);
    });

  if (tr.docChanged) {
    editor.view.dispatch(tr);
  }
}

export function tightenPassageLayoutInEditor(editor: Editor): void {
  removeEmptySynthesisBulletLists(editor);
  removeEmptyParagraphsBetweenH3AndScripture(editor);
  ensureScriptureParagraphsAfterH3(editor);
  ensureBlankLineBetweenVerseAndH4(editor);
}

/** Referencia H3 with versículo paragraph ready directly underneath. */
export function applyReferenceHeading(editor: Editor): void {
  editor.chain().focus().toggleHeading({ level: 3 }).run();
  tightenPassageLayoutInEditor(editor);

  const h3Pos = findH3AtSelection(editor);
  if (h3Pos == null) return;

  const h3Node = editor.state.doc.nodeAt(h3Pos);
  if (!h3Node) return;

  let after = h3Pos + h3Node.nodeSize;
  let next = editor.state.doc.nodeAt(after);
  while (next && isEmptyParagraph(next as typeof h3Node)) {
    after += next.nodeSize;
    next = editor.state.doc.nodeAt(after);
  }

  if (!next || next.type.name !== "paragraph") {
    editor
      .chain()
      .focus()
      .insertContentAt(after, `<p class="${SCRIPTURE_CLASS}"></p>`)
      .setTextSelection(after + 1)
      .run();
    return;
  }

  const cls = String(next.attrs.class || "");
  if (paragraphNeedsScriptureTag(cls, next.attrs as Record<string, unknown>)) {
    editor.view.dispatch(
      editor.state.tr.setNodeMarkup(after, undefined, scriptureTagAttrs(next.attrs as Record<string, unknown>))
    );
  }

  editor.chain().focus().setTextSelection(after + 1).run();
}
