import type { LexiconEntry, LexiconLang } from "./types";
import { loadLexicon, type LexiconIndex } from "./load";

function entryKey(lang: LexiconLang, lemma: string): string {
  return `${lang}:${lemma}`;
}

export async function lookupLemma(
  lang: LexiconLang,
  lemma: string,
  baseUrl?: string
): Promise<LexiconEntry | null> {
  const index = await loadLexicon(lang, baseUrl);
  return lookupLemmaInIndex(index, lang, lemma);
}

export function lookupLemmaInIndex(
  index: LexiconIndex,
  lang: LexiconLang,
  lemma: string
): LexiconEntry | null {
  return index.get(entryKey(lang, lemma)) ?? null;
}

export function lookupStrongs(
  index: LexiconIndex,
  strongs: string
): LexiconEntry | null {
  const target = strongs.toUpperCase().replace(/^([GH])0+/, "$1");
  for (const entry of index.values()) {
    if (entry.strongs?.toUpperCase() === target) {
      return entry;
    }
  }
  return null;
}

/** Compact line for popups: G1586 · escoger */
export function formatLexiconLine(entry: LexiconEntry): string {
  const parts: string[] = [];
  if (entry.strongs) parts.push(entry.strongs);
  if (entry.gloss_es) parts.push(entry.gloss_es);
  return parts.join(" · ") || entry.lemma;
}
