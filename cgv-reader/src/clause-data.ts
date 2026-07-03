import { parseNblaContent } from "cgv-bible";
import type { BibleVerse } from "cgv-bible";
import titusNbla from "../../../cgv-data/bibles/NBLA/tito.nbla.md?raw";
import titusAlignment from "../../MNA/datasets/interlinear/NT/tito.tokens.jsonl?raw";

export interface SpanishWord {
  id: string;
  chapter: number;
  verse: number;
  index: number;
  text: string;
  finiteVerbId: string | null;
  greekSurface?: string;
  greekMorph?: string;
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
  spanishHint: string;
}

export interface ClauseAssignment {
  finiteVerbId: string;
  selectedSpan: string[];
}

export type ClauseAssignments = Record<string, ClauseAssignment>;

const WORD_PATTERN = /[\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\s\wáéíóúüñÁÉÍÓÚÜÑ]+/gu;
export const CLAUSE_STORAGE_KEY = "the-reader:spanish-clause-builder:titus:v1";
const LEGACY_CLAUSE_STORAGE_KEY = "the-reader:clause-builder:titus:1:1-4:v2";

const FINITE_ANCHOR_OVERRIDES: Record<string, { text: string; occurrence?: number }> = {
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

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");
}

function spanishHintParts(value: string): string[] {
  return value
    .replace(/·/g, " ")
    .split(/\s+/)
    .map(normalize)
    .filter(Boolean);
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
    const exact = words.find(word => word.index >= cursor && normalize(word.text) === part);
    if (exact) return exact.index;
  }

  for (const part of parts) {
    if (part.length < 4) continue;
    const soft = words.find(word => {
      if (word.index < cursor) return false;
      const text = normalize(word.text);
      return text.startsWith(part.slice(0, 4)) || part.startsWith(text.slice(0, 4));
    });
    if (soft) return soft.index;
  }

  return -1;
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

  for (const alignment of parseFiniteAlignments()) {
    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;
    const anchorIndex = findAnchorIndex(alignment, verse.words, cursors.get(key) ?? 0);
    if (anchorIndex < 0) continue;
    const anchor = verse.words[anchorIndex];
    anchor.finiteVerbId = alignment.id;
    anchor.greekSurface = alignment.greekSurface;
    anchor.greekMorph = alignment.greekMorph;
    cursors.set(key, anchor.index + 1);
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
      const record = value as { finiteVerbId?: unknown; selectedSpan?: unknown };
      if (Array.isArray(record.selectedSpan)) {
        const selectedSpan = record.selectedSpan.filter((id): id is string => typeof id === "string");
        if (selectedSpan.length) {
          out[finiteVerbId] = {
            finiteVerbId: typeof record.finiteVerbId === "string" ? record.finiteVerbId : finiteVerbId,
            selectedSpan
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
