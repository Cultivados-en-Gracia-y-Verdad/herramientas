import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

const otBookUsfxCodes = {
  "01": "GEN",
  "02": "EXO",
  "03": "LEV",
  "04": "NUM",
  "05": "DEU",
  "06": "JOS",
  "07": "JDG",
  "08": "RUT",
  "09": "1SA",
  "10": "2SA",
  "11": "1KI",
  "12": "2KI",
  "13": "1CH",
  "14": "2CH",
  "15": "EZR",
  "16": "NEH",
  "17": "EST",
  "18": "JOB",
  "19": "PSA",
  "20": "PRO",
  "21": "ECC",
  "22": "SNG",
  "23": "ISA",
  "24": "JER",
  "25": "LAM",
  "26": "EZK",
  "27": "DAN",
  "28": "HOS",
  "29": "JOL",
  "30": "AMO",
  "31": "OBA",
  "32": "JON",
  "33": "MIC",
  "34": "NAM",
  "35": "HAB",
  "36": "ZEP",
  "37": "HAG",
  "38": "ZEC",
  "39": "MAL"
};

const ntBookUsfxCodes = {
  "01": "MAT",
  "02": "MRK",
  "03": "LUK",
  "04": "JHN",
  "05": "ACT",
  "06": "ROM",
  "07": "1CO",
  "08": "2CO",
  "09": "GAL",
  "10": "EPH",
  "11": "PHP",
  "12": "COL",
  "13": "1TH",
  "14": "2TH",
  "15": "1TI",
  "16": "2TI",
  "17": "TIT",
  "18": "PHM",
  "19": "HEB",
  "20": "JAS",
  "21": "1PE",
  "22": "2PE",
  "23": "1JN",
  "24": "2JN",
  "25": "3JN",
  "26": "JUD",
  "27": "REV"
};

const strongsSearchPatterns = {
  G1401: /\b(siervos?|esclavos?|mozos?|criados?|sirvientes?)\b/giu,
  G652: /\b(ap[oó]stol(?:es)?)\b/giu,
  G4102: /\b(fe|fidelidad)\b/giu
};

const rv1862OtUnavailable = "Unavailable in cgv-data: RV1862 source is NT-only.";

const rv1862DuplicateBooks = {
  CORINTIOS: ["07", "08"],
  TESALONICENSES: ["13", "14"],
  TIMOTEO: ["15", "16"],
  "SAN PEDRO APOSTOL": ["21", "22"],
  "SAN JUAN APOSTOL": ["23", "24", "25"]
};

let cachedIndexes = null;

function emptyUsfxIndexes() {
  return {
    strongIndex: new Map(),
    verseTextIndex: new Map()
  };
}

function normalizeHeader(line) {
  return line.trim().replace(/\^+/g, "").replace(/\.$/, "").toUpperCase();
}

function referenceToBcv(bookNumber, chapter, verse, testament = "NT") {
  const padded = String(bookNumber || "").padStart(2, "0");
  const code = testament === "OT" ? otBookUsfxCodes[padded] : ntBookUsfxCodes[padded];
  if (!code) return "";
  return `${code}.${chapter}.${verse}`;
}

function stripUsfxVerseText(segment) {
  return segment
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildUsfxIndexes(content) {
  const strongIndex = new Map();
  const verseTextIndex = new Map();
  let currentBcv = "";
  let verseStart = 0;

  const bcvMatches = [...content.matchAll(/bcv="([^"]+)"/g)];

  for (let index = 0; index < bcvMatches.length; index += 1) {
    const match = bcvMatches[index];
    const next = bcvMatches[index + 1];
    const start = content.lastIndexOf("<v", match.index);
    const nextStart = next ? content.lastIndexOf("<v", next.index) : -1;
    const segment = content.slice(
      start === -1 ? match.index : start,
      nextStart === -1 ? content.length : nextStart
    );
    const bcv = match[1];
    verseTextIndex.set(bcv, stripUsfxVerseText(segment));

    for (const wordMatch of segment.matchAll(/<w\s+s="([GHA]\d+)">([^<]*)<\/w>/gi)) {
      const strongs = wordMatch[1].toUpperCase();
      const text = wordMatch[2].trim();
      if (!text) continue;
      const key = `${bcv}|${strongs}`;
      if (!strongIndex.has(key)) strongIndex.set(key, []);
      strongIndex.get(key).push(text);
    }
  }

  return { strongIndex, verseTextIndex };
}

function parseRv1862VerseIndex(content) {
  const index = new Map();
  let currentBook = "";
  let currentChapter = 0;
  const duplicateCounts = new Map();

  const lines = content.replace(/\r\n/g, "\n").split("\n");
  let currentVerse = 0;
  let currentText = "";

  const flushVerse = () => {
    if (!currentBook || !currentChapter || !currentVerse || !currentText.trim()) return;
    index.set(`${currentBook}|${currentChapter}|${currentVerse}`, currentText.replace(/\s+/g, " ").trim());
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    const normalized = normalizeHeader(line);
    if (normalized === "SAN MATEO") {
      currentBook = "01";
      currentChapter = 0;
      continue;
    }
    if (normalized === "SAN MARCOS") {
      currentBook = "02";
      currentChapter = 0;
      continue;
    }
    if (normalized === "SAN LUCAS") {
      currentBook = "03";
      currentChapter = 0;
      continue;
    }
    if (normalized === "SAN JUAN") {
      currentBook = "04";
      currentChapter = 0;
      continue;
    }
    if (normalized === "LOS HECHOS DE LOS APOSTOLES") {
      currentBook = "05";
      currentChapter = 0;
      continue;
    }
    if (normalized === "ROMANOS") {
      currentBook = "06";
      currentChapter = 0;
      continue;
    }
    if (normalized === "GALATAS") {
      currentBook = "09";
      currentChapter = 0;
      continue;
    }
    if (normalized === "EFESIOS") {
      currentBook = "10";
      currentChapter = 0;
      continue;
    }
    if (normalized === "FILIPENSES") {
      currentBook = "11";
      currentChapter = 0;
      continue;
    }
    if (normalized === "COLOSENSES") {
      currentBook = "12";
      currentChapter = 0;
      continue;
    }
    if (normalized === "TITO") {
      currentBook = "17";
      currentChapter = 0;
      continue;
    }
    if (normalized === "FILEMON") {
      currentBook = "18";
      currentChapter = 0;
      continue;
    }
    if (normalized === "HEBREOS") {
      currentBook = "19";
      currentChapter = 0;
      continue;
    }
    if (normalized === "LA EPISTOLA UNIVERSAL DE SANTIAGO") {
      currentBook = "20";
      currentChapter = 0;
      continue;
    }
    if (normalized === "SAN JUAN EL TEOLOGO") {
      currentBook = "27";
      currentChapter = 0;
      continue;
    }
    if (normalized === "LA EPISTOLA UNIVERSAL SAN JUDAS APOSTOL") {
      currentBook = "26";
      currentChapter = 0;
      continue;
    }

    for (const [label, books] of Object.entries(rv1862DuplicateBooks)) {
      if (normalized !== label) continue;
      const count = duplicateCounts.get(label) ?? 0;
      currentBook = books[count] ?? books[books.length - 1];
      duplicateCounts.set(label, count + 1);
      currentChapter = 0;
    }

    const chapterMatch = line.match(/^CAPITULO\s+(\d+)\.?/i);
    if (chapterMatch) {
      flushVerse();
      currentChapter = Number(chapterMatch[1]);
      currentVerse = 0;
      currentText = "";
      continue;
    }

    const verseMatch = rawLine.match(/^\s+(\d+)\s+([\s\S]*)$/);
    if (verseMatch && currentBook && currentChapter) {
      flushVerse();
      currentVerse = Number(verseMatch[1]);
      currentText = verseMatch[2].trim();
      continue;
    }

    if (currentVerse && currentText) {
      currentText += ` ${line}`;
    }
  }

  flushVerse();
  return index;
}

function parseRv1909VerseIndex(content, defaultBook = "04") {
  const index = new Map();
  let currentBook = defaultBook;
  let currentChapter = 0;
  let currentVerse = 0;
  let currentText = "";

  const flushVerse = () => {
    if (!currentBook || !currentChapter || !currentVerse || !currentText.trim()) return;
    index.set(`${currentBook}|${currentChapter}|${currentVerse}`, currentText.replace(/\s+/g, " ").trim());
  };

  for (const rawLine of content.replace(/\r\n/g, "\n").split("\n")) {
    const trimmed = rawLine.trim();
    if (!trimmed) continue;
    const normalized = normalizeHeader(trimmed);

    if (normalized === "A LOS ROMANOS") {
      flushVerse();
      currentBook = "06";
      currentChapter = 0;
      currentVerse = 0;
      currentText = "";
      continue;
    }

    const chapterMatch = trimmed.match(/^Capitulo\s+(\d+)\.?/i);
    if (chapterMatch) {
      flushVerse();
      currentChapter = Number(chapterMatch[1]);
      currentVerse = 0;
      currentText = "";
      continue;
    }

    const verseMatch = rawLine.match(/^\s+(\d+)\s+([\s\S]*)$/);
    if (verseMatch && currentChapter) {
      flushVerse();
      currentVerse = Number(verseMatch[1]);
      currentText = verseMatch[2].trim();
      continue;
    }

    if (currentVerse && currentText) {
      currentText += ` ${trimmed}`;
    }
  }

  flushVerse();
  return index;
}

function lookupUsfxRendering(strongIndex, verseTextIndex, bcv, strongs, occurrenceIndex) {
  if (!bcv || !strongs) return "";
  const [book, chapter, verseText] = bcv.split(".");
  const verse = Number(verseText);
  const candidates = [
    bcv,
    `${book}.${chapter}.${verse + 1}`,
    `${book}.${chapter}.${verse - 1}`
  ];

  for (const candidate of candidates) {
    const values = strongIndex.get(`${candidate}|${strongs}`);
    if (values?.length) {
      return values[occurrenceIndex] ?? values[0] ?? "";
    }
  }

  const pattern = strongsSearchPatterns[strongs];
  if (!pattern) return "";

  for (const candidate of candidates) {
    const verseTextValue = verseTextIndex.get(candidate);
    if (!verseTextValue) continue;
    const matches = [...verseTextValue.matchAll(pattern)];
    if (!matches.length) continue;
    return matches[occurrenceIndex]?.[0] ?? matches[0][0] ?? "";
  }

  return "";
}

function lookupRvRendering(index, book, chapter, verse, strongs, occurrenceIndex) {
  const verseText = index.get(`${book}|${chapter}|${verse}`);
  if (!verseText) return "";

  const pattern = strongsSearchPatterns[strongs];
  if (!pattern) return "";

  const matches = [...verseText.matchAll(pattern)];
  if (!matches.length) return "";
  return matches[occurrenceIndex]?.[0] ?? matches[0][0] ?? "";
}

function lookupRvVerse(index, book, chapter, verse) {
  const padded = String(book || "").padStart(2, "0");
  return index.get(`${padded}|${chapter}|${verse}`)
    || index.get(`${book}|${chapter}|${verse}`)
    || "";
}

/** MorphGNT book 01–27 → Aquifer Protestant 40–66. */
export function morphBookToAquiferBook(book) {
  const value = Number(book);
  if (!Number.isFinite(value) || value < 1 || value > 27) return "";
  return String(value + 39).padStart(2, "0");
}

function bibleBookToMorphBook(book) {
  const value = Number(book);
  if (!Number.isFinite(value) || value < 40) return "";
  return String(value - 39).padStart(2, "0");
}

function sourceBookToAquiferBook(book, testament = "NT") {
  if (testament === "OT") {
    const value = Number(book);
    return Number.isFinite(value) && value >= 1 && value <= 39
      ? String(value).padStart(2, "0")
      : "";
  }

  return morphBookToAquiferBook(book);
}

/**
 * Look up RV1909 verse text by Aquifer Protestant book number (01–66).
 */
export function lookupRv1909AquiferVerse(indexes, aquiferBook, chapter, verse) {
  if (!indexes?.rv1909) return "";
  return lookupRvVerse(indexes.rv1909, aquiferBook, chapter, verse);
}

function stripLeadingVerseNumber(text) {
  return String(text || "").trim().replace(/^\d+\s*/u, "");
}

function tokenizeVerseText(text) {
  const normalized = stripLeadingVerseNumber(text);
  const matches = [...normalized.matchAll(/[\p{L}\p{N}]+(?:[’'][\p{L}\p{N}]+)?|[.,;:!?¿¡()[\]—-]/gu)];
  return matches.map((match, index) => ({
    position: index + 1,
    text: match[0]
  }));
}

function formatTokenSpan(tokens) {
  return tokens
    .map(token => token.text)
    .join(" ")
    .replace(/\s+([.,;:!?()[\]—-])/gu, "$1")
    .replace(/([¿¡])\s+/gu, "$1")
    .trim();
}

function parseMarkdownVerseIndex(content) {
  const verseTextIndex = new Map();
  const tokenIndex = new Map();
  const normalized = content.replace(/\r\n/g, "\n");
  const headingPattern = /^##\s+.+?\s+(\d+):(\d+)\s+\(id:\s*100(\d{2})(\d{3})(\d{3})\)$/gmu;
  const headings = [...normalized.matchAll(headingPattern)];

  for (let index = 0; index < headings.length; index += 1) {
    const match = headings[index];
    const next = headings[index + 1];
    const [, chapterText, verseText, bibleBook, chapterFromId, verseFromId] = match;
    const block = normalized.slice(match.index + match[0].length, next?.index ?? normalized.length);
    const verseLine = block
      .split("\n")
      .map(line => line.trim())
      .find(line => line && !line.startsWith("#") && !line.startsWith("-"));
    if (!verseLine) continue;

    const morphBook = bibleBookToMorphBook(bibleBook);
    const chapter = Number(chapterFromId || chapterText);
    const verse = Number(verseFromId || verseText);
    // Always index by Aquifer Protestant book number (01–66).
    // MorphGNT 01–27 keys collide with OT Aquifer numbers (e.g. 27 = Daniel vs Revelation).
    const verseKey = `${bibleBook}|${chapter}|${verse}`;
    const fullVerseKey = `${bibleBook}${chapterFromId}${verseFromId}`;
    const cleanText = stripLeadingVerseNumber(verseLine);
    verseTextIndex.set(verseKey, cleanText);
    if (morphBook) {
      // Keep a morph-prefixed alias for callers that still pass MorphGNT book codes.
      verseTextIndex.set(`m${morphBook}|${chapter}|${verse}`, cleanText);
    }
    tokenIndex.set(fullVerseKey, tokenizeVerseText(verseLine));
  }

  return { verseTextIndex, tokenIndex };
}

function mergeMarkdownVerseIndexes(indexes) {
  const merged = {
    verseTextIndex: new Map(),
    tokenIndex: new Map()
  };

  for (const index of indexes) {
    for (const [key, value] of index.verseTextIndex) {
      merged.verseTextIndex.set(key, value);
    }
    for (const [key, value] of index.tokenIndex) {
      merged.tokenIndex.set(key, value);
    }
  }

  return merged;
}

function parseAlignmentIndex(contents, targetTokenIndex) {
  const sourceToTargets = new Map();

  for (const content of contents) {
    let data;
    try {
      data = JSON.parse(content);
    } catch {
      continue;
    }

    for (const record of data.records || []) {
      const sourceIds = (record.source || [])
        .map(value => String(value).match(/^[no]?(\d+)\|/u)?.[1])
        .filter(Boolean);
      const targetIds = (record.target || [])
        .map(value => String(value).match(/^(\d+)\|/u)?.[1])
        .filter(Boolean);

      for (const sourceId of sourceIds) {
        if (!sourceToTargets.has(sourceId)) sourceToTargets.set(sourceId, []);
        sourceToTargets.get(sourceId).push(...targetIds);
      }
    }
  }

  return { sourceToTargets, targetTokenIndex };
}

function lookupAlignedSpan(alignmentIndex, sourceTokenIds = []) {
  if (!alignmentIndex || !sourceTokenIds.length) return "";
  const targetIds = sourceTokenIds.flatMap(id => {
    const normalizedId = String(id).replace(/^[no]/u, "");
    return alignmentIndex.sourceToTargets.get(normalizedId) || alignmentIndex.sourceToTargets.get(String(id)) || [];
  });
  if (!targetIds.length) return "";

  const verseIds = [...new Set(targetIds.map(id => id.slice(0, 8)))];
  if (verseIds.length !== 1) return "";

  const positions = targetIds
    .map(id => Number(id.slice(8, 11)))
    .filter(Number.isFinite);
  if (!positions.length) return "";

  const min = Math.min(...positions);
  const max = Math.max(...positions);
  const tokens = alignmentIndex.targetTokenIndex.get(verseIds[0]) || [];
  return formatTokenSpan(tokens.filter(token => token.position >= min && token.position <= max));
}

export function resolveAlignedSpan(indexes, sourceTokenIds = []) {
  return lookupAlignedSpan(indexes?.rv1909Alignment, sourceTokenIds);
}

export async function loadTranslationIndexes(cgvDataDir) {
  if (cachedIndexes) return cachedIndexes;

  const [spnbesRaw, spnvblRaw, rv1862Raw, legacyRv1909Raw] = await Promise.all([
    readFile(join(cgvDataDir, "bibles/SPNBES/spa-bes.usfx.xml"), "utf8").catch(() => ""),
    readFile(join(cgvDataDir, "bibles/SPNVBL/spa-vbl.usfx.xml"), "utf8").catch(() => ""),
    readFile(join(cgvDataDir, "bibles/RV1862/7va6210.txt"), "utf8").catch(() => ""),
    readFile(join(cgvDataDir, "bibles/RV1909/7va0910.txt"), "utf8").catch(() => "")
  ]);
  const rv1909MdDir = join(cgvDataDir, "bibles/RV1909/md");
  const rv1909AlignmentDir = join(cgvDataDir, "bibles/RV1909/alignments");
  const [rv1909MdFiles, rv1909AlignmentFiles] = await Promise.all([
    readdir(rv1909MdDir).catch(() => []),
    readdir(rv1909AlignmentDir).catch(() => [])
  ]);
  const rv1909MarkdownIndexes = await Promise.all(
    rv1909MdFiles
      .filter(file => file.endsWith(".content.md"))
      .map(async file => parseMarkdownVerseIndex(
        await readFile(join(rv1909MdDir, file), "utf8").catch(() => "")
      ))
  );
  const rv1909Markdown = mergeMarkdownVerseIndexes(rv1909MarkdownIndexes);
  const rv1909AlignmentContents = await Promise.all(
    rv1909AlignmentFiles
      .filter(file => file.endsWith(".alignment.json"))
      .map(file => readFile(join(rv1909AlignmentDir, file), "utf8").catch(() => ""))
  );

  cachedIndexes = {
    spnbes: spnbesRaw ? buildUsfxIndexes(spnbesRaw) : emptyUsfxIndexes(),
    spnvbl: spnvblRaw ? buildUsfxIndexes(spnvblRaw) : emptyUsfxIndexes(),
    rv1862: rv1862Raw ? parseRv1862VerseIndex(rv1862Raw) : new Map(),
    rv1909: rv1909Markdown.verseTextIndex.size
      ? rv1909Markdown.verseTextIndex
      : (legacyRv1909Raw ? parseRv1909VerseIndex(legacyRv1909Raw, "04") : new Map()),
    rv1909Alignment: parseAlignmentIndex(rv1909AlignmentContents, rv1909Markdown.tokenIndex)
  };

  return cachedIndexes;
}

function escapeRegExp(value = "") {
  return String(value).replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}

export function normalizeFocusToken(value = "") {
  return String(value || "")
    .replace(/\*\*/gu, "")
    .replace(/[•·]/gu, "")
    .replace(/\s+/gu, " ")
    .trim();
}

/**
 * Bold the investigated Spanish rendering(s) inside a witness verse.
 */
export function highlightWitnessText(text = "", focusWords = [], strongs = "") {
  let result = String(text || "");
  if (!result || result === "—") return result;

  const terms = [...new Set(
    (Array.isArray(focusWords) ? focusWords : [focusWords])
      .map(normalizeFocusToken)
      .filter(term => term && term.length > 1)
  )].sort((left, right) => right.length - left.length);

  for (const term of terms) {
    const pattern = escapeRegExp(term).replace(/\\ /gu, "\\s+");
    const re = new RegExp(`(?<!\\*\\*)(${pattern})(?!\\*\\*)`, "iu");
    result = result.replace(re, "**$1**");
  }

  // Fallback: Strong's Spanish gloss pattern (covers RV when USFX focus is missing).
  const strongsKey = String(strongs || "").trim().toUpperCase();
  const glossPattern = strongsSearchPatterns[strongsKey];
  if (glossPattern && !/\*\*[^*]+\*\*/u.test(result)) {
    const flags = glossPattern.flags.includes("g") ? glossPattern.flags : `${glossPattern.flags}g`;
    result = result.replace(new RegExp(glossPattern.source, flags), "**$1**");
  }

  return result;
}

export function resolveHistoricalRenderings(indexes, {
  book,
  chapter,
  verse,
  strongs,
  occurrenceIndex,
  testament = "NT",
  sourceTokenIds = []
}) {
  const bcv = referenceToBcv(book, chapter, verse, testament);
  const spnbesFocus = lookupUsfxRendering(
    indexes.spnbes.strongIndex,
    indexes.spnbes.verseTextIndex,
    bcv,
    strongs,
    occurrenceIndex
  );
  const spnvblFocus = lookupUsfxRendering(
    indexes.spnvbl.strongIndex,
    indexes.spnvbl.verseTextIndex,
    bcv,
    strongs,
    occurrenceIndex
  );
  const paddedBook = String(book || "").padStart(2, "0");
  const aquiferBook = sourceBookToAquiferBook(book, testament) || paddedBook;
  const rv1862Focus = testament === "NT"
    ? lookupRvRendering(indexes.rv1862, book, chapter, verse, strongs, occurrenceIndex)
    : "";
  const rv1909Focus = lookupRvRendering(indexes.rv1909, aquiferBook, chapter, verse, strongs, occurrenceIndex)
    || (testament === "NT" ? lookupRvRendering(indexes.rv1909, `m${paddedBook}`, chapter, verse, strongs, occurrenceIndex) : "");

  const rv1862 = testament === "NT"
    ? lookupRvVerse(indexes.rv1862, book, chapter, verse) || rv1862Focus
    : rv1862OtUnavailable;
  const rv1909Aligned = lookupAlignedSpan(indexes.rv1909Alignment, sourceTokenIds);
  const rv1909 = lookupRvVerse(indexes.rv1909, aquiferBook, chapter, verse)
    || (testament === "NT" ? lookupRvVerse(indexes.rv1909, `m${paddedBook}`, chapter, verse) : "")
    || rv1909Aligned
    || rv1909Focus;
  const spnbes = indexes.spnbes.verseTextIndex.get(bcv) || spnbesFocus;
  const spnvbl = indexes.spnvbl.verseTextIndex.get(bcv) || spnvblFocus;

  const focusWords = [...new Set(
    [spnbesFocus, spnvblFocus, rv1862Focus, rv1909Aligned, rv1909Focus]
      .map(normalizeFocusToken)
      .filter(Boolean)
  )];

  return {
    rv1862,
    rv1909,
    spnbes,
    spnvbl,
    focusWords,
    focusByWitness: {
      rv1862: rv1862Focus,
      rv1909: rv1909Aligned || rv1909Focus,
      spnbes: spnbesFocus,
      spnvbl: spnvblFocus
    }
  };
}
