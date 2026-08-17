import test from "node:test";
import assert from "node:assert/strict";

import { getGreekOccurrencesByStrongs, getHebrewOccurrencesByStrongs } from "../src/data/cgvData.js";

test("Hebrew occurrence evidence includes available OT historical witnesses", async () => {
  const report = await getHebrewOccurrencesByStrongs("H4428", { lemma: "מֶֽלֶךְ" });
  const daniel = report.occurrences.find(occurrence => occurrence.reference === "Daniel 1:1");

  assert.ok(daniel, "expected a Daniel 1:1 occurrence for H4428");
  assert.match(daniel.translations.rv1862, /RV1862 source is NT-only/);
  assert.match(daniel.translations.rv1909, /Joacim/);
  assert.match(daniel.translations.spnbes, /Joacim/);
  assert.match(daniel.translations.spnvbl, /Joaqu[ií]n/);
});

test("Greek occurrence evidence still includes NT historical witnesses", async () => {
  const report = await getGreekOccurrencesByStrongs("G1401", { lemma: "δοῦλος" });
  const matthew = report.occurrences.find(occurrence => occurrence.reference === "Matthew 8:9");

  assert.ok(matthew, "expected a Matthew 8:9 occurrence for G1401");
  assert.match(matthew.translations.rv1862, /siervo/);
  assert.match(matthew.translations.rv1909, /siervo/);
  assert.match(matthew.translations.spnbes, /sirviente/);
  assert.match(matthew.translations.spnvbl, /siervo/);
});

test("Hebrew occurrence evidence keeps H7087 lexical senses separate", async () => {
  const report = await getHebrewOccurrencesByStrongs("H7087", { lemma: "7087 b" });

  assert.equal(report.occurrences.length, 2);
  assert.ok(report.occurrences.every(occurrence => occurrence.reference === "Zechariah 14:6"));
  assert.deepEqual(
    report.occurrences.map(occurrence => occurrence.gloss),
    ["se·cuajarán", "y·congelación"]
  );
  assert.equal(report.occurrences[0].historicalFocus.spnbes, "");
  assert.equal(report.occurrences[0].historicalFocus.spnvbl, "");
  assert.equal(report.occurrences[1].historicalFocus.rv1909, "ni");
  assert.match(report.occurrences[1].translations.rv1909, /\*\*ni\*\*/u);
  assert.doesNotMatch(report.occurrences[1].translations.spnbes, /\*\*/u);
  assert.doesNotMatch(report.occurrences[1].translations.spnvbl, /\*\*/u);
});
