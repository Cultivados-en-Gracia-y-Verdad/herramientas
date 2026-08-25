#!/usr/bin/env node
/**
 * Smoke tests for Greek usage popups (lookup + markup enrichment).
 * Run: node scripts/test-greek-usage.js
 */
const assert = require("assert");
const path = require("path");

const root = path.join(__dirname, "..");
const {
  ensureGreekUsageIndex,
  lookupGreekUsage,
  describeGreekForm,
  describeMorphologyCode,
  normalizeGreek
} = require(path.join(root, "greekUsage"));

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

const index = ensureGreekUsageIndex(root);
check("MorphGNT index loads", () => {
  assert.ok(index.morphDir, "morphDir missing");
  assert.ok(index.surfaceToLemma.size > 1000, "too few surface forms");
});

check("diacritic-insensitive normalize", () => {
  assert.strictEqual(normalizeGreek("ἀναγεννήσας"), normalizeGreek("αναγεννησας"));
});

check("declined morphology labels include case/number/gender", () => {
  const desc = describeMorphologyCode("N-NSF");
  assert.match(desc, /sustantivo/);
  assert.match(desc, /nominativo/);
  assert.match(desc, /singular/);
  assert.match(desc, /femenino/);
});

check("ἀναγεννήσας → Spanish + same morphology", () => {
  const usage = lookupGreekUsage("ἀναγεννήσας", { presenterRootDir: root });
  assert.ok(usage, "lookup failed");
  assert.ok(usage.spanishLabel, "missing spanishLabel");
  assert.ok(usage.morphologyMatch, "expected morphologyMatch");
  assert.ok(usage.morphologyDescription.includes("participio"));
  assert.strictEqual(usage.occurrences.length, 1);
});

check("ὅ resolves in MorphGNT index", () => {
  const usage = lookupGreekUsage("ὅ", { presenterRootDir: root });
  assert.ok(usage, "ὅ lookup failed — MorphGNT missing or form absent");
  assert.ok(usage.spanishLabel, "missing spanishLabel for ὅ");
});

check("high-frequency forms are capped at 12", () => {
  const usage = lookupGreekUsage("θεοῦ", { presenterRootDir: root });
  assert.ok(usage);
  assert.ok(usage.count > 12, "expected many genitive θεοῦ hits");
  assert.strictEqual(usage.occurrences.length, 12);
  assert.ok(usage.occurrences.every(item => item.morphology === usage.morphology));
});

check("καί is a connector with footnote id", () => {
  const info = describeGreekForm("καί", root);
  assert.strictEqual(info.footnoteId, "kai");
  assert.ok(info.isConnector);
});

// Markup enrichment needs the live server module helpers. Import carefully:
// requiring server.js starts listening, so we spawn a child for HTTP checks.
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
  const port = 3457;
  const child = spawn(process.execPath, [path.join(root, "server.js")], {
    cwd: root,
    env: { ...process.env, PORT: String(port) },
    stdio: ["ignore", "pipe", "pipe"]
  });

  let ready = false;
  const boot = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("server boot timeout")), 20000);
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

    const love = await getJson(`http://127.0.0.1:${port}/greek/usage?surface=${encodeURIComponent("ἀγάπη")}`);
    check("/greek/usage ἀγάπη", () => {
      assert.strictEqual(love.status, 200);
      assert.ok(love.json.found);
      assert.ok(love.json.spanishLabel);
      assert.ok(love.json.popupHtml.includes("greek-usage-spanish") || love.json.popupHtml.includes(love.json.spanishLabel));
      assert.ok(love.json.popupHtml.includes("Misma morfología") || love.json.popupHtml.includes("Usos similares"));
      assert.ok(love.json.verseCount <= 12);
      assert.ok(love.json.matchCount >= love.json.verseCount);
      assert.ok(
        /<mark class="greek-usage-hit">/i.test(love.json.popupHtml),
        "expected Spanish hit highlight in occurrence verse"
      );
      assert.match(love.json.popupHtml, /Mateo\s+24:12/i);
    });

    const faith = await getJson(`http://127.0.0.1:${port}/greek/usage?surface=${encodeURIComponent("πίστις")}`);
    check("/greek/usage πίστις highlights fe", () => {
      assert.ok(faith.json.found);
      assert.match(String(faith.json.spanishLabel || ""), /fe/i);
      const marked = [...String(faith.json.popupHtml || "").matchAll(/<mark class="greek-usage-hit">([^<]*)<\/mark>/gi)]
        .map(match => match[1].toLowerCase());
      assert.ok(marked.length > 0, "expected at least one highlighted Spanish equivalent");
      assert.ok(marked.some(text => /fe/.test(text)), `expected fe highlight, got: ${marked.join(", ")}`);
    });

    check("/greek/usage header is Spanish — Greek (lemma) + Uso", () => {
      assert.match(love.json.popupHtml, /greek-usage-title/i);
      assert.match(love.json.popupHtml, /greek-usage-spanish/i);
      assert.match(love.json.popupHtml, /greek-usage-greek/i);
      assert.match(love.json.popupHtml, /greek-usage-lemma/i);
      assert.match(love.json.popupHtml, /greek-usage-use-label">Uso/i);
    });

    check("/greek/usage names Bible version under verse", () => {
      assert.ok(love.json.bibleVersion, "expected bibleVersion on payload");
      assert.ok(
        /greek-occurrence-bible/i.test(love.json.popupHtml),
        "expected Bible version under occurrence verse"
      );
      assert.match(String(love.json.bibleVersion), /\b[A-Z0-9]+\b/, `expected Bible version label, got ${love.json.bibleVersion}`);
      assert.match(love.json.popupHtml, new RegExp(`greek-occurrence-bible">${love.json.bibleVersion}`, "i"));
    });

    check("/greek/usage shows BLE and NBLA word glosses", () => {
      assert.match(love.json.popupHtml, /greek-translation-summary/i);
      assert.match(love.json.popupHtml, /greek-translation-label">BLE/i);
      assert.match(love.json.popupHtml, /greek-translation-label">NBLA/i);
      assert.match(love.json.popupHtml, /BLE<\/span>\s*<b>[^<]*amor/i);
      assert.match(love.json.popupHtml, /NBLA<\/span>\s*<b>[^<]*amor/i);
    });

    const koinonia = await getJson(`http://127.0.0.1:${port}/greek/usage?surface=${encodeURIComponent("κοινωνία")}`);
    check("/greek/usage κοινωνία lists multiple NBLA options", () => {
      assert.ok(koinonia.json.found);
      assert.match(koinonia.json.popupHtml, /greek-translation-label">NBLA/i);
      assert.match(koinonia.json.popupHtml, /comunión/i);
      assert.match(koinonia.json.popupHtml, /participaci[oó]n/i);
    });

    const born = await getJson(`http://127.0.0.1:${port}/greek/usage?surface=${encodeURIComponent("ἀναγεννήσας")}`);
    check("/greek/usage ἀναγεννήσας has morph description", () => {
      assert.ok(born.json.found);
      assert.match(born.json.morphologyDescription || "", /participio/);
      assert.ok(born.json.popupHtml.includes("bible-popup-verse"));
    });

    const bible = await getJson(`http://127.0.0.1:${port}/bible/test?text=${encodeURIComponent("renacer (ἀναγεννήσας)[^P] y (καί)")}`);
    check("enrich keeps Greek study link + participle footnote; καί → connector note", () => {
      assert.strictEqual(bible.status, 200);
      const html = bible.json.html;
      assert.ok(html.includes('data-popup-dynamic="greek"'), "greek dynamic link missing");
      assert.ok(html.includes("ἀναγεννήσας"), "greek surface missing");
      assert.ok(html.includes("data-footnote-id") || html.includes("footnote-ref"), "participle footnote missing");
      // καί should become pedagogical footnote, not a usage dump link
      assert.ok(
        /footnote-ref[^>]*>\(καί\)|data-footnote-id="kai"/i.test(html),
        `expected καί connector footnote, got: ${html.slice(0, 500)}`
      );
    });

    const missing = await getJson(`http://127.0.0.1:${port}/greek/usage?surface=${encodeURIComponent("zzzzz")}`);
    check("/greek/usage missing form returns fallback payload", () => {
      assert.strictEqual(missing.status, 200);
      assert.strictEqual(missing.json.found, false);
      assert.ok(missing.json.popupHtml.includes("Forma griega"));
    });
  } finally {
    child.kill("SIGTERM");
  }
}

runHttpTests()
  .then(() => {
    if (failed) {
      console.error(`\n${failed} test(s) failed`);
      process.exit(1);
    }
    console.log("\nAll Greek usage smoke tests passed.");
  })
  .catch(error => {
    console.error(error);
    process.exit(1);
  });
