import type { BibleVerse } from "cgv-bible";
import titusMorph from "../../../cgv-data/morphology/MorphGNT/77-Tit-morphgnt.txt?raw";
import titusAlignment from "../../MNA/datasets/interlinear/NT/tito.tokens.jsonl?raw";
import titusRv1909 from "../../../cgv-data/bibles/RV1909/md/56.content.md?raw";
import {
  crossReferenceVerseTokens,
  findWordIndexBySurface,
  loadRv1909AlignmentByVerse,
  resolveRv1909WordIndexes
} from "./rv1909-alignment";

// The Clause Builder pipeline (Brick 1-3, clause spans, observations) reads
// RV1909 — a manually-verified word-level Greek alignment exists for it, so
// finite-verb/particle anchoring is a lookup, not a guess. NBLA remains the
// text for the main Reader (see reader-data.ts / ReaderApp.tsx), which is
// untouched by this module.
function parseRv1909Content(content: string): BibleVerse[] {
  const verses: BibleVerse[] = [];
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  let pendingChapter: number | null = null;
  let pendingVerse: number | null = null;

  for (const line of lines) {
    const header = line.match(/^#+\s*Tito\s+(\d+):(\d+)/i);
    if (header) {
      pendingChapter = Number(header[1]);
      pendingVerse = Number(header[2]);
      continue;
    }

    if (pendingChapter === null || pendingVerse === null) continue;
    const trimmed = line.trim();
    if (!trimmed) continue;

    const text = trimmed.replace(/^\d+/, "").trim();
    if (text) {
      verses.push({ book: "Tito", chapter: pendingChapter, verse: pendingVerse, text });
    }
    pendingChapter = null;
    pendingVerse = null;
  }

  return verses;
}

export interface SpanishWord {
  id: string;
  chapter: number;
  verse: number;
  index: number;
  text: string;
  finiteVerbId: string | null;
  dependentIntroducerId: string | null;
  greekSurface?: string;
  greekMorph?: string;
  greekLemma?: string;
  dependentGreekSurface?: string;
  startChar: number;
  endChar: number;
}

export interface SpanishClauseVerse {
  chapter: number;
  verse: number;
  label: string;
  text: string;
  words: SpanishWord[];
}

interface FiniteAlignment {
  id: string;
  chapter: number;
  verse: number;
  token: number;
  greekSurface: string;
  greekMorph: string;
  greekLemma: string;
  spanishHint: string;
}

export interface ClauseAssignment {
  finiteVerbId: string;
  selectedSpan: string[];
  greekStartTokenId?: string;
  greekEndTokenId?: string;
}

export type ClauseAssignments = Record<string, ClauseAssignment>;

export interface ClauseBeginningToken {
  id: string;
  greek: string;
  ble: string;
  lemma: string;
  morph: string;
}

export interface GreekClauseRange {
  greekStartTokenId: string;
  greekEndTokenId: string;
}

const WORD_PATTERN = /[\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\s\wáéíóúüñÁÉÍÓÚÜÑ]+/gu;
const FINITE_MARKS_KEY = "o-prototype:titus:finite-verb-marks";
const DEPENDENT_INTRODUCER_MARKS_KEY = "roots:titus:brick3:dependentThoughtIntroducers";
export const CLAUSE_STORAGE_KEY = "the-reader:spanish-clause-builder:titus:v3";
const LEGACY_CLAUSE_STORAGE_KEY = "the-reader:clause-builder:titus:1:1-4:v2";
const DEPENDENT_INTRODUCER_SURFACES = new Set([
  "ἵνα",
  "ὅτι",
  "εἰ",
  "ἐάν",
  "ὅταν",
  "ἐπειδή",
  "ἐπεί",
  "καθώς",
  "ὡς",
  "πρίν"
]);

function wordId(chapter: number, verse: number, index: number): string {
  return `${chapter}:${verse}:${index}`;
}

function finiteAlignmentId(chapter: number, verse: number, token: number): string {
  return `${chapter}:${verse}:${token}`;
}

function parseAlignmentId(id: string): { chapter: number; verse: number; token: number } | null {
  const [chapter, verse, token] = id.split(":").map(Number);
  if (!Number.isFinite(chapter) || !Number.isFinite(verse) || !Number.isFinite(token)) return null;
  return { chapter, verse, token };
}

function stripGreekPunctuation(value: string): string {
  return value.replace(/[⸀⸁⸂⸃,.;·]/g, "");
}

export function readMarkedAlignmentIds(storageKey: string): Set<string> {
  let markedGreekIds: string[];

  try {
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) return new Set();
    const parsed = JSON.parse(stored);
    markedGreekIds = Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return new Set();
  }

  if (!markedGreekIds.length) return new Set();

  const markedGreekIdSet = new Set(markedGreekIds);
  const alignmentIds = new Set<string>();
  const verseTokenCounts = new Map<string, number>();

  titusMorph
    .replace(/\r\n/g, "\n")
    .split("\n")
    .forEach((line, index) => {
      const match = line.trim().match(/^(\d{6})\s+/);
      if (!match) return;

      const reference = match[1];
      const chapter = Number(reference.slice(2, 4));
      const verse = Number(reference.slice(4, 6));
      const verseKey = `${chapter}:${verse}`;
      const token = (verseTokenCounts.get(verseKey) ?? 0) + 1;
      verseTokenCounts.set(verseKey, token);

      if (markedGreekIdSet.has(`${reference}-${index}`)) {
        alignmentIds.add(finiteAlignmentId(chapter, verse, token));
      }
    });

  return alignmentIds;
}

function readFiniteMarkedAlignmentIds(): Set<string> {
  return readMarkedAlignmentIds(FINITE_MARKS_KEY);
}

function readDependentIntroducerMarkedAlignmentIds(): Set<string> {
  return readMarkedAlignmentIds(DEPENDENT_INTRODUCER_MARKS_KEY);
}

function tokenizeVerse(verse: BibleVerse): SpanishWord[] {
  const words: SpanishWord[] = [];
  let index = 0;
  const pattern = new RegExp(WORD_PATTERN.source, WORD_PATTERN.flags);

  for (let match = pattern.exec(verse.text); match; match = pattern.exec(verse.text)) {
    const piece = match[0];
    if (!/[\wáéíóúüñÁÉÍÓÚÜÑ]/i.test(piece)) continue;
    words.push({
      id: wordId(verse.chapter, verse.verse, index),
      chapter: verse.chapter,
      verse: verse.verse,
      index,
      text: piece,
      finiteVerbId: null,
      dependentIntroducerId: null,
      startChar: match.index,
      endChar: match.index + piece.length
    });
    index += 1;
  }

  return words;
}

function parseFiniteAlignments(): FiniteAlignment[] {
  return titusAlignment
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map(line => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter((row): row is Record<string, unknown> => Boolean(row))
    .filter(row => {
      return (
        row.book === "tito" &&
        typeof row.ch === "number" &&
        typeof row.vs === "number" &&
        typeof row.tok === "number" &&
        typeof row.surface === "string" &&
        typeof row.morph === "string" &&
        typeof row.es === "string" &&
        /^V-[123]/.test(row.morph)
      );
    })
    .map(row => ({
      id: finiteAlignmentId(row.ch as number, row.vs as number, row.tok as number),
      chapter: row.ch as number,
      verse: row.vs as number,
      token: row.tok as number,
      greekSurface: row.surface as string,
      greekMorph: row.morph as string,
      greekLemma: typeof row.lemma === "string" ? row.lemma : "",
      spanishHint: row.es as string
    }));
}

function parseTokenAlignments(): FiniteAlignment[] {
  return titusAlignment
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map(line => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter((row): row is Record<string, unknown> => Boolean(row))
    .filter(row => {
      return (
        row.book === "tito" &&
        typeof row.ch === "number" &&
        typeof row.vs === "number" &&
        typeof row.tok === "number" &&
        typeof row.surface === "string" &&
        typeof row.morph === "string" &&
        typeof row.es === "string"
      );
    })
    .map(row => ({
      id: finiteAlignmentId(row.ch as number, row.vs as number, row.tok as number),
      chapter: row.ch as number,
      verse: row.vs as number,
      token: row.tok as number,
      greekSurface: row.surface as string,
      greekMorph: row.morph as string,
      greekLemma: typeof row.lemma === "string" ? row.lemma : "",
      spanishHint: row.es as string
    }));
}

/**
 * Verses whose Greek text has no finite verb at all (e.g. Titus 1:1's long
 * verbless run of appositions) — computed from the Greek morphology directly,
 * independent of whether Brick 1 marking has reached that verse yet. These
 * are deliberately out of scope for the skeleton pass (spec: "Do not invent
 * a category for them now... leave them alone"); this only identifies them
 * so the app can show them as visibly excluded rather than silently absent.
 */
export function getVersesWithoutFiniteVerb(): Set<string> {
  const hasFiniteVerb = new Set<string>();
  const allVerses = new Set<string>();

  for (const alignment of parseTokenAlignments()) {
    const key = `${alignment.chapter}:${alignment.verse}`;
    allVerses.add(key);
    if (/^V-[123]/.test(alignment.greekMorph)) hasFiniteVerb.add(key);
  }

  const verbless = new Set<string>();
  for (const key of allVerses) {
    if (!hasFiniteVerb.has(key)) verbless.add(key);
  }
  return verbless;
}

/**
 * Builds a Greek-token-number -> RV1909-word-index map for one verse, by
 * chaining the app's own Greek tokens through Mission Mutual's verified
 * alignment to RV1909's target text, then locating that text in the verse's
 * own tokenized word array. Replaces the old fuzzy-matching anchor logic
 * entirely — every step here is either a direct lookup or an exact match.
 */

// Genuine gaps in Mission Mutual's alignment — these tokens have no record
// at all (confirmed by direct inspection, not a matching failure). Unlike
// the old NBLA overrides (16 cases, born from a systematic gloss vs.
// translation mismatch), this is a handful of honest omissions, each
// verified against RV1909's actual text. Only applied when no record exists.
const RV1909_ALIGNMENT_GAPS: Record<string, string> = {
  "1:5:3": "dejé", // ἀπέλιπόν — absent from Mission Mutual's source list for 1:5
  "1:7:1": "es", // δεῖ — absent from Mission Mutual's source list for 1:7; RV1909 renders as "es menester"
  "1:9:10": "pueda", // ᾖ (part of δυνατὸς ᾖ, "may be able") — RV1909 renders as "pueda"
  "2:1:5": "conviene" // πρέπει — RV1909: "lo que conviene á la sana doctrina"
};

// Cases where Mission Mutual DOES have a record, but it points at a word
// that's technically linked but useless as a finite-verb anchor. Always
// applied, overriding the alignment's own target for that token. Found by a
// full-book scan for finite verbs whose target resolves to a Spanish clitic
// pronoun or function word — a recurring pattern for Greek passive/deponent
// or reflexive-sense verbs, where Mission Mutual links to the particle
// carrying the reflexive/passive sense rather than the verb form itself.
const RV1909_ANCHOR_CORRECTIONS: Record<string, string> = {
  // ἐστιν ("is") — aligned to "que"; RV1909 actually renders this clause
  // with "fuere" ("El que fuere sin crimen...").
  "1:6:3": "fuere",
  // Ἐπεφάνη ("appeared/was manifested," passive) — aligned to "se," the
  // reflexive-passive particle in "se manifestó," not the verb itself.
  "2:11:1": "manifestó",
  // ἔδωκεν ("he gave") — Mission Mutual aligns this to "se," the reflexive
  // pronoun in "se dió á sí mismo" ("gave himself"), not the verb form
  // itself. Defensible as a semantic pairing, useless for marking the
  // clause's finite verb — "dió" is what a student needs to click.
  "2:14:2": "dió"
};

function buildVerseTokenWordMap(
  chapter: number,
  verse: number,
  words: SpanishWord[]
): Map<number, number> {
  const currentTokens = parseTokenAlignments()
    .filter(alignment => alignment.chapter === chapter && alignment.verse === verse)
    .sort((a, b) => a.token - b.token)
    .map(alignment => ({ token: alignment.token, surface: alignment.greekSurface }));

  const records = loadRv1909AlignmentByVerse().get(`${chapter}:${verse}`) ?? [];
  const crossReference = crossReferenceVerseTokens(currentTokens, records);

  for (const { token } of currentTokens) {
    const key = `${chapter}:${verse}:${token}`;
    if (RV1909_ANCHOR_CORRECTIONS[key]) {
      crossReference.set(token, RV1909_ANCHOR_CORRECTIONS[key]);
    } else if (!crossReference.has(token) && RV1909_ALIGNMENT_GAPS[key]) {
      crossReference.set(token, RV1909_ALIGNMENT_GAPS[key]);
    }
  }

  const resolved = resolveRv1909WordIndexes(
    currentTokens.map(token => token.token),
    crossReference,
    words
  );

  // A gap-fill/correction may point at a word another token already
  // legitimately holds (e.g. δυνατὸς ᾖ, "may be able," collapsing into
  // RV1909's one word "pueda") — that's not a conflict, it's two Greek words
  // sharing one Spanish word. Only reached when the normal exclusive
  // resolution left an overridden token unplaced.
  for (const { token } of currentTokens) {
    if (resolved.has(token)) continue;
    const key = `${chapter}:${verse}:${token}`;
    const override = RV1909_ANCHOR_CORRECTIONS[key] ?? RV1909_ALIGNMENT_GAPS[key];
    if (!override) continue;
    const index = findWordIndexBySurface(words, override);
    if (index !== null) resolved.set(token, index);
  }

  return resolved;
}

export function loadTitusClauseVerses(): SpanishClauseVerse[] {
  const verses = parseRv1909Content(titusRv1909).map(verse => ({
    chapter: verse.chapter,
    verse: verse.verse,
    label: `Tito ${verse.chapter}:${verse.verse}`,
    text: verse.text,
    words: tokenizeVerse(verse)
  }));

  const verseByKey = new Map(verses.map(verse => [`${verse.chapter}:${verse.verse}`, verse]));
  const markedFiniteAlignmentIds = readFiniteMarkedAlignmentIds();
  const markedDependentIntroducerAlignmentIds = readDependentIntroducerMarkedAlignmentIds();
  const tokenWordMapCache = new Map<string, Map<number, number>>();

  function getTokenWordMap(chapter: number, verse: number, words: SpanishWord[]): Map<number, number> {
    const key = `${chapter}:${verse}`;
    const cached = tokenWordMapCache.get(key);
    if (cached) return cached;
    const map = buildVerseTokenWordMap(chapter, verse, words);
    tokenWordMapCache.set(key, map);
    return map;
  }

  for (const alignment of parseFiniteAlignments()) {
    if (!markedFiniteAlignmentIds.has(alignment.id)) continue;

    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;
    const wordIndex = getTokenWordMap(alignment.chapter, alignment.verse, verse.words).get(alignment.token);
    if (wordIndex === undefined) continue;
    const anchor = verse.words[wordIndex];
    anchor.finiteVerbId = alignment.id;
    anchor.greekSurface = alignment.greekSurface;
    anchor.greekMorph = alignment.greekMorph;
    anchor.greekLemma = alignment.greekLemma;
  }

  for (const alignment of parseTokenAlignments()) {
    if (!markedDependentIntroducerAlignmentIds.has(alignment.id)) continue;
    if (!DEPENDENT_INTRODUCER_SURFACES.has(stripGreekPunctuation(alignment.greekSurface))) continue;

    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;

    const wordIndex = getTokenWordMap(alignment.chapter, alignment.verse, verse.words).get(alignment.token);
    if (wordIndex === undefined) continue;
    const word = verse.words[wordIndex];
    if (!word) continue;
    word.dependentIntroducerId = alignment.id;
    word.dependentGreekSurface = alignment.greekSurface;
  }

  return verses;
}

export function wordInSpan(word: SpanishWord, selectedSpan: string[] | null): boolean {
  return Boolean(selectedSpan?.includes(word.id));
}

export function spanFromRange(start: SpanishWord, end: SpanishWord): string[] | null {
  if (start.chapter !== end.chapter || start.verse !== end.verse) return null;
  const low = Math.min(start.index, end.index);
  const high = Math.max(start.index, end.index);
  const ids: string[] = [];
  for (let index = low; index <= high; index += 1) {
    ids.push(wordId(start.chapter, start.verse, index));
  }
  return ids;
}

export function formatClauseSpan(
  selectedSpan: string[],
  verseWords: SpanishWord[],
  verseText?: string
): string {
  const selected = selectedSpan
    .map(id => verseWords.find(word => word.id === id))
    .filter((word): word is SpanishWord => Boolean(word))
    .sort((a, b) => a.index - b.index);
  if (!selected.length) return "";

  if (verseText) {
    return verseText.slice(selected[0].startChar, selected[selected.length - 1].endChar);
  }

  return selected.map(word => word.text).join(" ");
}

export function getClauseBeginningTokens(
  range: GreekClauseRange | null
): ClauseBeginningToken[] {
  if (!range) return [];
  const start = parseAlignmentId(range.greekStartTokenId);
  const end = parseAlignmentId(range.greekEndTokenId);
  if (!start || !end || start.chapter !== end.chapter || start.verse !== end.verse) return [];

  const low = Math.min(start.token, end.token);
  const high = Math.max(start.token, end.token);

  return parseTokenAlignments()
    .filter(alignment => alignment.chapter === start.chapter && alignment.verse === start.verse)
    .filter(alignment => alignment.token >= low && alignment.token <= high)
    .map(alignment => ({
      id: alignment.id,
      greek: stripGreekPunctuation(alignment.greekSurface),
      lemma: alignment.greekLemma,
      morph: alignment.greekMorph,
      ble: alignment.spanishHint.replace(/·/g, " ")
    }))
    .slice(0, 12);
}

export function deriveGreekClauseRange(
  selectedSpan: string[],
  verseWords: SpanishWord[],
  finiteVerbId: string
): GreekClauseRange | null {
  const selectedIds = new Set(selectedSpan);
  const finiteVerbPosition = parseAlignmentId(finiteVerbId);
  const firstWord = verseWords.find(word => selectedIds.has(word.id));
  if (!firstWord || !finiteVerbPosition) return null;

  const verseTokens = parseTokenAlignments()
    .filter(alignment => alignment.chapter === firstWord.chapter && alignment.verse === firstWord.verse)
    .sort((a, b) => a.token - b.token);
  const finiteToken = verseTokens.find(alignment => alignment.id === finiteVerbId);
  if (!finiteToken) return null;

  const tokenWordMap = buildVerseTokenWordMap(firstWord.chapter, firstWord.verse, verseWords);
  const selectedTokenIds = verseTokens
    .filter(alignment => {
      if (alignment.id === finiteVerbId) return true;
      const wordIndex = tokenWordMap.get(alignment.token);
      if (wordIndex === undefined) return false;
      return selectedIds.has(wordId(alignment.chapter, alignment.verse, wordIndex));
    })
    .map(alignment => alignment.token);

  const previousBoundaryTokens = verseTokens
    .filter(alignment => alignment.token < finiteToken.token)
    .filter(alignment => /[,.;·]/.test(alignment.greekSurface) || /^V-[123]/.test(alignment.greekMorph));
  const previousBoundaryToken = previousBoundaryTokens[previousBoundaryTokens.length - 1];
  const startToken = Math.max((previousBoundaryToken?.token ?? 0) + 1, 1);
  const endToken = Math.max(...selectedTokenIds, finiteVerbPosition.token);

  return {
    greekStartTokenId: finiteAlignmentId(firstWord.chapter, firstWord.verse, startToken),
    greekEndTokenId: finiteAlignmentId(firstWord.chapter, firstWord.verse, endToken)
  };
}

function legacySpanToIds(value: unknown): string[] {
  if (!value || typeof value !== "object") return [];
  const span = value as { chapter?: unknown; verse?: unknown; startIndex?: unknown; endIndex?: unknown };
  if (
    typeof span.chapter !== "number" ||
    typeof span.verse !== "number" ||
    typeof span.startIndex !== "number" ||
    typeof span.endIndex !== "number"
  ) {
    return [];
  }
  const low = Math.min(span.startIndex, span.endIndex);
  const high = Math.max(span.startIndex, span.endIndex);
  const ids: string[] = [];
  for (let index = low; index <= high; index += 1) {
    ids.push(wordId(span.chapter, span.verse, index));
  }
  return ids;
}

function parseStoredClauseAssignments(stored: string | null): ClauseAssignments {
  if (!stored) return {};
  try {
    const parsed = JSON.parse(stored);
    if (!parsed || typeof parsed !== "object") return {};
    const out: ClauseAssignments = {};

    for (const [finiteVerbId, value] of Object.entries(parsed)) {
      if (typeof finiteVerbId !== "string") continue;
      if (Array.isArray(value)) {
        const selectedSpan = value.filter((id): id is string => typeof id === "string");
        if (selectedSpan.length) out[finiteVerbId] = { finiteVerbId, selectedSpan };
        continue;
      }
      if (!value || typeof value !== "object") continue;
      const record = value as {
        finiteVerbId?: unknown;
        selectedSpan?: unknown;
        greekStartTokenId?: unknown;
        greekEndTokenId?: unknown;
      };
      if (Array.isArray(record.selectedSpan)) {
        const selectedSpan = record.selectedSpan.filter((id): id is string => typeof id === "string");
        if (selectedSpan.length) {
          out[finiteVerbId] = {
            finiteVerbId: typeof record.finiteVerbId === "string" ? record.finiteVerbId : finiteVerbId,
            selectedSpan,
            ...(typeof record.greekStartTokenId === "string" ? { greekStartTokenId: record.greekStartTokenId } : {}),
            ...(typeof record.greekEndTokenId === "string" ? { greekEndTokenId: record.greekEndTokenId } : {})
          };
        }
        continue;
      }
      const selectedSpan = legacySpanToIds(value);
      if (selectedSpan.length) out[finiteVerbId] = { finiteVerbId, selectedSpan };
    }

    return out;
  } catch {
    return {};
  }
}

export function readClauseAssignments(): ClauseAssignments {
  const current = parseStoredClauseAssignments(window.localStorage.getItem(CLAUSE_STORAGE_KEY));
  if (Object.keys(current).length) return current;

  const legacy = parseStoredClauseAssignments(window.localStorage.getItem(LEGACY_CLAUSE_STORAGE_KEY));
  if (Object.keys(legacy).length) writeClauseAssignments(legacy);
  return legacy;
}

export function writeClauseAssignments(assignments: ClauseAssignments): void {
  window.localStorage.setItem(CLAUSE_STORAGE_KEY, JSON.stringify(assignments));
}
