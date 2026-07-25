const fs = require("fs");
const path = require("path");

const MAX_POPUP_VERSES = 12;
const MAX_EXACT_FORM_FIRST = 8;

const BOOK_NAMES_ES = {
  "01": "Mateo",
  "02": "Marcos",
  "03": "Lucas",
  "04": "Juan",
  "05": "Hechos",
  "06": "Romanos",
  "07": "1Corintios",
  "08": "2Corintios",
  "09": "Galatas",
  "10": "Efesios",
  "11": "Filipenses",
  "12": "Colosenses",
  "13": "1Tesalonicenses",
  "14": "2Tesalonicenses",
  "15": "1Timoteo",
  "16": "2Timoteo",
  "17": "Tito",
  "18": "Filemon",
  "19": "Hebreos",
  "20": "Santiago",
  "21": "1Pedro",
  "22": "2Pedro",
  "23": "1Juan",
  "24": "2Juan",
  "25": "3Juan",
  "26": "Judas",
  "27": "Apocalipsis"
};

const BOOK_ALIASES_ES = {
  "01": ["Mateo", "Mt"],
  "02": ["Marcos", "Mc"],
  "03": ["Lucas", "Lc"],
  "04": ["Juan", "Jn"],
  "05": ["Hechos", "Hch"],
  "06": ["Romanos", "Ro", "Rom"],
  "07": ["1Corintios", "1 Corintios", "1Co"],
  "08": ["2Corintios", "2 Corintios", "2Co"],
  "09": ["Galatas", "Gálatas", "Ga"],
  "10": ["Efesios", "Ef"],
  "11": ["Filipenses", "Fil", "Flp"],
  "12": ["Colosenses", "Col"],
  "13": ["1Tesalonicenses", "1 Tesalonicenses", "1Ts"],
  "14": ["2Tesalonicenses", "2 Tesalonicenses", "2Ts"],
  "15": ["1Timoteo", "1 Timoteo", "1Ti"],
  "16": ["2Timoteo", "2 Timoteo", "2Ti"],
  "17": ["Tito", "Tit"],
  "18": ["Filemon", "Filemón", "Flm"],
  "19": ["Hebreos", "Heb"],
  "20": ["Santiago", "Stg", "Sant"],
  "21": ["1Pedro", "1 Pedro", "1Pe"],
  "22": ["2Pedro", "2 Pedro", "2Pe"],
  "23": ["1Juan", "1 Juan", "1Jn"],
  "24": ["2Juan", "2 Juan", "2Jn"],
  "25": ["3Juan", "3 Juan", "3Jn"],
  "26": ["Judas", "Jud"],
  "27": ["Apocalipsis", "Ap"]
};

let indexState = {
  loaded: false,
  morphDir: "",
  surfaceToLemma: new Map(),
  lemmaRows: new Map()
};

function firstExistingDirectory(candidates) {
  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
        return candidate;
      }
    } catch {
      // try next
    }
  }
  return "";
}

function resolveMorphGntDir(presenterRootDir) {
  const configured = process.env.CGV_DATA_PATH
    ? path.join(process.env.CGV_DATA_PATH, "morphology", "MorphGNT")
    : "";

  return firstExistingDirectory([
    configured,
    path.join(presenterRootDir, "..", "..", "cgv-data", "morphology", "MorphGNT"),
    path.join(presenterRootDir, "..", "MNA", "SOURCES", "MorphGNT"),
    path.join(presenterRootDir, "data", "MorphGNT")
  ]);
}

function normalizeGreek(value) {
  return String(value || "")
    .normalize("NFC")
    .replace(/[⸀⸁⸂⸃*]/gu, "")
    .replace(/^[,.;:!?·«»"'“”]+|[,.;:!?·«»"'“”]+$/gu, "")
    .trim()
    .toLocaleLowerCase("el");
}

function parseMorphLine(line) {
  const match = String(line || "").match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/u);
  if (!match) return null;
  const [, verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma] = match;
  return {
    verseId,
    partOfSpeech,
    parsing,
    surfaceWithPunctuation,
    surfaceForm,
    normalizedForm,
    lemma: String(lemma || "").trim()
  };
}

function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
}

function referenceFromVerseId(verseId) {
  const book = String(verseId || "").slice(0, 2);
  const chapter = Number(String(verseId).slice(2, 4));
  const verse = Number(String(verseId).slice(4, 6));
  return {
    book,
    chapter,
    verse,
    reference: `${BOOK_NAMES_ES[book] || `Libro ${book}`} ${chapter}:${verse}`
  };
}

function ensureGreekUsageIndex(presenterRootDir) {
  if (indexState.loaded) return indexState;

  const morphDir = resolveMorphGntDir(presenterRootDir);
  indexState.morphDir = morphDir;
  indexState.loaded = true;

  if (!morphDir) {
    console.warn("Greek usage index: MorphGNT not found. Parenthetical Greek popups disabled.");
    return indexState;
  }

  const files = fs.readdirSync(morphDir)
    .filter(name => name.endsWith("-morphgnt.txt"))
    .sort();

  for (const file of files) {
    const content = fs.readFileSync(path.join(morphDir, file), "utf8");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const row = parseMorphLine(line);
      if (!row?.lemma) continue;

      const surfaceKey = normalizeGreek(row.surfaceForm);
      const normalizedKey = normalizeGreek(row.normalizedForm);
      if (surfaceKey) {
        if (!indexState.surfaceToLemma.has(surfaceKey)) {
          indexState.surfaceToLemma.set(surfaceKey, new Set());
        }
        indexState.surfaceToLemma.get(surfaceKey).add(row.lemma);
      }
      if (normalizedKey) {
        if (!indexState.surfaceToLemma.has(normalizedKey)) {
          indexState.surfaceToLemma.set(normalizedKey, new Set());
        }
        indexState.surfaceToLemma.get(normalizedKey).add(row.lemma);
      }

      if (!indexState.lemmaRows.has(row.lemma)) {
        indexState.lemmaRows.set(row.lemma, []);
      }
      indexState.lemmaRows.get(row.lemma).push({
        verseId: row.verseId,
        surfaceForm: row.surfaceForm,
        normalizedForm: row.normalizedForm,
        morphology: formatRmac(row.partOfSpeech, row.parsing)
      });
    }
  }

  console.log(
    `Greek usage index ready: ${indexState.surfaceToLemma.size} forms, ${indexState.lemmaRows.size} lemmas from ${morphDir}`
  );
  return indexState;
}

function chooseLemma(surfaceKey, lemmas) {
  if (!lemmas?.size) return "";
  if (lemmas.size === 1) return [...lemmas][0];

  let bestLemma = "";
  let bestScore = -1;
  for (const lemma of lemmas) {
    const rows = indexState.lemmaRows.get(lemma) || [];
    const score = rows.reduce((total, row) => (
      total + (normalizeGreek(row.surfaceForm) === surfaceKey || normalizeGreek(row.normalizedForm) === surfaceKey ? 1 : 0)
    ), 0);
    if (score > bestScore) {
      bestScore = score;
      bestLemma = lemma;
    }
  }
  return bestLemma || [...lemmas][0];
}

function lookupGreekUsage(surface, options = {}) {
  const presenterRootDir = options.presenterRootDir || __dirname;
  ensureGreekUsageIndex(presenterRootDir);

  const surfaceKey = normalizeGreek(surface);
  if (!surfaceKey || !indexState.morphDir) return null;

  const lemmas = indexState.surfaceToLemma.get(surfaceKey);
  const lemma = chooseLemma(surfaceKey, lemmas);
  if (!lemma) return null;

  const rows = [...(indexState.lemmaRows.get(lemma) || [])];
  const exactRows = [];
  const otherRows = [];
  let morphology = "";

  for (const row of rows) {
    const isExact = normalizeGreek(row.surfaceForm) === surfaceKey
      || normalizeGreek(row.normalizedForm) === surfaceKey;
    if (isExact) {
      if (!morphology) morphology = row.morphology;
      exactRows.push(row);
    } else {
      otherRows.push(row);
    }
  }

  exactRows.sort((a, b) => a.verseId.localeCompare(b.verseId));
  otherRows.sort((a, b) => a.verseId.localeCompare(b.verseId));

  const prioritized = [
    ...exactRows.slice(0, MAX_EXACT_FORM_FIRST),
    ...otherRows,
    ...exactRows.slice(MAX_EXACT_FORM_FIRST)
  ];

  const seenVerses = new Set();
  const occurrences = [];

  for (const row of prioritized) {
    if (seenVerses.has(row.verseId)) continue;
    seenVerses.add(row.verseId);

    const ref = referenceFromVerseId(row.verseId);
    const spanish = typeof options.lookupVerseText === "function"
      ? options.lookupVerseText(ref.book, ref.chapter, ref.verse) || ""
      : "";

    occurrences.push({
      ...ref,
      surfaceForm: row.surfaceForm,
      morphology: row.morphology,
      spanish
    });

    if (occurrences.length >= MAX_POPUP_VERSES) break;
  }

  if (!occurrences.length) return null;

  return {
    surface: String(surface || "").trim(),
    lemma,
    morphology: morphology || occurrences[0].morphology || "",
    count: occurrences.length,
    occurrences
  };
}

function bibleBookCandidates(bookCode) {
  return BOOK_ALIASES_ES[bookCode] || (BOOK_NAMES_ES[bookCode] ? [BOOK_NAMES_ES[bookCode]] : []);
}

module.exports = {
  ensureGreekUsageIndex,
  lookupGreekUsage,
  bibleBookCandidates,
  normalizeGreek,
  BOOK_NAMES_ES
};
