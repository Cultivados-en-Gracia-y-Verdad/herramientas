import { existsSync } from "node:fs";
import { access, readFile, readdir } from "node:fs/promises";
import { constants } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadTranslationIndexes, resolveHistoricalRenderings, highlightWitnessText, normalizeFocusToken } from "./translationIndexes.js";

const rootDir = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const fallbackCgvDataPath = "../cgv-data";
const configuredCgvDataPath = process.env.CGV_DATA_PATH || fallbackCgvDataPath;

function resolveCgvDataDir() {
  const configuredPath = resolve(rootDir, configuredCgvDataPath);
  if (process.env.CGV_DATA_PATH || existsSync(configuredPath)) {
    return configuredPath;
  }

  const localWorkspacePath = resolve(rootDir, "../../cgv-data");
  return existsSync(localWorkspacePath) ? localWorkspacePath : configuredPath;
}

const cgvDataDir = resolveCgvDataDir();
const optionalBleOutputDir = resolve(rootDir, "../Biblia-BLE/output");

const expectedGreekData = [
  "morphology/MorphGNT/*-morphgnt.txt",
  "a Greek Strong's-to-lemma or occurrence index for general Strong's lookup"
];

const prototypeStrongMappings = {
  G1401: {
    lemma: "δοῦλος",
    subject: "G1401 δοῦλος"
  },
  G652: {
    lemma: "ἀπόστολος",
    subject: "G652 ἀπόστολος"
  },
  G4102: {
    lemma: "πίστις",
    subject: "G4102 πίστις"
  }
};

let lemmaStrongsIndexPromise = null;

async function loadLemmaStrongsIndexes() {
  if (!lemmaStrongsIndexPromise) {
    lemmaStrongsIndexPromise = (async () => {
      const candidates = [
        resolve(rootDir, "../MNA/datasets/rules/grc_lemma_strongs.json"),
        join(cgvDataDir, "dictionaries", "grc_lemma_strongs.json"),
        join(cgvDataDir, "lexicons", "grc_lemma_strongs.json")
      ];
      for (const path of candidates) {
        const raw = await readFile(path, "utf8").catch(() => "");
        if (!raw) continue;
        try {
          const data = JSON.parse(raw);
          const lemmaToStrongs = new Map();
          const strongsToLemma = new Map();
          for (const [lemma, strongs] of Object.entries(data || {})) {
            const normalized = String(strongs || "").trim().toUpperCase();
            if (!lemma || !/^G\d+$/.test(normalized)) continue;
            lemmaToStrongs.set(lemma, normalized);
            if (!strongsToLemma.has(normalized)) {
              strongsToLemma.set(normalized, lemma);
            }
          }
          return { lemmaToStrongs, strongsToLemma, path };
        } catch {
          // try next candidate
        }
      }
      return { lemmaToStrongs: new Map(), strongsToLemma: new Map(), path: "" };
    })();
  }
  return lemmaStrongsIndexPromise;
}

function normalizeStrongsId(value = "", { defaultPrefix = "G" } = {}) {
  const raw = String(value || "").trim().toUpperCase();
  if (!raw || raw === "—") return "";
  const prefixed = raw.match(/^([GHA])(\d+)/);
  if (prefixed) return `${prefixed[1]}${prefixed[2]}`;
  if (/^\d+$/.test(raw)) return `${defaultPrefix}${raw}`;
  return raw;
}

function isHebrewStrongs(strongs = "") {
  const normalized = String(strongs || "").trim().toUpperCase();
  return normalized.startsWith("H") || normalized.startsWith("A");
}

/** Extract Strong's number stems from an OSHB lemma code (`b/8141`, `d/4428`, `1004 b`). */
export function oshbLemmaStrongsNumbers(lemma = "") {
  const nums = [];
  for (const part of String(lemma || "").split("/")) {
    const match = part.trim().match(/^(\d+)/u);
    if (match) nums.push(match[1]);
  }
  return nums;
}

export function oshbLemmaMatchesStrongs(lemma = "", strongs = "") {
  const num = String(strongs || "").trim().toUpperCase().replace(/^[GHA]/u, "");
  if (!num) return false;
  return oshbLemmaStrongsNumbers(lemma).includes(num);
}

function oshbLemmaSense(lemma = "") {
  const parts = String(lemma || "").split("/");
  for (let index = parts.length - 1; index >= 0; index -= 1) {
    const match = parts[index].trim().match(/^(\d+)(?:\s+([a-z]))?/iu);
    if (match) return `${match[1]}${match[2] ? ` ${match[2].toLowerCase()}` : ""}`;
  }
  return "";
}

function aquiferOshbSourceTokenIds(bookNumber, row = {}) {
  const book = String(bookNumber || "").padStart(2, "0");
  const chapter = String(Number(row.ch || 0)).padStart(3, "0");
  const verse = String(Number(row.vs || 0)).padStart(3, "0");
  const word = String(Number(row.w || 0)).padStart(3, "0");
  if (!bookNumber || !Number(row.ch) || !Number(row.vs) || !Number(row.w)) return [];
  const prefix = `o${book}${chapter}${verse}${word}`;
  return Array.from({ length: 9 }, (_, index) => `${prefix}${index + 1}`);
}

const OT_BOOK_LABELS_EN = {
  genesis: "Genesis",
  exodo: "Exodus",
  levitico: "Leviticus",
  numeros: "Numbers",
  deuteronomio: "Deuteronomy",
  josue: "Joshua",
  jueces: "Judges",
  rut: "Ruth",
  "1samuel": "1 Samuel",
  "2samuel": "2 Samuel",
  "1reyes": "1 Kings",
  "2reyes": "2 Kings",
  "1cronicas": "1 Chronicles",
  "2cronicas": "2 Chronicles",
  esdras: "Ezra",
  nehemias: "Nehemiah",
  ester: "Esther",
  job: "Job",
  salmos: "Psalms",
  proverbios: "Proverbs",
  eclesiastes: "Ecclesiastes",
  cantares: "Song of Songs",
  isaias: "Isaiah",
  jeremias: "Jeremiah",
  lamentaciones: "Lamentations",
  ezequiel: "Ezekiel",
  daniel: "Daniel",
  oseas: "Hosea",
  joel: "Joel",
  amos: "Amos",
  abdias: "Obadiah",
  jonas: "Jonah",
  miqueas: "Micah",
  nahum: "Nahum",
  habacuc: "Habakkuk",
  sofonias: "Zephaniah",
  hageo: "Haggai",
  zacarias: "Zechariah",
  malaquias: "Malachi"
};

const OT_BOOK_NUMBERS = {
  genesis: "01",
  exodo: "02",
  levitico: "03",
  numeros: "04",
  deuteronomio: "05",
  josue: "06",
  jueces: "07",
  rut: "08",
  "1samuel": "09",
  "2samuel": "10",
  "1reyes": "11",
  "2reyes": "12",
  "1cronicas": "13",
  "2cronicas": "14",
  esdras: "15",
  nehemias: "16",
  ester: "17",
  job: "18",
  salmos: "19",
  proverbios: "20",
  eclesiastes: "21",
  cantares: "22",
  isaias: "23",
  jeremias: "24",
  lamentaciones: "25",
  ezequiel: "26",
  daniel: "27",
  oseas: "28",
  joel: "29",
  amos: "30",
  abdias: "31",
  jonas: "32",
  miqueas: "33",
  nahum: "34",
  habacuc: "35",
  sofonias: "36",
  hageo: "37",
  zacarias: "38",
  malaquias: "39"
};

function missingHebrewDataError(detail = "") {
  const error = new Error(
    `Could not find Hebrew occurrence data in cgv-data (interlinears/OT/*.tokens.jsonl).${detail ? ` ${detail}` : ""}`
  );
  error.code = "HEBREW_DATA_MISSING";
  return error;
}

/**
 * Resolve Strong's + lemma for occurrence gathering.
 * Accepts either a known Strong's, a lemma hint, or both.
 */
export async function resolveGreekLemmaSubject({ strongs = "", lemma = "" } = {}) {
  const normalizedStrongs = normalizeStrongsId(strongs, { defaultPrefix: "G" });
  const lemmaHint = String(lemma || "").trim();

  if (isHebrewStrongs(normalizedStrongs)) {
    throw missingGreekDataError(
      `Strong's ${normalizedStrongs} is Hebrew/Aramaic — use Hebrew occurrence gathering.`
    );
  }

  if (normalizedStrongs && prototypeStrongMappings[normalizedStrongs]) {
    const mapping = prototypeStrongMappings[normalizedStrongs];
    return {
      strongs: normalizedStrongs,
      lemma: mapping.lemma,
      subject: mapping.subject
    };
  }

  const indexes = await loadLemmaStrongsIndexes();

  if (normalizedStrongs) {
    const mappedLemma = indexes.strongsToLemma.get(normalizedStrongs) || lemmaHint;
    if (mappedLemma) {
      return {
        strongs: normalizedStrongs,
        lemma: mappedLemma,
        subject: `${normalizedStrongs} ${mappedLemma}`
      };
    }
  }

  if (lemmaHint) {
    const mappedStrongs = indexes.lemmaToStrongs.get(lemmaHint) || normalizedStrongs;
    if (mappedStrongs || lemmaHint) {
      return {
        strongs: mappedStrongs || "",
        lemma: lemmaHint,
        subject: [mappedStrongs, lemmaHint].filter(Boolean).join(" ")
      };
    }
  }

  throw missingGreekDataError(
    `No Strong's/lemma mapping for ${normalizedStrongs || "blank Strong's"} ${lemmaHint || ""}`.trim()
  );
}

const bookNames = {
  "01": "Matthew",
  "02": "Mark",
  "03": "Luke",
  "04": "John",
  "05": "Acts",
  "06": "Romans",
  "07": "1 Corinthians",
  "08": "2 Corinthians",
  "09": "Galatians",
  "10": "Ephesians",
  "11": "Philippians",
  "12": "Colossians",
  "13": "1 Thessalonians",
  "14": "2 Thessalonians",
  "15": "1 Timothy",
  "16": "2 Timothy",
  "17": "Titus",
  "18": "Philemon",
  "19": "Hebrews",
  "20": "James",
  "21": "1 Peter",
  "22": "2 Peter",
  "23": "1 John",
  "24": "2 John",
  "25": "3 John",
  "26": "Jude",
  "27": "Revelation"
};

const bookSlugs = {
  "01": "mateo",
  "02": "marcos",
  "03": "lucas",
  "04": "juan",
  "05": "hechos",
  "06": "romanos",
  "07": "1corintios",
  "08": "2corintios",
  "09": "galatas",
  "10": "efesios",
  "11": "filipenses",
  "12": "colosenses",
  "13": "1tesalonicenses",
  "14": "2tesalonicenses",
  "15": "1timoteo",
  "16": "2timoteo",
  "17": "tito",
  "18": "filemon",
  "19": "hebreos",
  "20": "santiago",
  "21": "1pedro",
  "22": "2pedro",
  "23": "1juan",
  "24": "2juan",
  "25": "3juan",
  "26": "judas",
  "27": "apocalipsis"
};

class CgvDataError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = "CgvDataError";
    this.code = "CGV_DATA_MISSING";
    this.details = details;
  }
}

async function fileExists(path) {
  return access(path, constants.R_OK).then(() => true).catch(() => false);
}

function missingGreekDataError(extra = "") {
  const expected = expectedGreekData.join(", ");
  const suffix = extra ? ` ${extra}` : "";
  return new CgvDataError(
    `Could not find Greek occurrence data in cgv-data. Expected: ${expected}.${suffix}`,
    { cgvDataPath: cgvDataDir, expected: expectedGreekData }
  );
}

function parseMorphLine(line) {
  const match = line.match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/u);
  if (!match) return null;
  const [, verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma] = match;
  return {
    verseId,
    partOfSpeech,
    parsing,
    surfaceWithPunctuation,
    surfaceForm,
    normalizedForm,
    lemma
  };
}

function verseIdToReferenceParts(verseId) {
  const book = verseId.slice(0, 2);
  const chapter = Number(verseId.slice(2, 4));
  const verse = Number(verseId.slice(4, 6));
  return {
    book,
    bookSlug: bookSlugs[book] || "",
    chapter,
    verse,
    reference: `${bookNames[book] || `Book ${book}`} ${chapter}:${verse}`
  };
}

function formatMorphGntVerse(rows, targetRow = null) {
  const targetRows = Array.isArray(targetRow) ? new Set(targetRow) : new Set(targetRow ? [targetRow] : []);
  return rows
    .map(row => targetRows.has(row) ? `**${row.surfaceWithPunctuation}**` : row.surfaceWithPunctuation)
    .join(" ")
    .replace(/\s+([,.;·:!?])/gu, "$1")
    .replace(/\s+([)\]])/gu, "$1")
    .replace(/([([])\s+/gu, "$1")
    .trim();
}

function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
}

function extractCaseCode(parsing) {
  return String(parsing || "").replace(/-/gu, "").match(/[NGDAV]/u)?.[0] || "";
}

function caseDescription(caseCode) {
  return {
    N: "Nominative",
    G: "Genitive",
    D: "Dative",
    A: "Accusative",
    V: "Vocative"
  }[caseCode] || "";
}

function pad3(value) {
  return String(value).padStart(3, "0");
}

function morphBookToBibleBook(book) {
  const value = Number(book);
  return Number.isFinite(value) ? String(value + 39).padStart(2, "0") : "";
}

function sourceTokenId(referenceParts, tokenPosition) {
  const bibleBook = morphBookToBibleBook(referenceParts.book);
  if (!bibleBook || !tokenPosition) return "";
  return `${bibleBook}${pad3(referenceParts.chapter)}${pad3(referenceParts.verse)}${pad3(tokenPosition)}`;
}

function normalizeComparableText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/gu, "")
    .replace(/[⸀-⸃.,;:!?·'"“”‘’()[\]{}]/gu, "")
    .trim()
    .toLowerCase();
}

async function findFirstExistingDir(paths) {
  for (const path of paths) {
    if (await fileExists(path)) return path;
  }

  return "";
}

async function readProjectLiteralEvidence() {
  const interlinearDir = await findFirstExistingDir([
    join(cgvDataDir, "datasets", "interlinear", "NT"),
    resolve(rootDir, "../MNA/datasets/interlinear/NT")
  ]);

  if (!interlinearDir) {
    return {
      tokenIndex: new Map(),
      verseIndex: new Map()
    };
  }

  const tokenIndex = new Map();
  const verseRows = new Map();
  const files = (await readdir(interlinearDir).catch(() => []))
    .filter(file => file.endsWith(".tokens.jsonl"));

  for (const file of files) {
    const content = await readFile(join(interlinearDir, file), "utf8").catch(() => "");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      if (!line.trim()) continue;

      let row;
      try {
        row = JSON.parse(line);
      } catch {
        continue;
      }

      if (!row.book || !row.ch || !row.vs || !row.lemma) continue;

      const key = `${row.book}|${row.ch}|${row.vs}|${row.lemma}|${normalizeComparableText(row.surface)}`;
      if (!tokenIndex.has(key)) {
        tokenIndex.set(key, []);
      }
      tokenIndex.get(key).push(row.es || "");

      const verseKey = `${row.book}|${row.ch}|${row.vs}`;
      if (!verseRows.has(verseKey)) {
        verseRows.set(verseKey, []);
      }
      verseRows.get(verseKey).push(row.es || "");
    }
  }

  const verseIndex = new Map();
  for (const [key, values] of verseRows) {
    verseIndex.set(key, values.filter(Boolean).join(" ").replace(/\s+/gu, " ").trim());
  }

  return { tokenIndex, verseIndex };
}

async function readBleEvidence() {
  const tokenIndex = new Map();
  const verseIndex = new Map();

  for (const bleDir of [
    join(cgvDataDir, "bibles", "BLE"),
    optionalBleOutputDir
  ]) {
    const bleFiles = (await readdir(bleDir).catch(() => []))
      .filter(file => file.endsWith(".ble.md"));

    for (const file of bleFiles) {
      const book = file.replace(/\.ble\.md$/u, "");
      const content = await readFile(join(bleDir, file), "utf8").catch(() => "");
      for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
        const match = line.match(/^(.+?)\s+(\d+):(\d+)\s+(.+)$/u);
        if (!match) continue;
        const [, , chapter, verse, text] = match;
        const key = `${book}|${Number(chapter)}|${Number(verse)}`;
        if (!verseIndex.has(key)) {
          verseIndex.set(key, text.trim());
        }
      }
    }
  }

  const bleInterlinearDir = join(optionalBleOutputDir, "interlinear", "NT");

  if (!(await fileExists(bleInterlinearDir))) {
    return { tokenIndex, verseIndex };
  }

  const files = (await readdir(bleInterlinearDir).catch(() => []))
    .filter(file => file.endsWith(".interlinear.txt"));

  const tokenPattern = /([^<\s]+)<([^|>]+)\|([^|>]+)\|([^|>]+)\|([^>]+)>/gu;

  for (const file of files) {
    const content = await readFile(join(bleInterlinearDir, file), "utf8").catch(() => "");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const match = line.match(/^([a-z0-9]+)\s+(\d+):(\d+)\t(.+)$/u);
      if (!match) continue;

      const [, book, chapter, verse, tokens] = match;
      for (const token of tokens.matchAll(tokenPattern)) {
        const [, surface, lemma, strongs, morphology, rendering] = token;
        const key = `${book}|${Number(chapter)}|${Number(verse)}|${lemma}|${strongs}|${morphology}|${normalizeComparableText(surface)}`;
        if (!tokenIndex.has(key)) {
          tokenIndex.set(key, []);
        }
        tokenIndex.get(key).push(rendering || "");
      }
    }
  }

  return { tokenIndex, verseIndex };
}

async function readMorphGntRows() {
  const morphDir = await findFirstExistingDir([
    join(cgvDataDir, "morphology", "MorphGNT"),
    join(cgvDataDir, "SOURCES", "MorphGNT"),
    resolve(rootDir, "../MNA/SOURCES/MorphGNT")
  ]);

  if (!morphDir) {
    throw missingGreekDataError(`Checked cgv-data path: ${cgvDataDir}`);
  }

  const files = (await readdir(morphDir))
    .filter(file => file.endsWith("-morphgnt.txt"))
    .sort();

  if (files.length === 0) {
    throw missingGreekDataError(`Checked MorphGNT directory: ${morphDir}`);
  }

  const verseRows = new Map();
  const rows = [];

  for (const file of files) {
    const content = await readFile(join(morphDir, file), "utf8");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const row = parseMorphLine(line);
      if (!row) continue;

      if (!verseRows.has(row.verseId)) {
        verseRows.set(row.verseId, []);
      }
      const verseRowList = verseRows.get(row.verseId);
      row.file = file;
      row.tokenPosition = verseRowList.length + 1;
      rows.push(row);
      verseRowList.push(row);
    }
  }

  return { rows, verseRows };
}

function takeIndexedRendering(index, key) {
  const values = index.get(key);
  if (!values || values.length === 0) return "";
  return values.shift() || "";
}

function peekIndexedRendering(index, key) {
  const values = index.get(key);
  if (!values || values.length === 0) return "";
  return values[0] || "";
}

function buildHighlightedTranslations({
  historical,
  projectLiteralVerse,
  projectLiteralToken,
  bleVerse,
  bleToken,
  strongs = ""
}) {
  const projectFocus = [normalizeFocusToken(projectLiteralToken)].filter(Boolean);
  const bleFocus = [normalizeFocusToken(bleToken)].filter(Boolean);
  const witnessFocus = historical.focusByWitness || {};

  return {
    ...defaultTranslations(),
    projectLiteral: highlightWitnessText(projectLiteralVerse || projectLiteralToken || "", projectFocus, strongs),
    ble: highlightWitnessText(bleVerse || bleToken || "", bleFocus, strongs),
    rv1862: highlightWitnessText(historical.rv1862 || "", [witnessFocus.rv1862], strongs),
    rv1909: highlightWitnessText(historical.rv1909 || "", [witnessFocus.rv1909], strongs),
    spnbes: highlightWitnessText(historical.spnbes || "", [witnessFocus.spnbes], strongs),
    spnvbl: highlightWitnessText(historical.spnvbl || "", [witnessFocus.spnvbl], strongs)
  };
}

function defaultTranslations() {
  return {
    projectLiteral: "",
    ble: "",
    rv1862: "",
    rv1909: "",
    spnbes: "",
    spnvbl: ""
  };
}

export function getCgvDataPath() {
  return cgvDataDir;
}

export async function getGreekOccurrencesByStrongs(strongs, options = {}) {
  const mapping = await resolveGreekLemmaSubject({
    strongs,
    lemma: options.lemma || ""
  });
  const normalizedStrongs = mapping.strongs || normalizeStrongsId(strongs);

  const morphDir = await findFirstExistingDir([
    join(cgvDataDir, "morphology", "MorphGNT"),
    join(cgvDataDir, "SOURCES", "MorphGNT"),
    resolve(rootDir, "../MNA/SOURCES/MorphGNT")
  ]);

  if (!morphDir) {
    throw missingGreekDataError(`Checked cgv-data path: ${cgvDataDir}`);
  }

  const files = (await readdir(morphDir))
    .filter(file => file.endsWith("-morphgnt.txt"))
    .sort();

  if (files.length === 0) {
    throw missingGreekDataError(`Checked MorphGNT directory: ${morphDir}`);
  }

  const occurrences = [];
  const verseRows = new Map();
  const candidateRows = [];
  const verseOccurrenceCounts = new Map();
  const projectLiteralEvidence = await readProjectLiteralEvidence();
  const bleEvidence = await readBleEvidence();
  const translationIndexes = await loadTranslationIndexes(cgvDataDir);

  for (const file of files) {
    const content = await readFile(join(morphDir, file), "utf8");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const row = parseMorphLine(line);
      if (!row) continue;

      if (!verseRows.has(row.verseId)) {
        verseRows.set(row.verseId, []);
      }
      verseRows.get(row.verseId).push(row);

      if (row.lemma !== mapping.lemma) continue;
      candidateRows.push({ file, row });
    }
  }

  for (const { file, row } of candidateRows) {
      const referenceParts = verseIdToReferenceParts(row.verseId);
      const occurrenceIndex = verseOccurrenceCounts.get(row.verseId) ?? 0;
      verseOccurrenceCounts.set(row.verseId, occurrenceIndex + 1);
      const historical = resolveHistoricalRenderings(translationIndexes, {
        book: referenceParts.book,
        chapter: referenceParts.chapter,
        verse: referenceParts.verse,
        strongs: normalizedStrongs,
        occurrenceIndex
      });
      const literalKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse,
        row.lemma,
        normalizeComparableText(row.surfaceForm)
      ].join("|");
      const verseKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse
      ].join("|");
      const bleKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse,
        row.lemma,
        normalizedStrongs,
        formatRmac(row.partOfSpeech, row.parsing),
        normalizeComparableText(row.surfaceForm)
      ].join("|");

      const literalToken = peekIndexedRendering(projectLiteralEvidence.tokenIndex, literalKey);
      const bleToken = peekIndexedRendering(bleEvidence.tokenIndex, bleKey);
      const literalVerse = projectLiteralEvidence.verseIndex.get(verseKey) || "";
      const bleVerse = bleEvidence.verseIndex.get(verseKey) || "";

      occurrences.push({
        reference: referenceParts.reference,
        book: referenceParts.book,
        bookName: bookNames[referenceParts.book] || `Book ${referenceParts.book}`,
        chapter: referenceParts.chapter,
        verse: referenceParts.verse,
        surfaceForm: row.surfaceForm,
        lemma: row.lemma,
        strongs: normalizedStrongs,
        morphology: formatRmac(row.partOfSpeech, row.parsing),
        greekText: formatMorphGntVerse(verseRows.get(row.verseId) || [], row),
        translations: buildHighlightedTranslations({
          historical,
          projectLiteralVerse: literalVerse,
          projectLiteralToken: literalToken,
          bleVerse,
          bleToken,
          strongs: normalizedStrongs
        }),
        source: {
          morphology: `morphology/MorphGNT/${file}`,
          greekText: `morphology/MorphGNT/${file}`,
          sourceNt: "SBLGNT"
        }
      });
  }

  if (occurrences.length === 0) {
    throw missingGreekDataError(`Found MorphGNT files, but no rows for ${mapping.subject}.`);
  }

  return {
    strongs: normalizedStrongs,
    lemma: mapping.lemma,
    subject: mapping.subject,
    source: "cgv-data MorphGNT SBLGNT",
    corpus: "NT",
    language: "greek",
    cgvDataPath: cgvDataDir,
    occurrences
  };
}

/**
 * Gather OT occurrences for a Hebrew/Aramaic Strong's from OSHB token streams.
 */
export async function getHebrewOccurrencesByStrongs(strongs, options = {}) {
  const lemmaHint = String(options.lemma || "").trim();
  const requestedSense = /\d+\s+[a-z]\b/iu.test(lemmaHint) ? oshbLemmaSense(lemmaHint) : "";
  const normalizedStrongs = normalizeStrongsId(strongs, { defaultPrefix: "H" });
  if (!isHebrewStrongs(normalizedStrongs) && !/^\d+$/.test(String(strongs || "").trim())) {
    if (String(normalizedStrongs || "").startsWith("G")) {
      throw missingHebrewDataError(`Strong's ${normalizedStrongs} is Greek — use Greek occurrence gathering.`);
    }
  }
  const hebrewStrongs = isHebrewStrongs(normalizedStrongs)
    ? normalizedStrongs
    : normalizeStrongsId(strongs, { defaultPrefix: "H" });

  const otDir = join(cgvDataDir, "interlinears", "OT");
  let files = [];
  try {
    files = (await readdir(otDir))
      .filter(file => file.endsWith(".tokens.jsonl"))
      .sort();
  } catch {
    throw missingHebrewDataError(`Checked: ${otDir}`);
  }
  if (!files.length) {
    throw missingHebrewDataError(`Checked: ${otDir}`);
  }

  const occurrences = [];
  const translationIndexes = await loadTranslationIndexes(cgvDataDir);
  for (const file of files) {
    const bookId = file.replace(/\.tokens\.jsonl$/u, "");
    const bookLabel = OT_BOOK_LABELS_EN[bookId] || bookId;
    const bookNumber = OT_BOOK_NUMBERS[bookId] || "";
    const content = await readFile(join(otDir, file), "utf8");
    const byVerse = new Map();
    const verseOccurrenceCounts = new Map();

    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      if (!line.trim()) continue;
      let row;
      try {
        row = JSON.parse(line);
      } catch {
        continue;
      }
      const key = `${row.ch}:${row.vs}`;
      if (!byVerse.has(key)) byVerse.set(key, []);
      byVerse.get(key).push(row);
    }

    for (const rows of byVerse.values()) {
      rows.sort((a, b) => Number(a.w) - Number(b.w));
      const hebrewText = rows.map(row => row.surface).filter(Boolean).join(" ");
      for (const row of rows) {
        if (!oshbLemmaMatchesStrongs(row.lemma, hebrewStrongs)) continue;
        if (requestedSense && oshbLemmaSense(row.lemma) !== requestedSense) continue;
        const lang = String(row.morph || "").startsWith("A") ? "arc" : "he";
        const verseKey = `${bookId}|${row.ch}|${row.vs}`;
        const occurrenceIndex = verseOccurrenceCounts.get(verseKey) ?? 0;
        verseOccurrenceCounts.set(verseKey, occurrenceIndex + 1);
        const historical = bookNumber
          ? resolveHistoricalRenderings(translationIndexes, {
            book: bookNumber,
            chapter: Number(row.ch),
            verse: Number(row.vs),
            strongs: hebrewStrongs,
            occurrenceIndex,
            testament: "OT",
            sourceTokenIds: aquiferOshbSourceTokenIds(bookNumber, row)
          })
          : defaultTranslations();
        occurrences.push({
          reference: `${bookLabel} ${row.ch}:${row.vs}`,
          book: bookNumber,
          bookName: bookLabel,
          bookId,
          chapter: Number(row.ch),
          verse: Number(row.vs),
          author: bookLabel,
          surfaceForm: row.surface || "",
          lemma: row.lemma || lemmaHint || hebrewStrongs.replace(/^[HA]/u, ""),
          strongs: hebrewStrongs,
          morphology: row.morph || "",
          lang,
          sourceText: hebrewText,
          hebrewText,
          greekText: hebrewText,
          gloss: row.es || "",
          translations: buildHighlightedTranslations({
            historical,
            projectLiteralVerse: "",
            projectLiteralToken: row.es || "",
            bleVerse: "",
            bleToken: "",
            strongs: hebrewStrongs
          }),
          historicalFocus: historical.focusByWitness || {}
        });
      }
    }
  }

  if (!occurrences.length) {
    throw missingHebrewDataError(`No OT token rows for ${hebrewStrongs}${lemmaHint ? ` (${lemmaHint})` : ""}.`);
  }

  const displayLemma = lemmaHint || occurrences[0]?.surfaceForm || hebrewStrongs;
  return {
    strongs: hebrewStrongs,
    lemma: displayLemma,
    subject: `${hebrewStrongs} ${displayLemma}`.trim(),
    source: "cgv-data OSHB interlinears/OT",
    corpus: "OT",
    language: "hebrew",
    cgvDataPath: cgvDataDir,
    occurrences
  };
}

export async function getGreekConstructionEvidence({
  strongs,
  lemma,
  surface,
  reference,
  rmac,
  prepositionLemma,
  prepositionSurface,
  caseCode
}) {
  const mapping = await resolveGreekLemmaSubject({ strongs, lemma });
  const normalizedStrongs = mapping.strongs;
  const targetLemma = mapping.lemma;
  const targetSurface = String(surface || "").trim();
  const targetCase = String(caseCode || "A").trim().toUpperCase();
  const prepLemma = String(prepositionLemma || "κατά").trim();
  const prepSurface = String(prepositionSurface || "κατὰ").trim();
  const selectedReference = String(reference || "").trim();
  const selectedRmac = String(rmac || "").trim();

  if (!targetLemma) {
    throw missingGreekDataError(`No lemma supplied for construction evidence.`);
  }

  const { verseRows } = await readMorphGntRows();
  const projectLiteralEvidence = await readProjectLiteralEvidence();
  const bleEvidence = await readBleEvidence();
  const translationIndexes = await loadTranslationIndexes(cgvDataDir);
  const occurrenceCounts = new Map();
  const occurrences = [];

  for (const [verseId, rows] of verseRows.entries()) {
    rows.forEach((row, index) => {
      const previous = rows[index - 1];
      const matchesConstruction = previous
        && previous.lemma === prepLemma
        && row.lemma === targetLemma
        && extractCaseCode(row.parsing) === targetCase;

      if (!matchesConstruction) return;

      const referenceParts = verseIdToReferenceParts(verseId);
      const previousSourceTokenId = sourceTokenId(referenceParts, previous.tokenPosition);
      const selectedSourceTokenId = sourceTokenId(referenceParts, row.tokenPosition);
      const occurrenceIndex = occurrenceCounts.get(verseId) ?? 0;
      occurrenceCounts.set(verseId, occurrenceIndex + 1);
      const historical = resolveHistoricalRenderings(translationIndexes, {
        book: referenceParts.book,
        chapter: referenceParts.chapter,
        verse: referenceParts.verse,
        strongs: normalizedStrongs,
        occurrenceIndex,
        sourceTokenIds: [previousSourceTokenId, selectedSourceTokenId].filter(Boolean)
      });
      const literalKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse,
        row.lemma,
        normalizeComparableText(row.surfaceForm)
      ].join("|");
      const verseKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse
      ].join("|");
      const bleKey = [
        referenceParts.bookSlug,
        referenceParts.chapter,
        referenceParts.verse,
        row.lemma,
        normalizedStrongs,
        formatRmac(row.partOfSpeech, row.parsing),
        normalizeComparableText(row.surfaceForm)
      ].join("|");

      occurrences.push({
        reference: referenceParts.reference,
        book: referenceParts.book,
        bookName: bookNames[referenceParts.book] || `Book ${referenceParts.book}`,
        chapter: referenceParts.chapter,
        verse: referenceParts.verse,
        constructionText: `${previous.surfaceForm} ${row.surfaceForm}`,
        constructionPattern: `${previous.lemma} + ${row.lemma} + ${caseDescription(extractCaseCode(row.parsing)).toLowerCase() || extractCaseCode(row.parsing)}`,
        greekText: formatMorphGntVerse(rows, [previous, row]),
        surfaceForm: row.surfaceForm,
        lemma: row.lemma,
        strongs: normalizedStrongs,
        morphology: formatRmac(row.partOfSpeech, row.parsing),
        caseCode: extractCaseCode(row.parsing),
        caseDescription: caseDescription(extractCaseCode(row.parsing)),
        preposition: {
          surfaceForm: previous.surfaceForm,
          lemma: previous.lemma,
          morphology: formatRmac(previous.partOfSpeech, previous.parsing)
        },
        sourceTokenIds: [previousSourceTokenId, selectedSourceTokenId].filter(Boolean),
        translations: buildHighlightedTranslations({
          historical,
          projectLiteralVerse: projectLiteralEvidence.verseIndex.get(verseKey) || "",
          projectLiteralToken: peekIndexedRendering(projectLiteralEvidence.tokenIndex, literalKey),
          bleVerse: bleEvidence.verseIndex.get(verseKey) || "",
          bleToken: peekIndexedRendering(bleEvidence.tokenIndex, bleKey),
          strongs: normalizedStrongs
        }),
        source: {
          morphology: `morphology/MorphGNT/${row.file}`,
          greekText: `morphology/MorphGNT/${row.file}`,
          sourceNt: "SBLGNT"
        }
      });
    });
  }

  return {
    investigationReference: selectedReference,
    selectedToken: targetSurface,
    selectedRmac,
    construction: `${prepSurface} ${targetSurface || targetLemma}`,
    searchPattern: `${prepSurface} + ${targetLemma} + ${caseDescription(targetCase).toLowerCase() || targetCase}`,
    matchBasis: "same preposition + same lemma + same case",
    preposition: {
      surfaceForm: prepSurface,
      lemma: prepLemma
    },
    target: {
      surfaceForm: targetSurface,
      lemma: targetLemma,
      strongs: normalizedStrongs,
      caseCode: targetCase,
      caseDescription: caseDescription(targetCase)
    },
    source: "cgv-data MorphGNT SBLGNT",
    cgvDataPath: cgvDataDir,
    occurrences
  };
}
