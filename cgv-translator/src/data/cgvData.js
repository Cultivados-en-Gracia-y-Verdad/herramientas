import { existsSync } from "node:fs";
import { access, readFile, readdir } from "node:fs/promises";
import { constants } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadTranslationIndexes, resolveHistoricalRenderings } from "./translationIndexes.js";

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
const optionalBleOutputDir = resolve(rootDir, "../biblia - BLE/output");

const expectedGreekData = [
  "morphology/MorphGNT/*-morphgnt.txt",
  "a Greek Strong's-to-lemma or occurrence index for general Strong's lookup"
];

const prototypeStrongMappings = {
  G1401: {
    lemma: "δοῦλος",
    subject: "G1401 δοῦλος"
  }
};

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
  return rows
    .map(row => row === targetRow ? `**${row.surfaceWithPunctuation}**` : row.surfaceWithPunctuation)
    .join(" ")
    .replace(/\s+([,.;·:!?])/gu, "$1")
    .replace(/\s+([)\]])/gu, "$1")
    .replace(/([([])\s+/gu, "$1")
    .trim();
}

function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
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
  const bleInterlinearDir = join(optionalBleOutputDir, "interlinear", "NT");
  const tokenIndex = new Map();
  const verseIndex = new Map();

  const bleFiles = (await readdir(optionalBleOutputDir).catch(() => []))
    .filter(file => file.endsWith(".ble.md"));

  for (const file of bleFiles) {
    const book = file.replace(/\.ble\.md$/u, "");
    const content = await readFile(join(optionalBleOutputDir, file), "utf8").catch(() => "");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const match = line.match(/^(.+?)\s+(\d+):(\d+)\s+(.+)$/u);
      if (!match) continue;
      const [, , chapter, verse, text] = match;
      verseIndex.set(`${book}|${Number(chapter)}|${Number(verse)}`, text.trim());
    }
  }

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

function takeIndexedRendering(index, key) {
  const values = index.get(key);
  if (!values || values.length === 0) return "";
  return values.shift() || "";
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

export async function getGreekOccurrencesByStrongs(strongs) {
  const normalizedStrongs = String(strongs || "").trim().toUpperCase();
  const mapping = prototypeStrongMappings[normalizedStrongs];

  if (!mapping) {
    throw missingGreekDataError(`No prototype mapping exists for ${normalizedStrongs || "blank Strong's value"}.`);
  }

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

      occurrences.push({
        reference: referenceParts.reference,
        surfaceForm: row.surfaceForm,
        lemma: row.lemma,
        strongs: normalizedStrongs,
        morphology: formatRmac(row.partOfSpeech, row.parsing),
        greekText: formatMorphGntVerse(verseRows.get(row.verseId) || [], row),
        translations: {
          ...defaultTranslations(),
          projectLiteral: projectLiteralEvidence.verseIndex.get(verseKey)
            || takeIndexedRendering(projectLiteralEvidence.tokenIndex, literalKey),
          ble: bleEvidence.verseIndex.get(verseKey)
            || takeIndexedRendering(bleEvidence.tokenIndex, bleKey),
          rv1862: historical.rv1862,
          rv1909: historical.rv1909,
          spnbes: historical.spnbes,
          spnvbl: historical.spnvbl
        },
        source: {
          morphology: `morphology/MorphGNT/${file}`,
          greekText: `morphology/MorphGNT/${file}`,
          sourceNt: "SBLGNT"
        }
      });
  }

  if (occurrences.length === 0) {
    throw missingGreekDataError(`Found MorphGNT files, but no rows for ${normalizedStrongs} ${mapping.lemma}.`);
  }

  return {
    strongs: normalizedStrongs,
    lemma: mapping.lemma,
    subject: mapping.subject,
    source: "cgv-data MorphGNT SBLGNT",
    cgvDataPath: cgvDataDir,
    occurrences
  };
}
