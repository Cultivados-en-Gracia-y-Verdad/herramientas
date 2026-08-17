import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

import { loadNtBookUnits } from "../src/data/morphLoader.js";

const rootDir = fileURLToPath(new URL("../", import.meta.url));

test("Zechariah OSHB tokens receive their deterministic Spanish glosses", async () => {
  const loaded = await loadNtBookUnits(rootDir, "zechariah");
  const firstVerse = loaded.units.find(unit => unit.reference === "Zechariah 1:1");

  assert.ok(firstVerse, "expected Zechariah 1:1");
  assert.equal(firstVerse.tokenRows.length, 16);
  assert.ok(firstVerse.tokenRows.every(row => row.ble), "every controlled source token should have a gloss");
  assert.equal(firstVerse.tokenRows[0].oshbId, "38xeN");
  assert.equal(firstVerse.tokenRows[0].ble, "en•mes");
});
