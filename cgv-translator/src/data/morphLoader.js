/**
 * MorphGNT / OSHB loaders for Translator.
 */
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { findBook, sourceTokenId, NT_BOOKS, OT_PILOT_BOOKS } from "./bookCatalog.js";
import { strongsForLemma } from "./strongsIndex.js";
import { getCgvDataPath } from "./cgvData.js";
import { loadTranslationIndexes, resolveAlignedSpan } from "./translationIndexes.js";

const bleGlossBulletMarks = new Set(["de", "a", "en", "por", "para", "con", "sin", "que", "medio", "causa"]);
const bleGlossSplits = { del: ["de"], al: ["a", "el"] };

async function readFirstExistingFile(candidates) {
  for (const candidate of candidates) {
    try {
      return await readFile(candidate, "utf8");
    } catch {
      // next
    }
  }
  return "";
}

export function parseMorphLine(line) {
  const match = line.match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/u);
  if (!match) return null;
  const [, verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma] = match;
  return { verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma };
}

export function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
}

function parseVerbMorph(parsing = "") {
  const raw = String(parsing || "").replace(/-/gu, "");
  if (!raw) return null;
  if (/^[123][PIFARL]/u.test(raw)) {
    return {
      person: raw[0],
      tense: raw[1],
      voice: raw[2],
      mood: raw[3],
      number: raw[4] || ""
    };
  }
  if (/^[PIFARL][AMPEONQX]/u.test(raw)) {
    return {
      tense: raw[0],
      voice: raw[1],
      mood: raw[2],
      person: raw[3] || "",
      number: raw[4] || ""
    };
  }
  return null;
}

/** Fix: gender must use noun case-number-gender slots, not first [MFN] in the string. */
export function describeMorphologySpanish(partOfSpeech, parsing) {
  const caseNames = { N: "nominativo", G: "genitivo", D: "dativo", A: "acusativo", V: "vocativo" };
  const numberNames = { S: "singular", P: "plural" };
  const genderNames = { M: "masculino", F: "femenino", N: "neutro" };
  const tenseNames = { P: "presente", I: "imperfecto", F: "futuro", A: "aoristo", R: "perfecto", L: "pluscuamperfecto" };
  const voiceNames = { A: "activo", M: "medio", P: "pasivo", E: "medio/pasivo", D: "medio", O: "pasivo", N: "medio/pasivo" };
  const moodNames = { I: "indicativo", S: "subjuntivo", O: "optativo", M: "imperativo", N: "infinitivo", P: "participio", D: "imperativo" };

  const pos = String(partOfSpeech || "");
  const compact = String(parsing || "").replace(/-/gu, "");

  if (pos === "V-" || pos.startsWith("V")) {
    const verb = parseVerbMorph(parsing);
    if (!verb) return "—";
    return [
      tenseNames[verb.tense],
      voiceNames[verb.voice],
      moodNames[verb.mood],
      verb.person ? `${verb.person}.ª persona` : "",
      numberNames[verb.number]
    ].filter(Boolean).join(", ") || "—";
  }

  // Nominal / adjective / article / pronoun: MorphGNT trailing case-number-gender
  const cng = compact.match(/([NGDAV])([SP])([MFN])$/u);
  if (cng) {
    return [caseNames[cng[1]], numberNames[cng[2]], genderNames[cng[3]]].filter(Boolean).join(" ");
  }

  return "—";
}

export function formatGreekVerse(rows) {
  return rows
    .map(row => row.surfaceWithPunctuation)
    .join(" ")
    .replace(/\s+([,.;·:!?])/gu, "$1")
    .replace(/\s+([)\]])/gu, "$1")
    .replace(/([([])\s+/gu, "$1")
    .trim();
}

function bleGlossToText(es) {
  const core = String(es || "").trim();
  if (!core || core === "?") return "";
  if (!core.includes("·")) return core;
  const parts = [];
  for (const raw of core.split("·")) {
    const part = raw.trim();
    if (!part) continue;
    parts.push(...(bleGlossSplits[part.toLowerCase()] || [part]));
  }
  let out = "";
  for (const part of parts) {
    if (bleGlossBulletMarks.has(part.toLowerCase())) {
      out += `${part}•`;
    } else {
      if (out && !out.endsWith("•")) out += " ";
      out += part;
    }
  }
  return out;
}

async function loadBleTokenGlossIndex(rootDir, bookSlug) {
  const index = new Map();
  const content = await readFirstExistingFile([
    join(rootDir, "..", "MNA", "datasets", "interlinear", "NT", `${bookSlug}.tokens.jsonl`),
    join(getCgvDataPath(), "datasets", "interlinear", "NT", `${bookSlug}.tokens.jsonl`)
  ]);
  if (!content) return index;
  for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
    if (!line.trim()) continue;
    let row;
    try {
      row = JSON.parse(line);
    } catch {
      continue;
    }
    if (!row?.ch || !row?.vs || !row?.tok) continue;
    index.set(`${Number(row.ch)}|${Number(row.vs)}|${Number(row.tok)}`, bleGlossToText(row.es || ""));
  }
  return index;
}

function splitReferenceTokens(text) {
  return String(text || "")
    .trim()
    .split(/\s+/u)
    .map(token => token.replace(/^[,.;:!?¿¡]+|[,.;:!?¿¡]+$/gu, ""))
    .filter(Boolean);
}

export async function buildTokenRows({
  rootDir,
  rows,
  bookCode,
  chapter,
  verse,
  bleText,
  translationIndexes,
  bleGlossIndex = null
}) {
  const bleTokens = splitReferenceTokens(bleText);
  const out = [];
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const id = sourceTokenId(bookCode, chapter, verse, index + 1);
    const glossKey = `${Number(chapter)}|${Number(verse)}|${index + 1}`;
    const bleFromJsonl = bleGlossIndex?.get(glossKey) || "";
    // eslint-disable-next-line no-await-in-loop
    const strongs = await strongsForLemma(rootDir, row.lemma);
    out.push({
      sourceTokenId: id,
      greek: row.surfaceForm,
      lemma: row.lemma,
      strongs,
      rmac: formatRmac(row.partOfSpeech, row.parsing),
      morphology: describeMorphologySpanish(row.partOfSpeech, row.parsing),
      ble: bleFromJsonl || bleTokens[index] || "",
      rv1909: resolveAlignedSpan(translationIndexes, [id])
    });
  }
  return out;
}

export async function loadNtBookUnits(rootDir, bookId = "titus") {
  const book = findBook(bookId) || findBook("titus");
  if (!book) throw new Error(`Unknown book: ${bookId}`);
  const bookCode = book.bookCode || book.number;
  const cgvDataDir = getCgvDataPath();
  const morphDir = join(rootDir, "..", "MNA", "SOURCES", "MorphGNT");
  const bibliaBleOutputDir = join(rootDir, "..", "Biblia-BLE", "output");

  const [translationIndexes, bleGlossIndex, bleContent, morphContent] = await Promise.all([
    loadTranslationIndexes(cgvDataDir),
    loadBleTokenGlossIndex(rootDir, book.bleSlug),
    readFirstExistingFile([
      join(cgvDataDir, `bibles/BLE/${book.bleSlug}.ble.md`),
      join(bibliaBleOutputDir, `${book.bleSlug}.ble.md`)
    ]),
    readFirstExistingFile([
      join(cgvDataDir, `morphology/MorphGNT/${book.morphFile}`),
      join(cgvDataDir, `SOURCES/MorphGNT/${book.morphFile}`),
      join(morphDir, book.morphFile)
    ])
  ]);

  const greekByReference = new Map();
  for (const line of morphContent.replace(/\r\n/g, "\n").split("\n")) {
    const row = parseMorphLine(line);
    if (!row) continue;
    const chapter = Number(row.verseId.slice(2, 4));
    const verse = Number(row.verseId.slice(4, 6));
    const reference = `${book.label} ${chapter}:${verse}`;
    if (!greekByReference.has(reference)) greekByReference.set(reference, []);
    greekByReference.get(reference).push(row);
  }

  const bleLabel = book.bleSlug === "tito" ? "Tito" : book.label;
  // BLE files use Spanish book names; try both patterns.
  const bleLines = bleContent.replace(/\r\n/g, "\n").split("\n");
  const units = [];

  for (const [reference, greekRows] of greekByReference) {
    const m = reference.match(/^(.+?)\s+(\d+):(\d+)$/u);
    if (!m) continue;
    const chapter = Number(m[2]);
    const verse = Number(m[3]);
    const bleLine = bleLines.find(line =>
      new RegExp(`^(?:Tito|${book.label}|${bleLabel})\\s+${chapter}:${verse}\\s+`, "u").test(line)
    );
    const bleText = bleLine ? bleLine.replace(/^[^\d]+\d+:\d+\s+/u, "").trim() : "";
    const tokenRows = await buildTokenRows({
      rootDir,
      rows: greekRows,
      bookCode,
      chapter,
      verse,
      bleText,
      translationIndexes,
      bleGlossIndex
    });
    const sourceTokenIds = tokenRows.map(row => row.sourceTokenId);
    units.push({
      bookId: book.id,
      reference,
      chapter,
      verse,
      greekText: formatGreekVerse(greekRows),
      sourceTokenIds,
      tokenRows,
      rv1909Text: translationIndexes.rv1909.get(`${bookCode}|${chapter}|${verse}`)
        || resolveAlignedSpan(translationIndexes, sourceTokenIds),
      bleText: tokenRows.map(row => row.ble).filter(Boolean).join(" ") || bleText
    });
  }

  units.sort((a, b) => a.chapter - b.chapter || a.verse - b.verse);
  return { book, units };
}

export function listNtBooks() {
  return NT_BOOKS.map(({ id, label, usfm }) => ({ id, label, usfm }));
}

/**
 * Minimal OSHB verse loader for OT pilot (surface + morph codes).
 */
export async function loadOshbPilotChapter(rootDir, bookId = "jonah", chapter = 1) {
  const book = OT_PILOT_BOOKS.find(b => b.id === String(bookId || "").toLowerCase()) || null;
  if (!book) throw new Error(`Unknown OT pilot book: ${bookId}`);
  const xmlPath = join(rootDir, "..", "Biblia-LBF", "source", "hebrew", "OSHB", "morphhb", "wlc", book.oshbFile);
  const xml = await readFile(xmlPath, "utf8");
  const chapterRe = new RegExp(`<chapter n="${chapter}">([\\s\\S]*?)</chapter>`, "u");
  const chapterMatch = xml.match(chapterRe);
  if (!chapterMatch) return { book, chapter, verses: [] };

  const verses = [];
  const verseRe = /<verse n="(\d+)">([\s\S]*?)<\/verse>/gu;
  let vm;
  while ((vm = verseRe.exec(chapterMatch[1]))) {
    const vs = Number(vm[1]);
    const body = vm[2];
    const tokens = [];
    const wRe = /<w[^>]*lemma="([^"]*)"[^>]*morph="([^"]*)"[^>]*>([^<]*)<\/w>/gu;
    let wm;
    let pos = 0;
    while ((wm = wRe.exec(body))) {
      pos += 1;
      const lemmaAttr = wm[1];
      const num = (lemmaAttr.match(/0*(\d+)/u) || [])[1];
      const strongs = num ? `H${Number(num)}` : "";
      tokens.push({
        sourceTokenId: `h${String(book.number).padStart(2, "0")}${String(chapter).padStart(3, "0")}${String(vs).padStart(3, "0")}${String(pos).padStart(3, "0")}`,
        surface: wm[3],
        lemma: lemmaAttr,
        morph: wm[2],
        strongs
      });
    }
    verses.push({
      reference: `${book.label} ${chapter}:${vs}`,
      verse: vs,
      tokens,
      hebrewText: tokens.map(t => t.surface).join(" ")
    });
  }
  return { book, chapter, verses };
}
