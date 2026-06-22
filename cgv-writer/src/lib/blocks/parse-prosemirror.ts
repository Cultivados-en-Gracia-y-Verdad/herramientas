import type { Editor } from "@tiptap/core";
import type { Mark, Node as ProseMirrorNode } from "@tiptap/pm/model";
import { coerceQuizMarkersInMarkdown, restoreStrayMarkdownComments, sanitizeH4AnchorText, tightenCgvDefaultSpacing } from "../markdown-html";
import { markH6Bullet } from "./commentary-helpers";
import {
  isSynthesisBulletText,
  isSynthesisTitleText,
  stripBulletPrefix
} from "../synthesis-block";
import { compileBlocks } from "./compile";
import type { ContentBlock } from "./types";
import { newBlockId } from "./types";

function hasClass(node: ProseMirrorNode, token: string): boolean {
  return String(node.attrs.class || "")
    .split(/\s+/)
    .filter(Boolean)
    .includes(token);
}

function isSpacer(node: ProseMirrorNode): boolean {
  return node.type.name === "paragraph" && hasClass(node, "cgv-md-spacer");
}

function isQuizParagraph(node: ProseMirrorNode): boolean {
  return node.type.name === "paragraph" && (hasClass(node, "cgv-quiz") || Boolean(node.attrs.dataQuizId));
}

function isScriptureParagraph(node: ProseMirrorNode): boolean {
  return node.type.name === "paragraph" && hasClass(node, "cgv-scripture");
}

function wrapMarks(text: string, marks: readonly Mark[]): string {
  if (!marks.length) return text;

  const order = ["code", "link", "bold", "italic", "underline", "strike"];
  const sorted = [...marks].sort(
    (a, b) => order.indexOf(a.type.name) - order.indexOf(b.type.name)
  );

  return sorted.reduce((acc, mark) => {
    switch (mark.type.name) {
      case "bold":
        return `**${acc}**`;
      case "italic":
        return `*${acc}*`;
      case "underline":
        return `<u>${acc}</u>`;
      case "code":
        return `\`${acc}\``;
      case "link":
        return `[${acc}](${String(mark.attrs.href ?? "")})`;
      case "strike":
        return `~~${acc}~~`;
      default:
        return acc;
    }
  }, text);
}

function serializeInlineContent(parent: ProseMirrorNode): string {
  let result = "";
  parent.forEach(node => {
    if (node.isText) {
      result += wrapMarks(node.text ?? "", node.marks);
      return;
    }
    if (node.type.name === "hardBreak") {
      result += "\n";
      return;
    }
    result += serializeInlineContent(node);
  });
  return result;
}

function inlineMarkdown(node: ProseMirrorNode): string {
  return serializeInlineContent(node).trim();
}

function collectCommentaryBullets(
  nodes: ProseMirrorNode[],
  startIndex: number
): { bullets: string[]; nextIndex: number } {
  const bullets: string[] = [];
  let i = startIndex;

  while (i < nodes.length) {
    const next = nodes[i];

    if (isSpacer(next)) {
      i++;
      continue;
    }

    if (next.type.name === "heading" && next.attrs.level === 6) {
      bullets.push(markH6Bullet(inlineMarkdown(next)));
      i++;
      continue;
    }

    if (next.type.name === "paragraph" && (hasClass(next, "cgv-h6") || hasClass(next, "cgv-comment-3"))) {
      bullets.push(markH6Bullet(inlineMarkdown(next)));
      i++;
      continue;
    }

    if (next.type.name === "bulletList") {
      next.forEach(item => {
        item.forEach(child => {
          const text = inlineMarkdown(child);
          if (text) bullets.push(text);
        });
      });
      i++;
      continue;
    }

    if (
      next.type.name === "heading" &&
      [1, 2, 3, 4, 5].includes(Number(next.attrs.level))
    ) {
      break;
    }

    if (next.type.name === "horizontalRule") break;
    break;
  }

  return { bullets, nextIndex: i };
}

function parseSynthesisBlockquote(node: ProseMirrorNode): ContentBlock {
  const paragraphs: ProseMirrorNode[] = [];
  const bullets: string[] = [];

  node.forEach(child => {
    if (child.type.name === "paragraph") {
      paragraphs.push(child);
      return;
    }

    if (child.type.name === "bulletList") {
      child.forEach(item => {
        item.forEach(listChild => {
          const text = inlineMarkdown(listChild);
          if (text) bullets.push(text);
        });
      });
    }
  });

  let title = "";

  for (const para of paragraphs) {
    const text = inlineMarkdown(para).trim();
    if (!text) continue;
    if (hasClass(para, "cgv-synthesis-title") || isSynthesisTitleText(text)) {
      title = text;
      break;
    }
  }

  if (!title) {
    for (const para of paragraphs) {
      const text = inlineMarkdown(para).trim();
      if (!text || isSynthesisBulletText(text)) continue;
      title = text;
      break;
    }
  }

  for (const para of paragraphs) {
    const text = inlineMarkdown(para).trim();
    if (!text || text === title) continue;
    if (isSynthesisBulletText(text)) {
      bullets.push(stripBulletPrefix(text));
    }
  }

  return { id: newBlockId(), type: "synthesis", title, bullets };
}

function parseCgvH5Block(node: ProseMirrorNode): ContentBlock {
  let title = "";
  const bullets: string[] = [];

  node.forEach(child => {
    if (child.type.name === "paragraph" && isSpacer(child)) {
      return;
    }

    if (child.type.name === "heading" && child.attrs.level === 5) {
      title = inlineMarkdown(child);
      return;
    }

    if (child.type.name === "paragraph" && (hasClass(child, "cgv-h5") || hasClass(child, "cgv-comment-2"))) {
      title = inlineMarkdown(child);
      return;
    }

    if (child.type.name === "heading" && child.attrs.level === 6) {
      bullets.push(markH6Bullet(inlineMarkdown(child)));
      return;
    }

    if (child.type.name === "paragraph" && (hasClass(child, "cgv-h6") || hasClass(child, "cgv-comment-3"))) {
      bullets.push(markH6Bullet(inlineMarkdown(child)));
      return;
    }

    if (child.type.name === "bulletList") {
      child.forEach(item => {
        item.forEach(listChild => {
          const text = inlineMarkdown(listChild);
          if (text) bullets.push(text);
        });
      });
    }
  });

  return { id: newBlockId(), type: "commentary", title, bullets };
}

/** Parse TipTap document directly — avoids getHTML + DOMParser + per-node turndown. */
export function prosemirrorDocToBlocks(doc: ProseMirrorNode): ContentBlock[] {
  const nodes: ProseMirrorNode[] = [];
  doc.forEach(node => nodes.push(node));

  const blocks: ContentBlock[] = [];
  let i = 0;

  while (i < nodes.length) {
    const node = nodes[i];

    if (isSpacer(node)) {
      i++;
      continue;
    }

    const name = node.type.name;

    if (name === "heading") {
      const level = Number(node.attrs.level);

      if (level === 1) {
        blocks.push({ id: newBlockId(), type: "h1", text: inlineMarkdown(node) });
        i++;
        continue;
      }

      if (level === 2) {
        blocks.push({ id: newBlockId(), type: "h2", text: inlineMarkdown(node) });
        i++;
        continue;
      }

      if (level === 3) {
        const reference = inlineMarkdown(node);
        i++;
        const scriptureLines: string[] = [];

        while (i < nodes.length) {
          const next = nodes[i];
          if (isSpacer(next)) {
            i++;
            break;
          }
          if (
            next.type.name === "heading" ||
            next.type.name === "horizontalRule" ||
            isQuizParagraph(next)
          ) {
            break;
          }
          if (next.type.name === "paragraph") {
            const text = inlineMarkdown(next);
            if (!text.trim()) {
              i++;
              continue;
            }
            scriptureLines.push(text);
            i++;
            break;
          }
          break;
        }

        blocks.push({
          id: newBlockId(),
          type: "verse",
          reference,
          scripture: scriptureLines.join("\n")
        });
        continue;
      }

      if (level === 4) {
        blocks.push({
          id: newBlockId(),
          type: "focus",
          phrase: sanitizeH4AnchorText(inlineMarkdown(node))
        });
        i++;
        continue;
      }

      if (level === 5) {
        const title = inlineMarkdown(node);
        i++;
        const { bullets, nextIndex } = collectCommentaryBullets(nodes, i);
        blocks.push({ id: newBlockId(), type: "commentary", title, bullets });
        i = nextIndex;
        continue;
      }

      if (level === 6) {
        const h6 = inlineMarkdown(node);
        i++;
        const { bullets, nextIndex } = collectCommentaryBullets(nodes, i);
        blocks.push({ id: newBlockId(), type: "commentary", title: "", h6, bullets });
        i = nextIndex;
        continue;
      }
    }

    if (name === "cgvTable") {
      blocks.push({
        id: newBlockId(),
        type: "table",
        markdown: String(node.attrs.markdown || "").trim()
      });
      i++;
      continue;
    }

    if (name === "cgvH5Block") {
      blocks.push(parseCgvH5Block(node));
      i++;
      continue;
    }

    if (name === "bulletList") {
      const bullets: string[] = [];
      node.forEach(item => {
        item.forEach(child => {
          const text = inlineMarkdown(child);
          if (text) bullets.push(text);
        });
      });
      blocks.push({ id: newBlockId(), type: "commentary", title: "", bullets });
      i++;
      continue;
    }

    if (name === "blockquote") {
      blocks.push(parseSynthesisBlockquote(node));
      i++;
      continue;
    }

    if (name === "horizontalRule") {
      blocks.push({ id: newBlockId(), type: "slideBreak" });
      i++;
      continue;
    }

    if (name === "paragraph") {
      if (isQuizParagraph(node)) {
        const id =
          String(node.attrs.dataQuizId || "").trim() ||
          (node.textContent?.trim().match(/^Quiz:\s*(.+)$/i)?.[1] ?? "");
        blocks.push({ id: newBlockId(), type: "quiz", quizId: id });
        i++;
        continue;
      }

      if (isScriptureParagraph(node)) {
        blocks.push({
          id: newBlockId(),
          type: "verse",
          reference: "",
          scripture: inlineMarkdown(node)
        });
        i++;
        continue;
      }

      if (hasClass(node, "definition-term")) {
        const term = inlineMarkdown(node);
        const next = nodes[i + 1];
        if (next?.type.name === "paragraph" && hasClass(next, "definition-text")) {
          const defText = inlineMarkdown(next);
          const gloss = defText.startsWith(":") ? defText : `: ${defText.replace(/^:\s*/, "")}`;
          blocks.push({ id: newBlockId(), type: "definition", term, definition: gloss });
          i += 2;
          continue;
        }
      }

      const text = inlineMarkdown(node);
      if (text) {
        blocks.push({ id: newBlockId(), type: "paragraph", text });
      }
      i++;
      continue;
    }

    i++;
  }

  return blocks;
}

export function editorDocToMarkdown(editor: Editor): string {
  const blocks = prosemirrorDocToBlocks(editor.state.doc);
  return restoreStrayMarkdownComments(
    coerceQuizMarkersInMarkdown(tightenCgvDefaultSpacing(compileBlocks(blocks)).trimEnd())
  );
}
