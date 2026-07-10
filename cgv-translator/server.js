import { createServer } from "node:http";
import { appendFile, mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { basename, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { getCgvDataPath, getGreekConstructionEvidence, getGreekOccurrencesByStrongs } from "./src/data/cgvData.js";
import { loadTranslationIndexes, resolveAlignedSpan } from "./src/data/translationIndexes.js";

const rootDir = fileURLToPath(new URL(".", import.meta.url));
const publicDir = join(rootDir, "public");
const investigationsDir = join(rootDir, "investigations");
const translationsDir = join(rootDir, "translations");
const translationDocumentFile = join(translationsDir, "titus-1-1.md");
const translationPhraseFile = join(translationsDir, "titus-phrases.json");
const port = Number(process.env.PORT || 1424);

const tabs = [
  { id: "README", file: "README.md" },
  { id: "Observations", file: "observations.md" },
  { id: "Decision", file: "decision.md" },
  { id: "Questions", file: "questions.md" },
  { id: "Evidence", file: "evidence.md" },
  { id: "Research", file: "research.md" },
  { id: "Policy", file: "policy.md" },
  { id: "History", file: "history.md" }
];

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml"
};

function send(response, status, body, contentType = "text/plain; charset=utf-8") {
  response.writeHead(status, {
    "Content-Type": contentType,
    "Cache-Control": "no-store"
  });
  response.end(body);
}

function sendJson(response, status, body) {
  send(response, status, JSON.stringify(body), "application/json; charset=utf-8");
}

function normalizeTranslationPhrases(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => ({
      reference: typeof item.reference === "string" && item.reference.trim()
        ? item.reference.trim()
        : "Titus 1:1",
      phraseIndex: Number.isInteger(Number(item.phraseIndex)) ? Number(item.phraseIndex) : index,
      greek: typeof item.greek === "string" ? item.greek : "",
      spanish: typeof item.spanish === "string" ? item.spanish : "",
      sourceTokenIds: Array.isArray(item.sourceTokenIds) ? item.sourceTokenIds.map(String) : [],
      rv1909Text: typeof item.rv1909Text === "string" ? item.rv1909Text : "",
      bleText: typeof item.bleText === "string" ? item.bleText : "",
      suggestionSource: typeof item.suggestionSource === "string" ? item.suggestionSource : ""
    }))
    .filter(item => item.phraseIndex >= 0)
    .sort((a, b) => a.phraseIndex - b.phraseIndex);
}

function safeInvestigationPath(id) {
  if (!/^INV-\d{4}$/.test(id)) {
    throw new Error("Invalid investigation ID");
  }
  return join(investigationsDir, id);
}

function safeTabFile(file) {
  const tab = tabs.find(item => item.file === file);
  if (!tab) {
    throw new Error("Invalid investigation file");
  }
  return tab;
}

function safeEvidenceFile(file) {
  if (!/^[a-z0-9-]+\.md$/.test(file)) {
    throw new Error("Invalid evidence file");
  }
  return file;
}

function todayIsoDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/La_Paz" });
}

function parseMorphLine(line) {
  const match = line.match(/^(\d{6})\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$/u);
  if (!match) return null;
  const [, verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma] = match;
  return { verseId, partOfSpeech, parsing, surfaceWithPunctuation, surfaceForm, normalizedForm, lemma };
}

function formatRmac(partOfSpeech, parsing) {
  return `${partOfSpeech}${String(parsing || "").replace(/^-+/u, "").replace(/-+$/u, "")}`;
}

function describeMorphologySpanish(partOfSpeech, parsing) {
  const compact = String(parsing || "").replace(/-/gu, "");
  const caseNames = { N: "nominativo", G: "genitivo", D: "dativo", A: "acusativo", V: "vocativo" };
  const numberNames = { S: "singular", P: "plural" };
  const genderNames = { M: "masculino", F: "femenino", N: "neutro" };
  const tenseNames = { P: "presente", I: "imperfecto", F: "futuro", A: "aoristo", R: "perfecto", L: "pluscuamperfecto" };
  const voiceNames = { A: "activo", M: "medio", P: "pasivo" };
  const moodNames = { I: "indicativo", S: "subjuntivo", O: "optativo", M: "imperativo", N: "infinitivo", P: "participio" };

  if (partOfSpeech === "V-") {
    const person = compact.match(/[123]/u)?.[0];
    const tense = tenseNames[compact[1]] || tenseNames[compact[0]];
    const voice = voiceNames[compact[2]] || voiceNames[compact[1]];
    const mood = moodNames[compact[3]] || moodNames[compact[2]];
    const number = numberNames[compact.match(/[SP]/u)?.[0]];
    return [tense, voice, mood, person ? `${person}.ª persona` : "", number].filter(Boolean).join(", ") || "—";
  }

  const caseCode = compact.match(/[NGDAV]/u)?.[0];
  const numberCode = compact.match(/[SP]/u)?.[0];
  const genderCode = compact.match(/[MFN]/u)?.[0];
  const description = [caseNames[caseCode], numberNames[numberCode], genderNames[genderCode]].filter(Boolean).join(" ");
  return description || "—";
}

function knownStrongForLemma(lemma) {
  return {
    δοῦλος: "G1401",
    ἀπόστολος: "G652",
    πίστις: "G4102",
    πίστιν: "G4102"
  }[lemma] || "";
}

function formatGreekVerse(rows) {
  return rows
    .map(row => row.surfaceWithPunctuation)
    .join(" ")
    .replace(/\s+([,.;·:!?])/gu, "$1")
    .replace(/\s+([)\]])/gu, "$1")
    .replace(/([([])\s+/gu, "$1")
    .trim();
}

function titusSourceTokenId(chapter, verse, position) {
  return `n56${String(chapter).padStart(3, "0")}${String(verse).padStart(3, "0")}${String(position).padStart(3, "0")}`;
}

function titusSourceTokenRange(chapter, verse, start, end) {
  return Array.from({ length: end - start + 1 }, (_, index) => titusSourceTokenId(chapter, verse, start + index));
}

const knownPhraseTokenIds = new Map([
  ["Titus 1:1|0", titusSourceTokenRange(1, 1, 1, 3)],
  ["Titus 1:1|1", titusSourceTokenRange(1, 1, 4, 7)],
  ["Titus 1:1|2", titusSourceTokenRange(1, 1, 8, 11)],
  ["Titus 1:1|3", titusSourceTokenRange(1, 1, 12, 14)],
  ["Titus 1:1|4", titusSourceTokenRange(1, 1, 15, 17)]
]);

function splitReferenceTokens(text) {
  return String(text || "")
    .trim()
    .split(/\s+/u)
    .map(token => token.replace(/^[,.;:!?¿¡]+|[,.;:!?¿¡]+$/gu, ""))
    .filter(Boolean);
}

function buildTokenRows(rows, chapter, verse, bleText, translationIndexes) {
  const bleTokens = splitReferenceTokens(bleText);
  return rows.map((row, index) => {
    const sourceTokenId = titusSourceTokenId(chapter, verse, index + 1);
    return {
      sourceTokenId,
      greek: row.surfaceForm,
      lemma: row.lemma,
      strongs: knownStrongForLemma(row.lemma),
      rmac: formatRmac(row.partOfSpeech, row.parsing),
      morphology: describeMorphologySpanish(row.partOfSpeech, row.parsing),
      ble: bleTokens[index] || "",
      rv1909: resolveAlignedSpan(translationIndexes, [sourceTokenId])
    };
  });
}

async function loadTitusTranslationUnits() {
  const cgvDataDir = getCgvDataPath();
  const translationIndexes = await loadTranslationIndexes(cgvDataDir);
  const [bleContent, morphContent] = await Promise.all([
    readFile(join(cgvDataDir, "bibles/BLE/tito.ble.md"), "utf8").catch(() => ""),
    readFile(join(cgvDataDir, "morphology/MorphGNT/77-Tit-morphgnt.txt"), "utf8").catch(() => "")
  ]);
  const greekByReference = new Map();

  for (const line of morphContent.replace(/\r\n/g, "\n").split("\n")) {
    const row = parseMorphLine(line);
    if (!row) continue;
    const chapter = Number(row.verseId.slice(2, 4));
    const verse = Number(row.verseId.slice(4, 6));
    const reference = `Titus ${chapter}:${verse}`;
    if (!greekByReference.has(reference)) greekByReference.set(reference, []);
    greekByReference.get(reference).push(row);
  }

  return bleContent
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map(line => {
      const match = line.match(/^Tito\s+(\d+):(\d+)\s+(.+)$/u);
      if (!match) return null;
      const [, chapter, verse, bleText] = match;
      const reference = `Titus ${Number(chapter)}:${Number(verse)}`;
      const greekRows = greekByReference.get(reference) || [];
      const sourceTokenIds = greekRows
        .map((_, index) => titusSourceTokenId(Number(chapter), Number(verse), index + 1));
      return {
        reference,
        greekText: formatGreekVerse(greekRows),
        sourceTokenIds,
        tokenRows: buildTokenRows(greekRows, Number(chapter), Number(verse), bleText.trim(), translationIndexes),
        rv1909Text: translationIndexes.rv1909.get(`17|${Number(chapter)}|${Number(verse)}`)
          || resolveAlignedSpan(translationIndexes, sourceTokenIds),
        bleText: bleText.trim()
      };
    })
    .filter(Boolean);
}

async function enrichTranslationPhraseRecords(phrases) {
  const units = await loadTitusTranslationUnits().catch(() => []);
  const unitsByReference = new Map(units.map(unit => [unit.reference, unit]));
  return phrases.map(phrase => {
    const unit = unitsByReference.get(phrase.reference);
    if (!unit) return phrase;
    const tokenIds = phrase.sourceTokenIds.length
      ? phrase.sourceTokenIds
      : (knownPhraseTokenIds.get(`${phrase.reference}|${phrase.phraseIndex}`) || unit.sourceTokenIds || []);
    const tokenIdSet = new Set(tokenIds);
    const tokenRows = (unit.tokenRows || []).filter(row => tokenIdSet.has(row.sourceTokenId));
    const rv1909TokenText = tokenRows.map(row => row.rv1909).filter(Boolean).join(" ");
    const bleTokenText = tokenRows.map(row => row.ble).filter(Boolean).join(" ");
    return {
      ...phrase,
      sourceTokenIds: tokenIds,
      tokenRows,
      rv1909Text: phrase.rv1909Text || rv1909TokenText || unit.rv1909Text || "",
      bleText: phrase.bleText || bleTokenText || unit.bleText || "",
      suggestionSource: phrase.suggestionSource || (unit.rv1909Text ? "rv1909" : (unit.bleText ? "ble" : "blank"))
    };
  });
}

const decisionDefaults = {
  status: "Draft",
  version: "1.0",
  effectiveDate: "",
  lemma: "δοῦλος",
  strongs: "G1401",
  preferredRendering: "",
  confidence: "Medium",
  reason: ""
};

function normalizeDecisionValue(value) {
  return String(value || "").trim();
}

function valueOrDash(value) {
  return normalizeDecisionValue(value) || "—";
}

function defaultDecisionMarkdown() {
  return serializeDecisionVersions([decisionDefaults]);
}

function parseDecisionVersions(markdown) {
  const normalized = markdown.replace(/\r\n/g, "\n");
  const matches = [...normalized.matchAll(/^## Version (.+)$/gmu)];
  if (!matches.length) return [];

  return matches.map((match, index) => {
    const start = match.index;
    const end = matches[index + 1]?.index ?? normalized.length;
    const block = normalized.slice(start, end).trim();
    const readField = label => {
      const fieldMatch = block.match(new RegExp(`^${label}:\\s*(.*)$`, "mu"));
      const value = fieldMatch?.[1]?.trim() || "";
      return value === "—" ? "" : value;
    };
    const reasonMatch = block.match(/^### Reason\s*\n([\s\S]*)$/mu);
    const reason = reasonMatch?.[1]
      ?.replace(/\n---\s*$/u, "")
      .trim() || "";

    return {
      status: readField("Status") || "Draft",
      version: readField("Version") || match[1].trim(),
      effectiveDate: readField("Effective Date"),
      lemma: readField("Lemma") || decisionDefaults.lemma,
      strongs: readField("Strong's") || decisionDefaults.strongs,
      preferredRendering: readField("Preferred Rendering"),
      confidence: readField("Confidence") || "Medium",
      reason
    };
  });
}

function serializeDecisionVersions(versions) {
  const content = versions.map(version => `## Version ${version.version}

Status: ${valueOrDash(version.status)}
Version: ${valueOrDash(version.version)}
Effective Date: ${valueOrDash(version.effectiveDate)}
Lemma: ${valueOrDash(version.lemma)}
Strong's: ${valueOrDash(version.strongs)}
Preferred Rendering: ${valueOrDash(version.preferredRendering)}
Confidence: ${valueOrDash(version.confidence)}

### Reason

${normalizeDecisionValue(version.reason)}
`).join("\n---\n\n");

  return `# Decision

${content}`;
}

function nextDecisionVersion(version) {
  const major = Number.parseInt(String(version || "1.0").split(".")[0], 10);
  return `${Number.isFinite(major) ? major + 1 : 2}.0`;
}

function sameDecisionContent(left, right) {
  return [
    "effectiveDate",
    "lemma",
    "strongs",
    "preferredRendering",
    "confidence",
    "reason"
  ].every(key => normalizeDecisionValue(left[key]) === normalizeDecisionValue(right[key]));
}

async function readDecisionFile(filePath) {
  const content = await readFile(filePath, "utf8").catch(() => "");
  return content || defaultDecisionMarkdown();
}

async function appendHistory(investigationDir, entry) {
  await appendFile(
    join(investigationDir, "history.md"),
    `\n## ${todayIsoDate()}\n\n${entry}\n`,
    "utf8"
  );
}

function decisionFromBody(body, fallback) {
  return {
    ...fallback,
    status: body.status === "Under Review" ? "Under Review" : "Draft",
    version: fallback.version,
    effectiveDate: normalizeDecisionValue(body.effectiveDate),
    lemma: fallback.lemma || decisionDefaults.lemma,
    strongs: fallback.strongs || decisionDefaults.strongs,
    preferredRendering: normalizeDecisionValue(body.preferredRendering),
    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",
    reason: normalizeDecisionValue(body.reason)
  };
}

async function handleDecision(request, response, id) {
  const investigationDir = safeInvestigationPath(id);
  const filePath = join(investigationDir, "decision.md");

  if (request.method === "GET") {
    const content = await readDecisionFile(filePath);
    const versions = parseDecisionVersions(content);
    sendJson(response, 200, {
      decision: versions.at(-1) || decisionDefaults,
      versions,
      content
    });
    return;
  }

  if (request.method !== "PUT") {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const body = await readJsonBody(request);
  const existingContent = await readFile(filePath, "utf8").catch(() => "");
  const versions = parseDecisionVersions(existingContent);
  const existingLatest = versions.at(-1) || decisionDefaults;
  let latest = decisionFromBody(body, existingLatest);
  const historyEntries = [];

  if (!versions.length) {
    versions.push(latest);
    historyEntries.push(`Created decision ${latest.version} for ${latest.strongs} ${latest.lemma}.`);
  } else if (existingLatest.status === "Approved" && !sameDecisionContent(existingLatest, latest)) {
    latest = {
      ...latest,
      status: "Draft",
      version: nextDecisionVersion(existingLatest.version),
      effectiveDate: ""
    };
    versions.push(latest);
    historyEntries.push(`Revised decision for ${latest.strongs} ${latest.lemma}; created version ${latest.version}.`);
  } else if (existingLatest.status !== "Approved") {
    versions[versions.length - 1] = latest;
  }

  if (body.action === "approve") {
    const current = versions.at(-1);
    if (!normalizeDecisionValue(current.preferredRendering) || !normalizeDecisionValue(current.reason)) {
      sendJson(response, 400, { error: "Preferred Rendering and Reason are required before approval." });
      return;
    }

    const previousApproved = versions.slice(0, -1).filter(version => version.status === "Approved");
    for (const version of previousApproved) {
      version.status = "Superseded";
      historyEntries.push(`Superseded decision ${version.version} for ${version.strongs} ${version.lemma}.`);
    }

    if (current.status !== "Approved") {
      current.status = "Approved";
      current.effectiveDate = current.effectiveDate || todayIsoDate();
      historyEntries.push(`Approved decision ${current.version} for ${current.strongs} ${current.lemma}.`);
    }
  }

  await writeFile(filePath, serializeDecisionVersions(versions), "utf8");
  for (const entry of historyEntries) {
    await appendHistory(investigationDir, entry);
  }

  sendJson(response, 200, {
    saved: true,
    decision: versions.at(-1),
    versions
  });
}

function formatOccurrenceEvidence(report, generatedAt) {
  const countBy = (items, getKey) => {
    const counts = new Map();
    for (const item of items) {
      const key = valueOrDash(getKey(item));
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return [...counts.entries()].map(([label, count]) => ({ label, count }));
  };
  const countTable = (headers, rows) => {
    const alignment = headers.map((_, index) => index === headers.length - 1 ? "------:" : "------");
    const body = rows.map(row => `| ${row.map(valueOrDash).join(" | ")} |`).join("\n");
    return [
      `| ${headers.join(" | ")} |`,
      `|${alignment.map(value => ` ${value} `).join("|")}|`,
      body || `| ${headers.map((_, index) => index === headers.length - 1 ? "0" : "—").join(" | ")} |`
    ].join("\n");
  };
  const sortedCounts = counts => [...counts].sort((left, right) => (
    right.count - left.count || left.label.localeCompare(right.label, "el")
  ));
  const morphDescription = () => "—";
  const firstReference = predicate => report.occurrences.find(predicate)?.reference || "—";

  const formRows = sortedCounts(countBy(report.occurrences, occurrence => occurrence.surfaceForm))
    .map(row => [row.label, row.count]);
  const morphologyRows = sortedCounts(countBy(report.occurrences, occurrence => occurrence.morphology))
    .map(row => [row.label, morphDescription(row.label), row.count]);
  const distributionRows = countBy(report.occurrences, occurrence => occurrence.author || occurrence.bookName)
    .map(row => [row.label, row.count]);
  const firstNt = report.occurrences[0]?.reference || "—";
  const firstPauline = firstReference(occurrence => occurrence.author === "Paul");
  const firstTitus = firstReference(occurrence => occurrence.bookName === "Titus");

  const occurrenceSections = report.occurrences.map(occurrence => {
    const translations = occurrence.translations || {};

    return `<details>
<summary>${occurrence.reference}</summary>

#### Reference

${valueOrDash(occurrence.reference)}

#### Greek Context

${valueOrDash(occurrence.greekText)}

#### Morphology

Surface form: ${valueOrDash(occurrence.surfaceForm)}  
Lemma: ${valueOrDash(occurrence.lemma)}  
Strong's: ${valueOrDash(occurrence.strongs)}  
RMAC: ${valueOrDash(occurrence.morphology)}

#### Project

Literal: ${valueOrDash(translations.projectLiteral)}

BLE: ${valueOrDash(translations.ble)}

#### Historical Witnesses

RV1862: ${valueOrDash(translations.rv1862)}

RV1909: ${valueOrDash(translations.rv1909)}

SPNBES: ${valueOrDash(translations.spnbes)}

SPNVBL: ${valueOrDash(translations.spnvbl)}

</details>`;
  }).join("\n\n");

  return `# Lemma Profile v0.1 — ${report.subject}

## Lemma Summary

| Field | Value |
|------|-------|
| Lemma | ${valueOrDash(report.lemma)} |
| Strong's | ${valueOrDash(report.strongs)} |
| Total NT occurrences | ${report.occurrences.length} |
| Source | cgv-data |
| Generated timestamp | ${generatedAt} |

## Forms Found

${countTable(["Form", "Count"], formRows)}

## Morphology Summary

${countTable(["RMAC", "Description", "Count"], morphologyRows)}

## Author Distribution

${countTable(["Author / Book", "Count"], distributionRows)}

## First Uses

First NT occurrence: ${firstNt}

First Pauline occurrence: ${firstPauline}

First occurrence in Titus: ${firstTitus}

## Occurrence Blocks

${occurrenceSections}
`;
}

function formatSingleOccurrenceEvidence(report, generatedAt, target = {}) {
  const reference = normalizeDecisionValue(target.reference);
  const surface = normalizeDecisionValue(target.surface);
  const occurrence = report.occurrences.find(item => (
    (!reference || item.reference === reference)
    && (!surface || item.surfaceForm === surface)
  )) || report.occurrences[0];
  const translations = occurrence?.translations || {};

  return `# Occurrence Evidence v0.1 — ${valueOrDash(occurrence?.reference)}

## Occurrence Summary

| Field | Value |
|------|-------|
| Reference | ${valueOrDash(occurrence?.reference)} |
| Lemma | ${valueOrDash(occurrence?.lemma || report.lemma)} |
| Strong's | ${valueOrDash(occurrence?.strongs || report.strongs)} |
| Source | cgv-data |
| Generated timestamp | ${generatedAt} |

## Greek Context

${valueOrDash(occurrence?.greekText)}

## Morphology

Surface form: ${valueOrDash(occurrence?.surfaceForm)}  
Lemma: ${valueOrDash(occurrence?.lemma)}  
Strong's: ${valueOrDash(occurrence?.strongs)}  
RMAC: ${valueOrDash(occurrence?.morphology)}

## Project

Literal: ${valueOrDash(translations.projectLiteral)}

BLE: ${valueOrDash(translations.ble)}

## Historical Witnesses

RV1862: ${valueOrDash(translations.rv1862)}

RV1909: ${valueOrDash(translations.rv1909)}

SPNBES: ${valueOrDash(translations.spnbes)}

SPNVBL: ${valueOrDash(translations.spnvbl)}
`;
}

function formatConstructionEvidence(report, generatedAt, id) {
  const occurrenceSections = report.occurrences.map(occurrence => {
    const translations = occurrence.translations || {};

    return `### ${occurrence.reference}

Greek:
${valueOrDash(occurrence.greekText)}

Selected form:
${valueOrDash(occurrence.surfaceForm)}

Lemma:
${valueOrDash(occurrence.lemma)}

RMAC:
${valueOrDash(occurrence.morphology)}

BLE:
${valueOrDash(translations.ble)}

RV1909:
${valueOrDash(translations.rv1909)}

RV1862:
—

SPNBES:
—

SPNVBL:
—`;
  }).join("\n\n");

  return `# Construction Evidence — ${valueOrDash(report.construction)}

## Metadata

Investigation: ${valueOrDash(id)}
Reference: ${valueOrDash(report.investigationReference)}
Selected token: ${valueOrDash(report.selectedToken || report.target?.surfaceForm)}
Lemma: ${valueOrDash(report.target?.lemma)}
RMAC: ${valueOrDash(report.selectedRmac)}
Construction: ${valueOrDash(report.construction)}
Search pattern: ${valueOrDash(report.searchPattern)}
Source: cgv-data
Generated at: ${generatedAt}

## Summary

Total matches: ${report.occurrences.length}

## Matches

${occurrenceSections || "No exact construction matches found."}
`;
}

function readMarkdownValue(markdown, heading) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const headingIndex = lines.findIndex(line => line.trim() === `## ${heading}`);
  if (headingIndex === -1) return "";

  for (let index = headingIndex + 1; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line || line === "---") continue;
    if (line.startsWith("#")) return "";
    return line;
  }

  return "";
}

function readOriginValue(markdown, label) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n").map(line => line.trim());
  const originIndex = lines.findIndex(line => line === "## Origin");
  if (originIndex === -1) return "";

  const nextSection = lines.findIndex((line, index) => index > originIndex && line.startsWith("## "));
  const end = nextSection === -1 ? lines.length : nextSection;

  for (let index = originIndex + 1; index < end; index += 1) {
    if (lines[index] !== label) continue;
    for (let valueIndex = index + 1; valueIndex < end; valueIndex += 1) {
      const value = lines[valueIndex];
      if (!value || value === "---") continue;
      return value.startsWith("#") ? "" : value;
    }
  }

  return "";
}

async function readInvestigationMeta(id, investigationDir) {
  const readme = await readFile(join(investigationDir, "README.md"), "utf8").catch(() => "");
  return {
    id,
    primarySubject: readMarkdownValue(readme, "Primary Subject"),
    originReference: readOriginValue(readme, "Reference"),
    currentStatus: readMarkdownValue(readme, "Current Status")
  };
}

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

async function sendEvidenceMarkdown(response, id, fileName) {
  const investigationDir = safeInvestigationPath(id);
  const evidenceDir = join(investigationDir, "evidence");
  const safeFileName = safeEvidenceFile(decodeURIComponent(fileName));
  const content = await readFile(join(evidenceDir, safeFileName), "utf8").catch(() => "");
  if (!content) {
    send(response, 404, "Not found");
    return;
  }
  send(response, 200, content, "text/markdown; charset=utf-8");
}

async function handleTranslation(request, response) {
  if (request.method === "GET") {
    const [content, phraseContent] = await Promise.all([
      readFile(translationDocumentFile, "utf8").catch(() => ""),
      readFile(translationPhraseFile, "utf8").catch(() => "")
    ]);
    let phrases = [];
    if (phraseContent) {
      try {
        phrases = normalizeTranslationPhrases(JSON.parse(phraseContent));
      } catch {
        phrases = [];
      }
    }
    phrases = await enrichTranslationPhraseRecords(phrases);
    sendJson(response, 200, { reference: "Titus 1:1", content, phrases });
    return;
  }

  if (request.method === "PUT" || request.method === "POST") {
    const body = await readJsonBody(request);
    const content = typeof body.content === "string" ? body.content : "";
    const phrases = await enrichTranslationPhraseRecords(normalizeTranslationPhrases(body.phrases));
    await mkdir(translationsDir, { recursive: true });
    await writeFile(translationDocumentFile, content.endsWith("\n") ? content : `${content}\n`, "utf8");
    await writeFile(translationPhraseFile, `${JSON.stringify(phrases, null, 2)}\n`, "utf8");
    sendJson(response, 200, { saved: true, reference: "Titus 1:1" });
    return;
  }

  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleApi(request, response, url) {
  if (url.pathname === "/api/translation/current") {
    await handleTranslation(request, response);
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/translation/units") {
    const units = await loadTitusTranslationUnits();
    sendJson(response, 200, { book: "Titus", units });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/investigations") {
    const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);
    const investigations = entries
      .filter(entry => entry.isDirectory() && /^INV-\d{4}$/.test(entry.name))
      .map(entry => entry.name)
      .sort();
    sendJson(response, 200, { investigations });
    return;
  }

  const evidenceMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{4})\/evidence(?:\/([^/]+))?$/);
  if (evidenceMatch) {
    const [, id, fileName] = evidenceMatch;
    const investigationDir = safeInvestigationPath(id);
    const evidenceDir = join(investigationDir, "evidence");

    if (request.method === "GET" && !fileName) {
      const entries = await readdir(evidenceDir, { withFileTypes: true }).catch(() => []);
      const files = entries
        .filter(entry => entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md")
        .map(entry => ({ name: entry.name, path: `evidence/${entry.name}` }))
        .sort((left, right) => left.name.localeCompare(right.name));
      sendJson(response, 200, { id, files });
      return;
    }

    if (request.method === "GET" && fileName) {
      await sendEvidenceMarkdown(response, id, fileName);
      return;
    }

    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const gatherMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{4})\/gather$/);
  if (gatherMatch) {
    const [, id] = gatherMatch;
    const investigationDir = safeInvestigationPath(id);

    if (request.method !== "POST") {
      sendJson(response, 405, { error: "Method not allowed" });
      return;
    }

    const evidenceDir = join(investigationDir, "evidence");
    const body = await readJsonBody(request);
    const evidenceTypes = {
      occurrence: {
        fileName: "occurrence.md",
        existsMessage: "occurrence.md already exists"
      },
      occurrences: {
        fileName: "occurrences.md",
        existsMessage: "occurrences.md already exists"
      },
      construction: {
        fileName: "construction.md",
        existsMessage: "construction.md already exists"
      }
    };
    const evidenceType = evidenceTypes[body.type];

    if (!evidenceType) {
      sendJson(response, 400, { error: "Only occurrence, lemma, and construction gathering are implemented" });
      return;
    }

    const fileName = evidenceType.fileName;
    const filePath = join(evidenceDir, fileName);
    const exists = await stat(filePath).then(() => true).catch(() => false);

    if (exists && body.replace !== true) {
      sendJson(response, 409, {
        code: "EVIDENCE_EXISTS",
        fileName,
        error: evidenceType.existsMessage
      });
      return;
    }

    const strongs = normalizeDecisionValue(body.strongs) || "G1401";
    const generatedAt = new Date().toISOString();
    let evidence = "";
    let historyEntry = "";

    if (body.type === "construction") {
      const report = await getGreekConstructionEvidence({
        strongs,
        lemma: body.lemma,
        surface: body.surface,
        reference: body.reference,
        rmac: body.rmac,
        prepositionLemma: body.prepositionLemma,
        prepositionSurface: body.prepositionSurface,
        caseCode: body.caseCode
      });
      evidence = formatConstructionEvidence(report, generatedAt, id);
      historyEntry = `Generated Construction Evidence v0.1 for ${report.construction} from cgv-data.`;
    } else {
      const report = await getGreekOccurrencesByStrongs(strongs);
      evidence = body.type === "occurrence"
        ? formatSingleOccurrenceEvidence(report, generatedAt, body)
        : formatOccurrenceEvidence(report, generatedAt);
      historyEntry = body.type === "occurrence"
        ? `Generated occurrence evidence for ${strongs} ${report.lemma} from cgv-data.`
        : `Generated Lemma Profile v0.1 occurrence evidence for ${strongs} ${report.lemma} from cgv-data.`;
    }

    await mkdir(evidenceDir, { recursive: true });
    await writeFile(filePath, evidence.endsWith("\n") ? evidence : `${evidence}\n`, "utf8");
    await appendHistory(investigationDir, historyEntry);

    sendJson(response, 200, {
      generated: true,
      replaced: exists,
      file: { name: basename(filePath), path: `evidence/${fileName}` }
    });
    return;
  }

  const decisionMatch = url.pathname.match(/^\/api\/investigations\/(INV-\d{4})\/decision$/);
  if (decisionMatch) {
    await handleDecision(request, response, decisionMatch[1]);
    return;
  }

  const match = url.pathname.match(/^\/api\/investigations\/(INV-\d{4})(?:\/files\/([^/]+))?$/);
  if (!match) {
    sendJson(response, 404, { error: "Not found" });
    return;
  }

  const [, id, fileName] = match;
  const investigationDir = safeInvestigationPath(id);

  if (request.method === "GET" && !fileName) {
    const files = await Promise.all(
      tabs.map(async tab => {
        const path = join(investigationDir, tab.file);
        const exists = await stat(path).then(() => true).catch(() => false);
        return { ...tab, exists };
      })
    );
    const meta = await readInvestigationMeta(id, investigationDir);
    sendJson(response, 200, { id, meta, files });
    return;
  }

  if (!fileName) {
    sendJson(response, 405, { error: "Method not allowed" });
    return;
  }

  const tab = safeTabFile(decodeURIComponent(fileName));
  const filePath = join(investigationDir, tab.file);

  if (request.method === "GET") {
    const content = tab.file === "decision.md"
      ? await readDecisionFile(filePath)
      : await readFile(filePath, "utf8").catch(() => "");
    sendJson(response, 200, { id, tab: tab.id, file: tab.file, content });
    return;
  }

  if (request.method === "PUT") {
    const body = await readJsonBody(request);
    const content = typeof body.content === "string" ? body.content : "";
    await writeFile(filePath, content.endsWith("\n") ? content : `${content}\n`, "utf8");
    sendJson(response, 200, { saved: true, id, tab: tab.id, file: tab.file });
    return;
  }

  sendJson(response, 405, { error: "Method not allowed" });
}

async function handleStatic(response, url) {
  const requested = url.pathname === "/" ? "/index.html" : url.pathname;
  const path = normalize(join(publicDir, requested));
  if (!path.startsWith(publicDir)) {
    send(response, 403, "Forbidden");
    return;
  }

  try {
    const content = await readFile(path);
    send(response, 200, content, contentTypes[extname(path)] || "application/octet-stream");
  } catch {
    send(response, 404, "Not found");
  }
}

createServer(async (request, response) => {
  try {
    const url = new URL(request.url || "/", `http://${request.headers.host}`);
    if (url.pathname.startsWith("/api/")) {
      await handleApi(request, response, url);
      return;
    }

    const evidenceAliasMatch = url.pathname.match(/^\/(?:investigations\/(INV-\d{4})\/)?evidence\/([^/]+)$/);
    if (request.method === "GET" && evidenceAliasMatch) {
      const [, id = "INV-0001", fileName] = evidenceAliasMatch;
      await sendEvidenceMarkdown(response, id, fileName);
      return;
    }

    await handleStatic(response, url);
  } catch (error) {
    sendJson(response, 500, { error: error instanceof Error ? error.message : String(error) });
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`CGV Translator prototype: http://127.0.0.1:${port}/`);
});
