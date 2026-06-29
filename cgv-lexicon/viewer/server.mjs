#!/usr/bin/env node
/**
 * ROOTS Lexicon viewer — local dev server.
 *
 *   GET /lexicon/greek              browse Greek verbs
 *   GET /lexicon/greek/:lemma       observation page
 *   GET /lexicon/hebrew             browse Hebrew lemmas (gloss index)
 *   GET /api/lexicon/greek/index    phase-1 lemma list
 *   GET /api/lexicon/greek/:lemma   phase-1 observation JSON
 *   GET /api/lexicon/hebrew/index   gloss lemma list
 *   GET /api/lexicon/hebrew/:lemma  gloss entry JSON
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const GREEK_DIR = join(ROOT, "data", "lexicon", "phase1", "greek");
const GRC_ENTRIES = join(ROOT, "data", "grc.entries.jsonl");
const HBO_ENTRIES = join(ROOT, "data", "hbo.entries.jsonl");
const VIEWER_DIR = __dirname;
const PORT = Number(process.env.PORT || 4177);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

let greekIndexCache = null;
let hebrewIndexCache = null;

function normalizeLemma(s) {
  return decodeURIComponent(s).normalize("NFC").trim();
}

async function readJsonFile(path) {
  const text = await readFile(path, "utf8");
  return JSON.parse(text);
}

async function loadGreekIndex() {
  if (greekIndexCache) return greekIndexCache;
  const indexPath = join(GREEK_DIR, "index.json");
  if (!existsSync(indexPath)) return null;
  greekIndexCache = await readJsonFile(indexPath);
  return greekIndexCache;
}

async function readGreekLemma(lemma) {
  const normalized = normalizeLemma(lemma);
  const path = join(GREEK_DIR, `${normalized}.json`);
  if (existsSync(path)) return readFile(path, "utf8");
  const index = await loadGreekIndex();
  if (!index) return null;
  const hit = (index.lemmas || []).find((e) => e.lemma === normalized);
  if (!hit) return null;
  const alt = join(GREEK_DIR, hit.file);
  if (!existsSync(alt)) return null;
  return readFile(alt, "utf8");
}

async function loadJsonlEntries(path) {
  if (!existsSync(path)) return [];
  const text = await readFile(path, "utf8");
  return text
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

async function loadHebrewIndex() {
  if (hebrewIndexCache) return hebrewIndexCache;
  const entries = await loadJsonlEntries(HBO_ENTRIES);
  hebrewIndexCache = {
    language: "hebrew",
    scope: "gloss",
    lemma_count: entries.length,
    lemmas: entries.map((e) => ({
      lemma: e.lemma,
      gloss_es: e.gloss_es || null,
      strongs: e.strongs || null,
      observation: false,
    })),
  };
  return hebrewIndexCache;
}

async function readHebrewLemma(lemma) {
  const normalized = normalizeLemma(lemma);
  const entries = await loadJsonlEntries(HBO_ENTRIES);
  const hit = entries.find((e) => e.lemma === normalized);
  if (!hit) return null;
  return JSON.stringify({
    lemma: hit.lemma,
    language: "hebrew",
    gloss_es: hit.gloss_es || null,
    strongs: hit.strongs || null,
    observation: false,
    definition_phase2: null,
    definition_status: "not_started",
  });
}

function send(res, status, body, type = "text/plain; charset=utf-8") {
  res.writeHead(status, { "Content-Type": type });
  res.end(body);
}

async function sendJson(res, status, data) {
  send(res, status, JSON.stringify(data), "application/json; charset=utf-8");
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);
    const pathname = decodeURIComponent(url.pathname);

    if (req.method !== "GET") {
      send(res, 405, "Method not allowed");
      return;
    }

    if (pathname === "/api/health") {
      const greekIndex = await loadGreekIndex();
      await sendJson(res, 200, {
        ok: true,
        greek_observation: Boolean(greekIndex?.lemma_count),
        greek_lemmas: greekIndex?.lemma_count || 0,
        hebrew_gloss: existsSync(HBO_ENTRIES),
      });
      return;
    }

    if (pathname === "/api/lexicon/greek/index") {
      const index = await loadGreekIndex();
      if (!index) {
        await sendJson(res, 503, {
          error: "Greek observation data not built. Run: npm run build:lexicon-phase1",
        });
        return;
      }
      send(res, 200, JSON.stringify(index), "application/json; charset=utf-8");
      return;
    }

    const greekApi = pathname.match(/^\/api\/lexicon\/greek\/(.+)$/);
    if (greekApi) {
      const json = await readGreekLemma(greekApi[1]);
      if (!json) {
        await sendJson(res, 404, { error: "lemma not found", lemma: normalizeLemma(greekApi[1]) });
        return;
      }
      send(res, 200, json, "application/json; charset=utf-8");
      return;
    }

    if (pathname === "/api/lexicon/hebrew/index") {
      const index = await loadHebrewIndex();
      if (!index.lemmas.length) {
        await sendJson(res, 503, {
          error: "Hebrew gloss data not built. Run: npm run build:lexicon",
        });
        return;
      }
      send(res, 200, JSON.stringify(index), "application/json; charset=utf-8");
      return;
    }

    const hebrewApi = pathname.match(/^\/api\/lexicon\/hebrew\/(.+)$/);
    if (hebrewApi) {
      const json = await readHebrewLemma(hebrewApi[1]);
      if (!json) {
        await sendJson(res, 404, { error: "lemma not found", lemma: normalizeLemma(hebrewApi[1]) });
        return;
      }
      send(res, 200, json, "application/json; charset=utf-8");
      return;
    }

    if (pathname === "/viewer.js" || pathname === "/viewer.css") {
      const file = pathname.slice(1);
      const body = await readFile(join(VIEWER_DIR, file));
      const ext = file.slice(file.lastIndexOf("."));
      send(res, 200, body, MIME[ext]);
      return;
    }

    // SPA shell for all UI routes (must use the dev server — not file://)
    const html = await readFile(join(VIEWER_DIR, "index.html"));
    send(res, 200, html, MIME[".html"]);
  } catch (err) {
    send(res, 500, String(err));
  }
});

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`Port ${PORT} is already in use. Try: PORT=${PORT + 1} npm run serve:lexicon`);
  } else {
    console.error(err);
  }
  process.exit(1);
});

server.listen(PORT, async () => {
  const greekIndex = await loadGreekIndex();
  console.log("ROOTS Lexicon viewer");
  console.log(`  Home:   http://localhost:${PORT}/lexicon`);
  if (greekIndex?.lemma_count) {
    console.log(`  Greek:  http://localhost:${PORT}/lexicon/greek  (${greekIndex.lemma_count} verbs)`);
    console.log(`  Sample: http://localhost:${PORT}/lexicon/greek/${encodeURIComponent("ἀγαπάω")}`);
  } else {
    console.warn("  Greek observation data missing — run: npm run build:lexicon-phase1");
  }
  if (existsSync(HBO_ENTRIES)) {
    console.log(`  Hebrew: http://localhost:${PORT}/lexicon/hebrew`);
  }
  console.log("\n  Open the URLs above in a browser (do not open index.html as a file).");
});
