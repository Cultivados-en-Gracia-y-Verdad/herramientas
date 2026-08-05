#!/usr/bin/env node
/**
 * Smoke tests for Hebrew usage popups (OT tokens index + markup enrichment).
 * Run: node scripts/test-hebrew-usage.js
 */
const assert = require("assert");
const path = require("path");

const root = path.join(__dirname, "..");
const {
  ensureHebrewUsageIndex,
  lookupHebrewUsage,
  describeHebrewForm,
  describeOshbMorphology,
  normalizeHebrew
} = require(path.join(root, "hebrewUsage"));

let failed = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`ok  - ${name}`);
  } catch (error) {
    failed += 1;
    console.error(`FAIL - ${name}`);
    console.error(`     ${error.message}`);
  }
}

const index = ensureHebrewUsageIndex(root);
check("OT tokens index loads", () => {
  assert.ok(index.tokensDir, "tokensDir missing");
  assert.ok(index.surfaceToLemma.size > 1000, "too few surface forms");
});

check("Hebrew normalize strips vowels", () => {
  assert.strictEqual(normalizeHebrew("בָּרָ֣א"), normalizeHebrew("ברא"));
});

check("OSHB morphology labels include stem/aspect", () => {
  const desc = describeOshbMorphology("HVqp3ms");
  assert.match(desc, /verbo/);
  assert.match(desc, /qal/);
  assert.match(desc, /perfecto/);
  assert.match(desc, /3/);
});

check("ברא → Spanish + same morphology", () => {
  const usage = lookupHebrewUsage("ברא", { presenterRootDir: root });
  assert.ok(usage, "lookup failed");
  assert.ok(usage.spanishLabel, "missing spanishLabel");
  assert.ok(usage.morphologyMatch, "expected morphologyMatch");
  assert.ok(usage.morphologyDescription.includes("verbo") || usage.morphologyDescription.includes("qal"));
  assert.ok(usage.occurrences.length >= 1);
  assert.ok(usage.occurrences.length <= 12);
});

check("אֱלֹהִים resolves in OT index", () => {
  const usage = lookupHebrewUsage("אֱלֹהִים", { presenterRootDir: root });
  assert.ok(usage, "אלהים lookup failed");
  assert.ok(usage.spanishLabel, "missing spanishLabel for אלהים");
});

check("high-frequency forms are capped at 12", () => {
  const usage = lookupHebrewUsage("יהוה", { presenterRootDir: root });
  assert.ok(usage, "יהוה lookup failed");
  assert.ok(usage.count > 12, "expected many יהוה hits");
  assert.strictEqual(usage.occurrences.length, 12);
  assert.ok(usage.occurrences.every(item => item.morphology === usage.morphology));
});

const { spawn } = require("child_process");
const http = require("http");

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let body = "";
      res.on("data", chunk => { body += chunk; });
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode, json: JSON.parse(body) });
        } catch (error) {
          reject(error);
        }
      });
    }).on("error", reject);
  });
}

async function runHttpTests() {
  const port = 3458;
  const child = spawn(process.execPath, [path.join(root, "server.js")], {
    cwd: root,
    env: { ...process.env, PORT: String(port) },
    stdio: ["ignore", "pipe", "pipe"]
  });

  let ready = false;
  const boot = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("server boot timeout")), 30000);
    const onData = chunk => {
      const text = String(chunk);
      if (/running at/i.test(text)) {
        ready = true;
        clearTimeout(timer);
        resolve();
      }
    };
    child.stdout.on("data", onData);
    child.stderr.on("data", onData);
    child.on("exit", code => {
      if (!ready) {
        clearTimeout(timer);
        reject(new Error(`server exited early: ${code}`));
      }
    });
  });

  try {
    await boot;

    const created = await getJson(`http://127.0.0.1:${port}/hebrew/usage?surface=${encodeURIComponent("ברא")}`);
    check("/hebrew/usage ברא", () => {
      assert.strictEqual(created.status, 200);
      assert.ok(created.json.found);
      assert.ok(created.json.spanishLabel);
      assert.ok(created.json.popupHtml.includes("greek-usage-spanish") || created.json.popupHtml.includes(created.json.spanishLabel));
      assert.ok(created.json.popupHtml.includes("Misma morfología") || created.json.popupHtml.includes("Usos similares"));
      assert.ok(created.json.verseCount <= 12);
      assert.ok(created.json.matchCount >= created.json.verseCount);
    });

    check("/hebrew/usage header is Spanish — Hebrew (lemma) + Uso", () => {
      assert.match(created.json.popupHtml, /greek-usage-title/i);
      assert.match(created.json.popupHtml, /greek-usage-spanish/i);
      assert.match(created.json.popupHtml, /hebrew-surface/i);
      assert.match(created.json.popupHtml, /greek-usage-lemma/i);
      assert.match(created.json.popupHtml, /greek-usage-use-label">Uso/i);
    });

    check("/hebrew/usage names Bible version under verse", () => {
      assert.ok(created.json.bibleVersion, "expected bibleVersion on payload");
      assert.ok(
        /greek-occurrence-bible/i.test(created.json.popupHtml),
        "expected Bible version under occurrence verse"
      );
      assert.match(String(created.json.bibleVersion), /\bBLE\b/, `expected BLE study text, got ${created.json.bibleVersion}`);
      assert.match(created.json.popupHtml, /greek-occurrence-bible">BLE</i);
    });

    check("/hebrew/usage shows BLE translation glosses", () => {
      assert.match(created.json.popupHtml, /greek-translation-summary/i);
      assert.match(created.json.popupHtml, /greek-translation-label">BLE/i);
    });

    const elohim = await getJson(`http://127.0.0.1:${port}/hebrew/usage?surface=${encodeURIComponent("אלהים")}`);
    check("/hebrew/usage אלהים highlights Dios", () => {
      assert.ok(elohim.json.found);
      assert.match(String(elohim.json.spanishLabel || ""), /dios/i);
      const marked = [...String(elohim.json.popupHtml || "").matchAll(/<mark class="greek-usage-hit">([^<]*)<\/mark>/gi)]
        .map(match => match[1].toLowerCase());
      assert.ok(marked.length > 0, "expected at least one highlighted Spanish equivalent");
      assert.ok(marked.some(text => /dios/.test(text)), `expected Dios highlight, got: ${marked.join(", ")}`);
    });

    const missing = await getJson(`http://127.0.0.1:${port}/hebrew/usage?surface=${encodeURIComponent("zzzzz")}`);
    check("/hebrew/usage missing form returns fallback payload", () => {
      assert.strictEqual(missing.status, 200);
      assert.strictEqual(missing.json.found, false);
      assert.match(missing.json.popupHtml, /no encontrada/i);
    });

    const enrich = await getJson(`http://127.0.0.1:${port}/bible/test?text=${encodeURIComponent("En el principio (ברא) Dios")}`);
    check("enrich wraps Hebrew parenthetical as hebrew-ref", () => {
      assert.match(enrich.json.html, /hebrew-ref/i);
      assert.match(enrich.json.html, /data-popup-dynamic="hebrew"/i);
      assert.match(enrich.json.html, /data-hebrew-surface="/i);
    });
  } finally {
    child.kill();
  }
}

runHttpTests()
  .then(() => {
    if (failed) {
      console.error(`\n${failed} Hebrew usage smoke test(s) failed.`);
      process.exit(1);
    }
    console.log("\nAll Hebrew usage smoke tests passed.");
  })
  .catch(error => {
    console.error(error);
    process.exit(1);
  });
