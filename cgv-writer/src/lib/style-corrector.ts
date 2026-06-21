import { formatScriptureLine } from "cgv-bible";
import { compileBlocks } from "./blocks/compile";
import { parseBodyToBlocks } from "./blocks/parse";
import type { CommentaryBlock, ContentBlock } from "./blocks/types";
import { newBlockId } from "./blocks/types";
import { loadBibleIndex, resolveReferenceFromLibrary } from "./bible-client";
import {
  isLikelyBibleReference,
  isDefinitionGlossLine,
  normalizeCgvMarkdown,
  sanitizeH4AnchorText
} from "./markdown-html";
import { cleanBlockquoteLine, isBlockquoteLine } from "./synthesis-block";

export interface StyleCorrectStats {
  scriptureUpdated: number;
  anchorsSet: number;
  linesPromotedToH5: number;
  referencesDemoted: number;
}

export interface StyleCorrectResult {
  body: string;
  changed: boolean;
  stats: StyleCorrectStats;
  warnings: string[];
}

function normalizeMdForCompare(md: string): string {
  return String(md || "")
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+$/gm, "")
    .trim();
}

function cloneBlock<T extends ContentBlock>(block: T): T {
  return { ...block, id: newBlockId() };
}

function focusBlock(phrase: string): ContentBlock {
  return {
    id: newBlockId(),
    type: "focus",
    phrase: sanitizeH4AnchorText(phrase)
  };
}

/** Normalize inline markdown headings stored as plain paragraphs. */
function normalizeMisplacedHeading(block: ContentBlock): ContentBlock[] {
  if (block.type !== "paragraph") return [block];

  const text = block.text.trim();
  if (!text) return [];

  if (isBlockquoteLine(text)) {
    return [
      {
        id: newBlockId(),
        type: "synthesis",
        title: cleanBlockquoteLine(text),
        bullets: []
      }
    ];
  }

  if (/^:::/.test(text)) {
    return [{ id: newBlockId(), type: "raw", text: block.text }];
  }

  if (isDefinitionGlossLine(text)) {
    return [block];
  }

  if (/^######\s+/.test(text)) {
    return [commentaryBlock("", [text.replace(/^######\s+/, "")])];
  }

  if (/^#####\s+/.test(text)) {
    return [commentaryBlock(text.replace(/^#####\s+/, ""))];
  }

  if (/^-\s+/.test(text)) {
    return [commentaryBlock("", [text.replace(/^-\s+/, "")])];
  }

  if (/^####\s+/.test(text)) {
    return [focusBlock(text.replace(/^####\s+/, "").trim())];
  }

  if (/^###\s+/.test(text)) {
    return [
      {
        id: newBlockId(),
        type: "verse",
        reference: text.replace(/^###\s+/, "").trim(),
        scripture: ""
      }
    ];
  }

  return [block];
}

function commentaryBlock(title: string, bullets: string[] = []): CommentaryBlock {
  return {
    id: newBlockId(),
    type: "commentary",
    title: title.trim(),
    bullets: bullets.map(item => item.trim()).filter(Boolean)
  };
}

function cloneCommentary(block: CommentaryBlock): CommentaryBlock {
  return commentaryBlock(block.title, block.bullets);
}

function normalizeVerseComparisonText(text: string): string {
  return String(text || "")
    .trim()
    .toLowerCase()
    .replace(/[«»"""\u201C\u201D]/g, "")
    .replace(/\s+/g, " ");
}

/** Plain text or H4 anchor that repeats the start of the verse — not a real focus phrase. */
function isDuplicateVerseFragment(scripture: string, text: string): boolean {
  const s = normalizeVerseComparisonText(scripture);
  const t = normalizeVerseComparisonText(text);
  if (!t || t.length < 12 || !s) return false;
  if (s.startsWith(t)) return true;
  if (t.length >= 20 && s.includes(t)) return true;
  return false;
}

function demotedVerseBlocks(reference: string, scripture: string): ContentBlock[] {
  const out: ContentBlock[] = [];
  const ref = reference.trim();
  const verse = scripture.trim();

  if (ref) {
    out.push({
      id: newBlockId(),
      type: "commentary",
      title: ref,
      bullets: []
    });
  }

  if (verse) {
    out.push({
      id: newBlockId(),
      type: "commentary",
      title: verse,
      bullets: []
    });
  }

  return out;
}

function mergeConsecutiveBulletLists(blocks: ContentBlock[]): ContentBlock[] {
  const out: ContentBlock[] = [];

  for (const block of blocks) {
    const prev = out[out.length - 1];
    if (
      block.type === "commentary" &&
      !block.title.trim() &&
      block.bullets.length &&
      prev?.type === "commentary" &&
      !prev.title.trim() &&
      prev.bullets.length
    ) {
      out[out.length - 1] = commentaryBlock("", [...prev.bullets, ...block.bullets]);
      continue;
    }
    out.push(block);
  }

  return out;
}

async function resolveScriptureText(reference: string): Promise<string | null> {
  const resolved = await resolveReferenceFromLibrary(reference);
  if (!resolved?.verses?.length) return null;
  const line = formatScriptureLine(resolved.verses).trim();
  return line || null;
}

async function transformBlocks(
  blocks: ContentBlock[],
  stats: StyleCorrectStats,
  warnings: string[]
): Promise<ContentBlock[]> {
  const normalized = blocks.flatMap(block => normalizeMisplacedHeading(block));
  const out: ContentBlock[] = [];
  let afterVerseScripture: string | null = null;

  for (const block of normalized) {
    if (
      block.type === "slideBreak" ||
      block.type === "h1" ||
      block.type === "h2" ||
      block.type === "quiz" ||
      block.type === "definition" ||
      block.type === "synthesis" ||
      block.type === "table" ||
      block.type === "raw"
    ) {
      afterVerseScripture = null;
      out.push(cloneBlock(block));
      continue;
    }

    if (block.type === "verse") {
      if (!isLikelyBibleReference(block.reference)) {
        afterVerseScripture = null;
        out.push(...demotedVerseBlocks(block.reference, block.scripture));
        stats.referencesDemoted += 1;
        continue;
      }

      let scripture = block.scripture.trim();
      const fetched = await resolveScriptureText(block.reference);
      if (fetched) {
        if (fetched !== scripture) {
          stats.scriptureUpdated += 1;
        }
        scripture = fetched;
      } else if (!scripture) {
        warnings.push(`Sin texto NBLA: ${block.reference.trim()}`);
      }

      out.push({
        id: newBlockId(),
        type: "verse",
        reference: block.reference.trim(),
        scripture
      });
      afterVerseScripture = scripture;
      continue;
    }

    if (block.type === "focus") {
      if (afterVerseScripture && isDuplicateVerseFragment(afterVerseScripture, block.phrase)) {
        continue;
      }
      afterVerseScripture = null;
      out.push(focusBlock(block.phrase));
      continue;
    }

    if (block.type === "commentary") {
      afterVerseScripture = null;
      out.push(cloneCommentary(block));
      continue;
    }

    if (block.type === "paragraph") {
      const text = block.text.trim();
      if (!text) continue;

      if (isBlockquoteLine(text) || /^:::/.test(text) || isDefinitionGlossLine(text)) {
        afterVerseScripture = null;
        out.push(cloneBlock(block));
        continue;
      }

      if (text.startsWith("- ")) {
        afterVerseScripture = null;
        out.push(commentaryBlock("", [text.slice(2).trim()]));
        continue;
      }

      if (afterVerseScripture && isDuplicateVerseFragment(afterVerseScripture, text)) {
        continue;
      }

      if (afterVerseScripture) {
        out.push(cloneBlock(block));
        continue;
      }

      out.push(commentaryBlock(text));
      stats.linesPromotedToH5 += 1;
    }
  }

  return mergeConsecutiveBulletLists(out);
}

export async function correctManualStyle(body: string): Promise<StyleCorrectResult> {
  const source = String(body || "");
  const stats: StyleCorrectStats = {
    scriptureUpdated: 0,
    anchorsSet: 0,
    linesPromotedToH5: 0,
    referencesDemoted: 0
  };
  const warnings: string[] = [];

  if (!source.trim()) {
    return {
      body: source,
      changed: false,
      stats,
      warnings: ["El manual está vacío."]
    };
  }

  await loadBibleIndex();

  const trimmedSource = source.trim();
  const parsed = parseBodyToBlocks(trimmedSource);
  const corrected = await transformBlocks(parsed, stats, warnings);
  const compiled = normalizeCgvMarkdown(compileBlocks(corrected));

  const changed = normalizeMdForCompare(compiled) !== normalizeMdForCompare(trimmedSource);

  return {
    body: compiled,
    changed,
    stats,
    warnings
  };
}
