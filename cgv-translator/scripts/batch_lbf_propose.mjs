#!/usr/bin/env node
/**
 * (b) loop helper: Analyze → Propose for draft LBF phrases.
 *
 * Usage:
 *   node scripts/batch_lbf_propose.mjs [--limit 5] [--start Titus 2:1] [--dry-run]
 *
 * Writes review log to translations/review-log.jsonl
 * Updates titus-phrases.json with AI proposals as suggestionSource=ai-proposed
 * (does NOT auto-approve — human/agent must set approval after review).
 */
import { readFile, writeFile, appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { analyzePhraseGates } from "../src/pipeline/analyzeGates.js";
import { assistPhraseGates } from "../src/pipeline/assistGates.js";
import { loadTranslatorEnv } from "../src/ai/suggestPhrase.js";
import { loadNtBookUnits } from "../src/data/morphLoader.js";

const rootDir = dirname(fileURLToPath(new URL(".", import.meta.url)));
await loadTranslatorEnv(rootDir);

const args = process.argv.slice(2);
function argValue(flag, fallback = null) {
  const i = args.indexOf(flag);
  if (i < 0) return fallback;
  return args[i + 1] ?? fallback;
}
const limit = Number(argValue("--limit", "5")) || 5;
const startRef = argValue("--start", "Titus 2:1");
const dryRun = args.includes("--dry-run");

const phrasePath = join(rootDir, "translations", "titus-phrases.json");
const logPath = join(rootDir, "translations", "review-log.jsonl");
const phrases = JSON.parse(await readFile(phrasePath, "utf8"));
const { units } = await loadNtBookUnits(rootDir, "titus");
const unitByRef = new Map(units.map(u => [u.reference, u]));

function enrichPhrase(phrase) {
  const unit = unitByRef.get(phrase.reference);
  if (!unit) return phrase;
  const idSet = new Set(phrase.sourceTokenIds || []);
  const tokenRows = (unit.tokenRows || []).filter(r => idSet.has(r.sourceTokenId));
  return {
    ...phrase,
    tokenRows,
    greek: tokenRows.map(r => r.greek).join(" ") || phrase.greek,
    bleText: tokenRows.map(r => r.ble).filter(Boolean).join(" ") || phrase.bleText,
    rv1909Text: phrase.rv1909Text || unit.rv1909Text || ""
  };
}

function isDraft(p) {
  const st = p?.approval?.status || "";
  const source = p?.suggestionSource || "";
  // Do not overwrite human/preliminary seeds that already have Spanish.
  if (String(p?.spanish || "").trim() && (source === "lbf-preliminary" || source === "lbf-approved" || st === "preliminary" || st === "approved")) {
    return false;
  }
  return st !== "approved" && source !== "lbf-approved" && source !== "lbf-preliminary";
}

const startIdx = phrases.findIndex(p => p.reference === startRef);
const from = startIdx >= 0 ? startIdx : 0;
const targets = [];
for (let i = from; i < phrases.length && targets.length < limit; i += 1) {
  if (isDraft(phrases[i])) targets.push(i);
}

console.log(`Processing ${targets.length} draft phrases from ${startRef} (limit ${limit})`);

const priorApproved = () => phrases
  .filter(p => (p.approval?.status === "approved") || p.suggestionSource === "lbf-approved")
  .filter(p => p.spanish?.trim())
  .slice(-12)
  .map(p => ({ reference: p.reference, spanish: p.spanish }));

for (const index of targets) {
  const base = enrichPhrase(phrases[index]);
  console.log(`\n=== ${base.reference} #${base.phraseIndex} ===`);
  console.log("Greek:", base.greek);
  console.log("Seed: ", base.spanish);

  const analysis = await analyzePhraseGates({
    rootDir,
    reference: base.reference,
    greek: base.greek,
    tokenRows: base.tokenRows || [],
    rv1909Text: base.rv1909Text || "",
    priorLbf: priorApproved()
  });

  console.log("Gate4:", analysis.gates.generalContext?.summary);
  if (analysis.pipelineStatus === "blocked") {
    console.log("BLOCKED", analysis.constraints?.blockedLemma);
    const entry = {
      at: new Date().toISOString(),
      reference: base.reference,
      phraseIndex: base.phraseIndex,
      status: "blocked",
      blockedLemma: analysis.constraints?.blockedLemma || null
    };
    await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");
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
    console.log("AI error:", error.message);
    await appendFile(logPath, `${JSON.stringify({
      at: new Date().toISOString(),
      reference: base.reference,
      phraseIndex: base.phraseIndex,
      status: "ai-error",
      error: error.message
    })}\n`, "utf8");
    continue;
  }

  console.log("AI:   ", assist.proposedSpanish);
  console.log("src:  ", assist.draftSource, "flags:", (assist.flags || []).join(" | ") || "none");
  console.log("RV1909:", base.rv1909Text || "—");

  const entry = {
    at: new Date().toISOString(),
    reference: base.reference,
    phraseIndex: base.phraseIndex,
    greek: base.greek,
    seed: base.spanish,
    proposedSpanish: assist.proposedSpanish,
    draftSource: assist.draftSource,
    flags: assist.flags || [],
    rationale: assist.rationale || [],
    gate4: analysis.gates.generalContext?.summary || "",
    rv1909: base.rv1909Text || ""
  };
  await appendFile(logPath, `${JSON.stringify(entry)}\n`, "utf8");

  if (!dryRun && assist.proposedSpanish) {
    // Never clobber human-approved LBF.
    if ((phrases[index].approval?.status === "approved")
      || phrases[index].suggestionSource === "lbf-approved") {
      console.log("SKIP write: already approved");
    } else {
      phrases[index] = {
        ...phrases[index],
        greek: base.greek,
        tokenRows: base.tokenRows,
        bleText: base.bleText,
        rv1909Text: base.rv1909Text,
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
}

if (!dryRun) {
  await mkdir(join(rootDir, "translations"), { recursive: true });
  // Re-read disk and preserve any phrases approved while this batch ran.
  try {
    const disk = JSON.parse(await readFile(phrasePath, "utf8"));
    if (Array.isArray(disk) && disk.length === phrases.length) {
      for (let i = 0; i < phrases.length; i += 1) {
        const d = disk[i];
        if ((d?.approval?.status === "approved") || d?.suggestionSource === "lbf-approved") {
          phrases[i] = d;
        }
      }
    }
  } catch {
    // keep in-memory phrases
  }
  await writeFile(phrasePath, `${JSON.stringify(phrases, null, 2)}\n`, "utf8");
  console.log(`\nUpdated ${phrasePath}`);
}
console.log(`Log: ${logPath}`);
