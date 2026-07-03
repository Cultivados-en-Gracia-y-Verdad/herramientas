#!/usr/bin/env node
/**
 * Extract observable Greek NT occurrences for a Strong's number.
 *
 * Usage:
 *   node cgv-dictionary/scripts/extract-lemma-occurrences.js G3341
 *   npm run dictionary:extract -- G3341
 */

import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DICT_ROOT = join(__dirname, "..");
const REPO_ROOT = join(DICT_ROOT, "..");
const NT_DIR = join(REPO_ROOT, "MNA", "datasets", "interlinear", "NT");
const STRONGS_MAP_PATH = join(REPO_ROOT, "MNA", "datasets", "rules", "grc_lemma_strongs.json");
const STRONGS_SUPPLEMENT_PATH = join(
  REPO_ROOT,
  "MNA",
  "datasets",
  "rules",
  "grc_lemma_strongs_supplement.json"
);

const BOOK_DISPLAY = {
  mateo: "Matthew",
  marcos: "Mark",
  lucas: "Luke",
  juan: "John",
  hechos: "Acts",
  romanos: "Romans",
  "1corintios": "1 Corinthians",
  "2corintios": "2 Corinthians",
  galatas: "Galatians",
  efesios: "Ephesians",
  filipenses: "Philippians",
  colosenses: "Colossians",
  "1tesalonicenses": "1 Thessalonians",
  "2tesalonicenses": "2 Thessalonians",
  "1timoteo": "1 Timothy",
  "2timoteo": "2 Timothy",
  tito: "Titus",
  filemon: "Philemon",
  hebreos: "Hebrews",
  santiago: "James",
  "1pedro": "1 Peter",
  "2pedro": "2 Peter",
  "1juan": "1 John",
  "2juan": "2 John",
  "3juan": "3 John",
  judas: "Jude",
  apocalipsis: "Revelation",
};

const NT_BOOK_ORDER = [
  "mateo",
  "marcos",
  "lucas",
  "juan",
  "hechos",
  "romanos",
  "1corintios",
  "2corintios",
  "galatas",
  "efesios",
  "filipenses",
  "colosenses",
  "1tesalonicenses",
  "2tesalonicenses",
  "1timoteo",
  "2timoteo",
  "tito",
  "filemon",
  "hebreos",
  "santiago",
  "1pedro",
  "2pedro",
  "1juan",
  "2juan",
  "3juan",
  "judas",
  "apocalipsis",
];

function displayBook(slug) {
  return BOOK_DISPLAY[slug] || slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatReference(slug, chapter, verse) {
  return `${displayBook(slug)} ${chapter}:${verse}`;
}

function normalizeStrongs(arg) {
  const raw = String(arg || "").trim().toUpperCase();
  if (!raw) return null;
  if (/^G\d+$/.test(raw)) return raw;
  if (/^\d+$/.test(raw)) return `G${raw}`;
  return null;
}

function loadStrongsMap() {
  const map = JSON.parse(readFileSync(STRONGS_MAP_PATH, "utf8"));
  if (existsSync(STRONGS_SUPPLEMENT_PATH)) {
    const supplement = JSON.parse(readFileSync(STRONGS_SUPPLEMENT_PATH, "utf8"));
    Object.assign(map, supplement);
  }
  return map;
}

function lemmasForStrongs(strongs, lemmaToStrongs) {
  const lemmas = new Set();
  for (const [lemma, code] of Object.entries(lemmaToStrongs)) {
    if (code === strongs) lemmas.add(lemma);
  }
  return lemmas;
}

function canonicalLemma(lemmas) {
  const plain = [...lemmas].find((l) => !l.includes(",") && !l.includes("ἡ"));
  return plain || [...lemmas].sort((a, b) => a.length - b.length)[0];
}

function loadNtTokens() {
  if (!existsSync(NT_DIR)) {
    throw new Error(`NT token directory not found: ${NT_DIR}`);
  }

  const verses = new Map();

  for (const file of readdirSync(NT_DIR).filter((f) => f.endsWith(".tokens.jsonl")).sort()) {
    const lines = readFileSync(join(NT_DIR, file), "utf8").split("\n");
    for (const line of lines) {
      if (!line.trim()) continue;
      const token = JSON.parse(line);
      const key = `${token.book}:${token.ch}:${token.vs}`;
      if (!verses.has(key)) verses.set(key, []);
      verses.get(key).push(token);
    }
  }

  for (const tokens of verses.values()) {
    tokens.sort((a, b) => a.tok - b.tok);
  }

  return verses;
}

function bookOrderIndex(slug) {
  const idx = NT_BOOK_ORDER.indexOf(slug);
  return idx === -1 ? NT_BOOK_ORDER.length : idx;
}

function buildOccurrences(strongs, targetLemmas, verses) {
  const occurrences = [];
  const primaryLemma = canonicalLemma(targetLemmas);

  for (const tokens of verses.values()) {
    const greekVerse = tokens.map((t) => t.surface).join(" ");
    const matches = tokens.filter((t) => targetLemmas.has(t.lemma));

    matches.forEach((token, matchedTokenIndex) => {
      occurrences.push({
        reference: formatReference(token.book, token.ch, token.vs),
        book: displayBook(token.book),
        chapter: token.ch,
        verse: token.vs,
        strongs,
        lemma: token.lemma,
        form: token.surface,
        morphology: token.morph || "",
        greekVerse,
        matchedTokenIndex,
      });
    });
  }

  occurrences.sort((a, b) => {
    const bookSlugA = Object.entries(BOOK_DISPLAY).find(([, name]) => name === a.book)?.[0]
      || a.book.toLowerCase();
    const bookSlugB = Object.entries(BOOK_DISPLAY).find(([, name]) => name === b.book)?.[0]
      || b.book.toLowerCase();
    const bookCmp = bookOrderIndex(bookSlugA) - bookOrderIndex(bookSlugB);
    if (bookCmp !== 0) return bookCmp;
    if (a.chapter !== b.chapter) return a.chapter - b.chapter;
    if (a.verse !== b.verse) return a.verse - b.verse;
    return a.matchedTokenIndex - b.matchedTokenIndex;
  });

  return { primaryLemma, occurrences };
}

function main() {
  const strongs = normalizeStrongs(process.argv[2]);
  if (!strongs) {
    console.error("Usage: node cgv-dictionary/scripts/extract-lemma-occurrences.js G3341");
    process.exit(1);
  }

  console.log(`CGV Dictionary — extract occurrences for ${strongs}`);

  const lemmaToStrongs = loadStrongsMap();
  const targetLemmas = lemmasForStrongs(strongs, lemmaToStrongs);

  if (!targetLemmas.size) {
    console.error(`No lemmas mapped to ${strongs} in grc_lemma_strongs.json`);
    process.exit(1);
  }

  const verses = loadNtTokens();
  const { primaryLemma, occurrences } = buildOccurrences(strongs, targetLemmas, verses);

  const outDir = join(DICT_ROOT, "greek", strongs);
  const outPath = join(outDir, "occurrences.json");
  mkdirSync(outDir, { recursive: true });

  const payload = {
    strongs,
    lemma: primaryLemma,
    source: "MNA/datasets/interlinear/NT",
    extractedAt: new Date().toISOString(),
    count: occurrences.length,
    occurrences,
  };

  writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

  console.log(`Lemma forms: ${[...targetLemmas].join(", ")}`);
  console.log(`Occurrences: ${occurrences.length}`);
  console.log(`Output: cgv-dictionary/greek/${strongs}/occurrences.json`);

  if (occurrences.length > 0) {
    console.log(`Sample: ${occurrences[0].reference} — ${occurrences[0].form}`);
  }
}

main();
