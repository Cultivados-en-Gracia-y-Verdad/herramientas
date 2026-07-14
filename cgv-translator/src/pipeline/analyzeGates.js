import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const LIGHT_LEMMAS = new Set([
  "δέ", "δὲ", "καί", "καὶ", "ὁ", "ἡ", "τό", "τοῦ", "τῆς", "τῷ", "τῇ",
  "τόν", "τὸν", "τήν", "τὴν", "τά", "τὰ", "οἱ", "αἱ", "τούς", "τοὺς",
  "τάς", "τὰς", "τῶν", "οὐ", "μή", "μὴ", "τε", "γάρ", "γὰρ", "οὖν",
  "μέν", "μὲν", "ἀλλά", "ἀλλὰ", "ὡς", "ὅτι"
]);

const CASE_MAP = {
  N: "nominative",
  G: "genitive",
  D: "dative",
  A: "accusative",
  V: "vocative"
};

const NUMBER_MAP = {
  S: "singular",
  P: "plural",
  D: "dual"
};

const GENDER_MAP = {
  M: "masculine",
  F: "feminine",
  N: "neuter"
};

const TENSE_MAP = {
  P: "present",
  I: "imperfect",
  F: "future",
  A: "aorist",
  R: "perfect",
  L: "pluperfect"
};

const VOICE_MAP = {
  A: "active",
  M: "middle",
  P: "passive",
  E: "middle/passive",
  D: "middle",
  O: "passive",
  N: "middle/passive",
  Q: "impersonal active",
  X: "no voice"
};

const MOOD_MAP = {
  I: "indicative",
  D: "imperative",
  S: "subjunctive",
  O: "optative",
  N: "infinitive",
  P: "participle"
};

const PERSON_MAP = {
  1: "1st person",
  2: "2nd person",
  3: "3rd person"
};

function morphNumber(code = "") {
  const raw = String(code || "").trim();
  if (/^V-/.test(raw)) {
    const verb = parseVerbCode(raw);
    return verb?.number ? NUMBER_MAP[verb.number] || null : null;
  }
  if (/^[NA]-/.test(raw) && raw.length >= 4) {
    return NUMBER_MAP[raw[3]] || null;
  }
  if (/RPGP$/u.test(raw) || /GP$/u.test(raw)) return "plural";
  if (/RP[NGDAV]S/u.test(raw) || /NS$/u.test(raw) || /GS$/u.test(raw) || /AS$/u.test(raw)) {
    return "singular";
  }
  return null;
}

function parseVerbCode(code = "") {
  const raw = String(code || "").replace(/^V-/u, "").replace(/-/gu, "");
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

function isPassiveVerb(code = "") {
  const verb = parseVerbCode(code);
  return Boolean(verb && (verb.voice === "P" || verb.voice === "O"));
}

function parseDecisionVersions(markdown) {
  const sections = String(markdown || "").split(/^## Version\s+/m).slice(1);
  return sections.map(section => {
    const lines = section.replace(/\r\n/g, "\n").split("\n");
    const fields = {};
    for (const line of lines) {
      const match = line.match(/^([^:]+):\s*(.*)$/);
      if (!match) continue;
      fields[match[1].trim().toLowerCase()] = match[2].trim();
    }
    const reasonMatch = section.match(/### Reason\s*\n([\s\S]*?)(?=\n### |\n## |$)/);
    return {
      status: fields.status || "",
      lemma: fields.lemma || "",
      strongs: fields["strong's"] || fields.strongs || "",
      preferredRendering: fields["preferred rendering"] || "",
      confidence: fields.confidence || "",
      reason: reasonMatch ? reasonMatch[1].trim() : ""
    };
  });
}

export async function loadLemmaPolicyIndex(rootDir) {
  const investigationsDir = join(rootDir, "investigations");
  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);
  const approved = [];
  const openInvestigations = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || !/^INV-\d{4}$/.test(entry.name)) continue;
    const markdown = await readFile(join(investigationsDir, entry.name, "decision.md"), "utf8").catch(() => "");
    const versions = parseDecisionVersions(markdown);
    const latest = versions.at(-1);
    if (!latest?.lemma && !latest?.strongs) continue;

    const record = {
      investigationId: entry.name,
      lemma: latest.lemma || "",
      strongs: latest.strongs || "",
      preferredRendering: latest.preferredRendering || "",
      confidence: latest.confidence || "",
      reason: latest.reason || "",
      status: latest.status || "Draft"
    };

    openInvestigations.push(record);
    if (/^approved$/i.test(record.status) && record.lemma && record.preferredRendering) {
      approved.push(record);
    }
  }

  return { approved, openInvestigations };
}

export async function loadApprovedLemmaPolicies(rootDir) {
  const { approved } = await loadLemmaPolicyIndex(rootDir);
  return approved;
}

export function isSignificantLemma(row = {}) {
  const lemma = row.lemma || "";
  if (!lemma) return false;
  if (LIGHT_LEMMAS.has(lemma)) return false;
  if (row.strongs) return true;
  // Content words without Strong's still need attention.
  return !/^[δέκαὶὁἡτό]$/u.test(lemma);
}

export function explainRmac(code = "") {
  const raw = String(code || "").trim();
  if (!raw || raw === "—" || raw === "C-") {
    return raw === "C-" ? "conjunction / discourse particle" : "no morphology code";
  }

  if (raw.startsWith("N-")) {
    const rest = raw.slice(2);
    const caseName = CASE_MAP[rest[0]] || rest[0] || "?";
    const number = NUMBER_MAP[rest[1]] || rest[1] || "?";
    const gender = GENDER_MAP[rest[2]] || "";
    return ["noun", caseName, number, gender].filter(Boolean).join(" ");
  }

  if (raw.startsWith("V-")) {
    const verb = parseVerbCode(raw);
    if (!verb) return raw;
    return [
      "verb",
      TENSE_MAP[verb.tense] || verb.tense,
      VOICE_MAP[verb.voice] || verb.voice,
      MOOD_MAP[verb.mood] || verb.mood,
      PERSON_MAP[verb.person] || "",
      NUMBER_MAP[verb.number] || ""
    ].filter(Boolean).join(" ");
  }

  if (raw.startsWith("A-")) {
    const rest = raw.slice(2);
    return ["adjective", CASE_MAP[rest[0]], NUMBER_MAP[rest[1]], GENDER_MAP[rest[2]]]
      .filter(Boolean)
      .join(" ");
  }

  if (raw.startsWith("P-") || raw.startsWith("RP") || raw.startsWith("RD") || raw.startsWith("RI")) {
    return `pronoun/deictic (${raw})`;
  }

  if (raw.startsWith("D-") || raw === "ADV") return "adverb";
  if (raw.startsWith("C") || raw === "CONJ") return "conjunction / particle";
  if (raw.startsWith("X") || raw === "INJ") return "particle / interjection";
  if (raw.startsWith("I-")) return "interjection";
  if (raw.startsWith("T-")) return "article";
  if (raw.startsWith("P")) return `preposition (${raw})`;

  return raw;
}

function findPolicy(row, policies) {
  const strongs = String(row.strongs || "").toUpperCase();
  const lemma = row.lemma || "";
  return policies.find(item =>
    (strongs && item.strongs && item.strongs.toUpperCase() === strongs)
    || (lemma && item.lemma === lemma)
  ) || null;
}

function findOpenInvestigation(row, openInvestigations) {
  return findPolicy(row, openInvestigations);
}

function analyzeLemmaGate(tokenRows, policies, openInvestigations = []) {
  const tokens = [];
  const blocked = [];

  for (const row of tokenRows) {
    const significant = isSignificantLemma(row);
    const policy = findPolicy(row, policies);
    const openInv = findOpenInvestigation(row, openInvestigations);
    const token = {
      sourceTokenId: row.sourceTokenId || "",
      greek: row.greek || "",
      lemma: row.lemma || "",
      strongs: row.strongs || "",
      significant,
      allowedRenderings: policy ? [policy.preferredRendering] : [],
      policySource: policy ? `investigation/${policy.investigationId}` : null,
      investigationId: policy?.investigationId || openInv?.investigationId || null,
      confidence: policy?.confidence || null,
      status: !significant
        ? "not-applicable"
        : policy
          ? "resolved"
          : row.strongs
            ? "blocked"
            : "unreviewed"
    };
    tokens.push(token);
    if (token.status === "blocked") {
      blocked.push(token);
    }
  }

  if (blocked.length) {
    const first = blocked[0];
    return {
      id: "lemma",
      name: "Lemma",
      status: "blocked",
      summary: `Blocked: no approved lemma policy for ${first.strongs || "—"} ${first.lemma}`.trim(),
      blockedLemma: `${first.strongs || ""} ${first.lemma}`.trim(),
      blockedStrongs: first.strongs || "",
      blockedLemmaForm: first.lemma || "",
      investigationId: first.investigationId,
      tokens
    };
  }

  const unreviewed = tokens.filter(item => item.status === "unreviewed");
  const resolvedCount = tokens.filter(item => item.status === "resolved").length;
  return {
    id: "lemma",
    name: "Lemma",
    status: "resolved",
    summary: [
      resolvedCount
        ? `Resolved ${resolvedCount} lemma polic${resolvedCount === 1 ? "y" : "ies"} from approved investigations.`
        : "No Strong's-linked lemmas required policy in this phrase.",
      unreviewed.length
        ? `${unreviewed.length} content lemma(s) lack Strong's/policy (flagged, not hard-blocked): ${unreviewed.map(t => t.lemma).join(", ")}.`
        : null
    ].filter(Boolean).join(" "),
    tokens
  };
}

function morphCase(code = "") {
  const raw = String(code || "").trim();
  if (/^[NA]-/.test(raw) && raw.length >= 3) {
    return CASE_MAP[raw[2]] || null;
  }
  // Pronouns/articles: RPGSM, RPGP, RRASN, RAASM
  if (/^R[APRD]/.test(raw) && raw.length >= 3) {
    return CASE_MAP[raw[2]] || null;
  }
  return null;
}

function morphGender(code = "") {
  const raw = String(code || "").trim();
  if (/^[NA]-/.test(raw) && raw.length >= 5) {
    return GENDER_MAP[raw[4]] || null;
  }
  return null;
}

function analyzeMorphologyGate(tokenRows, lemmaGate) {
  const constraints = tokenRows.map((row, index) => {
    const code = row.rmac || "";
    const explanation = explainRmac(code) || row.morphology || "—";
    const lemmaToken = (lemmaGate.tokens || []).find(item =>
      (row.sourceTokenId && item.sourceTokenId === row.sourceTokenId)
      || item.lemma === row.lemma
    );
    const requirements = [];
    const number = morphNumber(code);
    const caseName = morphCase(code);
    const gender = morphGender(code);
    if (number) {
      requirements.push(
        `NUMBER=${number} — Spanish must preserve ${number}; do not change singular↔plural`
      );
    }
    if (caseName) {
      requirements.push(`CASE=${caseName}`);
    }
    if ((code.startsWith("N-") || code.startsWith("A-")) && code[2] === "G") {
      requirements.push("genitive relationship — often Spanish 'de …'");
    }
    if ((code.startsWith("N-") || code.startsWith("A-")) && code[2] === "N") {
      requirements.push("nominative — subject / predicate nominative candidate");
    }
    if (code === "C-" || explanation.includes("particle") || explanation.includes("conjunction")) {
      requirements.push("discourse connector — account for it or flag omission");
    }
    if (number === "plural" && (code.startsWith("A-") || code.startsWith("N-"))) {
      requirements.push(
        `plural form ${row.greek || row.lemma || ""} — use plural Spanish (e.g. escogidos/elegidos), never singular el elegido`
      );
    }

    // Detect impossible attributive agreement with previous content word.
    const prev = tokenRows[index - 1];
    if (prev && code.startsWith("A-") && String(prev.rmac || "").startsWith("N-")) {
      const prevCase = morphCase(prev.rmac);
      const prevNumber = morphNumber(prev.rmac);
      const prevGender = morphGender(prev.rmac);
      const agrees = prevCase === caseName && prevNumber === number && prevGender === gender;
      if (!agrees && caseName === "genitive") {
        requirements.push(
          `NOT an attributive adjective on ${prev.greek || prev.lemma}: case/number/gender disagree (${prev.rmac} vs ${code}). Treat as dependent genitive: "de [los] …", never as feminine singular "fe elegida/escogida".`
        );
      }
    }

    return {
      sourceTokenId: row.sourceTokenId || "",
      greek: row.greek || "",
      lemma: row.lemma || "",
      morphology: code || row.morphology || "—",
      explanation,
      number: number || null,
      case: caseName || null,
      gender: gender || null,
      requirements,
      permittedRenderings: lemmaToken?.allowedRenderings || []
    };
  });

  return {
    id: "morphology",
    name: "Morphology",
    status: "resolved",
    summary: `Parsed morphology for ${constraints.length} token${constraints.length === 1 ? "" : "s"}.`,
    constraints
  };
}

function analyzeImmediateContextGate(tokenRows, greek) {
  const nominatives = tokenRows.filter(row => String(row.rmac || "").startsWith("N-N"));
  const genitives = tokenRows.filter(row => String(row.rmac || "")[2] === "G");
  const accusatives = tokenRows.filter(row => String(row.rmac || "")[2] === "A");
  const connectors = tokenRows.filter(row => {
    const code = String(row.rmac || "");
    return code === "C-" || LIGHT_LEMMAS.has(row.lemma || "");
  });

  const syntaxNotes = [];
  for (let index = 0; index < tokenRows.length; index += 1) {
    const row = tokenRows[index];
    const prev = tokenRows[index - 1];
    const code = String(row.rmac || "");
    if (!prev || !code.startsWith("A-") || !String(prev.rmac || "").startsWith("N-")) continue;
    if (morphCase(code) !== "genitive") continue;
    if (
      morphCase(prev.rmac) === morphCase(code)
      && morphNumber(prev.rmac) === morphNumber(code)
      && morphGender(prev.rmac) === morphGender(code)
    ) {
      continue;
    }
    syntaxNotes.push(
      `${row.greek} (${code}) cannot attributively modify ${prev.greek} (${prev.rmac}): read as genitive dependent of ${prev.greek} → "de [plural] …", not "${prev.ble || prev.lemma} ${row.ble || "adjective"}" collapsed into one noun phrase gender.`
    );
  }

  const structure = {
    subjectCandidates: nominatives.map(row => row.greek).filter(Boolean),
    accusativeObjects: accusatives.map(row => row.greek).filter(Boolean),
    genitiveModifiers: genitives.map(row => row.greek).filter(Boolean),
    connectors: connectors.map(row => row.greek).filter(Boolean),
    notes: [
      greek ? `Phrase span: ${greek}` : null,
      accusatives.length ? `Accusative object material: ${accusatives.map(r => r.greek).join(" ")}` : null,
      nominatives.length ? `Nominative material: ${nominatives.map(r => r.greek).join(" ")}` : null,
      genitives.length ? `Genitive dependents: ${genitives.map(r => r.greek).join(" ")}` : null,
      ...syntaxNotes,
      connectors.length ? `Connectors/particles: ${connectors.map(r => r.greek).join(" ")}` : "No overt discourse particle in this phrase."
    ].filter(Boolean)
  };

  return {
    id: "immediateContext",
    name: "Immediate context",
    status: "resolved",
    summary: syntaxNotes[0] || structure.notes[0] || "Immediate clause structure noted from token roles.",
    structure
  };
}

function analyzeGeneralContextGate(reference, priorLbf = []) {
  const nearby = priorLbf.slice(-4);
  const notes = [
    reference ? `Current reference: ${reference}` : null,
    nearby.length
      ? `Nearby approved LBF: ${nearby.map(item => `${item.reference} → ${item.spanish}`).join("; ")}`
      : "No nearby approved LBF phrases yet."
  ].filter(Boolean);

  return {
    id: "generalContext",
    name: "General context",
    status: "resolved",
    summary: notes[1] || notes[0] || "Book/verse context pending richer discourse data.",
    scope: [reference].filter(Boolean),
    notes,
    remainingOptions: []
  };
}

function analyzeRv1909Gate(greek, tokenRows, rv1909Text) {
  const flags = [];
  const greekTokenCount = tokenRows.filter(row => row.greek).length;
  const rv = String(rv1909Text || "").trim();

  if (!rv) {
    return {
      id: "rv1909Review",
      name: "RV1909 review",
      status: "consulted",
      summary: "No RV1909 span available for this phrase.",
      rv1909Text: "",
      flags: [],
      advisoryNotes: ["Proceed from Greek constraints only."]
    };
  }

  if (/jesucristo/i.test(rv) && tokenRows.some(r => /Ἰησοῦ/.test(r.greek || "")) && tokenRows.some(r => /Χριστοῦ/.test(r.greek || ""))) {
    flags.push({
      type: "traditional-compound",
      note: "RV1909 merges Ἰησοῦ + Χριστοῦ as Jesucristo; Greek keeps two genitives."
    });
  }

  if (/\by\b/i.test(rv) && tokenRows.some(r => (r.lemma || "") === "δέ" || (r.lemma || "") === "δὲ")) {
    flags.push({
      type: "connector-rendering",
      note: "RV1909 uses 'y'; Greek particle is δέ (mild contrast/continuation, not always 'and')."
    });
  }

  const rvWords = rv.split(/\s+/).filter(Boolean).length;
  if (greekTokenCount && rvWords > greekTokenCount + 2) {
    flags.push({
      type: "possible-added-words",
      note: `RV1909 word count (${rvWords}) is higher than Greek token count (${greekTokenCount}).`
    });
  }

  return {
    id: "rv1909Review",
    name: "RV1909 review",
    status: "consulted",
    summary: flags.length
      ? `Consulted RV1909 with ${flags.length} advisory flag${flags.length === 1 ? "" : "s"}.`
      : "Consulted RV1909; no automatic conflict flags.",
    rv1909Text: rv,
    flags,
    advisoryNotes: [
      "RV1909 may inform style.",
      "RV1909 must not override lemma, morphology, or context."
    ]
  };
}

function collectConstraintStack(gates) {
  const lemma = gates.lemma;
  const allowed = (lemma.tokens || [])
    .filter(token => token.allowedRenderings?.length)
    .map(token => `${token.lemma} → ${token.allowedRenderings.join(" / ")}`);

  const morphNotes = (gates.morphology.constraints || [])
    .flatMap(item => item.requirements || []);

  const contextNotes = [
    ...(gates.immediateContext.structure?.notes || []),
    ...(gates.generalContext.notes || [])
  ];

  const rvFlags = (gates.rv1909Review.flags || []).map(flag => flag.note);

  return {
    allowedRenderings: allowed,
    morphologyRequirements: morphNotes,
    contextNotes,
    rv1909Flags: rvFlags,
    blocked: lemma.status === "blocked",
    blockedLemma: lemma.blockedLemma || null,
    blockedStrongs: lemma.blockedStrongs || null,
    blockedLemmaForm: lemma.blockedLemmaForm || null,
    investigationId: lemma.investigationId || null
  };
}

function cleanGloss(value = "") {
  return String(value || "")
    .replaceAll("•", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^de\s+/i, "");
}

function stripLeadingDe(value = "") {
  return cleanGloss(value).replace(/^de\s+/i, "").trim();
}

function agreesInCaseNumberGender(a, b) {
  const aCode = String(a?.rmac || "");
  const bCode = String(b?.rmac || "");
  if (!aCode || !bCode) return false;
  return morphCase(aCode) === morphCase(bCode)
    && morphNumber(aCode) === morphNumber(bCode)
    && morphGender(aCode) === morphGender(bCode);
}

function isAttributiveModifier(row, prev) {
  if (!prev) return false;
  const code = String(row.rmac || "");
  const prevCode = String(prev.rmac || "");
  if (!(code.startsWith("A-") || code.startsWith("N-"))) return false;
  if (!(prevCode.startsWith("N-") || prevCode.startsWith("A-"))) return false;
  return agreesInCaseNumberGender(row, prev);
}

function isGenitiveDependentOnPrevious(row, prev) {
  if (!prev) return false;
  const code = String(row.rmac || "");
  const prevCode = String(prev.rmac || "");
  if (!(code.startsWith("N-") || code.startsWith("A-") || code.startsWith("R"))) return false;
  if (morphCase(code) !== "genitive") return false;
  // Articles in genitive still mark dependency.
  if (code.startsWith("T-") || LIGHT_LEMMAS.has(row.lemma || "")) return morphCase(code) === "genitive";
  if (!prevCode) return true;
  // Attributive adjective/noun in full agreement is not a "de" dependency.
  if (isAttributiveModifier(row, prev)) return false;
  // Apposition: genitive noun after another genitive noun (optionally with possessive between).
  if (code.startsWith("N-") && (prevCode.startsWith("N-") || isPossessivePronoun(prev))) {
    return false;
  }
  return true;
}

function isArticle(row = {}) {
  const lemma = row.lemma || "";
  const code = String(row.rmac || "");
  return lemma === "ὁ" || code.startsWith("RA") || code.startsWith("T-");
}

function isPossessivePronoun(row = {}) {
  const code = String(row.rmac || "");
  const lemma = row.lemma || "";
  return (code.startsWith("RP") && morphCase(code) === "genitive")
    || (lemma === "αὐτός" && morphCase(code) === "genitive")
    || ((lemma === "ἐγώ" || lemma === "σύ") && morphCase(code) === "genitive");
}

function possessiveSpanish(row = {}) {
  const lemma = row.lemma || "";
  const greek = row.greek || "";
  const number = morphNumber(row.rmac || "");
  if (lemma === "αὐτός" || /^αὐτ/u.test(greek)) return "su";
  if (greek === "ἡμῶν" || (lemma === "ἐγώ" && number === "plural")) return "nuestro";
  if (greek === "μου" || (lemma === "ἐγώ" && number === "singular")) return "mi";
  if (greek === "ὑμῶν" || (lemma === "σύ" && number === "plural")) return "vuestro";
  if (greek === "σου" || (lemma === "σύ" && number === "singular")) return "tu";
  return stripLeadingDe(row.ble) || "";
}

function lexicalFill(row, lemmaGate) {
  const lemmaToken = (lemmaGate.tokens || []).find(item =>
    (row.sourceTokenId && item.sourceTokenId === row.sourceTokenId)
    || (row.lemma && item.lemma === row.lemma)
  );
  if (lemmaToken?.allowedRenderings?.[0]) return lemmaToken.allowedRenderings[0];

  const lemma = row.lemma || "";
  const code = String(row.rmac || "");

  // πιστεύω passive = "entrust", not "believe"
  if (lemma === "πιστεύω" && isPassiveVerb(code)) {
    const verb = parseVerbCode(code);
    if (verb?.person === "1") return "me fue confiada";
    if (verb?.person === "3") return "fue confiada";
    return "fue confiado";
  }

  if (isPossessivePronoun(row)) return possessiveSpanish(row);

  return stripLeadingDe(row.ble)
    || lemma
    || cleanGloss(row.greek)
    || "";
}

function assembleSlots(slots = []) {
  const chunks = [];
  for (const slot of slots) {
    if (slot.omit) continue;
    if (slot.relation === "possessive-before") {
      const prefix = slot.keepDe ? "de " : "";
      chunks.push(`${prefix}${slot.possessive} ${slot.value}`.replace(/\s+/g, " ").trim());
      continue;
    }
    if (slot.relation === "de") {
      const article = slot.number === "plural" ? "los " : "";
      chunks.push(`de ${article}${slot.value}`.replace(/\s+/g, " ").trim());
      continue;
    }
    if (slot.relation === "en") {
      chunks.push(`en ${slot.value}`.replace(/\s+/g, " ").trim());
      continue;
    }
    if (slot.relation === "soft-de") continue;
    if (slot.value) chunks.push(slot.value);
  }
  return chunks.join(" ")
    .replace(/\s+/g, " ")
    .replace(/\bde el\b/giu, "del")
    .trim();
}

/**
 * Grammar-first synthesis: locked relations from morphology; lexical fills are the only free slots.
 */
function buildMechanicalDraft(tokenRows = [], lemmaGate) {
  const slots = [];

  for (let index = 0; index < tokenRows.length; index += 1) {
    const row = tokenRows[index];
    const prev = tokenRows[index - 1];
    const next = tokenRows[index + 1];
    const code = String(row.rmac || "");
    const lemma = row.lemma || "";
    const slotId = row.sourceTokenId || `t${index + 1}`;
    const number = morphNumber(code);
    const caseName = morphCase(code);
    const fill = lexicalFill(row, lemmaGate);

    if (lemma === "δέ" || lemma === "δὲ") {
      slots.push({
        id: slotId,
        greek: row.greek || lemma,
        lemma,
        morph: code || "C-",
        role: "particle",
        relation: "soft-de",
        relationLocked: true,
        value: "",
        number: null,
        omit: true,
        note: "δέ present — soft continuation; do not force 'y'"
      });
      continue;
    }

    if (isArticle(row)) {
      slots.push({
        id: slotId,
        greek: row.greek || "",
        lemma,
        morph: code || "—",
        role: "article",
        relation: null,
        relationLocked: true,
        value: "",
        number,
        omit: true,
        note: "article omitted from skeleton; Spanish may supply articles"
      });
      continue;
    }

    if (isPossessivePronoun(row) && prev && (String(prev.rmac || "").startsWith("N-") || String(prev.rmac || "").startsWith("A-"))) {
      slots.push({
        id: slotId,
        greek: row.greek || "",
        lemma,
        morph: code || "—",
        role: "possessive",
        relation: null,
        relationLocked: true,
        value: possessiveSpanish(row),
        number,
        omit: true,
        note: "folded into previous noun as Spanish possessive"
      });
      const prevSlot = [...slots].reverse().find(slot => !slot.omit && slot.role !== "preposition");
      if (prevSlot) {
        const keepDe = prevSlot.relation === "de" || prevSlot.keepDe;
        prevSlot.relation = "possessive-before";
        prevSlot.possessive = possessiveSpanish(row);
        prevSlot.keepDe = keepDe;
        prevSlot.note = `${prevSlot.greek} + ${row.greek} → ${keepDe ? "de " : ""}${prevSlot.possessive} ${prevSlot.value}`;
      }
      continue;
    }

    // Emphatic ἐγώ after a 1st-person verb is usually unneeded in Spanish.
    if ((lemma === "ἐγώ" || row.greek === "ἐγὼ") && morphCase(code) === "nominative") {
      const prevVerb = [...slots].reverse().find(slot => /^V-/.test(slot.morph || ""));
      if (prevVerb && /1/.test(prevVerb.morph || "")) {
        slots.push({
          id: slotId,
          greek: row.greek || "",
          lemma,
          morph: code || "—",
          role: "emphatic-pronoun",
          relation: null,
          relationLocked: true,
          value: "",
          number,
          omit: true,
          note: "emphatic ἐγώ omitted after 1st-person verb"
        });
        continue;
      }
    }

    const isPrep = code === "P-" || code.startsWith("P-");
    let role = "content";
    let relation = null;
    let keepDe = false;
    let note = lemma === "πιστεύω" && isPassiveVerb(code)
      ? "πιστεύω passive = entrusted/confided, NOT believed"
      : null;

    if (isPrep) {
      role = "preposition";
    } else if (isAttributiveModifier(row, prev)) {
      // καιροῖς ἰδίοις → "en tiempos propios", not "en tiempos en propios"
      role = "attributive";
      relation = null;
      note = `attributive with ${prev.greek}; keep case agreement, no extra preposition`;
    } else if (
      caseName === "dative"
      && !(prev && (String(prev.rmac || "") === "P-" || ["ἐν", "ἐπί", "πρός", "παρά"].includes(prev.lemma || "")))
    ) {
      relation = "en";
      role = "dative";
    } else if (isGenitiveDependentOnPrevious(row, prev) && !isPossessivePronoun(row)) {
      role = "genitive-dependent";
      relation = "de";
    } else if (
      code.startsWith("N-")
      && caseName === "genitive"
      && prev
      && (isPossessivePronoun(prev) || (String(prev.rmac || "").startsWith("N-") && morphCase(prev.rmac) === "genitive"))
    ) {
      // τοῦ σωτῆρος ἡμῶν θεοῦ → nuestro salvador Dios (apposition, not "de Dios")
      role = "apposition";
      relation = null;
      note = "genitive apposition; do not insert 'de'";
    }

    if (next && isPossessivePronoun(next) && (code.startsWith("N-") || code.startsWith("A-"))) {
      keepDe = relation === "de";
      relation = "possessive-before";
    }

    // Relative ὃ → "que" reads better than bare BLE "cual"
    let value = fill;
    if ((lemma === "ὅς" || lemma === "ὅστις") && (fill === "cual" || fill === "el cual")) {
      value = "que";
    }

    slots.push({
      id: slotId,
      greek: row.greek || "",
      lemma,
      morph: code || "—",
      role,
      relation,
      relationLocked: Boolean(relation) || isPrep || role === "attributive" || role === "apposition",
      possessive: relation === "possessive-before" && next ? possessiveSpanish(next) : null,
      keepDe,
      value,
      valueLocked: false,
      number,
      case: caseName,
      omit: false,
      note
    });
  }

  const proposedSpanish = assembleSlots(slots) || null;
  const template = slots
    .filter(slot => !slot.omit)
    .map(slot => {
      if (slot.relation === "possessive-before") {
        const prefix = slot.keepDe ? "de " : "";
        return `${prefix}${slot.possessive || "su"} {${slot.greek}}`;
      }
      if (slot.relation === "de") {
        const art = slot.number === "plural" ? "los " : "";
        return `de ${art}{${slot.greek}}`;
      }
      if (slot.relation === "en") return `en {${slot.greek}}`;
      return `{${slot.greek}}`;
    })
    .join(" ");

  return {
    proposedSpanish,
    source: "mechanical",
    template,
    slots,
    notes: [
      "Grammar-locked draft: relations come from morphology; only lexical fills may be polished.",
      "Passive πιστεύω = confiar/encargar, not creer.",
      "Possessive genitives (αὐτοῦ/ἡμῶν) become su/nuestro before the noun."
    ]
  };
}

export function applySlotPolishes(mechanicalDraft, polishes = []) {
  if (!mechanicalDraft?.slots?.length) return mechanicalDraft;
  const byId = new Map(
    (Array.isArray(polishes) ? polishes : [])
      .filter(item => item && item.slotId && typeof item.value === "string")
      .map(item => [item.slotId, stripLeadingDe(item.value)])
  );

  const slots = mechanicalDraft.slots.map(slot => {
    if (slot.omit || slot.valueLocked) return slot;
    if (!byId.has(slot.id)) return slot;
    const next = byId.get(slot.id);
    if (!next) return slot;
    // Preserve plural morphology: reject obvious singular collapse for plural slots.
    if (slot.number === "plural" && /\b\w+o\b$/i.test(next) && !/\w+os\b$/i.test(next) && !/\w+es\b$/i.test(next)) {
      return slot;
    }
    return { ...slot, value: next, polished: true };
  });

  return {
    ...mechanicalDraft,
    slots,
    proposedSpanish: assembleSlots(slots),
    source: byId.size ? "mechanical+slot-polish" : mechanicalDraft.source
  };
}

export async function analyzePhraseGates({
  rootDir,
  reference,
  greek,
  tokenRows = [],
  rv1909Text = "",
  priorLbf = []
}) {
  const { approved, openInvestigations } = await loadLemmaPolicyIndex(rootDir);
  const lemma = analyzeLemmaGate(tokenRows, approved, openInvestigations);
  const morphology = analyzeMorphologyGate(tokenRows, lemma);
  const immediateContext = analyzeImmediateContextGate(tokenRows, greek);
  const generalContext = analyzeGeneralContextGate(reference, priorLbf);
  const rv1909Review = analyzeRv1909Gate(greek, tokenRows, rv1909Text);

  const gates = {
    lemma,
    morphology,
    immediateContext,
    generalContext,
    rv1909Review
  };

  const readyForSynthesis = lemma.status !== "blocked"
    && morphology.status === "resolved"
    && immediateContext.status === "resolved"
    && generalContext.status === "resolved"
    && rv1909Review.status === "consulted";

  const mechanicalDraft = readyForSynthesis
    ? buildMechanicalDraft(tokenRows, lemma)
    : null;

  return {
    reference,
    greek,
    gates,
    constraints: collectConstraintStack(gates),
    mechanicalDraft,
    readyForSynthesis,
    pipelineStatus: lemma.status === "blocked" ? "blocked" : readyForSynthesis ? "ready" : "incomplete"
  };
}
