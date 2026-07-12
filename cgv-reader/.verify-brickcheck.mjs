import { createServer } from "vite";
import { readFileSync } from "fs";

const bundle = JSON.parse(readFileSync("/Users/johnwry/Downloads/titus-progress-2026-07-12 (4).json", "utf8"));
const data = bundle.data;

const server = await createServer({ server: { middlewareMode: true } });
const oData = await server.ssrLoadModule("/src/o-data.ts");

const titusData = oData.loadTitusData();

function moodFromSourceMorph(sourceMorph) {
  if (!/^V-[123]/.test(sourceMorph)) return null;
  switch (sourceMorph[5]) {
    case "I": return "indicative";
    case "S": return "subjunctive";
    case "D":
    case "M": return "imperative";
    case "O": return "optative";
    default: return null;
  }
}

const finiteIds = new Set();
const byMood = { indicative: new Set(), subjunctive: new Set(), imperative: new Set(), optative: new Set() };
for (const [, verses] of titusData.greek) {
  for (const verse of verses) {
    for (const token of verse.tokens) {
      const mood = moodFromSourceMorph(token.sourceMorph);
      if (!mood) continue;
      finiteIds.add(token.id);
      byMood[mood].add(token.id);
    }
  }
}

function setsMatch(a, b) {
  if (a.size !== b.size) return false;
  for (const id of a) if (!b.has(id)) return false;
  return true;
}

const studentFinite = new Set(data["o-prototype:titus:finite-verb-marks"]);
const studentImperative = new Set(data["roots:titus:brick2:mood:imperativeCandidates"]);
const studentIndicative = new Set(data["roots:titus:brick2c:mood:statementCandidates"]);
const studentSubjunctive = new Set(data["roots:titus:brick3:mood:subjunctiveCandidates"]);
const studentOptative = new Set(data["roots:titus:brick3c:mood:optativeCandidates"]);

console.log("Ground truth finite verb count:", finiteIds.size);
console.log("Student finite verb count:", studentFinite.size);
console.log("Brick 1 matches:", setsMatch(studentFinite, finiteIds));
if (!setsMatch(studentFinite, finiteIds)) {
  const missing = [...finiteIds].filter(id => !studentFinite.has(id));
  const extra = [...studentFinite].filter(id => !finiteIds.has(id));
  console.log("  ground truth has but student missing:", missing);
  console.log("  student has but not in ground truth:", extra);
}

console.log("\nGround truth imperative count:", byMood.imperative.size, "| student:", studentImperative.size, "| match:", setsMatch(studentImperative, byMood.imperative));
console.log("Ground truth indicative count:", byMood.indicative.size, "| student:", studentIndicative.size, "| match:", setsMatch(studentIndicative, byMood.indicative));
console.log("Ground truth subjunctive count:", byMood.subjunctive.size, "| student:", studentSubjunctive.size, "| match:", setsMatch(studentSubjunctive, byMood.subjunctive));
console.log("Ground truth optative count:", byMood.optative.size, "| student:", studentOptative.size, "| match:", setsMatch(studentOptative, byMood.optative));

if (!setsMatch(studentImperative, byMood.imperative)) {
  console.log("  imperative missing:", [...byMood.imperative].filter(id => !studentImperative.has(id)));
  console.log("  imperative extra:", [...studentImperative].filter(id => !byMood.imperative.has(id)));
}
if (!setsMatch(studentIndicative, byMood.indicative)) {
  console.log("  indicative missing:", [...byMood.indicative].filter(id => !studentIndicative.has(id)));
  console.log("  indicative extra:", [...studentIndicative].filter(id => !byMood.indicative.has(id)));
}
if (!setsMatch(studentSubjunctive, byMood.subjunctive)) {
  console.log("  subjunctive missing:", [...byMood.subjunctive].filter(id => !studentSubjunctive.has(id)));
  console.log("  subjunctive extra:", [...studentSubjunctive].filter(id => !byMood.subjunctive.has(id)));
}

await server.close();
