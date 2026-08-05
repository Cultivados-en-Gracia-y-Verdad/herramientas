const fs = require("fs");
const path = require("path");
const { highlightSpanishInVerse } = require("./greekUsage");

const MAX_POPUP_VERSES = 12;
const MAX_EXACT_FORM_FIRST = 8;
const MAX_TRANSLATION_SAMPLES = 24;

const BOOK_NAMES_ES = {
  genesis: "Génesis",
  exodo: "Éxodo",
  levitico: "Levítico",
  numeros: "Números",
  deuteronomio: "Deuteronomio",
  josue: "Josué",
  jueces: "Jueces",
  rut: "Rut",
  "1samuel": "1 Samuel",
  "2samuel": "2 Samuel",
  "1reyes": "1 Reyes",
  "2reyes": "2 Reyes",
  "1cronicas": "1 Crónicas",
  "2cronicas": "2 Crónicas",
  esdras: "Esdras",
  nehemias: "Nehemías",
  ester: "Ester",
  job: "Job",
  salmos: "Salmos",
  proverbios: "Proverbios",
  eclesiastes: "Eclesiastés",
  cantares: "Cantares",
  isaias: "Isaías",
  jeremias: "Jeremías",
  lamentaciones: "Lamentaciones",
  ezequiel: "Ezequiel",
  daniel: "Daniel",
  oseas: "Oseas",
  joel: "Joel",
  amos: "Amós",
  abdias: "Abdías",
  jonas: "Jonás",
  miqueas: "Miqueas",
  nahum: "Nahúm",
  habacuc: "Habacuc",
  sofonias: "Sofonías",
  hageo: "Hageo",
  zacarias: "Zacarías",
  malaquias: "Malaquías"
};

const BOOK_ALIASES_ES = {
  genesis: ["Génesis", "Genesis", "Gn", "Gén"],
  exodo: ["Éxodo", "Exodo", "Éx", "Ex"],
  levitico: ["Levítico", "Levitico", "Lv", "Lev"],
  numeros: ["Números", "Numeros", "Nm", "Núm"],
  deuteronomio: ["Deuteronomio", "Dt", "Deut"],
  josue: ["Josué", "Josue", "Jos"],
  jueces: ["Jueces", "Jue", "Jc"],
  rut: ["Rut", "Rt"],
  "1samuel": ["1 Samuel", "1Samuel", "1 Sam", "1Sa"],
  "2samuel": ["2 Samuel", "2Samuel", "2 Sam", "2Sa"],
  "1reyes": ["1 Reyes", "1Reyes", "1 Re", "1Re", "1 R"],
  "2reyes": ["2 Reyes", "2Reyes", "2 Re", "2Re", "2 R"],
  "1cronicas": ["1 Crónicas", "1 Cronicas", "1Crónicas", "1 Cronicas", "1 Cr", "1Cr"],
  "2cronicas": ["2 Crónicas", "2 Cronicas", "2Crónicas", "2 Cronicas", "2 Cr", "2Cr"],
  esdras: ["Esdras", "Esd"],
  nehemias: ["Nehemías", "Nehemias", "Neh"],
  ester: ["Ester", "Est"],
  job: ["Job"],
  salmos: ["Salmos", "Salmo", "Sal", "Sl"],
  proverbios: ["Proverbios", "Prov", "Pr"],
  eclesiastes: ["Eclesiastés", "Eclesiastes", "Ec", "Ecl"],
  cantares: ["Cantares", "Cantar de los Cantares", "Cnt", "Cant"],
  isaias: ["Isaías", "Isaias", "Is"],
  jeremias: ["Jeremías", "Jeremias", "Jer"],
  lamentaciones: ["Lamentaciones", "Lam"],
  ezequiel: ["Ezequiel", "Ez", "Eze"],
  daniel: ["Daniel", "Dn", "Dan"],
  oseas: ["Oseas", "Os"],
  joel: ["Joel", "Jl"],
  amos: ["Amós", "Amos", "Am"],
  abdias: ["Abdías", "Abdias", "Abd"],
  jonas: ["Jonás", "Jonas", "Jon"],
  miqueas: ["Miqueas", "Miq", "Mi"],
  nahum: ["Nahúm", "Nahum", "Nah"],
  habacuc: ["Habacuc", "Hab"],
  sofonias: ["Sofonías", "Sofonias", "Sof"],
  hageo: ["Hageo", "Hag"],
  zacarias: ["Zacarías", "Zacarias", "Zac"],
  malaquias: ["Malaquías", "Malaquias", "Mal"]
};

let indexState = {
  loaded: false,
  tokensDir: "",
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

function resolveOtTokensDir(presenterRootDir) {
  const configured = process.env.CGV_DATA_PATH
    ? path.join(process.env.CGV_DATA_PATH, "interlinears", "OT")
    : "";
  const resourcesRoot = process.resourcesPath || "";

  return firstExistingDirectory([
    configured,
    resourcesRoot ? path.join(resourcesRoot, "interlinears", "OT") : "",
    path.join(presenterRootDir, "..", "..", "cgv-data", "interlinears", "OT"),
    path.join(presenterRootDir, "..", "Biblia-BLE", "output", "interlinear", "OT"),
    path.join(presenterRootDir, "data", "ot-tokens")
  ]);
}

function normalizeHebrew(value) {
  return String(value || "")
    .normalize("NFC")
    // Strip cantillation marks, vowel points, and related marks.
    .replace(/[\u0591-\u05C7]/gu, "")
    .replace(/[\u05F3\u05F4]/gu, "")
    .replace(/[\/\\|]/gu, "")
    .replace(/^[,.;:!?·«»"'“”׳״]+|[,.;:!?·«»"'“”׳״]+$/gu, "")
    .trim();
}

function unpointHebrew(value) {
  return normalizeHebrew(value);
}

function cleanBleGloss(gloss) {
  return String(gloss || "")
    .replace(/[•·]/gu, " ")
    .replace(/\s+/gu, " ")
    .trim();
}

function normalizeSpanish(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/gu, "")
    .toLowerCase()
    .replace(/[•·]/gu, "")
    .trim();
}

const SPANISH_STOPWORDS = new Set([
  "a", "al", "de", "del", "el", "la", "lo", "los", "las", "un", "una", "uno", "unos", "unas",
  "y", "e", "o", "u", "en", "con", "por", "para", "sin", "sobre", "entre", "como", "que",
  "se", "su", "sus", "mi", "mis", "tu", "tus", "le", "les", "me", "te", "nos", "os",
  "es", "son", "ser", "esta", "este", "esto", "estos", "estas", "hay", "obj"
]);

function formatStrongLemma(lemma) {
  const raw = String(lemma || "").trim();
  if (!raw) return "";
  // "1254 a" → H1254a ; "b/7225" → b/H7225
  return raw.replace(/\b(\d{1,5})(?:\s*([a-z]))?\b/giu, (_, num, letter) => (
    `H${num}${letter ? String(letter).toLowerCase() : ""}`
  ));
}

const POS_LABELS = {
  V: "verbo",
  N: "sustantivo",
  A: "adjetivo",
  R: "preposición",
  C: "conjunción",
  D: "adverbio",
  P: "pronombre",
  S: "sufijo",
  T: "partícula",
  I: "interjección",
  M: "número"
};

const STEM_LABELS = {
  q: "qal",
  N: "nifal",
  p: "piel",
  P: "pual",
  h: "hifil",
  H: "hofal",
  t: "hitpael",
  o: "polal",
  O: "polal",
  u: "pulal"
};

const ASPECT_LABELS = {
  p: "perfecto",
  i: "imperfecto",
  w: "wayyiqtol",
  v: "imperativo",
  j: "yusivo",
  r: "participio",
  c: "infinitivo constructo",
  a: "infinitivo absoluto"
};

const GENDER_LABELS = {
  m: "masculino",
  f: "femenino",
  b: "común",
  c: "común"
};

const NUMBER_LABELS = {
  s: "singular",
  p: "plural",
  d: "dual"
};

const STATE_LABELS = {
  a: "absoluto",
  c: "constructo",
  d: "determinado"
};

const PERSON_LABELS = {
  1: "1ª persona",
  2: "2ª persona",
  3: "3ª persona"
};

function describeOshbPart(part) {
  const value = String(part || "").trim();
  if (!value) return [];

  const labels = [];
  let rest = value;

  if (/^[HA]/u.test(rest) && rest.length > 1) {
    if (rest[0] === "A") labels.push("arameo");
    rest = rest.slice(1);
  }

  const pos = rest[0];
  if (POS_LABELS[pos]) labels.push(POS_LABELS[pos]);
  rest = rest.slice(1);

  if (pos === "V" && rest.length >= 2) {
    const stem = STEM_LABELS[rest[0]] || "";
    const aspect = ASPECT_LABELS[rest[1]] || "";
    if (stem) labels.push(stem);
    if (aspect) labels.push(aspect);
    rest = rest.slice(2);

    const personMatch = rest.match(/^([123])/u);
    if (personMatch) {
      labels.push(PERSON_LABELS[personMatch[1]]);
      rest = rest.slice(1);
    }
  }

  if (/^[mfbc]/iu.test(rest[0] || "")) {
    const gender = GENDER_LABELS[rest[0].toLowerCase()];
    if (gender) labels.push(gender);
    rest = rest.slice(1);
  }
  if (/^[spd]/iu.test(rest[0] || "")) {
    const number = NUMBER_LABELS[rest[0].toLowerCase()];
    if (number) labels.push(number);
    rest = rest.slice(1);
  }
  if (/^[acd]/iu.test(rest[0] || "") && (pos === "N" || pos === "A" || pos === "V")) {
    const state = STATE_LABELS[rest[0].toLowerCase()];
    if (state) labels.push(state);
  }

  return labels;
}

function describeOshbMorphology(code) {
  const value = String(code || "").trim();
  if (!value) return "";

  const parts = value.split("/").filter(Boolean);
  const labels = [];
  for (const part of parts) {
    for (const label of describeOshbPart(part)) {
      if (!labels.includes(label)) labels.push(label);
    }
  }
  return labels.join(" · ");
}

function verseSortKey(book, chapter, verse) {
  return `${book}|${String(chapter).padStart(3, "0")}|${String(verse).padStart(3, "0")}`;
}

function ensureHebrewUsageIndex(presenterRootDir) {
  if (indexState.loaded) return indexState;

  const tokensDir = resolveOtTokensDir(presenterRootDir);
  indexState.tokensDir = tokensDir;
  indexState.loaded = true;

  if (!tokensDir) {
    console.warn("Hebrew usage index: OT tokens not found. Parenthetical Hebrew popups disabled.");
    return indexState;
  }

  const files = fs.readdirSync(tokensDir)
    .filter(name => name.endsWith(".tokens.jsonl"))
    .sort();

  for (const file of files) {
    const book = path.basename(file, ".tokens.jsonl");
    const content = fs.readFileSync(path.join(tokensDir, file), "utf8");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      if (!line.trim()) continue;
      let token;
      try {
        token = JSON.parse(line);
      } catch {
        continue;
      }

      const surfaceForm = String(token.surface || "").trim();
      const lemma = String(token.lemma || "").trim();
      if (!surfaceForm || !lemma) continue;

      const morph = String(token.morph || token.gram?.raw || "").trim();
      const gloss = cleanBleGloss(token.es);
      const chapter = Number(token.ch);
      const verse = Number(token.vs);
      if (!chapter || !verse) continue;

      const surfaceKey = normalizeHebrew(surfaceForm);
      const segmentKeys = surfaceForm
        .split("/")
        .map(part => normalizeHebrew(part))
        .filter(Boolean);

      const keys = new Set([surfaceKey, ...segmentKeys].filter(Boolean));
      for (const key of keys) {
        if (!indexState.surfaceToLemma.has(key)) {
          indexState.surfaceToLemma.set(key, new Set());
        }
        indexState.surfaceToLemma.get(key).add(lemma);
      }

      if (!indexState.lemmaRows.has(lemma)) {
        indexState.lemmaRows.set(lemma, []);
      }
      indexState.lemmaRows.get(lemma).push({
        book,
        chapter,
        verse,
        sortKey: verseSortKey(book, chapter, verse),
        surfaceForm,
        lemma,
        morphology: morph,
        gloss,
        reference: `${BOOK_NAMES_ES[book] || book} ${chapter}:${verse}`
      });
    }
  }

  console.log(
    `Hebrew usage index ready: ${indexState.surfaceToLemma.size} forms, ${indexState.lemmaRows.size} lemmas from ${tokensDir}`
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
      total + (normalizeHebrew(row.surfaceForm) === surfaceKey ? 1 : 0)
    ), 0);
    if (score > bestScore) {
      bestScore = score;
      bestLemma = lemma;
    }
  }
  return bestLemma || [...lemmas][0];
}

function pickHebrewDisplaySpanish(occurrences = [], surface = "") {
  const surfaceKey = normalizeHebrew(surface);
  const ordered = [
    ...occurrences.filter(item => normalizeHebrew(item.surfaceForm) === surfaceKey),
    ...occurrences
  ];

  const glossCounts = new Map();
  for (const item of ordered) {
    const cleaned = cleanBleGloss(item.gloss);
    if (!cleaned) continue;
    const trimmed = cleaned.replace(/^(de|del|la|el|los|las|un|una)\s+/iu, "").trim() || cleaned;
    const key = normalizeSpanish(trimmed);
    if (!key || SPANISH_STOPWORDS.has(key)) continue;
    const current = glossCounts.get(key) || { label: trimmed, count: 0 };
    current.count += 1;
    if (trimmed.length < current.label.length) current.label = trimmed;
    glossCounts.set(key, current);
  }

  let best = null;
  for (const entry of glossCounts.values()) {
    if (
      !best
      || entry.count > best.count
      || (entry.count === best.count && entry.label.length < best.label.length)
    ) {
      best = entry;
    }
  }
  if (best?.label) return best.label;

  for (const item of ordered) {
    const mark = String(item.spanishHtml || "").match(/<mark[^>]*>([\s\S]*?)<\/mark>/iu);
    if (!mark) continue;
    const text = mark[1].replace(/<[^>]+>/gu, "").trim();
    if (text) return text;
  }

  return "";
}

function displayLemmaForSurface(surface, strongsLemma) {
  const consonants = unpointHebrew(surface);
  if (consonants) return consonants;
  return formatStrongLemma(strongsLemma);
}

function lookupHebrewUsage(surface, options = {}) {
  const presenterRootDir = options.presenterRootDir || __dirname;
  ensureHebrewUsageIndex(presenterRootDir);

  const surfaceKey = normalizeHebrew(surface);
  if (!surfaceKey || !indexState.tokensDir) return null;

  const lemmas = indexState.surfaceToLemma.get(surfaceKey);
  const lemma = chooseLemma(surfaceKey, lemmas);
  if (!lemma) return null;

  const rows = [...(indexState.lemmaRows.get(lemma) || [])];
  const exactRows = [];
  const otherRows = [];
  let morphology = "";

  for (const row of rows) {
    const normalizedSurface = normalizeHebrew(row.surfaceForm);
    const isExact = normalizedSurface === surfaceKey
      || row.surfaceForm.split("/").some(part => normalizeHebrew(part) === surfaceKey);
    if (isExact) {
      if (!morphology) morphology = row.morphology;
      exactRows.push(row);
    } else {
      otherRows.push(row);
    }
  }

  exactRows.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  otherRows.sort((a, b) => a.sortKey.localeCompare(b.sortKey));

  const sameMorphologyRows = morphology
    ? rows.filter(row => row.morphology === morphology).sort((a, b) => a.sortKey.localeCompare(b.sortKey))
    : [];
  const morphologyMatch = sameMorphologyRows.length > 0;
  const prioritized = morphologyMatch
    ? sameMorphologyRows
    : [
      ...exactRows.slice(0, MAX_EXACT_FORM_FIRST),
      ...otherRows,
      ...exactRows.slice(MAX_EXACT_FORM_FIRST)
    ];

  const totalMatchCount = new Set(prioritized.map(row => `${row.book}|${row.chapter}|${row.verse}`)).size;
  const seenVerses = new Set();
  const occurrences = [];

  for (const row of prioritized) {
    const verseKey = `${row.book}|${row.chapter}|${row.verse}`;
    if (seenVerses.has(verseKey)) continue;
    seenVerses.add(verseKey);

    const verseLookup = typeof options.lookupVerseText === "function"
      ? options.lookupVerseText(row.book, row.chapter, row.verse)
      : "";
    const spanish = typeof verseLookup === "string"
      ? verseLookup
      : String(verseLookup?.text || "");
    const bibleVersion = typeof verseLookup === "string"
      ? ""
      : String(verseLookup?.version || "").trim().toUpperCase();
    const gloss = row.gloss;

    occurrences.push({
      book: row.book,
      chapter: row.chapter,
      verse: row.verse,
      reference: row.reference,
      surfaceForm: row.surfaceForm,
      morphology: row.morphology,
      morphologyDescription: describeOshbMorphology(row.morphology),
      gloss,
      spanish,
      bibleVersion,
      spanishHtml: highlightSpanishInVerse(
        spanish,
        [gloss, cleanBleGloss(gloss).split(/\s+/u).pop()].filter(Boolean)
      )
    });

    if (occurrences.length >= MAX_POPUP_VERSES) break;
  }

  if (!occurrences.length) return null;

  const spanishLabel = pickHebrewDisplaySpanish(occurrences, surface);
  if (spanishLabel) {
    for (const item of occurrences) {
      item.spanishHtml = highlightSpanishInVerse(
        item.spanish,
        [spanishLabel, item.gloss, cleanBleGloss(item.gloss).split(/\s+/u).pop()].filter(Boolean)
      );
    }
  }

  const translationSamples = [];
  const seenTranslationVerses = new Set();
  const lemmaRowsForSamples = [...rows].sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  for (const row of lemmaRowsForSamples) {
    const verseKey = `${row.book}|${row.chapter}|${row.verse}`;
    if (seenTranslationVerses.has(verseKey)) continue;
    seenTranslationVerses.add(verseKey);
    translationSamples.push({
      book: row.book,
      chapter: row.chapter,
      verse: row.verse,
      reference: row.reference,
      surfaceForm: row.surfaceForm,
      gloss: row.gloss
    });
    if (translationSamples.length >= MAX_TRANSLATION_SAMPLES) break;
  }

  const displaySurface = String(surface || "").trim() || exactRows[0]?.surfaceForm || occurrences[0].surfaceForm;
  const displayLemma = displayLemmaForSurface(displaySurface, lemma);

  return {
    surface: displaySurface,
    lemma: displayLemma,
    strongs: formatStrongLemma(lemma),
    morphology: morphology || occurrences[0].morphology || "",
    morphologyDescription: describeOshbMorphology(morphology || occurrences[0].morphology || ""),
    spanishLabel,
    count: totalMatchCount,
    morphologyMatch,
    translationSamples,
    occurrences
  };
}

function describeHebrewForm(surface, presenterRootDir = __dirname) {
  ensureHebrewUsageIndex(presenterRootDir);
  const surfaceKey = normalizeHebrew(surface);
  if (!surfaceKey) {
    return { surface: "", lemma: "", morphology: "", morphologyDescription: "" };
  }

  const lemmas = indexState.surfaceToLemma.get(surfaceKey);
  const lemma = chooseLemma(surfaceKey, lemmas) || "";
  if (!lemma) {
    return {
      surface: String(surface || "").trim(),
      lemma: "",
      strongs: "",
      morphology: "",
      morphologyDescription: ""
    };
  }

  const rows = indexState.lemmaRows.get(lemma) || [];
  const exact = rows.find(row =>
    normalizeHebrew(row.surfaceForm) === surfaceKey
    || row.surfaceForm.split("/").some(part => normalizeHebrew(part) === surfaceKey)
  );
  const morphology = exact?.morphology || rows[0]?.morphology || "";

  return {
    surface: String(surface || "").trim(),
    lemma: displayLemmaForSurface(surface, lemma),
    strongs: formatStrongLemma(lemma),
    morphology,
    morphologyDescription: describeOshbMorphology(morphology)
  };
}

function bibleBookCandidates(bookSlug) {
  return BOOK_ALIASES_ES[bookSlug] || (BOOK_NAMES_ES[bookSlug] ? [BOOK_NAMES_ES[bookSlug]] : []);
}

module.exports = {
  ensureHebrewUsageIndex,
  lookupHebrewUsage,
  describeHebrewForm,
  describeOshbMorphology,
  normalizeHebrew,
  bibleBookCandidates,
  BOOK_NAMES_ES
};
