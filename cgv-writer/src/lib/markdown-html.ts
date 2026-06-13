import { marked } from "marked";
import TurndownService from "turndown";
import {
  compileSynthesisMarkdown,
  isBlockquoteLine,
  isSynthesisMarkdownChunk,
  isSynthesisTitleLine,
  parseSynthesisLines,
  synthesisMarkdownLinesFromChunk
} from "./synthesis-block";

marked.setOptions({ gfm: true, breaks: false });

const QUIZ_MD = /<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->/g;
const STRAY_HTML_COMMENT = /<!--\s*(?!@(?:quiz|illustration)\b)([\s\S]*?)\s*-->/g;

/** H3 is only for short bible references — not commentary paragraphs. */
export function isLikelyBibleReference(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  if (t.length > 72) return false;
  if (/<[^>]+>/.test(t)) return false;
  if (t.split(/\s+/).length >= 8) return false;
  return true;
}

/** H4 anchor: plain text — strip * and " but keep « » (NBLA-style guillemets). */
export function sanitizeH4AnchorText(text: string): string {
  let result = String(text || "").trim();
  if (!result) return "";

  result = result.replace(/<[^>]+>/g, "");
  result = result.replace(/\*\*([^*]+)\*\*/g, "$1");
  result = result.replace(/\*([^*]+)\*/g, "$1");
  result = result.replace(/\*/g, "");
  result = result.replace(/["""\u201C\u201D]/g, "");
  result = result.replace(/\s+/g, " ").trim();

  return result;
}

function restoreUnwrappedCommentLine(inner: string): string {
  const text = inner.trim();
  const h3 = text.match(/^###\s+([\s\S]+)$/);
  if (h3 && !isLikelyBibleReference(h3[1])) {
    return `##### ${h3[1]}`;
  }
  return text;
}

function demoteMisplacedH3Lines(md: string): string {
  return md.replace(/^### (.+)$/gm, (line, content: string) => {
    if (isLikelyBibleReference(content)) return line;
    return `##### ${content}`;
  });
}

function unwrapStrayMarkdownComments(md: string): string {
  return md.replace(STRAY_HTML_COMMENT, (_match, inner: string) =>
    restoreUnwrappedCommentLine(inner)
  );
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function stripSpanishQuotes(text: string) {
  return text.replace(/^[«"“]|[»"”]$/g, "").trim();
}

function unwrapLegacyScriptureMarkdown(text: string) {
  let clean = stripSpanishQuotes(text.trim());
  const guillemet = clean.match(/^\*«([\s\S]+?)»\*$/);
  if (guillemet) clean = guillemet[1];
  if (/^«[\s\S]+»$/.test(clean)) clean = clean.slice(1, -1);
  return clean.trim();
}

/** Plain verse line under ### — no guillemets, no HTML comments. */
function formatScriptureMarkdown(text: string) {
  const clean = unwrapLegacyScriptureMarkdown(text);
  return clean;
}

function normalizeScriptureLine(line: string) {
  const comment = line.match(/^<!--\s*(?!@(?:quiz|illustration)\b)([\s\S]*?)\s*-->$/);
  if (comment) return restoreUnwrappedCommentLine(comment[1]);
  return unwrapLegacyScriptureMarkdown(line);
}

/** Keep ### reference on the line immediately above verse text (CGV format). */
function coalesceH3WithScripture(body: string) {
  return body.replace(
    /^(### (?:(?!#{1,6}\s).)+)\n\s*\n(?!(#{1,6}\s|<!--\s*@(?:quiz|illustration)\b))(\S[^\n]*)/gm,
    "$1\n$3"
  );
}

/** Recover stray HTML comments before turndown (turndown drops comment nodes). */
function htmlStrayCommentsToScripture(html: string) {
  return html.replace(STRAY_HTML_COMMENT, (_match, text: string) => {
    const inner = text.trim();
    const h3 = inner.match(/^###\s+([\s\S]+)$/);
    const cleaned =
      h3 && !isLikelyBibleReference(h3[1]) ? h3[1] : restoreUnwrappedCommentLine(inner);
    const inline = marked.parseInline(cleaned, { async: false }) as string;
    if (h3 && !isLikelyBibleReference(h3[1])) {
      return `<h5>${inline}</h5>`;
    }
    return `<p class="cgv-scripture">${inline}</p>`;
  });
}

/** Tag plain paragraph(s) after H3 and before H4 as scripture blocks. */
function tagScriptureParagraphs(html: string) {
  let result = html;
  let prev = "";

  while (prev !== result) {
    prev = result;
    result = result.replace(
      /<h3>([\s\S]*?)<\/h3>\s*<p(?![^>]*class="[^"]*cgv-scripture)(?![^>]*cgv-quiz)(?![^>]*definition-)([^>]*)>/i,
      (_match, heading, attrs) => `<h3>${heading}</h3><p class="cgv-scripture"${attrs}>`
    );
  }

  return result;
}

function fixCgvPassageLayout(md: string) {
  let result = unwrapStrayMarkdownComments(md);
  result = demoteMisplacedH3Lines(result);

  // ### Reference\n\nVerse → ### Reference\nVerse
  result = result.replace(/^(### [^\n]+)\n\n(?!(#{1,6}\s|<!--\s*@))/gm, "$1\n");

  return result;
}

/** Undo turndown over-escaping — CGV manuals should not accumulate backslashes. */
export function normalizeCgvMarkdown(md: string): string {
  let result = md;
  let prev = "";

  while (prev !== result) {
    prev = result;
    result = result.replace(/\\+\[\^(\d+)\s*\\+\]/g, "[^$1]");
    result = result.replace(/__([^_\n]+?)__/g, "$1");
    result = result.replace(/^\*«([\s\S]+?)»\*$/gm, "$1");
    // Strip turndown escapes for punctuation that should stay literal in CGV files
    result = result.replace(/\\([\\`*_{}\[\]()#+.!\->|])/g, "$1");
  }

  return fixCgvPassageLayout(result);
}

function isDefinitionPair(lines: string[], index: number) {
  return (
    index + 1 < lines.length &&
    lines[index].trim() &&
    lines[index + 1].startsWith(": ")
  );
}

function formatDefinitionLine(definitionLine: string) {
  const trimmed = definitionLine.trim();
  if (trimmed.startsWith(": ")) return trimmed;
  if (trimmed.startsWith(":")) return `: ${trimmed.slice(1).trim()}`;
  return `: ${trimmed}`;
}

function definitionToHtml(term: string, definitionLine: string) {
  const secondLine = formatDefinitionLine(definitionLine);
  return `<div class="cgv-definition"><p class="definition-term">${escapeHtml(term)}</p><p class="definition-text">${escapeHtml(secondLine)}</p></div>`;
}

function scriptureToHtml(text: string) {
  const normalized = normalizeScriptureLine(text);
  const inline = marked.parseInline(normalized, { async: false }) as string;
  return `<p class="cgv-scripture">${inline}</p>`;
}

function focusToHtml(html: string) {
  return `<h4>${html}</h4>`;
}

function h5TitleToHtml(html: string) {
  return `<h5>${html}</h5>`;
}

function h6ToHtml(html: string) {
  return `<h6>${html}</h6>`;
}

function h6ListToHtml(items: string[]) {
  return `<ul class="cgv-h6-bullets">${items.join("")}</ul>`;
}

function synthesisLinesToHtml(lines: string[]): string {
  const parsed = parseSynthesisLines(lines);
  if (!parsed) return "";

  const titleHtml = marked.parseInline(parsed.title, { async: false }) as string;
  const items = parsed.bullets
    .map(bullet => {
      const itemHtml = marked.parseInline(bullet, { async: false }) as string;
      return `<li>${itemHtml}</li>`;
    })
    .join("");

  return `<blockquote class="cgv-synthesis synthesis-box"><p class="cgv-synthesis-title">${titleHtml}</p><ul class="cgv-synthesis-bullets">${items}</ul></blockquote>`;
}

function synthesisChunkToHtml(chunk: string): string {
  const lines = synthesisMarkdownLinesFromChunk(chunk);
  return synthesisLinesToHtml(lines) || (marked.parse(chunk, { async: false }) as string);
}

/** Parse CGV passage chunks (### reference, scripture, comments, definitions). */
function chunkToEditorHtml(chunk: string): string {
  const lines = chunk.split("\n").map(line => line.trim());

  if (!lines.length || !lines[0]) {
    return marked.parse(chunk, { async: false }) as string;
  }

  const first = lines[0];

  if (isDefinitionPair(lines, 0)) {
    const parts: string[] = [];
    let index = 0;
    while (index < lines.length) {
      if (isDefinitionPair(lines, index)) {
        parts.push(definitionToHtml(lines[index], lines[index + 1]));
        index += 2;
        continue;
      }
      parts.push(marked.parseInline(lines[index], { async: false }) as string);
      index++;
    }
    return parts.map(line => `<p>${line}</p>`).join("");
  }

  if (!/^### /.test(first) || /^####/.test(first)) {
    return marked.parse(chunk, { async: false }) as string;
  }

  const refText = first.slice(4).trim();
  if (!isLikelyBibleReference(refText)) {
    return marked.parse(demoteMisplacedH3Lines(chunk), { async: false }) as string;
  }

  const parts: string[] = [`<h3>${escapeHtml(refText)}</h3>`];
  let index = 1;
  let beforeCommentHeadings = true;

  while (index < lines.length) {
    const line = lines[index];

    if (QUIZ_MD.test(line)) {
      const match = line.match(QUIZ_MD);
      const id = match?.[1] || "";
      parts.push(`<p class="cgv-quiz" data-quiz-id="${id}">Quiz: ${id}</p>`);
      index++;
      continue;
    }

    if (isDefinitionPair(lines, index)) {
      parts.push(definitionToHtml(lines[index], lines[index + 1]));
      index += 2;
      continue;
    }

    if (/^#### /.test(line) && !/^#####/.test(line)) {
      beforeCommentHeadings = false;
      const raw = sanitizeH4AnchorText(line.slice(5).trim());
      const text = marked.parseInline(raw, { async: false }) as string;
      parts.push(focusToHtml(text));
      index++;
      continue;
    }

    if (/^##### /.test(line)) {
      beforeCommentHeadings = false;
      const text = marked.parseInline(line.slice(6).trim(), { async: false }) as string;
      parts.push(h5TitleToHtml(text));
      index++;
      continue;
    }

    if (/^###### /.test(line)) {
      beforeCommentHeadings = false;
      const text = marked.parseInline(line.slice(7).trim(), { async: false }) as string;
      parts.push(h6ToHtml(text));
      index++;
      continue;
    }

    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (index < lines.length && lines[index].startsWith("- ")) {
        const itemHtml = marked.parseInline(lines[index].slice(2).trim(), {
          async: false
        }) as string;
        items.push(`<li>${itemHtml}</li>`);
        index++;
      }
      parts.push(h6ListToHtml(items));
      continue;
    }

    if (isSynthesisTitleLine(line)) {
      const group = [line];
      index++;
      while (index < lines.length && isBlockquoteLine(lines[index])) {
        group.push(lines[index]);
        index++;
      }
      parts.push(synthesisLinesToHtml(group));
      continue;
    }

    if (/^#{1,3}\s/.test(line)) {
      break;
    }

    if (beforeCommentHeadings && line) {
      parts.push(scriptureToHtml(line));
      index++;
      continue;
    }

    const text = marked.parseInline(line, { async: false }) as string;
    parts.push(h6ToHtml(text));
    index++;
  }

  return parts.join("");
}

export function markdownToEditorHtml(body: string): string {
  const normalized = normalizeCgvMarkdown(String(body || ""));
  const coalesced = coalesceH3WithScripture(normalized);
  const withQuiz = coalesced.replace(
    QUIZ_MD,
    (_, id) => `\n\n<p class="cgv-quiz" data-quiz-id="${id}">Quiz: ${id}</p>\n\n`
  );

  const chunks = withQuiz.split(/\n\s*\n/);
  return chunks
    .map(chunk => chunk.trim())
    .filter(Boolean)
    .map(chunk => {
      if (chunk.includes('class="cgv-quiz"')) return chunk;
      if (chunk.includes("cgv-slide-break")) {
        return '<hr class="cgv-slide-break" />';
      }
      if (isSynthesisMarkdownChunk(chunk)) {
        return synthesisChunkToHtml(chunk);
      }
      return chunkToEditorHtml(chunk);
    })
    .join("");
}

function h5BlockElementToMarkdown(el: HTMLElement): string {
  const lines: string[] = [];
  const title =
    el.querySelector("h5")?.textContent?.trim() ||
    el.querySelector(".cgv-h5")?.textContent?.trim() ||
    el.querySelector(".cgv-comment-2")?.textContent?.trim();
  if (title) lines.push(`##### ${title}`);

  el.querySelectorAll("h6, p.cgv-h6, p.cgv-comment-3").forEach(node => {
    const text = node.textContent?.trim();
    if (text) lines.push(`###### ${text}`);
  });

  el.querySelectorAll("ul.cgv-h6-bullets li, ul.cgv-comment-3 li").forEach(li => {
    const text = li.textContent?.trim();
    if (text) lines.push(`- ${text}`);
  });

  return lines.length ? `${lines.join("\n")}\n\n` : "";
}

export function editorHtmlToMarkdown(html: string): string {
  const prepared = tagScriptureParagraphs(htmlStrayCommentsToScripture(html || ""));

  const turndown = new TurndownService({
    headingStyle: "atx",
    bulletListMarker: "-",
    emDelimiter: "*",
    strongDelimiter: "**"
  });

  // CGV content is structured HTML — do not escape markdown punctuation in prose.
  turndown.escape = (text: string) => text;

  turndown.addRule("cgvSynthesis", {
    filter: node => {
      if (node.nodeName !== "BLOCKQUOTE") return false;
      const el = node as HTMLElement;
      return (
        el.classList?.contains("cgv-synthesis") || el.classList?.contains("synthesis-box")
      );
    },
    replacement: (_content, node) => {
      const el = node as HTMLElement;
      const title =
        el.querySelector(".cgv-synthesis-title")?.textContent?.trim() ||
        el.querySelector("p")?.textContent?.trim() ||
        "";
      const bullets: string[] = [];
      el.querySelectorAll(".cgv-synthesis-bullets li, ul li").forEach(li => {
        const text = li.textContent?.trim();
        if (text) bullets.push(text);
      });
      return `${compileSynthesisMarkdown(title, bullets)}\n\n`;
    }
  });

  turndown.addRule("cgvSlideBreak", {
    filter: node =>
      node.nodeName === "HR" &&
      (node as HTMLElement).classList?.contains("cgv-slide-break"),
    replacement: () => "\n\n"
  });

  turndown.addRule("cgvQuiz", {
    filter: node =>
      node.nodeName === "P" && (node as HTMLElement).classList?.contains("cgv-quiz"),
    replacement: (_content, node) => {
      const id = (node as HTMLElement).getAttribute("data-quiz-id") || "";
      return `\n\n<!-- @quiz ${id} -->\n\n`;
    }
  });

  turndown.addRule("cgvDefinition", {
    filter: node =>
      node.nodeName === "DIV" && (node as HTMLElement).classList?.contains("cgv-definition"),
    replacement: (_content, node) => {
      const el = node as HTMLElement;
      const term =
        el.querySelector(".definition-term")?.textContent?.trim() ||
        el.querySelector("p")?.textContent?.trim() ||
        "";
      const definitionLine = formatDefinitionLine(
        el.querySelector(".definition-text")?.textContent?.trim() || ""
      );
      return `${term}\n${definitionLine}\n\n`;
    }
  });

  turndown.addRule("cgvScripture", {
    filter: node => {
      if (node.nodeName === "P") {
        return (node as HTMLElement).classList?.contains("cgv-scripture");
      }
      if (node.nodeName === "H3") {
        return (node as HTMLElement).classList?.contains("cgv-scripture");
      }
      return false;
    },
    replacement: content => `${formatScriptureMarkdown(content)}\n`
  });

  turndown.addRule("cgvH4", {
    filter: node => node.nodeName === "H4",
    replacement: content => `#### ${sanitizeH4AnchorText(content)}\n\n`
  });

  turndown.addRule("cgvH5Heading", {
    filter: node => node.nodeName === "H5",
    replacement: content => `##### ${content.trim()}\n\n`
  });

  turndown.addRule("cgvH6Heading", {
    filter: node => node.nodeName === "H6",
    replacement: content => `###### ${content.trim()}\n\n`
  });

  turndown.addRule("cgvH5Block", {
    filter: node =>
      node.nodeName === "DIV" && (node as HTMLElement).classList?.contains("cgv-h5-block"),
    replacement: (_content, node) => h5BlockElementToMarkdown(node as HTMLElement)
  });

  turndown.addRule("cgvFocus", {
    filter: node => {
      if (node.nodeName !== "P") return false;
      const el = node as HTMLElement;
      return el.classList?.contains("cgv-focus") || el.classList?.contains("cgv-comment-1");
    },
    replacement: content => `#### ${sanitizeH4AnchorText(content)}\n\n`
  });

  turndown.addRule("cgvH5", {
    filter: node => {
      if (node.nodeName !== "P") return false;
      const el = node as HTMLElement;
      return (
        (el.classList?.contains("cgv-h5") || el.classList?.contains("cgv-comment-2")) &&
        !el.closest(".cgv-h5-block")
      );
    },
    replacement: content => `##### ${content.trim()}\n\n`
  });

  turndown.addRule("cgvH6", {
    filter: node => {
      if (node.nodeName !== "P") return false;
      const el = node as HTMLElement;
      return el.classList?.contains("cgv-h6") && !el.closest(".cgv-h5-block");
    },
    replacement: content => `###### ${content.trim()}\n\n`
  });

  turndown.addRule("cgvH6List", {
    filter: node => {
      if (node.nodeName !== "UL") return false;
      const el = node as HTMLElement;
      if (el.closest(".cgv-h5-block")) return false;
      return (
        el.classList?.contains("cgv-h6-bullets") || el.classList?.contains("cgv-comment-3")
      );
    },
    replacement: content => `${content.trim()}\n\n`
  });

  turndown.addRule("cgvUnderline", {
    filter: ["u"],
    replacement: content => `<u>${content}</u>`
  });

  let md = turndown.turndown(prepared);
  md = md.replace(/\n{3,}/g, "\n\n").trim();
  return normalizeCgvMarkdown(md);
}

export function splitYamlBody(text: string) {
  const match = String(text || "").match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return { frontMatter: "", body: text || "" };
  return {
    frontMatter: match[1],
    body: text.slice(match[0].length)
  };
}

export function joinYamlBody(frontMatter: string, body: string) {
  const trimmed = body.trim();
  if (!frontMatter.trim()) return trimmed ? `${trimmed}\n` : "";
  return `---\n${frontMatter.trim()}\n---\n\n${trimmed}\n`;
}
