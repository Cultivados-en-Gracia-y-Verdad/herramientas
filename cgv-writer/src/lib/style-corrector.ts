import { formatScriptureLine } from "cgv-bible";
import { compileBlocks } from "./blocks/compile";
import { parseBodyToBlocks } from "./blocks/parse";
import type { CommentaryBlock, ContentBlock } from "./blocks/types";
import { newBlockId } from "./blocks/types";
import { loadBibleIndex, resolveReferenceFromLibrary } from "./bible-client";
import {
  checkContentPreserved,
  normalizeContentFingerprint,
  safeMarkdownTransform
} from "./content-preservation";
import {
  isLikelyBibleReference,
  isDefinitionGlossLine,
  normalizeCgvMarkdown,
  normalizeMdForCompare,
  sanitizeH4AnchorText,
  stripCommentWrapper
} from "./markdown-html";
import { isBlockquoteLine } from "./synthesis-block";

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

  const text = stripCommentWrapper(block.text);
  if (!text) return [block];

  if (isBlockquoteLine(text)) {
    return [block];
  }

  if (/^:::/.test(text)) {
    return [{ id: newBlockId(), type: "raw", text: block.text }];
  }

  if (isDefinitionGlossLine(text)) {
    return [block];
  }

  if (/^######\s+/.test(text)) {
    return [commentaryBlock("", [], text.replace(/^######\s+/, ""))];
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

function commentaryBlock(title: string, bullets: string[] = [], h6?: string): CommentaryBlock {
  return {
    id: newBlockId(),
    type: "commentary",
    title: title.trim(),
    h6: h6?.trim() || undefined,
    bullets: bullets.map(item => item.trim()).filter(Boolean)
  };
}

function cloneCommentary(block: CommentaryBlock): CommentaryBlock {
  return commentaryBlock(block.title, block.bullets, block.h6);
}

function normalizeSpillLine(text: string): string {
  return String(text || "")
    .trim()
    .toLowerCase()
    .replace(/[«»"""\u201C\u201D]/g, "")
    .replace(/\s+/g, " ");
}

function spillLinesFromVerseScripture(scripture: string, canonical: string): string[] {
  const canonicalNorm = normalizeSpillLine(canonical);
  if (!canonicalNorm) return [];

  const spill: string[] = [];
  for (const line of scripture.split("\n").map(item => item.trim()).filter(Boolean)) {
    const lineNorm = normalizeSpillLine(line);
    if (!lineNorm || lineNorm === canonicalNorm) continue;
    if (canonicalNorm.includes(lineNorm) && lineNorm.length >= 20) continue;
    spill.push(line);
  }
  return spill;
}

function scriptureFingerprints(scripture: string): Set<string> {
  const out = new Set<string>();
  for (const line of scripture.split("\n")) {
    const fp = normalizeContentFingerprint(line);
    if (fp) out.add(fp);
  }
  return out;
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
      prev?.type === "commentary" &&
      prev.h6?.trim() &&
      !prev.title.trim() &&
      !prev.bullets.length &&
      !block.title.trim() &&
      block.bullets.length
    ) {
      out[out.length - 1] = commentaryBlock("", block.bullets, prev.h6);
      continue;
    }
    if (
      block.type === "commentary" &&
      !block.title.trim() &&
      block.bullets.length &&
      prev?.type === "commentary" &&
      !prev.title.trim() &&
      prev.bullets.length
    ) {
      out[out.length - 1] = commentaryBlock("", [...prev.bullets, ...block.bullets], prev.h6);
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
  warnings: string[],
  allowedMissingFingerprints: Set<string>
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

      const originalScripture = block.scripture.trim();
      let scripture = originalScripture;
      const fetched = await resolveScriptureText(block.reference);
      if (fetched) {
        if (fetched !== scripture) {
          stats.scriptureUpdated += 1;
          for (const fp of scriptureFingerprints(originalScripture)) {
            allowedMissingFingerprints.add(fp);
          }
        }
        scripture = fetched.trim();
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

      const spill = spillLinesFromVerseScripture(originalScripture, scripture);
      for (const line of spill) {
        out.push(commentaryBlock(line));
        stats.linesPromotedToH5 += 1;
      }
      if (spill.length) {
        afterVerseScripture = null;
      }
      continue;
    }

    if (block.type === "focus") {
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
      const text = stripCommentWrapper(block.text);
      if (!text) {
        out.push(cloneBlock(block));
        continue;
      }

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

function synthesisBulletsFromBlocks(blocks: ContentBlock[]): string[] {
  const bullets: string[] = [];

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    if (block.type !== "synthesis") continue;

    for (const bullet of block.bullets) {
      const norm = normalizeContentFingerprint(bullet);
      if (norm) bullets.push(norm);
    }

    let j = i + 1;
    while (j < blocks.length) {
      const next = blocks[j];
      if (
        next.type === "commentary" &&
        !next.title.trim() &&
        !next.h6?.trim() &&
        next.bullets.length
      ) {
        for (const bullet of next.bullets) {
          const norm = normalizeContentFingerprint(bullet);
          if (norm) bullets.push(norm);
        }
        j++;
        continue;
      }
      break;
    }
  }

  return bullets;
}

function restoreSynthesisBullets(
  sourceBlocks: ContentBlock[],
  correctedBlocks: ContentBlock[]
): ContentBlock[] {
  const sourceByTitle = new Map<string, string[]>();

  for (let i = 0; i < sourceBlocks.length; i++) {
    const block = sourceBlocks[i];
    if (block.type !== "synthesis") continue;

    const key = normalizeContentFingerprint(block.title);
    if (!key) continue;

    const bullets = [...block.bullets];
    let j = i + 1;
    while (j < sourceBlocks.length) {
      const next = sourceBlocks[j];
      if (
        next.type === "commentary" &&
        !next.title.trim() &&
        !next.h6?.trim() &&
        next.bullets.length
      ) {
        bullets.push(...next.bullets);
        j++;
        continue;
      }
      break;
    }

    sourceByTitle.set(key, bullets);
  }

  if (!sourceByTitle.size) return correctedBlocks;

  return correctedBlocks.map(block => {
    if (block.type !== "synthesis") return block;

    const sourceBullets = sourceByTitle.get(normalizeContentFingerprint(block.title));
    if (!sourceBullets?.length) return block;

    const seen = new Set(block.bullets.map(item => normalizeContentFingerprint(item)));
    const restored = [...block.bullets];
    for (const bullet of sourceBullets) {
      const key = normalizeContentFingerprint(bullet);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      restored.push(bullet);
    }

    return restored.length === block.bullets.length
      ? block
      : { ...block, bullets: restored };
  });
}

function filterAllowedMissing(
  loss: ReturnType<typeof checkContentPreserved>,
  allowedMissingFingerprints: Set<string>
): string[] {
  if (!allowedMissingFingerprints.size) return loss.missing;

  return loss.missing.filter(line => {
    const fp = normalizeContentFingerprint(line);
    if (!fp) return true;
    if (!allowedMissingFingerprints.has(fp)) return true;
    allowedMissingFingerprints.delete(fp);
    return false;
  });
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
  const allowedMissingFingerprints = new Set<string>();
  const corrected = restoreSynthesisBullets(
    parsed,
    await transformBlocks(parsed, stats, warnings, allowedMissingFingerprints)
  );

  const compiledRaw = compileBlocks(corrected);
  const layout = safeMarkdownTransform(compiledRaw, normalizeCgvMarkdown);
  if (layout.blocked) {
    return {
      body: trimmedSource,
      changed: false,
      stats,
      warnings: [
        "Corrector cancelado: el ajuste de espaciado eliminaría contenido.",
        ...layout.loss.missing.slice(0, 3).map(line => `· ${line.slice(0, 120)}`)
      ]
    };
  }

  const compiled = layout.output;
  const loss = checkContentPreserved(trimmedSource, compiled);
  const blockedMissing = filterAllowedMissing(loss, allowedMissingFingerprints);

  if (blockedMissing.length) {
    const synthesisMissing = synthesisBulletsFromBlocks(parseBodyToBlocks(trimmedSource)).filter(
      bullet => !synthesisBulletsFromBlocks(parseBodyToBlocks(compiled)).includes(bullet)
    );

    return {
      body: trimmedSource,
      changed: false,
      stats,
      warnings: [
        synthesisMissing.length
          ? `Corrector cancelado: eliminaría ${synthesisMissing.length} punto(s) de «En Síntesis».`
          : `Corrector cancelado: eliminaría ${blockedMissing.length} línea(s) de contenido.`,
        ...blockedMissing.slice(0, 3).map(line => `· ${line.slice(0, 120)}`)
      ]
    };
  }

  const changed = normalizeMdForCompare(compiled) !== normalizeMdForCompare(trimmedSource);

  return {
    body: compiled,
    changed,
    stats,
    warnings
  };
}
