import { renderMarkdownBlock, renderMarkdownInline } from "../marked-gfm";
import { encodeTableMarkdown, renderTableHtml } from "../table-block";
import { isH6Bullet, unmarkH6Bullet } from "./commentary-helpers";
import type { CommentaryBlock, ContentBlock } from "./types";

function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineHtml(text: string): string {
  return renderMarkdownInline(String(text || ""));
}

function definitionToHtml(term: string, definitionLine: string) {
  const gloss = definitionLine.trim();
  const secondLine = gloss.startsWith(":") ? gloss : `: ${gloss.replace(/^:\s*/, "")}`;
  return `<div class="cgv-definition"><p class="definition-term">${escapeHtml(term)}</p><p class="definition-text">${escapeHtml(secondLine)}</p></div>`;
}

function synthesisToHtml(title: string, bullets: string[]): string {
  const titleHtml = inlineHtml(title);
  const items = bullets
    .map(bullet => bullet.trim())
    .filter(Boolean)
    .map(bullet => `<li>${inlineHtml(bullet)}</li>`)
    .join("");
  const list = items ? `<ul class="cgv-synthesis-bullets">${items}</ul>` : "";
  return `<blockquote class="cgv-synthesis synthesis-box"><p class="cgv-synthesis-title">${titleHtml}</p>${list}</blockquote>`;
}

/** CGV blank-line rules when joining blocks — mirrors compileBlocks spacing. */
function needsCgvBlankLineBetween(prev: ContentBlock | null, next: ContentBlock): boolean {
  if (!prev || prev.type === "slideBreak" || next.type === "slideBreak") {
    return false;
  }
  if (prev.type === "focus" && next.type === "commentary") {
    return false;
  }
  if (prev.type === "commentary" && next.type === "focus") {
    return false;
  }
  if (prev.type === "verse") {
    return true;
  }
  if (prev.type === "paragraph" && next.type === "paragraph") {
    return false;
  }
  if (prev.type === "commentary" && next.type === "commentary") {
    if (!prev.title.trim() && !next.title.trim()) {
      return false;
    }
  }
  return true;
}

function renderCommentaryHtml(block: CommentaryBlock): string {
  const parts: string[] = [];
  if (block.title.trim()) {
    parts.push(`<h5>${inlineHtml(block.title)}</h5>`);
  }
  if (block.h6?.trim()) {
    parts.push(`<h6>${inlineHtml(block.h6)}</h6>`);
  }

  let pendingBullets: string[] = [];
  const flushBullets = () => {
    if (!pendingBullets.length) return;
    const items = pendingBullets.map(bullet => `<li>${inlineHtml(bullet)}</li>`).join("");
    parts.push(`<ul class="cgv-h6-bullets">${items}</ul>`);
    pendingBullets = [];
  };

  for (const bullet of block.bullets) {
    const text = bullet.trim();
    if (!text) continue;
    if (isH6Bullet(text)) {
      if (pendingBullets.length) {
        flushBullets();
        parts.push('<p class="cgv-md-spacer"></p>');
      } else {
        flushBullets();
      }
      parts.push(`<h6>${inlineHtml(unmarkH6Bullet(text))}</h6>`);
    } else {
      pendingBullets.push(text);
    }
  }
  flushBullets();

  const inner = parts.join("");
  if (block.title.trim()) {
    return `<div class="cgv-h5-block">${inner}</div>`;
  }
  return inner;
}

function renderBlock(block: ContentBlock): string {
  switch (block.type) {
    case "h1":
      return `<h1>${inlineHtml(block.text)}</h1>`;
    case "h2":
      return `<h2>${inlineHtml(block.text)}</h2>`;
    case "verse": {
      const parts = [`<h3>${escapeHtml(block.reference)}</h3>`];
      for (const line of block.scripture.split("\n")) {
        if (!line.trim()) {
          parts.push('<p class="cgv-md-spacer"></p>');
        } else {
          parts.push(`<p class="cgv-scripture">${inlineHtml(line)}</p>`);
        }
      }
      return parts.join("");
    }
    case "focus":
      return `<h4>${inlineHtml(block.phrase)}</h4>`;
    case "commentary":
      return renderCommentaryHtml(block);
    case "synthesis":
      return synthesisToHtml(block.title, block.bullets);
    case "definition": {
      const gloss = block.definition.trim();
      return definitionToHtml(block.term, gloss);
    }
    case "quiz":
      return `<p class="cgv-quiz" data-quiz-id="${escapeHtml(block.quizId)}">Quiz: ${escapeHtml(block.quizId)}</p>`;
    case "table": {
      const markdown = block.markdown.trim();
      if (!markdown) return "";
      const html = renderTableHtml(markdown);
      return `<div class="cgv-table" data-markdown="${escapeHtml(encodeTableMarkdown(markdown))}"><div class="cgv-table-inner">${html}</div></div>`;
    }
    case "raw":
      return renderMarkdownBlock(block.text);
    case "paragraph":
      return `<p>${inlineHtml(block.text)}</p>`;
    case "slideBreak":
      return '<hr class="cgv-slide-break" />';
    default:
      return "";
  }
}

/** Render parsed CGV blocks to TipTap HTML — one structural unit per block, CGV-aware spacing. */
export function blocksToEditorHtml(blocks: ContentBlock[]): string {
  const parts: string[] = [];
  let prev: ContentBlock | null = null;

  for (const block of blocks) {
    if (needsCgvBlankLineBetween(prev, block)) {
      parts.push('<p class="cgv-md-spacer"></p>');
    }
    const html = renderBlock(block);
    if (html) parts.push(html);
    if (block.type !== "slideBreak") {
      prev = block;
    }
  }

  return parts.join("");
}
