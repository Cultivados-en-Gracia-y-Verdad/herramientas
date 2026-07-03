import { readFile } from "node:fs/promises";
import { join } from "node:path";

const bookUsfxCodes = {
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
  G1401: /\b(siervos?|esclavos?|mozos?|criados?|sirvientes?)\b/giu
};

const rv1862DuplicateBooks = {
  CORINTIOS: ["07", "08"],
  TESALONICENSES: ["13", "14"],
  TIMOTEO: ["15", "16"],
  "SAN PEDRO APOSTOL": ["21", "22"],
  "SAN JUAN APOSTOL": ["23", "24", "25"]
};

let cachedIndexes = null;

function normalizeHeader(line) {
  return line.trim().replace(/\^+/g, "").replace(/\.$/, "").toUpperCase();
}

function referenceToBcv(bookNumber, chapter, verse) {
  const code = bookUsfxCodes[bookNumber];
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
    const segment = content.slice(match.index, next?.index ?? content.length);
    const bcv = match[1];
    verseTextIndex.set(bcv, stripUsfxVerseText(segment));

    for (const wordMatch of segment.matchAll(/<w\s+s="(G\d+)">([^<]*)<\/w>/gi)) {
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

export async function loadTranslationIndexes(cgvDataDir) {
  if (cachedIndexes) return cachedIndexes;

  const [spnbesRaw, spnvblRaw, rv1862Raw, rv1909Raw] = await Promise.all([
    readFile(join(cgvDataDir, "bibles/SPNBES/spa-bes.usfx.xml"), "utf8"),
    readFile(join(cgvDataDir, "bibles/SPNVBL/spa-vbl.usfx.xml"), "utf8"),
    readFile(join(cgvDataDir, "bibles/RV1862/7va6210.txt"), "utf8"),
    readFile(join(cgvDataDir, "bibles/RV1909/7va0910.txt"), "utf8").catch(() => "")
  ]);

  cachedIndexes = {
    spnbes: buildUsfxIndexes(spnbesRaw),
    spnvbl: buildUsfxIndexes(spnvblRaw),
    rv1862: parseRv1862VerseIndex(rv1862Raw),
    rv1909: rv1909Raw ? parseRv1909VerseIndex(rv1909Raw, "04") : new Map()
  };

  return cachedIndexes;
}

export function resolveHistoricalRenderings(indexes, {
  book,
  chapter,
  verse,
  strongs,
  occurrenceIndex
}) {
  const bcv = referenceToBcv(book, chapter, verse);
  return {
    rv1862: lookupRvRendering(indexes.rv1862, book, chapter, verse, strongs, occurrenceIndex),
    rv1909: lookupRvRendering(indexes.rv1909, book, chapter, verse, strongs, occurrenceIndex),
    spnbes: lookupUsfxRendering(
      indexes.spnbes.strongIndex,
      indexes.spnbes.verseTextIndex,
      bcv,
      strongs,
      occurrenceIndex
    ),
    spnvbl: lookupUsfxRendering(
      indexes.spnvbl.strongIndex,
      indexes.spnvbl.verseTextIndex,
      bcv,
      strongs,
      occurrenceIndex
    )
  };
}
