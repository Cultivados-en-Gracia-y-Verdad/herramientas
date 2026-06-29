import type { LexiconEntry, LexiconLang, LexiconManifest } from "./types";

export type LexiconIndex = Map<string, LexiconEntry>;

const cache = new Map<LexiconLang, LexiconIndex>();

function entryKey(lang: LexiconLang, lemma: string): string {
  return `${lang}:${lemma}`;
}

async function fetchJsonl(url: string): Promise<LexiconEntry[]> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load lexicon: ${url} (${response.status})`);
  }
  const text = await response.text();
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as LexiconEntry);
}

export async function loadLexicon(
  lang: LexiconLang,
  baseUrl = "/lexicon"
): Promise<LexiconIndex> {
  const cached = cache.get(lang);
  if (cached) return cached;

  const file = lang === "grc" ? "grc.entries.jsonl" : "hbo.entries.jsonl";
  const entries = await fetchJsonl(`${baseUrl}/${file}`);
  const index: LexiconIndex = new Map();
  for (const entry of entries) {
    index.set(entryKey(lang, entry.lemma), entry);
  }
  cache.set(lang, index);
  return index;
}

export function loadLexiconFromEntries(entries: LexiconEntry[]): LexiconIndex {
  const index: LexiconIndex = new Map();
  for (const entry of entries) {
    index.set(entryKey(entry.lang, entry.lemma), entry);
  }
  return index;
}

export async function loadManifest(baseUrl = "/lexicon"): Promise<LexiconManifest> {
  const response = await fetch(`${baseUrl}/manifest.json`);
  if (!response.ok) {
    throw new Error(`Failed to load lexicon manifest (${response.status})`);
  }
  return response.json() as Promise<LexiconManifest>;
}
