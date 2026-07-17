#!/usr/bin/env node
/**
 * AI reverse-interlinear seeder for Titus (TR spine).
 *
 * Uses lemma + morphology + Strong's (not word-order zip) to propose
 * Spanish unit → TR sourceTokenIds links.
 *
 * Usage:
 *   node scripts/ai_seed_titus_reverse_links.mjs [--limit 10] [--start 11] [--only-auto] [--dry-run]
 *
 * Preserves status=seeded-hand entries. Writes/updates:
 *   translations/tr-spine/titus/titus-reverse-links.json
 */
import { readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadTranslatorEnv, runChatCompletion, describeAiAvailability } from "../src/ai/suggestPhrase.js";

const rootDir = dirname(fileURLToPath(new URL(".", import.meta.url)));
await loadTranslatorEnv(rootDir);

const args = process.argv.slice(2);
function argValue(flag, fallback = null) {
  const i = args.indexOf(flag);
  if (i < 0) return fallback;
  return args[i + 1] ?? fallback;
}

const limit = Number(argValue("--limit", "8")) || 8;
const start = Number(argValue("--start", "0")) || 0;
const onlyAuto = args.includes("--only-auto");
const dryRun = args.includes("--dry-run");
const force = args.includes("--force"); // rewrite even seeded-hand

const phrasesPath = join(rootDir, "translations/tr-spine/titus/titus-phrases-tr.json");
const linksPath = join(rootDir, "translations/tr-spine/titus/titus-reverse-links.json");

const WORD_RE = /[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+(?:'[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+)?/gu;

const SYSTEM = `You build reverse-interlinear links for La Biblia Fiel (Scrivener 1894 TR).

Rules:
1. Link Spanish → Greek tokens (sourceTokenId). Direction is reverse interlinear.
2. EVERY Spanish word must be covered by some unit (articles/prepositions may attach to a content word: "la fe", "de Dios").
3. Greek tokens MAY remain unlinked (discourse particles like δὲ, articles Spanish does not need, etc.).
4. Decide links using Greek SURFACE + LEMMA + MORPHOLOGY/RMAC + STRONG'S, not mere left-to-right zip.
5. Genitive nouns/adjectives often align with Spanish "de …".
6. Do not invent Greek ids. Only use sourceTokenIds from the provided token list.
7. Prefer natural Spanish spans that appear contiguously in the Spanish string.
8. Return ONLY JSON matching the schema.`;

function parseArgsJson(text) {
  const raw = String(text || "").trim();
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  const body = fenced ? fenced[1].trim() : raw;
  const startIdx = body.indexOf("{");
  const endIdx = body.lastIndexOf("}");
  if (startIdx < 0 || endIdx < 0) throw new Error("No JSON object in model response");
  return JSON.parse(body.slice(startIdx, endIdx + 1));
}

function spanishWords(spanish) {
  return [...String(spanish || "").matchAll(WORD_RE)].map(m => ({
    surface: m[0],
    start: m.index,
    end: m.index + m[0].length
  }));
}

function findSpan(spanish, surface) {
  if (!surface) return null;
  const exact = spanish.indexOf(surface);
  if (exact >= 0) return { start: exact, end: exact + surface.length };
  const low = spanish.toLowerCase();
  const target = surface.toLowerCase();
  const i = low.indexOf(target);
  if (i >= 0) return { start: i, end: i + surface.length };
  return null;
}

function validateUnits(phrase, units) {
  const spanish = phrase.spanish || "";
  const allowed = new Set((phrase.tokenRows || []).map(t => t.sourceTokenId));
  const issues = [];
  const normalized = [];
  const covered = Array(spanish.length).fill(false);

  for (const unit of units || []) {
    const surface = String(unit.surface || "").trim();
    const ids = Array.isArray(unit.sourceTokenIds) ? unit.sourceTokenIds.map(String) : [];
    if (!surface) {
      issues.push("empty surface");
      continue;
    }
    if (!ids.length) {
      issues.push(`no tokens for ${surface}`);
      continue;
    }
    for (const id of ids) {
      if (!allowed.has(id)) issues.push(`bad id ${id} for ${surface}`);
    }
    const span = findSpan(spanish, surface);
    if (!span) {
      issues.push(`surface not in spanish: ${surface}`);
      continue;
    }
    for (let i = span.start; i < span.end; i += 1) covered[i] = true;
    normalized.push({
      unitId: `${phrase.phraseIndex}:${normalized.length}`,
      surface: spanish.slice(span.start, span.end),
      charStart: span.start,
      charEnd: span.end,
      sourceTokenIds: ids,
      method: "ai"
    });
  }

  for (const w of spanishWords(spanish)) {
    const ok = covered.slice(w.start, w.end).every(Boolean);
    if (!ok) issues.push(`uncovered spanish: ${w.surface}`);
  }

  return { ok: issues.length === 0, issues, units: normalized };
}

function buildPrompt(phrase) {
  const tokens = (phrase.tokenRows || []).map((t, i) => ({
    row: i,
    sourceTokenId: t.sourceTokenId,
    greek: t.greek,
    lemma: t.lemma || "",
    strongs: t.strongs || "",
    rmac: t.rmac || "",
    morph: t.morphology || ""
  }));
  return `Phrase ${phrase.phraseIndex} — ${phrase.reference}

Spanish (must fully cover every word):
"""${phrase.spanish || ""}"""

Greek TR tokens (lemma + morph decide alignment):
${JSON.stringify(tokens, null, 2)}

Return JSON:
{
  "units": [
    {
      "surface": "exact contiguous span from Spanish",
      "sourceTokenIds": ["n56..."]
    }
  ],
  "unlinkedGreekIds": ["optional greek tokens with no Spanish"],
  "notes": "short rationale using lemma/morph"
}`;
}

const phrases = JSON.parse(await readFile(phrasesPath, "utf8"));
let existing = { bookId: "titus", textualBasis: "Scrivener 1894 TR", schemaVersion: 1, links: [] };
try {
  existing = JSON.parse(await readFile(linksPath, "utf8"));
} catch {
  // fresh
}

const byIndex = new Map((existing.links || []).map(l => [Number(l.phraseIndex), l]));
const availability = await describeAiAvailability();
if (!availability.available) {
  console.error(availability.message || "AI unavailable");
  process.exit(1);
}
console.log(`AI: ${availability.provider} / ${availability.model}`);

const targets = [];
for (const phrase of phrases) {
  const idx = Number(phrase.phraseIndex);
  if (idx < start) continue;
  const prev = byIndex.get(idx);
  if (!force && prev?.status === "seeded-hand") continue;
  if (onlyAuto && prev && prev.status !== "seeded-auto") continue;
  if (!String(phrase.spanish || "").trim()) continue;
  if (!(phrase.tokenRows || []).length) continue;
  targets.push(phrase);
  if (targets.length >= limit) break;
}

console.log(`Seeding ${targets.length} phrases from index >= ${start} (limit ${limit})${dryRun ? " [dry-run]" : ""}`);

let okCount = 0;
let failCount = 0;

for (const phrase of targets) {
  const idx = Number(phrase.phraseIndex);
  process.stdout.write(`\n#${idx} ${phrase.reference} … `);
  try {
    const result = await runChatCompletion({
      system: SYSTEM,
      prompt: buildPrompt(phrase),
      json: true
    });
    const parsed = parseArgsJson(result.text || result.content || result);
    const { ok, issues, units } = validateUnits(phrase, parsed.units || []);
    if (!ok) {
      failCount += 1;
      console.log("INVALID");
      console.log("  issues:", issues.join("; "));
      console.log("  notes:", parsed.notes || "");
      byIndex.set(idx, {
        phraseIndex: idx,
        reference: phrase.reference,
        status: "seeded-ai-invalid",
        units,
        issues,
        notes: parsed.notes || "",
        unlinkedGreekIds: parsed.unlinkedGreekIds || []
      });
      continue;
    }
    okCount += 1;
    console.log("ok", units.map(u => u.surface).join(" | "));
    if (parsed.notes) console.log("  ", parsed.notes);
    byIndex.set(idx, {
      phraseIndex: idx,
      reference: phrase.reference,
      status: "seeded-ai",
      units,
      notes: parsed.notes || "",
      unlinkedGreekIds: parsed.unlinkedGreekIds || []
    });
  } catch (error) {
    failCount += 1;
    console.log("ERROR", error.message || error);
    byIndex.set(idx, {
      phraseIndex: idx,
      reference: phrase.reference,
      status: "seeded-ai-error",
      units: byIndex.get(idx)?.units || [],
      issues: [String(error.message || error)]
    });
  }
}

const links = phrases.map(p => {
  const idx = Number(p.phraseIndex);
  return byIndex.get(idx) || {
    phraseIndex: idx,
    reference: p.reference,
    status: "missing",
    units: []
  };
});

const stats = {
  phrases: links.length,
  hand: links.filter(l => l.status === "seeded-hand").length,
  ai: links.filter(l => l.status === "seeded-ai").length,
  aiInvalid: links.filter(l => l.status === "seeded-ai-invalid").length,
  auto: links.filter(l => l.status === "seeded-auto").length,
  other: links.filter(l => !["seeded-hand", "seeded-ai", "seeded-ai-invalid", "seeded-auto"].includes(l.status)).length
};

const doc = {
  bookId: "titus",
  textualBasis: "Scrivener 1894 TR",
  schemaVersion: 1,
  notes:
    "Reverse interlinear: Spanish → TR tokens. Prefer seeded-hand / seeded-ai (lemma+morph). seeded-auto is weak zip scaffolding.",
  stats,
  links
};

if (!dryRun) {
  await writeFile(linksPath, `${JSON.stringify(doc, null, 2)}\n`, "utf8");
  console.log(`\nWrote ${linksPath}`);
} else {
  console.log("\nDry run — not written");
}

console.log("stats", stats);
console.log(`this run: ok=${okCount} fail=${failCount}`);
