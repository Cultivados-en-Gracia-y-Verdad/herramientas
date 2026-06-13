import { formatScriptureLine } from "cgv-bible";
import { compileBlocks } from "./blocks/compile";
import { parseBodyToBlocks } from "./blocks/parse";
import type { CommentaryBlock, ContentBlock } from "./blocks/types";
import { newBlockId } from "./blocks/types";
import { loadBibleIndex, resolveReferenceFromLibrary } from "./bible-client";
import {
  isLikelyBibleReference,
  normalizeCgvMarkdown,
  sanitizeH4AnchorText
} from "./markdown-html";

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
  let needsAnchor = false;

  for (const block of normalized) {
    if (
      block.type === "slideBreak" ||
      block.type === "h1" ||
      block.type === "h2" ||
      block.type === "quiz" ||
      block.type === "definition" ||
      block.type === "synthesis"
    ) {
      needsAnchor = false;
      out.push(cloneBlock(block));
      continue;
    }

    if (block.type === "verse") {
      needsAnchor = true;

      if (!isLikelyBibleReference(block.reference)) {
        out.push(...demotedVerseBlocks(block.reference, block.scripture));
        stats.referencesDemoted += 1;
        needsAnchor = false;
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
      continue;
    }

    if (block.type === "focus") {
      needsAnchor = false;
      out.push(focusBlock(block.phrase));
      continue;
    }

    if (block.type === "commentary") {
      const comm = cloneCommentary(block);

      if (needsAnchor) {
        if (comm.title) {
          out.push(focusBlock(comm.title));
          stats.anchorsSet += 1;
          needsAnchor = false;
          if (comm.bullets.length) {
            out.push(commentaryBlock("", comm.bullets));
          }
        } else if (comm.bullets.length) {
          needsAnchor = false;
          out.push(comm);
        }
        continue;
      }

      out.push(comm);
      if (comm.title) {
        stats.linesPromotedToH5 += 1;
      }
      continue;
    }

    if (block.type === "paragraph") {
      const text = block.text.trim();
      if (!text) continue;

      if (text.startsWith("- ")) {
        out.push(commentaryBlock("", [text.slice(2).trim()]));
        continue;
      }

      if (needsAnchor) {
        out.push(focusBlock(text));
        stats.anchorsSet += 1;
        needsAnchor = false;
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

  const parsed = parseBodyToBlocks(source);
  const corrected = await transformBlocks(parsed, stats, warnings);
  const compiled = normalizeCgvMarkdown(compileBlocks(corrected));
  const normalizedSource = normalizeCgvMarkdown(source.trim());

  const changed =
    compiled !== normalizedSource ||
    stats.scriptureUpdated > 0 ||
    stats.anchorsSet > 0 ||
    stats.linesPromotedToH5 > 0 ||
    stats.referencesDemoted > 0;

  return {
    body: compiled,
    changed,
    stats,
    warnings
  };
}
