import { formatCgvBulletLine, sanitizeH4AnchorText } from "../markdown-html";
import { compileSynthesisMarkdown } from "../synthesis-block";
import type { ContentBlock } from "./types";
import { splitFrontMatter } from "../analyze";

function needsBlankLineBetweenBlocks(prev: ContentBlock | null, next: ContentBlock): boolean {
  if (!prev || prev.type === "slideBreak" || next.type === "slideBreak") {
    return false;
  }
  if (prev.type === "verse" && next.type === "commentary") {
    return false;
  }
  if (prev.type === "focus" && next.type === "commentary") {
    return false;
  }
  return true;
}

function compileBlock(block: ContentBlock): string {
  switch (block.type) {
    case "h1":
      return `# ${block.text.trim()}`;
    case "h2":
      return `## ${block.text.trim()}`;
    case "verse": {
      const ref = block.reference.trim();
      const text = block.scripture.trim();
      return text ? `### ${ref}\n${text}` : `### ${ref}`;
    }
    case "focus":
      return `#### ${sanitizeH4AnchorText(block.phrase)}`;
    case "commentary": {
      const title = block.title.trim();
      const bulletLines = block.bullets
        .map(b => b.trim())
        .filter(Boolean)
        .map(b => formatCgvBulletLine(b))
        .join("\n");
      if (title && bulletLines) return `##### ${title}\n${bulletLines}`;
      if (title) return `##### ${title}`;
      if (bulletLines) return bulletLines;
      return "";
    }
    case "synthesis":
      return compileSynthesisMarkdown(block.title, block.bullets);
    case "definition": {
      const gloss = block.definition.trim();
      const secondLine = gloss.startsWith(":") ? gloss : `: ${gloss}`;
      return `${block.term.trim()}\n${secondLine}`;
    }
    case "quiz":
      return `<!-- @quiz ${block.quizId.trim()} -->`;
    case "table":
      return block.markdown.trim();
    case "raw":
      return block.text;
    case "paragraph":
      return block.text.trim();
    case "slideBreak":
      return "";
    default:
      return "";
  }
}

export function compileBlocks(blocks: ContentBlock[]): string {
  let result = "";
  let prev: ContentBlock | null = null;

  for (const block of blocks) {
    if (block.type === "slideBreak") {
      if (result) result += "\n\n";
      prev = null;
      continue;
    }

    const text = compileBlock(block);
    if (!text) continue;

    if (result) {
      result += needsBlankLineBetweenBlocks(prev, block) ? "\n\n" : "\n";
    }
    result += text;
    prev = block;
  }

  return result.replace(/\n{3,}/g, "\n\n").trim();
}

export function mergeDocument(frontMatter: string, blocks: ContentBlock[]): string {
  const body = compileBlocks(blocks);
  if (!frontMatter.trim()) return body;
  return `---\n${frontMatter.trim()}\n---\n\n${body}`.trimEnd() + "\n";
}

export function splitDocument(text: string) {
  const { meta, body } = splitFrontMatter(text);
  return { frontMatter: meta, body };
}
