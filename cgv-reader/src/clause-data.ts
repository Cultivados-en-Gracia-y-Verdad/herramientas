import { parseNblaContent } from "cgv-bible";
import type { BibleVerse } from "cgv-bible";
import titusNbla from "../../../cgv-data/bibles/NBLA/tito.nbla.md?raw";

export interface SpanishWord {
  id: string;
  chapter: number;
  verse: number;
  index: number;
  text: string;
  isFiniteVerb: boolean;
}

export interface SpanishClauseVerse {
  chapter: number;
  verse: number;
  label: string;
  words: SpanishWord[];
}

/** Finite verbs in NBLA for Tito 1:1–4 (matched case-insensitively). */
const FINITE_VERB_FORMS: Record<string, string[]> = {
  "1:2": ["prometió"],
  "1:3": ["manifestó", "fue"]
};

const WORD_PATTERN = /[\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\s\wáéíóúüñÁÉÍÓÚÜÑ]+/gu;

function wordId(chapter: number, verse: number, index: number): string {
  return `${chapter}:${verse}:${index}`;
}

function tokenizeVerse(verse: BibleVerse): SpanishWord[] {
  const key = `${verse.chapter}:${verse.verse}`;
  const finiteForms = new Set(
    (FINITE_VERB_FORMS[key] ?? []).map(form => form.toLowerCase())
  );
  const words: SpanishWord[] = [];
  let index = 0;

  for (const piece of verse.text.match(WORD_PATTERN) ?? []) {
    if (!/[\wáéíóúüñÁÉÍÓÚÜÑ]/i.test(piece)) continue;
    words.push({
      id: wordId(verse.chapter, verse.verse, index),
      chapter: verse.chapter,
      verse: verse.verse,
      index,
      text: piece,
      isFiniteVerb: finiteForms.has(piece.toLowerCase())
    });
    index += 1;
  }

  return words;
}

export function loadTitusClauseVerses(): SpanishClauseVerse[] {
  const all = parseNblaContent(titusNbla);
  return all
    .filter(verse => verse.chapter === 1 && verse.verse >= 1 && verse.verse <= 4)
    .map(verse => ({
      chapter: verse.chapter,
      verse: verse.verse,
      label: `Tito ${verse.chapter}:${verse.verse}`,
      words: tokenizeVerse(verse)
    }));
}

export const CLAUSE_STORAGE_KEY = "the-reader:clause-builder:titus:1:1-4";

export type ClauseAssignments = Record<string, string[]>;

export function readClauseAssignments(): ClauseAssignments {
  try {
    const stored = window.localStorage.getItem(CLAUSE_STORAGE_KEY);
    if (!stored) return {};
    const parsed = JSON.parse(stored);
    if (!parsed || typeof parsed !== "object") return {};
    const out: ClauseAssignments = {};
    for (const [verbId, wordIds] of Object.entries(parsed)) {
      if (typeof verbId !== "string" || !Array.isArray(wordIds)) continue;
      out[verbId] = wordIds.filter((id): id is string => typeof id === "string");
    }
    return out;
  } catch {
    return {};
  }
}

export function writeClauseAssignments(assignments: ClauseAssignments): void {
  window.localStorage.setItem(CLAUSE_STORAGE_KEY, JSON.stringify(assignments));
}

export function compareSpanishWords(a: SpanishWord, b: SpanishWord): number {
  return a.chapter - b.chapter || a.verse - b.verse || a.index - b.index;
}

export function sameVerseWords(a: SpanishWord, b: SpanishWord): boolean {
  return a.chapter === b.chapter && a.verse === b.verse;
}

export function wordIdsInSpan(
  start: SpanishWord,
  end: SpanishWord,
  verseWords: SpanishWord[],
  excludeId?: string | null
): string[] {
  if (!sameVerseWords(start, end)) return [];
  const lo = Math.min(start.index, end.index);
  const hi = Math.max(start.index, end.index);
  return verseWords
    .filter(word => word.index >= lo && word.index <= hi)
    .map(word => word.id)
    .filter(id => id !== excludeId);
}

export function sortWordIds(
  wordIds: string[],
  wordById: Map<string, SpanishWord>
): string[] {
  return [...wordIds].sort((a, b) => {
    const left = wordById.get(a);
    const right = wordById.get(b);
    if (!left || !right) return a.localeCompare(b);
    return compareSpanishWords(left, right);
  });
}

export function formatWordsInOrder(
  wordIds: string[],
  wordById: Map<string, SpanishWord>
): string {
  return sortWordIds(wordIds, wordById)
    .map(id => wordById.get(id)?.text ?? id)
    .join(" ");
}
