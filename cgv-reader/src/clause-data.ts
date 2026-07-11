import { parseNblaContent } from "cgv-bible";
import type { BibleVerse } from "cgv-bible";
import titusNbla from "../../../cgv-data/bibles/NBLA/tito.nbla.md?raw";
import titusMorph from "../../../cgv-data/morphology/MorphGNT/77-Tit-morphgnt.txt?raw";
import titusAlignment from "../../MNA/datasets/interlinear/NT/tito.tokens.jsonl?raw";

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

const FINITE_ANCHOR_OVERRIDES: Record<string, { text: string; occurrence?: number }> = {
  "1:5:10": { text: "pusieras" },
  "1:5:12": { text: "designaras" },
  "1:10:1": { text: "hay" },
  "1:11:7": { text: "están", occurrence: 1 },
  "1:11:11": { text: "deben" },
  "1:15:13": { text: "están" },
  "2:1:3": { text: "enseña" },
  "2:6:4": { text: "exhorta" },
  "2:14:13": { text: "PURIFICAR" },
  "2:15:4": { text: "exhorta" },
  "2:15:12": { text: "menosprecie" },
  "3:4:8": { text: "manifestó" },
  "3:5:8": { text: "hubiéramos" },
  "3:7:7": { text: "fuéramos" },
  "3:8:19": { text: "es" },
  "3:14:15": { text: "estén" }
};

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

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");
}

function stripGreekPunctuation(value: string): string {
  return value.replace(/[⸀⸁⸂⸃,.;·]/g, "");
}

function spanishHintParts(value: string): string[] {
  return value
    .replace(/·/g, " ")
    .split(/\s+/)
    .map(normalize)
    .filter(Boolean);
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

function findAnchorIndex(
  alignment: FiniteAlignment,
  words: SpanishWord[],
  cursor: number
): number {
  const override = FINITE_ANCHOR_OVERRIDES[alignment.id];
  if (override) {
    const wanted = normalize(override.text);
    const matches = words.filter(word => normalize(word.text) === wanted);
    return matches[(override.occurrence ?? 0)]?.index ?? -1;
  }

  const parts = spanishHintParts(alignment.spanishHint);
  for (const part of parts) {
    if (part.length < 4) continue;
    const exact = words.find(word => word.index >= cursor && normalize(word.text) === part);
    if (exact) return exact.index;
  }

  for (const part of parts) {
    if (part.length < 4) continue;
    const soft = words.find(word => {
      if (word.index < cursor) return false;
      const text = normalize(word.text);
      if (text.length < 4) return false;
      return text.startsWith(part.slice(0, 4)) || part.startsWith(text.slice(0, 4));
    });
    if (soft) return soft.index;
  }

  return -1;
}

function findHintSpanIndexes(alignment: FiniteAlignment, words: SpanishWord[]): number[] {
  const parts = spanishHintParts(alignment.spanishHint).filter(part => part.length >= 2);
  if (!parts.length) return [];

  for (let start = 0; start <= words.length - parts.length; start += 1) {
    const indexes: number[] = [];
    let matches = true;

    for (let offset = 0; offset < parts.length; offset += 1) {
      if (normalize(words[start + offset].text) !== parts[offset]) {
        matches = false;
        break;
      }
      indexes.push(words[start + offset].index);
    }

    if (matches) return indexes;
  }

  const anchorIndex = findAnchorIndex(alignment, words, 0);
  return anchorIndex >= 0 ? [anchorIndex] : [];
}

export function loadTitusClauseVerses(): SpanishClauseVerse[] {
  const verses = parseNblaContent(titusNbla).map(verse => ({
    chapter: verse.chapter,
    verse: verse.verse,
    label: `Tito ${verse.chapter}:${verse.verse}`,
    text: verse.text,
    words: tokenizeVerse(verse)
  }));

  const verseByKey = new Map(verses.map(verse => [`${verse.chapter}:${verse.verse}`, verse]));
  const cursors = new Map<string, number>();
  const markedFiniteAlignmentIds = readFiniteMarkedAlignmentIds();
  const markedDependentIntroducerAlignmentIds = readDependentIntroducerMarkedAlignmentIds();

  for (const alignment of parseFiniteAlignments()) {
    if (!markedFiniteAlignmentIds.has(alignment.id)) continue;

    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;
    const anchorIndex = findAnchorIndex(alignment, verse.words, cursors.get(key) ?? 0);
    if (anchorIndex < 0) continue;
    const anchor = verse.words[anchorIndex];
    anchor.finiteVerbId = alignment.id;
    anchor.greekSurface = alignment.greekSurface;
    anchor.greekMorph = alignment.greekMorph;
    anchor.greekLemma = alignment.greekLemma;
    cursors.set(key, anchor.index + 1);
  }

  for (const alignment of parseTokenAlignments()) {
    if (!markedDependentIntroducerAlignmentIds.has(alignment.id)) continue;
    if (!DEPENDENT_INTRODUCER_SURFACES.has(stripGreekPunctuation(alignment.greekSurface))) continue;

    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;

    for (const index of findHintSpanIndexes(alignment, verse.words)) {
      const word = verse.words[index];
      if (!word) continue;
      word.dependentIntroducerId = alignment.id;
      word.dependentGreekSurface = alignment.greekSurface;
    }
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

  const selectedTokenIds = verseTokens
    .filter(alignment => {
      if (alignment.id === finiteVerbId) return true;
      const indexes = findHintSpanIndexes(alignment, verseWords);
      return indexes.some(index => selectedIds.has(wordId(alignment.chapter, alignment.verse, index)));
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
