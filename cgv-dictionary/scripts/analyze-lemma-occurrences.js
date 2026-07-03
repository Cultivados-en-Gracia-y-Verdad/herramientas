#!/usr/bin/env node
/**
 * Analyze observable statistics from extracted lemma occurrences.
 *
 * Usage:
 *   node cgv-dictionary/scripts/analyze-lemma-occurrences.js G3341
 *   npm run dictionary:analyze -- G3341
 */

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DICT_ROOT = join(__dirname, "..");
const REPO_ROOT = join(DICT_ROOT, "..");
const NT_DIR = join(REPO_ROOT, "MNA", "datasets", "interlinear", "NT");

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

const BOOK_SLUG_BY_DISPLAY = Object.fromEntries(
  Object.entries(BOOK_DISPLAY).map(([slug, name]) => [name, slug])
);

const CASE_LABELS = {
  N: "nominative",
  G: "genitive",
  D: "dative",
  A: "accusative",
  V: "vocative",
};

const COLLOCATION_STOPLIST = new Set([
  "ὁ", "ὅς", "οὗτος", "ἐκεῖνος", "αὐτός", "ἐγώ", "σύ", "τις", "τίς", "πᾶς",
  "καί", "δέ", "γάρ", "οὖν", "ἀλλά", "ἵνα", "ὅτι", "εἰ", "ἐάν", "ὡς", "καθώς",
  "ἐν", "εἰς", "ἐκ", "ἀπό", "πρός", "διά", "μετά", "σύν", "περί", "ὑπό", "ἐπί",
  "κατά", "παρά", "ἄν", "οὐ", "οὐκ", "οὐχ", "μή", "μηδέ", "οὐδέ", "εἰμί",
]);

const NEARBY_WINDOW = 5;
const MIN_PHRASE_COUNT = 2;
const TOP_NEARBY = 25;
const TOP_PHRASES = 20;

function normalizeStrongs(arg) {
  const raw = String(arg || "").trim().toUpperCase();
  if (!raw) return null;
  if (/^G\d+$/.test(raw)) return raw;
  if (/^\d+$/.test(raw)) return `G${raw}`;
  return null;
}

function cleanSurface(surface) {
  return String(surface || "")
    .replace(/^[⸀⸂⸃]+/, "")
    .replace(/[·,.;:!?]+$/, "")
    .trim();
}

function parseCase(morphology) {
  if (!morphology || morphology.length < 7) return null;
  const pos = morphology[0];
  if (pos !== "N" && pos !== "A" && pos !== "P") return null;
  const code = morphology[6];
  return CASE_LABELS[code] || null;
}

function countMap(items, keyFn = (x) => x) {
  const map = new Map();
  for (const item of items) {
    const key = keyFn(item);
    if (key === null || key === undefined || key === "") continue;
    map.set(key, (map.get(key) || 0) + 1);
  }
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), "el"))
    .map(([key, count]) => ({ value: key, count }));
}

function loadVerseIndex() {
  const index = new Map();
  if (!existsSync(NT_DIR)) return index;

  for (const file of readdirSync(NT_DIR).filter((f) => f.endsWith(".tokens.jsonl"))) {
    const lines = readFileSync(join(NT_DIR, file), "utf8").split("\n");
    for (const line of lines) {
      if (!line.trim()) continue;
      const token = JSON.parse(line);
      const key = `${token.book}:${token.ch}:${token.vs}`;
      if (!index.has(key)) index.set(key, []);
      index.get(key).push(token);
    }
  }

  for (const tokens of index.values()) {
    tokens.sort((a, b) => a.tok - b.tok);
  }
  return index;
}

function verseKeyFromOccurrence(occ) {
  const slug = BOOK_SLUG_BY_DISPLAY[occ.book];
  if (!slug) return null;
  return `${slug}:${occ.chapter}:${occ.verse}`;
}

function matchIndices(tokens, targetLemmas) {
  const indices = [];
  tokens.forEach((token, idx) => {
    if (targetLemmas.has(token.lemma)) indices.push(idx);
  });
  return indices;
}

function collectNearbyWords(occurrences, verseIndex, targetLemmas) {
  const counts = new Map();

  for (const occ of occurrences) {
    const key = verseKeyFromOccurrence(occ);
    if (!key) continue;
    const tokens = verseIndex.get(key);
    if (!tokens) continue;

    const indices = matchIndices(tokens, targetLemmas);
    const targetIndex = indices[occ.matchedTokenIndex] ?? indices[0];
    if (targetIndex === undefined) continue;

    const lo = Math.max(0, targetIndex - NEARBY_WINDOW);
    const hi = Math.min(tokens.length, targetIndex + NEARBY_WINDOW + 1);

    for (let i = lo; i < hi; i += 1) {
      if (i === targetIndex) continue;
      const lemma = tokens[i].lemma;
      if (!lemma || targetLemmas.has(lemma) || COLLOCATION_STOPLIST.has(lemma)) continue;
      counts.set(lemma, (counts.get(lemma) || 0) + 1);
    }
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "el"))
    .slice(0, TOP_NEARBY)
    .map(([lemma, count]) => ({ lemma, count, window: NEARBY_WINDOW }));
}

function phraseVariants(tokens, centerIdx) {
  const surfaces = tokens.map((t) => cleanSurface(t.surface)).filter(Boolean);
  const phrases = new Set();

  for (let size = 2; size <= 4; size += 1) {
    for (let start = Math.max(0, centerIdx - size + 1); start <= centerIdx; start += 1) {
      const end = start + size;
      if (end > surfaces.length || start > centerIdx || end - 1 < centerIdx) continue;
      phrases.add(surfaces.slice(start, end).join(" "));
    }
  }

  return [...phrases];
}

function collectRepeatedPhrases(occurrences, verseIndex, targetLemmas) {
  const phraseCounts = new Map();
  const phraseExamples = new Map();

  for (const occ of occurrences) {
    const key = verseKeyFromOccurrence(occ);
    if (!key) continue;
    const tokens = verseIndex.get(key);
    if (!tokens) continue;

    const indices = matchIndices(tokens, targetLemmas);
    const targetIndex = indices[occ.matchedTokenIndex] ?? indices[0];
    if (targetIndex === undefined) continue;

    for (const phrase of phraseVariants(tokens, targetIndex)) {
      phraseCounts.set(phrase, (phraseCounts.get(phrase) || 0) + 1);
      if (!phraseExamples.has(phrase)) phraseExamples.set(phrase, new Set());
      phraseExamples.get(phrase).add(occ.reference);
    }
  }

  return [...phraseCounts.entries()]
    .filter(([, count]) => count >= MIN_PHRASE_COUNT)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "el"))
    .slice(0, TOP_PHRASES)
    .map(([phrase, count]) => ({
      phrase,
      count,
      examples: [...phraseExamples.get(phrase)].sort(),
    }));
}

function groupReferencesByBook(occurrences) {
  const grouped = {};
  for (const occ of occurrences) {
    if (!grouped[occ.book]) grouped[occ.book] = [];
    grouped[occ.book].push(occ.reference);
  }
  for (const book of Object.keys(grouped)) {
    grouped[book] = [...new Set(grouped[book])].sort((a, b) => a.localeCompare(b, "en"));
  }
  return grouped;
}

function analyze(occurrencesPayload) {
  const occurrences = occurrencesPayload.occurrences || [];
  const targetLemmas = new Set(
    occurrences.map((o) => o.lemma).filter(Boolean)
  );
  if (occurrencesPayload.lemma) targetLemmas.add(occurrencesPayload.lemma);

  const verseIndex = loadVerseIndex();

  const books = countMap(occurrences, (o) => o.book);
  const morphology = countMap(occurrences, (o) => o.morphology || "");
  const forms = countMap(occurrences, (o) => cleanSurface(o.form));
  const cases = countMap(
    occurrences.map((o) => parseCase(o.morphology)).filter(Boolean)
  );

  return {
    strongs: occurrencesPayload.strongs,
    lemma: occurrencesPayload.lemma,
    source: "occurrences.json",
    analyzedAt: new Date().toISOString(),
    count: occurrences.length,
    books: Object.fromEntries(books.map(({ value, count }) => [value, count])),
    morphology: Object.fromEntries(morphology.map(({ value, count }) => [value, count])),
    forms: Object.fromEntries(forms.map(({ value, count }) => [value, count])),
    cases: Object.fromEntries(cases.map(({ value, count }) => [value, count])),
    nearbyWords: collectNearbyWords(occurrences, verseIndex, targetLemmas),
    repeatedPhrases: collectRepeatedPhrases(occurrences, verseIndex, targetLemmas),
    referencesByBook: groupReferencesByBook(occurrences),
  };
}

function main() {
  const strongs = normalizeStrongs(process.argv[2]);
  if (!strongs) {
    console.error("Usage: node cgv-dictionary/scripts/analyze-lemma-occurrences.js G3341");
    process.exit(1);
  }

  const inPath = join(DICT_ROOT, "greek", strongs, "occurrences.json");
  const outPath = join(DICT_ROOT, "greek", strongs, "analysis.json");

  if (!existsSync(inPath)) {
    console.error(`Missing input: cgv-dictionary/greek/${strongs}/occurrences.json`);
    console.error(`Run: npm run dictionary:extract -- ${strongs}`);
    process.exit(1);
  }

  const payload = JSON.parse(readFileSync(inPath, "utf8"));
  const analysis = analyze(payload);

  writeFileSync(outPath, `${JSON.stringify(analysis, null, 2)}\n`, "utf8");

  console.log(`CGV Dictionary — analyze ${strongs}`);
  console.log(`Input:  greek/${strongs}/occurrences.json (${analysis.count} occurrences)`);
  console.log(`Output: greek/${strongs}/analysis.json`);
  console.log(`Books: ${Object.keys(analysis.books).length}`);
  console.log(`Forms: ${Object.keys(analysis.forms).length}`);
  console.log(`Repeated phrases (≥${MIN_PHRASE_COUNT}): ${analysis.repeatedPhrases.length}`);
}

main();
