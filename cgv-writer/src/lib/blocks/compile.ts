import { sanitizeH4AnchorText } from "../markdown-html";
import { compileSynthesisMarkdown } from "../synthesis-block";
import type { ContentBlock } from "./types";
import { splitFrontMatter } from "../analyze";

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
        .map(b => `- ${b}`)
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
    case "paragraph":
      return block.text.trim();
    case "slideBreak":
      return "";
    default:
      return "";
  }
}

export function compileBlocks(blocks: ContentBlock[]): string {
  const parts: string[] = [];

  for (const block of blocks) {
    if (block.type === "slideBreak") {
      parts.push("");
      continue;
    }
    const text = compileBlock(block);
    if (text) parts.push(text);
  }

  return parts.join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
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
