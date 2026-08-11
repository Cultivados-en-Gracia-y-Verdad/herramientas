#!/usr/bin/env node
/**
 * Book-generic LBF proposal helper.
 *
 * Usage:
 *   node scripts/propose_lbf.mjs --book zechariah --limit 5 --start "Zechariah 1:1"
 *   node scripts/propose_lbf.mjs --book zechariah --limit 1 --dry-run
 *
 * AI output is proposal work only. This command never creates lbf-approved.
 */
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { analyzePhraseGates } from "../src/pipeline/analyzeGates.js";
import { assistPhraseGates } from "../src/pipeline/assistGates.js";
import { loadTranslatorEnv } from "../src/ai/suggestPhrase.js";
import { findBook } from "../src/data/bookCatalog.js";
import { loadNtBookUnits } from "../src/data/morphLoader.js";

const rootDir = dirname(fileURLToPath(new URL(".", import.meta.url)));
await loadTranslatorEnv(rootDir);

const args = process.argv.slice(2);
function argValue(flag, fallback = null) {
  const index = args.indexOf(flag);
  if (index < 0) return fallback;
  return args[index + 1] ?? fallback;
}

const bookId = String(argValue("--book", "") || "").trim().toLowerCase();
if (!bookId) {
  throw new Error("--book is required (example: --book zechariah)");
}
const book = findBook(bookId);
if (!book) {
  throw new Error(`Unknown Translator book: ${bookId}`);
}

const limit = Number(argValue("--limit", "5")) || 5;
const startRef = String(argValue("--start", "") || "").trim();
const dryRun = args.includes("--dry-run");

function phrasePathForBook(item) {
  if (item.spine === "oshb") {
    return join(rootDir, "translations", "oshb-spine", item.id, `${item.id}-phrases.json`);
  }
  return join(rootDir, "translations", "tr-spine", item.id, `${item.id}-phrases-tr.json`);
}

function extractPhrases(document) {
  if (Array.isArray(document)) return document;
  if (document && Array.isArray(document.phrases)) return document.phrases;
  throw new Error("Phrase artifact must be an array or an object with phrases[]");
}

function withPhrases(document, phrases) {
  if (Array.isArray(document)) return phrases;
  return { ...document, phrases };
}

function isApproved(phrase) {
  return phrase?.approval?.status === "approved" || phrase?.suggestionSource === "lbf-approved";
}

function isDraft(phrase) {
  const source = String(phrase?.suggestionSource || "");
  const status = String(phrase?.approval?.status || "");
  const hasSpanish = Boolean(String(phrase?.spanish || "").trim());

  if (isApproved(phrase)) return false;
  // Preliminary Spanish has already entered the external G0A path. Do not
  // replace it with another AI proposal behind the reviewer's back.
  if (hasSpanish && (source === "lbf-preliminary" || status === "preliminary")) return false;
  return true;
}

const phrasePath = phrasePathForBook(book);
const rawDocument = JSON.parse(await readFile(phrasePath, "utf8"));
const phrases = extractPhrases(rawDocument);
const loaded = await loadNtBookUnits(rootDir, book.id);
const unitByRef = new Map((loaded.units || []).map(unit => [unit.reference, unit]));
const logPath = join(rootDir, "translations", "review-log.jsonl");

function enrichPhrase(phrase) {
  const unit = unitByRef.get(phrase.reference);
  if (!unit) return phrase;
  const idSet = new Set((phrase.sourceTokenIds || []).map(String));
  const tokenRows = (unit.tokenRows || []).filter(row => idSet.has(String(row.sourceTokenId)));
  return {
    ...phrase,
    tokenRows,
    greek: tokenRows.map(row => row.greek).filter(Boolean).join(" ") || phrase.greek || "",
    bleText: tokenRows.map(row => row.ble).filter(Boolean).join(" ") || phrase.bleText || "",
    rv1909Text: phrase.rv1909Text || unit.rv1909Text || ""
  };
}

const startIndex = startRef ? phrases.findIndex(phrase => phrase.reference === startRef) : 0;
if (startRef && startIndex < 0) {
  throw new Error(`Start reference not found in ${book.id}: ${startRef}`);
}
const from = Math.max(0, startIndex);
const targets = [];
for (let index = from; index < phrases.length && targets.length < limit; index += 1) {
  if (isDraft(phrases[index])) targets.push(index);
}

console.log(`Book: ${book.label}`);
console.log(`Processing ${targets.length} draft phrase(s)${startRef ? ` from ${startRef}` : ""} (limit ${limit})`);

const priorApproved = () => phrases
  .filter(isApproved)
  .filter(phrase => String(phrase.spanish || "").trim())
  .slice(-12)
  .map(phrase => ({ reference: phrase.reference, spanish: phrase.spanish }));

for (const index of targets) {
  const base = enrichPhrase(phrases[index]);
  console.log(`\n=== ${base.reference} #${base.phraseIndex} ===`);
  console.log("Source:", base.greek || "—");
  console.log("Current:", base.spanish || "—");

  const analysis = await analyzePhraseGates({
    rootDir,
    reference: base.reference,
    greek: base.greek || "",
    tokenRows: base.tokenRows || [],
    rv1909Text: base.rv1909Text || "",
    priorLbf: priorApproved()
  });

  if (analysis.pipelineStatus === "blocked") {
    const entry = {
      at: new Date().toISOString(),
      book: book.id,
      reference: base.reference,
      phraseIndex: base.phraseIndex,
      status: "blocked",
      blockedLemma: analysis.constraints?.blockedLemma || null
    };
    await mkdir(dirname(logPath), { recursive: true });
    await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");
    console.log("BLOCKED", entry.blockedLemma || "");
    continue;
  }

  let assist;
  try {
    assist = await assistPhraseGates({
      rootDir,
      analysis,
      rv1909Text: base.rv1909Text || ""
    });
  } catch (error) {
    const entry = {
      at: new Date().toISOString(),
      book: book.id,
      reference: base.reference,
      phraseIndex: base.phraseIndex,
      status: "ai-error",
      error: error.message
    };
    await mkdir(dirname(logPath), { recursive: true });
    await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");
    console.log("AI error:", error.message);
    continue;
  }

  console.log("AI:", assist.proposedSpanish || "—");
  const entry = {
    at: new Date().toISOString(),
    book: book.id,
    reference: base.reference,
    phraseIndex: base.phraseIndex,
    source: base.greek || "",
    currentSpanish: base.spanish || "",
    proposedSpanish: assist.proposedSpanish || "",
    draftSource: assist.draftSource,
    flags: assist.flags || [],
    rationale: assist.rationale || [],
    generalContext: analysis.gates.generalContext?.summary || ""
  };
  await mkdir(dirname(logPath), { recursive: true });
  await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");

  if (!dryRun && assist.proposedSpanish) {
    // Recheck the in-memory authority boundary immediately before mutation.
    if (isApproved(phrases[index])) {
      console.log("SKIP write: already approved");
      continue;
    }
    phrases[index] = {
      ...phrases[index],
      greek: base.greek || phrases[index].greek || "",
      tokenRows: base.tokenRows || phrases[index].tokenRows || [],
      bleText: base.bleText || phrases[index].bleText || "",
      rv1909Text: base.rv1909Text || phrases[index].rv1909Text || "",
      spanish: assist.proposedSpanish,
      suggestionSource: "ai-proposed",
      aiProposal: {
        proposedSpanish: assist.proposedSpanish,
        draftSource: assist.draftSource,
        flags: assist.flags || [],
        rationale: assist.rationale || [],
        at: entry.at
      },
      gates: {
        generalContext: analysis.gates.generalContext?.summary,
        morphology: analysis.gates.morphology?.summary,
        lemma: analysis.gates.lemma?.summary
      },
      approval: {
        status: "draft",
        approvedAt: "",
        approvedBy: ""
      }
    };
  }
}

if (!dryRun) {
  // Re-read disk and preserve anything that acquired external approval while
  // this batch was running. phraseIndex is the stable book-wide identity.
  const latestDocument = JSON.parse(await readFile(phrasePath, "utf8"));
  const latestPhrases = extractPhrases(latestDocument);
  const latestByIndex = new Map(latestPhrases.map(phrase => [Number(phrase.phraseIndex), phrase]));
  for (let index = 0; index < phrases.length; index += 1) {
    const latest = latestByIndex.get(Number(phrases[index].phraseIndex));
    if (latest && isApproved(latest)) phrases[index] = latest;
  }

  const output = withPhrases(latestDocument, phrases);
  await writeFile(phrasePath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
  console.log(`\nUpdated ${phrasePath}`);
} else {
  console.log("\nDRY RUN: phrase artifact not changed");
}
console.log(`Log: ${logPath}`);
