import { compileBlocks } from "./blocks/compile";
import { parseBodyToBlocks } from "./blocks/parse";
import { htmlToBlocks } from "./blocks/parse-html";
import { blocksToEditorHtml } from "./blocks/render-html";
import { isBlockquoteLine } from "./synthesis-block";

const QUIZ_PLAIN_LINE_GLOBAL = /^@quiz\s+#?([A-Za-z0-9_.:-]+)\s*$/gim;
const QUIZ_LABEL_LINE_GLOBAL = /^Quiz:\s*([A-Za-z0-9_.:-]+)\s*$/gim;
const PROTECTED_QUIZ_COMMENT = /<!--\s*@(quiz|illustration)\b[\s\S]*?-->/g;
const STRAY_HTML_COMMENT = /<!--\s*(?!@(?:quiz|illustration)\b)([\s\S]*?)\s*-->/g;

export function quizMarkerComment(quizId: string): string {
  const id = quizId.trim();
  return id ? `<!-- @quiz ${id} -->` : "";
}

/** Normalize loose quiz lines to Presenter HTML comment markers. */
export function coerceQuizMarkersInMarkdown(md: string): string {
  return String(md || "")
    .replace(QUIZ_PLAIN_LINE_GLOBAL, (_line, id: string) => quizMarkerComment(id))
    .replace(QUIZ_LABEL_LINE_GLOBAL, (_line, id: string) => quizMarkerComment(id));
}

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

function stripEmptyHtmlComments(text: string): string {
  return String(text || "").replace(/<!--\s*-->/g, "");
}

function unwrapStrayMarkdownComments(md: string): string {
  const placeholders: string[] = [];
  let protectedMd = stripEmptyHtmlComments(md);
  protectedMd = protectedMd.replace(PROTECTED_QUIZ_COMMENT, match => {
    const token = `\u0000CGVQUIZ${placeholders.length}\u0000`;
    placeholders.push(match);
    return token;
  });

  let result = protectedMd.replace(STRAY_HTML_COMMENT, (_match, inner: string) => {
    const restored = restoreUnwrappedCommentLine(inner);
    return restored ? restored : "";
  });

  result = result.replace(/\u0000CGVQUIZ(\d+)\u0000/g, (_match, index: string) => {
    return placeholders[Number(index)] ?? "";
  });

  return result;
}

/** CGV list marker: dash plus three spaces (Presenter / manual convention). */
export const CGV_BULLET_LINE_PREFIX = "-   ";

export function formatCgvBulletLine(text: string): string {
  return `${CGV_BULLET_LINE_PREFIX}${text.trim()}`;
}

export function isCgvBulletLine(line: string): boolean {
  const trimmed = String(line || "").trim();
  return /^-\s+\S/.test(trimmed);
}

function isBulletMarkdownLine(line: string): boolean {
  const trimmed = line.trim();
  return isCgvBulletLine(trimmed) || /^>-\s+/.test(trimmed) || /^>\s*-\s+/.test(trimmed);
}

function normalizeCgvBulletPrefixes(md: string): string {
  return md
    .split("\n")
    .map(line => {
      if (isBlockquoteLine(line)) return line;
      const match = line.match(/^(-)\s+(.*)$/);
      if (!match) return line;
      return formatCgvBulletLine(match[2]);
    })
    .join("\n");
}

/** Bullet lists should not contain blank lines between items. */
function collapseBlankLinesWithinBulletLists(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) {
      const prev = out[out.length - 1];
      let nextIndex = i + 1;
      while (nextIndex < lines.length && !lines[nextIndex].trim()) nextIndex += 1;
      const next = lines[nextIndex];
      if (prev && next && isBulletMarkdownLine(prev) && isBulletMarkdownLine(next)) {
        continue;
      }
    }
    out.push(line);
  }

  return out.join("\n");
}

/** Ensure one blank line between versículo text and the following #### anchor. */
function ensureVerseToH4BlankLine(md: string): string {
  let result = String(md || "");
  result = result.replace(
    /^(### [^\n]+)\n((?:[^\n#][^\n]*\n?)+)\n(#### )/gm,
    (_match, heading, scripture, h4) =>
      `${heading}\n${String(scripture).replace(/\s+$/, "")}\n\n${h4}`
  );
  result = result.replace(/^([^\n#][^\n]+)\n(#### )/gm, "$1\n\n$2");
  result = result.replace(/^([^\n#][^\n]+)\n\n+(#### )/gm, "$1\n\n$2");
  return result;
}

function fixCgvPassageLayout(md: string) {
  let result = unwrapStrayMarkdownComments(md);
  result = demoteMisplacedH3Lines(result);

  // ### Reference\n\nVerse → ### Reference\nVerse
  result = result.replace(/^(### [^\n]+)\n\n(?!(#{1,6}\s|<!--\s*@))/gm, "$1\n");

  result = ensureVerseToH4BlankLine(result);

  // #### anchor then ##### comment — no blank line
  result = result.replace(/^(#### [^\n]+)\n\n(##### )/gm, "$1\n$2");

  // ##### then bullet list — no blank line
  result = result.replace(/^(##### [^\n]+)\n\n(-\s+)/gm, "$1\n$2");

  result = collapseBlankLinesWithinBulletLists(result);
  result = normalizeCgvBulletPrefixes(result);

  return result;
}

/** Light cleanup on save/load/export — no layout reshaping. */
export function sanitizeCgvMarkdown(md: string): string {
  let result = String(md || "");
  let prev = "";

  while (prev !== result) {
    prev = result;
    result = result.replace(/\\+\[\^(\d+)\s*\\+\]/g, "[^$1]");
    result = result.replace(/__([^_\n]+?)__/g, "$1");
    result = result.replace(/^\*«([\s\S]+?)»\*$/gm, "$1");
    // Strip turndown escapes for punctuation that should stay literal in CGV files
    result = result.replace(/\\([\\`*_{}\[\]()#+.!\->|])/g, "$1");
  }

  return coerceQuizMarkersInMarkdown(stripEmptyHtmlComments(result));
}

/** Full CGV layout pass — only for explicit «Corregir estilo». */
export function normalizeCgvMarkdown(md: string): string {
  return fixCgvPassageLayout(sanitizeCgvMarkdown(md));
}

/** Trim-only compare — detects spacing/layout diffs normalizeCgvMarkdown would fix. */
export function normalizeMdForCompare(md: string): string {
  return String(md || "")
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+$/gm, "")
    .trim();
}

export function isDefinitionGlossLine(line: string): boolean {
  return /^:\s*\S/.test(String(line || "").trim());
}

/** Default CGV passage spacing for Markdown view and Manual export. */
export function tightenCgvDefaultSpacing(md: string): string {
  let result = String(md || "");
  // ### referencia + blank + versículo → no blank line
  result = result.replace(/^(### [^\n]+)\n\n(?!(#{1,6}\s|<!--\s*@))/gm, "$1\n");
  // versículo + #### ancla → one blank line
  result = ensureVerseToH4BlankLine(result);
  // #### ancla + blank + ##### comentario → no blank line
  result = result.replace(/^(#### [^\n]+)\n\n(##### )/gm, "$1\n$2");
  return result;
}

export function markdownToEditorHtml(body: string): string {
  return blocksToEditorHtml(parseBodyToBlocks(body || ""));
}

/** Loose HTML compare for Manual vs canonical CGV render. */
export function normalizeEditorHtmlForCompare(html: string): string {
  return String(html || "")
    .replace(/>\s+</g, "><")
    .replace(/\s+/g, " ")
    .trim();
}

export function canonicalManualEditorHtml(body: string): string {
  return markdownToEditorHtml(normalizeCgvMarkdown(body));
}

export function editorHtmlToMarkdown(html: string): string {
  const blocks = htmlToBlocks(stripEmptyHtmlComments(html || ""));
  return coerceQuizMarkersInMarkdown(tightenCgvDefaultSpacing(compileBlocks(blocks)).trimEnd());
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

/** Start index of the markdown body inside a full document string (after YAML). */
export function bodyStartInContent(content: string): number {
  const split = splitYamlBody(content);
  if (!split.frontMatter.trim()) return 0;
  return content.length - split.body.length;
}
