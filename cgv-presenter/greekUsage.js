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

const BOOK_SLUGS = {
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

let indexState = {
  loaded: false,
  morphDir: "",
  bleDir: "",
  surfaceToLemma: new Map(),
  lemmaRows: new Map(),
  verseRows: new Map(),
  bleGlossByVerseForm: new Map(),
  bleGlossByVerseLemma: new Map()
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

function resolveBleInterlinearDir(presenterRootDir) {
  const configured = process.env.CGV_DATA_PATH
    ? path.join(process.env.CGV_DATA_PATH, "bibles", "BLE", "interlinear", "NT")
    : "";

  return firstExistingDirectory([
    configured,
    path.join(presenterRootDir, "..", "..", "cgv-data", "interlinears", "NT"),
    path.join(presenterRootDir, "..", "Biblia-BLE", "output", "interlinear", "NT"),
    path.join(presenterRootDir, "..", "..", "cgv-data", "bibles", "BLE", "interlinear", "NT")
  ]);
}

function normalizeGreek(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]/gu, "")
    .normalize("NFC")
    .replace(/[⸀⸁⸂⸃*]/gu, "")
    .replace(/^[,.;:!?·«»"'“”]+|[,.;:!?·«»"'“”]+$/gu, "")
    .trim()
    .toLocaleLowerCase("el");
}

const GREEK_TRANSLATION_HINTS = Object.fromEntries(
  Object.entries({
    κοινωνία: ["comunión", "participación", "participar", "contribución", "colecta", "compañerismo"],
    πίστις: ["fe", "fidelidad", "confianza"],
    πιστεύω: ["creer", "creo", "creyó", "creyeron", "creído", "creyendo"],
    λόγος: ["palabra", "palabras", "mensaje", "asunto", "cuenta", "razón", "discurso", "dicho", "declaración", "hablar", "verbo"],
    ἀγάπη: ["amor", "amada", "amado"],
    ἀγαπάω: ["amar", "ama", "amó", "amado", "amada", "amando"],
    ἔχω: ["tener", "tiene", "tienen", "tenía", "teniendo", "tuvo", "tenido", "dueño"],
    θεός: ["Dios", "de Dios"],
    κύριος: ["Señor", "del Señor", "amo"],
    ἄνθρωπος: ["hombre", "persona", "ser humano", "hombres"],
    γίνομαι: ["ser", "llegar a ser", "hacerse", "fue", "fue hecho", "sucedió"],
    ποιέω: ["hacer", "hace", "hizo", "haciendo", "hecho"],
    λέγω: ["decir", "dice", "dijo", "diciendo", "dicho"],
    εἶδον: ["ver", "vio", "vieron", "visto"],
    ὁράω: ["ver", "ve", "vio", "viendo", "visto"]
  }).map(([lemma, hints]) => [normalizeGreek(lemma), hints])
);

function greekTranslationHints(lemma) {
  return GREEK_TRANSLATION_HINTS[normalizeGreek(lemma)] || [];
}

function normalizeSpanish(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/gu, "")
    .toLowerCase()
    .replace(/[•·]/gu, "")
    .trim();
}

function escapeRegExp(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function cleanBleGloss(gloss) {
  return String(gloss || "")
    .replace(/[•·]/gu, " ")
    .replace(/\s+/gu, " ")
    .trim();
}

function spanishStem(word) {
  const normalized = normalizeSpanish(word);
  if (normalized.length <= 3) return normalized;

  let stem = normalized
    .replace(/(amientos|imientos|aciones|uciones|idades|mente)$/u, "")
    // Longer participle / gerund endings first (ido before o).
    .replace(/(andose|endose|ándose|iéndose|ando|iendo|ados|adas|idos|idas|ado|ada|ido|ida)$/u, "")
    .replace(/(aron|ieron|abas|aban|amos|emos|imos|aste|iste|io|ia|ias|ian)$/u, "");

  const clipped = stem.replace(/(ar|er|ir|os|as|es|an|en|o|a|e)$/u, "");
  if (clipped.length >= 3) stem = clipped;
  return stem;
}

function conjugateSpanishInfinitive(infinitive) {
  const n = normalizeSpanish(infinitive);
  if (!/[aei]r$/u.test(n) || n.length < 4) return [n];

  const root = n.slice(0, -2);
  const theme = n.slice(-2, -1);
  const forms = new Set([n, root]);

  if (theme === "a") {
    [
      `${root}a`, `${root}as`, `${root}an`, `${root}amos`,
      `${root}o`, `${root}e`, `${root}es`, `${root}en`, `${root}emos`,
      `${root}ando`, `${root}ado`, `${root}ada`, `${root}ados`, `${root}adas`,
      `${root}aba`, `${root}abas`, `${root}aban`,
      `${root}o`, `${root}aste`, `${root}aron`,
      `${n}e`, `${n}as`, `${n}a`, `${n}an`, `${n}emos`
    ].forEach(form => forms.add(form));
  } else {
    [
      `${root}e`, `${root}es`, `${root}en`, `${root}emos`,
      `${root}o`, `${root}a`, `${root}as`, `${root}an`, `${root}amos`,
      `${root}iendo`, `${root}ido`, `${root}ida`, `${root}idos`, `${root}idas`,
      `${root}ia`, `${root}ias`, `${root}ian`,
      `${root}io`, `${root}iste`, `${root}ieron`,
      `${n}e`, `${n}as`, `${n}a`, `${n}an`, `${n}emos`
    ].forEach(form => forms.add(form));
  }

  return [...forms];
}

// Function words that appear in BLE glosses ("de herencia") must never highlight alone.
const SPANISH_STOPWORDS = new Set([
  "a", "al", "de", "del", "el", "la", "lo", "los", "las", "un", "una", "uno", "unos", "unas",
  "y", "e", "o", "u", "en", "con", "por", "para", "sin", "sobre", "entre", "como", "que",
  "se", "su", "sus", "mi", "mis", "tu", "tus", "le", "les", "me", "te", "nos", "os",
  "es", "son", "ser", "esta", "este", "esto", "estos", "estas", "hay"
]);

// BLE mechanical gloss → common NBLA/RV phrasing when the verse paraphrases.
const GLOSS_PHRASE_MAP = {
  regenerado: ["nacer de nuevo", "nacido de nuevo", "nacidos de nuevo", "hecho nacer de nuevo", "ha hecho nacer", "han nacido de nuevo", "han nacido"],
  regenerados: ["nacer de nuevo", "nacido de nuevo", "nacidos de nuevo", "han nacido de nuevo", "han nacido"],
  viviendo: ["viva", "vivo", "vivos", "vivas", "vive", "viven", "viviendo"],
  mucho: ["mucho", "mucha", "muchos", "muchas", "muy", "gran", "grande", "grandes"],
  muchos: ["mucho", "mucha", "muchos", "muchas", "muy", "gran", "grande", "grandes"],
  inmarcesible: ["no se marchitará", "marchitará", "marchita", "inmarcesible"],
  herencia: ["herencia", "heredad", "heredero", "herederos"],
  tentacion: ["tentación", "tentaciones", "prueba", "pruebas"],
  tentaciones: ["tentación", "tentaciones", "prueba", "pruebas"],
  entristecido: ["entristecido", "entristecidos", "triste", "tristes", "tristeza", "afligido", "afligidos", "afligidas"],
  entristecidos: ["entristecido", "entristecidos", "triste", "tristes", "tristeza", "afligido", "afligidos", "afligidas"],
  entristecer: ["entristecer", "triste", "tristes", "tristeza", "afligido", "afligidos", "afligidas"],
  incorruptible: ["incorruptible", "incorruptibles", "inmortal", "inmortales"],
  probar: ["probar", "prueba", "probado", "verificar", "verifiquen", "designado", "designados", "depravada", "reprobado"]
};

// Related infinitives to conjugate when BLE gloss is a different lemma than NBLA uses.
const GLOSS_RELATED_VERBS = {
  probar: ["probar", "examinar", "aprobar", "comprobar", "verificar", "designar"],
  regenerado: ["regenerar", "nacer"],
  regenerados: ["regenerar", "nacer"],
  amar: ["amar"],
  entristecido: ["entristecer", "afligir"],
  entristecidos: ["entristecer", "afligir"],
  entristecer: ["entristecer", "afligir"],
  tentacion: ["tentar", "probar"],
  tentaciones: ["tentar", "probar"],
  inmarcesible: ["marchitar"],
  herencia: ["heredar"],
  incorruptible: []
};

const GLOSS_PREFIX_MAP = {
  probar: ["prob", "examin", "aprob", "aprueb", "comprob", "acrisol", "verific", "design", "depravad", "reprob"],
  mucho: ["much", "muy", "gran"],
  muchos: ["much", "muy", "gran"],
  amar: ["am"],
  regenerado: ["renac"],
  regenerados: ["renac"],
  tentacion: ["tentacion", "tentac", "prueb"],
  tentaciones: ["tentacion", "tentac", "prueb"],
  entristecido: ["entristec", "aflig", "trist"],
  entristecidos: ["entristec", "aflig", "trist"],
  entristecer: ["entristec", "aflig", "trist"],
  herencia: ["herenc", "hered"],
  inmarcesible: ["marchit", "inmarces"],
  incorruptible: ["incorrupt", "inmortal"]
};

function glossCandidates(gloss) {
  const cleaned = cleanBleGloss(gloss);
  if (!cleaned) return [];

  const parts = cleaned.split(/\s+/u).filter(Boolean);
  const candidates = new Set([cleaned]);

  for (const part of parts) {
    const normalized = normalizeSpanish(part);
    if (!normalized || SPANISH_STOPWORDS.has(normalized)) continue;
    // Prefer singular/lemma-like keys for map lookups (tentaciones → tentacion).
    const keys = [...new Set([
      normalized,
      normalized.replace(/ciones$/u, "cion"),
      normalized.replace(/es$/u, ""),
      normalized.replace(/s$/u, "")
    ])].filter(key => key && key.length >= 2 && !SPANISH_STOPWORDS.has(key));

    for (const key of keys) {
      candidates.add(key);
      conjugateSpanishInfinitive(key).forEach(form => candidates.add(form));

      const relatedVerbs = GLOSS_RELATED_VERBS[key] || [];
      relatedVerbs.forEach(verb => {
        conjugateSpanishInfinitive(verb).forEach(form => candidates.add(form));
      });

      const stem = spanishStem(key);
      if (stem && stem.length >= 3) candidates.add(stem);

      const phrases = GLOSS_PHRASE_MAP[key] || [];
      phrases.forEach(phrase => candidates.add(phrase));

      const prefixes = GLOSS_PREFIX_MAP[key] || [];
      prefixes.forEach(prefix => candidates.add(prefix));
    }
  }

  return [...candidates]
    .map(term => String(term || "").trim())
    .filter(term => {
      if (!term) return false;
      const normalized = normalizeSpanish(term);
      if (!normalized || SPANISH_STOPWORDS.has(normalized)) return false;
      // Keep short content words (fe, sí) for exact word-boundary matching.
      if (normalized.length < 2) return false;
      if (/\s/u.test(term)) return term.length >= 4;
      return true;
    })
    .sort((left, right) => right.length - left.length);
}

function wrapHighlight(source, start, length) {
  return (
    escapeHtmlPlain(source.slice(0, start))
    + `<mark class="greek-usage-hit">${escapeHtmlPlain(source.slice(start, start + length))}</mark>`
    + escapeHtmlPlain(source.slice(start + length))
  );
}

function highlightSpanishInVerse(text, glosses = []) {
  const source = String(text || "");
  if (!source) return "";

  const terms = [...new Set(
    (Array.isArray(glosses) ? glosses : [glosses])
      .flatMap(gloss => {
        const value = String(gloss || "").trim();
        if (!value) return [];
        // Keep the raw display label itself (e.g. "fe", "de Dios") before expansion.
        return [value, ...glossCandidates(value)];
      })
      .filter(term => term && normalizeSpanish(term).length >= 2)
  )].sort((left, right) => right.length - left.length);

  // 1) Exact word or multi-word phrase (case-insensitive). Allow 2-letter content words like "fe".
  for (const term of terms) {
    const normalizedTerm = normalizeSpanish(term);
    if (normalizedTerm.length < 2) continue;
    if (normalizedTerm.length < 3 && /\s/u.test(term)) continue;
    const pattern = new RegExp(`(?<![\\p{L}])(${escapeRegExp(term)})(?![\\p{L}])`, "iu");
    const match = source.match(pattern);
    if (!match) continue;
    return wrapHighlight(source, match.index ?? 0, match[1].length);
  }

  // 2) Accent-insensitive exact word match (fe / fé, Dios / DIOS).
  const sourceNormalized = normalizeSpanish(source);
  for (const term of terms) {
    const normalizedTerm = normalizeSpanish(term);
    if (normalizedTerm.length < 2 || /\s/u.test(normalizedTerm)) continue;
    const pattern = new RegExp(`(?<![\\p{L}])(${escapeRegExp(normalizedTerm)})(?![\\p{L}])`, "iu");
    const match = sourceNormalized.match(pattern);
    if (!match || match.index == null) continue;
    // Map normalized index back onto the original string by walking letters.
    let originalIndex = 0;
    let normalizedIndex = 0;
    while (originalIndex < source.length && normalizedIndex < match.index) {
      const ch = source[originalIndex];
      const norm = normalizeSpanish(ch);
      if (norm) normalizedIndex += norm.length;
      originalIndex += 1;
    }
    let end = originalIndex;
    let consumed = 0;
    while (end < source.length && consumed < match[1].length) {
      const norm = normalizeSpanish(source[end]);
      if (norm) consumed += norm.length;
      end += 1;
    }
    if (end > originalIndex) return wrapHighlight(source, originalIndex, end - originalIndex);
  }

  // 3) Prefix / conjugation-aware word match inside the verse.
  const words = source.match(/[\p{L}]+(?:['’-][\p{L}]+)*/gu) || [];
  const prefixes = terms
    .map(term => normalizeSpanish(term))
    .filter(term => term.length >= 3 && !SPANISH_STOPWORDS.has(term) && !/\s/u.test(term))
    .sort((left, right) => right.length - left.length);

  for (const word of words) {
    const normalizedWord = normalizeSpanish(word);
    const wordStem = spanishStem(word);
    const hit = prefixes.some(prefix => {
      if (normalizedWord === prefix) return true;
      if (prefix.length >= 3 && normalizedWord.startsWith(prefix)) return true;
      if (prefix.length === 2 && normalizedWord.startsWith(prefix) && normalizedWord.length >= 3) {
        return true;
      }
      if (wordStem.length >= 4 && prefix.length >= 4 && wordStem === prefix) return true;
      // Shared stem: teniendo / tenía / tenemos ↔ tener / tenia
      if (wordStem.length >= 3 && prefix.length >= 3) {
        const prefixStem = spanishStem(prefix);
        if (prefixStem.length >= 3 && (wordStem.startsWith(prefixStem) || prefixStem.startsWith(wordStem))) {
          return true;
        }
      }
      return false;
    });
    if (!hit) continue;
    const index = source.indexOf(word);
    if (index < 0) continue;
    return wrapHighlight(source, index, word.length);
  }

  return escapeHtmlPlain(source);
}

function escapeHtmlPlain(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function loadBleGlossIndex(presenterRootDir) {
  const bleDir = resolveBleInterlinearDir(presenterRootDir);
  indexState.bleDir = bleDir;
  if (!bleDir) return;

  const tokenPattern = /([^<\s]+)<([^|>]+)\|([^|>]+)\|([^|>]+)\|([^>]+)>/gu;
  const files = fs.readdirSync(bleDir)
    .filter(name => name.endsWith(".interlinear.txt"))
    .sort();

  for (const file of files) {
    const content = fs.readFileSync(path.join(bleDir, file), "utf8");
    for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
      const match = line.match(/^([a-z0-9]+)\s+(\d+):(\d+)\t(.+)$/u);
      if (!match) continue;
      const [, book, chapter, verse, tokens] = match;
      for (const token of tokens.matchAll(tokenPattern)) {
        const [, surface, lemma, , , gloss] = token;
        const cleaned = cleanBleGloss(gloss);
        if (!cleaned || cleaned === "?") continue;
        const formKey = `${book}|${Number(chapter)}|${Number(verse)}|${normalizeGreek(surface)}`;
        const lemmaKey = `${book}|${Number(chapter)}|${Number(verse)}|${normalizeGreek(lemma)}`;
        if (!indexState.bleGlossByVerseForm.has(formKey)) {
          indexState.bleGlossByVerseForm.set(formKey, cleaned);
        }
        if (!indexState.bleGlossByVerseLemma.has(lemmaKey)) {
          indexState.bleGlossByVerseLemma.set(lemmaKey, cleaned);
        }
      }
    }
  }
}

function lookupBleGloss(bookCode, chapter, verse, surfaceForm, lemma) {
  const book = BOOK_SLUGS[bookCode];
  if (!book) return "";
  const formKey = `${book}|${Number(chapter)}|${Number(verse)}|${normalizeGreek(surfaceForm)}`;
  if (indexState.bleGlossByVerseForm.has(formKey)) {
    return indexState.bleGlossByVerseForm.get(formKey);
  }
  const lemmaKey = `${book}|${Number(chapter)}|${Number(verse)}|${normalizeGreek(lemma)}`;
  return indexState.bleGlossByVerseLemma.get(lemmaKey) || "";
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

const PART_OF_SPEECH_LABELS = {
  "A-": "adjetivo",
  "C-": "conjunción",
  "D-": "adverbio",
  "I-": "interjección",
  "N-": "sustantivo",
  "P-": "preposición",
  "RA": "artículo",
  "RD": "pronombre demostrativo",
  "RI": "pronombre interrogativo",
  "RP": "pronombre personal",
  "RR": "pronombre relativo",
  "V-": "verbo",
  "X-": "partícula"
};

const MOOD_LABELS = {
  I: "indicativo",
  S: "subjuntivo",
  O: "optativo",
  M: "imperativo",
  N: "infinitivo",
  P: "participio"
};

const TENSE_LABELS = {
  P: "presente",
  I: "imperfecto",
  F: "futuro",
  A: "aoristo",
  X: "perfecto",
  Y: "pluscuamperfecto"
};

const VOICE_LABELS = {
  A: "activa",
  M: "media",
  P: "pasiva",
  E: "medio/pasiva",
  D: "medio deponente",
  O: "pasivo deponente"
};

const CASE_LABELS = {
  N: "nominativo",
  G: "genitivo",
  D: "dativo",
  A: "acusativo",
  V: "vocativo"
};

const NUMBER_LABELS = {
  S: "singular",
  P: "plural"
};

const GENDER_LABELS = {
  M: "masculino",
  F: "femenino",
  N: "neutro"
};

function describeMorphologyCode(code) {
  const value = String(code || "").trim();
  if (!value) return "";

  const part = value.slice(0, 2);
  const parsing = value.slice(2);
  const labels = [PART_OF_SPEECH_LABELS[part] || part];

  if (part === "V-" && parsing.length >= 4) {
    const hasPersonPrefix = /^[123]/u.test(parsing);
    const tense = TENSE_LABELS[parsing[hasPersonPrefix ? 1 : 0]];
    const voice = VOICE_LABELS[parsing[hasPersonPrefix ? 2 : 1]];
    const mood = MOOD_LABELS[parsing[hasPersonPrefix ? 3 : 2]];
    [tense, voice, mood].filter(Boolean).forEach(label => labels.push(label));
  }

  const declinedMatch = value.match(/^(N-|A-|RA|RD|RI|RP|RR)([NGDAV])([SP])([MFN])?/u);
  if (declinedMatch) {
    const [, , caseCode, numberCode, genderCode] = declinedMatch;
    [CASE_LABELS[caseCode], NUMBER_LABELS[numberCode], GENDER_LABELS[genderCode]]
      .filter(Boolean)
      .forEach(label => labels.push(label));
  }

  return labels.join(" · ");
}

function isConditionMarker(surfaceOrLemma) {
  return ["εἰ", "ἐάν", "ἐὰν", "ἄν", "ἂν"].includes(normalizeGreek(surfaceOrLemma));
}

function findNextFiniteVerb(row) {
  if (!row?.verseId) return null;
  const verseRows = indexState.verseRows.get(row.verseId) || [];
  const startIndex = verseRows.findIndex(item => item === row);
  const after = startIndex >= 0 ? verseRows.slice(startIndex + 1, startIndex + 12) : [];

  return after.find(item => {
    if (item.partOfSpeech !== "V-") return false;
    const mood = String(item.parsing || "")[3];
    return ["I", "S", "O"].includes(mood);
  }) || null;
}

function classifyCondition(row) {
  const marker = normalizeGreek(row?.lemma || row?.normalizedForm || row?.surfaceForm);
  if (!isConditionMarker(marker)) return null;

  const verb = findNextFiniteVerb(row);
  const mood = String(verb?.parsing || "")[3] || "";
  const tense = String(verb?.parsing || "")[1] || "";
  const verbMorphology = verb ? formatRmac(verb.partOfSpeech, verb.parsing) : "";
  const verbLabel = verb
    ? `${verb.surfaceForm} (${describeMorphologyCode(verbMorphology) || verbMorphology})`
    : "";

  if (marker === "ἐάν" || marker === "ἐὰν" || marker === "ἄν" || marker === "ἂν") {
    return {
      className: mood === "S" ? "tercera clase" : "condición con ἐάν",
      pattern: verb ? `ἐάν + ${MOOD_LABELS[mood] || verbMorphology}` : "ἐάν",
      note: mood === "S"
        ? "Condición prospectiva: si sucede, entonces se sigue el resultado."
        : "Marcador condicional con ἐάν; revise el verbo cercano para el matiz.",
      verb: verbLabel
    };
  }

  if (marker === "εἰ") {
    if (mood === "I") {
      const isPast = tense === "I" || tense === "A";
      return {
        className: isPast ? "primera o segunda clase" : "primera clase",
        pattern: `εἰ + ${MOOD_LABELS[mood]}`,
        note: isPast
          ? "εἰ con indicativo pasado puede funcionar como condición asumida o contraria al hecho; revise el contexto."
          : "Condición presentada como asumida para el argumento.",
        verb: verbLabel
      };
    }

    if (mood === "O") {
      return {
        className: "cuarta clase",
        pattern: "εἰ + optativo",
        note: "Condición potencial o menos probable.",
        verb: verbLabel
      };
    }

    return {
      className: "condición con εἰ",
      pattern: verb ? `εἰ + ${MOOD_LABELS[mood] || verbMorphology}` : "εἰ",
      note: "Marcador condicional; revise el verbo cercano para clasificarla.",
      verb: verbLabel
    };
  }

  return null;
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
  loadBleGlossIndex(presenterRootDir);

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
      const indexedRow = {
        verseId: row.verseId,
        surfaceForm: row.surfaceForm,
        normalizedForm: row.normalizedForm,
        lemma: row.lemma,
        partOfSpeech: row.partOfSpeech,
        parsing: row.parsing,
        morphology: formatRmac(row.partOfSpeech, row.parsing)
      };
      indexState.lemmaRows.get(row.lemma).push(indexedRow);
      if (!indexState.verseRows.has(row.verseId)) {
        indexState.verseRows.set(row.verseId, []);
      }
      indexState.verseRows.get(row.verseId).push(indexedRow);
    }
  }

  console.log(
    `Greek usage index ready: ${indexState.surfaceToLemma.size} forms, ${indexState.lemmaRows.size} lemmas from ${morphDir}`
    + (indexState.bleDir ? `; BLE glosses from ${indexState.bleDir}` : "")
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

  const sameMorphologyRows = morphology
    ? rows.filter(row => row.morphology === morphology).sort((a, b) => a.verseId.localeCompare(b.verseId))
    : [];
  const morphologyMatch = sameMorphologyRows.length > 0;
  const prioritized = morphologyMatch
    ? sameMorphologyRows
    : [
      ...exactRows.slice(0, MAX_EXACT_FORM_FIRST),
      ...otherRows,
      ...exactRows.slice(MAX_EXACT_FORM_FIRST)
    ];
  const translationHints = greekTranslationHints(lemma);

  const totalMatchCount = new Set(prioritized.map(row => row.verseId)).size;
  const seenVerses = new Set();
  const occurrences = [];

  for (const row of prioritized) {
    if (seenVerses.has(row.verseId)) continue;
    seenVerses.add(row.verseId);

    const ref = referenceFromVerseId(row.verseId);
    const verseLookup = typeof options.lookupVerseText === "function"
      ? options.lookupVerseText(ref.book, ref.chapter, ref.verse)
      : "";
    const spanish = typeof verseLookup === "string"
      ? verseLookup
      : String(verseLookup?.text || "");
    const bibleVersion = typeof verseLookup === "string"
      ? ""
      : String(verseLookup?.version || "").trim().toUpperCase();
    const gloss = lookupBleGloss(ref.book, ref.chapter, ref.verse, row.surfaceForm, lemma);

    occurrences.push({
      ...ref,
      surfaceForm: row.surfaceForm,
      morphology: row.morphology,
      morphologyDescription: describeMorphologyCode(row.morphology),
      condition: classifyCondition(row),
      gloss,
      spanish,
      bibleVersion,
      spanishHtml: highlightSpanishInVerse(
        spanish,
        [gloss, cleanBleGloss(gloss).split(/\s+/u).pop(), ...translationHints].filter(Boolean)
      )
    });

    // Always cap popup size — high-frequency forms (καί, θεοῦ) would otherwise dump thousands of verses.
    if (occurrences.length >= MAX_POPUP_VERSES) break;
  }

  if (!occurrences.length) return null;

  const spanishLabel = pickGreekDisplaySpanish(occurrences, surface);
  // Second pass: re-highlight every verse with the shared Spanish label so short
  // glosses like "fe" and cross-verse equivalents stay marked consistently.
  if (spanishLabel) {
    for (const item of occurrences) {
      item.spanishHtml = highlightSpanishInVerse(
        item.spanish,
        [
          spanishLabel,
          item.gloss,
          cleanBleGloss(item.gloss).split(/\s+/u).pop(),
          ...translationHints
        ].filter(Boolean)
      );
    }
  }

  return {
    surface: String(surface || "").trim(),
    lemma,
    morphology: morphology || occurrences[0].morphology || "",
    morphologyDescription: describeMorphologyCode(morphology || occurrences[0].morphology || ""),
    condition: occurrences.find(item => item.condition)?.condition || null,
    spanishLabel,
    count: totalMatchCount,
    morphologyMatch,
    occurrences
  };
}

function pickGreekDisplaySpanish(occurrences = [], surface = "") {
  const surfaceKey = normalizeGreek(surface);
  const ordered = [
    ...occurrences.filter(item => normalizeGreek(item.surfaceForm) === surfaceKey),
    ...occurrences
  ];

  // Prefer the most common BLE gloss — more stable than the first verse hit
  // (λόγος should stay "palabra", not "hablar" from a single context).
  const glossCounts = new Map();
  for (const item of ordered) {
    const cleaned = cleanBleGloss(item.gloss);
    if (!cleaned) continue;
    const trimmed = cleaned.replace(/^(de|del|la|el|los|las|un|una)\s+/iu, "").trim() || cleaned;
    const key = normalizeSpanish(trimmed);
    if (!key || SPANISH_STOPWORDS.has(key)) continue;
    const current = glossCounts.get(key) || { label: trimmed, count: 0 };
    current.count += 1;
    // Prefer the shorter lexical label when tied ("palabra" over "la palabra").
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

function bibleBookCandidates(bookCode) {
  return BOOK_ALIASES_ES[bookCode] || (BOOK_NAMES_ES[bookCode] ? [BOOK_NAMES_ES[bookCode]] : []);
}

// Function words / discourse connectors: pedagogical footnotes, not usage dumps.
const CONNECTOR_LEMMAS = new Set([
  "καί", "δέ", "γάρ", "οὖν", "ἀλλά", "ἀλλά", "μέν", "τε",
  "ὅτι", "ἵνα", "εἰ", "ἐάν", "ὡς", "ὥστε", "διό", "ἄρα",
  "γε", "δή", "περ", "τοίνυν", "ἐπεί", "ἐπειδή",
  "μή", "οὐ", "οὐκ", "οὐχ", "οὐχί", "μηδέ", "μήτε", "οὔτε",
  "ἤ", "ἢ", "καίτοι", "καίπερ"
].map(normalizeGreek));

const FOOTNOTE_ID_BY_LEMMA = Object.fromEntries(
  Object.entries({
    καί: "kai",
    δέ: "de",
    γάρ: "gar",
    οὖν: "oun",
    ἀλλά: "alla",
    μέν: "men",
    τε: "te",
    ὅτι: "hoti",
    ἵνα: "hina",
    εἰ: "ei",
    ἐάν: "ean",
    ὡς: "hos",
    ὥστε: "hoste",
    διό: "dio",
    ἄρα: "ara",
    μή: "me",
    οὐ: "ou",
    οὐκ: "ou",
    οὐχ: "ou",
    ἤ: "e",
    ἢ: "e"
  }).map(([lemma, id]) => [normalizeGreek(lemma), id])
);

function describeGreekForm(surface, presenterRootDir = __dirname) {
  ensureGreekUsageIndex(presenterRootDir);
  const surfaceKey = normalizeGreek(surface);
  if (!surfaceKey) {
    return { surface: "", lemma: "", morphology: "", footnoteId: "", isConnector: false };
  }

  const lemmas = indexState.surfaceToLemma.get(surfaceKey);
  const lemma = chooseLemma(surfaceKey, lemmas) || "";
  const lemmaKey = normalizeGreek(lemma);
  const rows = indexState.lemmaRows.get(lemma) || [];
  const exact = rows.find(row =>
    normalizeGreek(row.surfaceForm) === surfaceKey
    || normalizeGreek(row.normalizedForm) === surfaceKey
  );
  const morphology = exact?.morphology || rows[0]?.morphology || "";
  const condition = classifyCondition(exact || rows[0]);
  const footnoteId = FOOTNOTE_ID_BY_LEMMA[lemmaKey]
    || FOOTNOTE_ID_BY_LEMMA[surfaceKey]
    || "";
  const isConnector = CONNECTOR_LEMMAS.has(lemmaKey)
    || CONNECTOR_LEMMAS.has(surfaceKey)
    || String(morphology).startsWith("C-");

  return {
    surface: String(surface || "").trim(),
    lemma,
    morphology,
    morphologyDescription: describeMorphologyCode(morphology),
    condition,
    footnoteId,
    isConnector
  };
}

module.exports = {
  ensureGreekUsageIndex,
  lookupGreekUsage,
  bibleBookCandidates,
  normalizeGreek,
  highlightSpanishInVerse,
  describeGreekForm,
  describeMorphologyCode,
  isConditionMarker,
  BOOK_NAMES_ES
};
