import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  buildTranslatePrompt,
  validateDraftAgainstGates
} from "../src/pipeline/assistGates.js";
import { analyzePhraseGates, loadLemmaPolicyIndex } from "../src/pipeline/analyzeGates.js";

const mechanical = "y será en día él no sa luz temer se cuajarán";
const hebrewAnalysis = {
  reference: "Zechariah 14:6",
  greek: "וְהָיָה בַיּוֹם הַהוּא לֹא יִהְיֶה אוֹר יְקָרוֹת יִקְפָּאוּן",
  readyForSynthesis: true,
  gates: {
    morphology: { constraints: [{ greek: "יִקְפָּאוּן", strongs: "H7087", morphology: "HVqi3mp" }] },
    lemma: { tokens: [] },
    immediateContext: { structure: { notes: [] } },
    generalContext: { notes: [], verseWindow: [], scope: [] },
    rv1909Review: { flags: [] }
  },
  mechanicalDraft: { proposedSpanish: mechanical, template: "{source words}" }
};

test("rejects an exact copy of the Zechariah mechanical gloss stream", () => {
  const result = validateDraftAgainstGates(mechanical, hebrewAnalysis);
  assert.equal(result.ok, false);
  assert.match(result.flags.join(" "), /copies the mechanical gloss stream/i);
});

test("rejects a lightly rearranged mechanical gloss stream", () => {
  const result = validateDraftAgainstGates("Y en día él será, no luz; se cuajarán", hebrewAnalysis);
  assert.equal(result.ok, false);
  assert.match(result.flags.join(" "), /light rearrangement|mechanical gloss stream/i);
});

test("does not reject distinct grammatical Spanish merely for using source vocabulary", () => {
  const result = validateDraftAgainstGates(
    "Y sucederá que en aquel día no habrá luz; las luminarias se congelarán.",
    hebrewAnalysis
  );
  assert.equal(result.ok, true);
});

test("Hebrew source produces a Hebrew/Aramaic prompt, not a Greek-only prompt", () => {
  const prompt = buildTranslatePrompt({ analysis: hebrewAnalysis, rulesMarkdown: "", rv1909Text: "" });
  assert.match(prompt, /Hebrew\/Aramaic phrase/);
  assert.match(prompt, /Translate FROM the Hebrew\/Aramaic source/);
  assert.match(prompt, /Translate the spine token/);
  assert.doesNotMatch(prompt, /Produce one modern Spanish rendering for this Greek phrase/);
});

test("rejects Ollama output that invents a source word and a divine title", () => {
  const result = validateDraftAgainstGates(
    "y será un solo día en que el Señor lo conocerá, no habrá luz, se cuajarán las sombras",
    hebrewAnalysis,
    ["Se traduce 'יִוּדַ֥ע' como 'lo conocerá'."]
  );
  assert.equal(result.ok, false);
  assert.match(result.flags.join(" "), /not present in this phrase/i);
  assert.match(result.flags.join(" "), /title absent from the selected source tokens/i);
});

test("unused qere inventories do not enter blockingReferences", async () => {
  const rootDir = await mkdtemp(join(tmpdir(), "lbf-inv-"));
  try {
    const sourceInv = join(rootDir, "investigations", "fixturebook", "INV-99-0001");
    const lemmaInv = join(rootDir, "investigations", "fixturebook", "INV-99-0002");
    await mkdir(sourceInv, { recursive: true });
    await mkdir(lemmaInv, { recursive: true });
    await writeFile(join(sourceInv, "README.md"), [
      "Status: Open",
      "Release-Blocking: Yes",
      "References: Fixturebook 1:1",
      ""
    ].join("\n"));
    await writeFile(join(sourceInv, "decision.md"), [
      "## Version 1.0",
      "Status: Open",
      "Release-Blocking: Yes",
      ""
    ].join("\n"));
    await writeFile(join(lemmaInv, "README.md"), [
      "Status: Open",
      "Release-Blocking: Yes",
      "References: Fixturebook 2:2",
      ""
    ].join("\n"));
    await writeFile(join(lemmaInv, "decision.md"), [
      "## Version 1.0",
      "Status: Open",
      "Release-Blocking: Yes",
      "Lemma: מלך",
      "Strong's: H4428",
      ""
    ].join("\n"));

    const index = await loadLemmaPolicyIndex(rootDir, "fixturebook");
    assert.deepEqual(
      index.blockingReferences.map(item => item.investigationId),
      ["INV-99-0002"]
    );
    assert.equal(index.blockingReferences[0].references.includes("Fixturebook 2:2"), true);
  } finally {
    await rm(rootDir, { recursive: true, force: true });
  }
});

test("Zechariah 14:6 is not blocked by the unused-qere inventory", async () => {
  const analysis = await analyzePhraseGates({
    rootDir: process.cwd(),
    bookId: "zechariah",
    reference: "Zechariah 14:6",
    greek: hebrewAnalysis.greek,
    tokenRows: [{
      sourceTokenId: "h38014006008",
      greek: "יקפאו/ן",
      lemma: "7087 b",
      strongs: "H7087",
      rmac: "HVqi3mp/Sn",
      ble: "se cuajarán"
    }]
  });

  assert.notEqual(analysis.gates.lemma.blockReason, "source-variant");
  assert.notEqual(analysis.gates.lemma.investigationId, "INV-38-0001");
  assert.notEqual(analysis.gates.lemma.status, "blocked");
});
