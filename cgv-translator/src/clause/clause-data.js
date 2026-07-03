import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { getCgvDataPath } from "../data/cgvData.js";

const rootDir = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const WORD_PATTERN = /[\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\s\wáéíóúüñÁÉÍÓÚÜÑ]+/gu;

const FINITE_ANCHOR_OVERRIDES = {
  "1:5:12": { text: "designaras" },
  "1:10:1": { text: "hay" },
  "1:11:7": { text: "están", occurrence: 1 },
  "1:11:11": { text: "deben" },
  "1:15:13": { text: "están" },
  "2:1:3": { text: "enseña" },
  "2:6:4": { text: "exhorta" },
  "2:14:13": { text: "PURIFICAR" },
  "2:15:4": { text: "exhorta" },
  "2:15:12": { text: "menosprecie" },
  "3:4:8": { text: "manifestó" },
  "3:5:8": { text: "hubiéramos" },
  "3:7:7": { text: "fuéramos" },
  "3:8:19": { text: "es" },
  "3:14:15": { text: "estén" }
};

function resolveMnaTokensPath() {
  const candidates = [
    resolve(rootDir, "../MNA/datasets/interlinear/NT/tito.tokens.jsonl"),
    resolve(getCgvDataPath(), "../MNA/datasets/interlinear/NT/tito.tokens.jsonl"),
    resolve(rootDir, "../../MNA/datasets/interlinear/NT/tito.tokens.jsonl")
  ];
  return candidates.find(path => existsSync(path)) || candidates[0];
}

function parseNblaContent(content) {
  const verses = [];
  for (const line of content.replace(/\r\n/g, "\n").split("\n")) {
    const match =
      line.match(/^(.+?)\s+(\d+):(\d+)\s+(.+)$/) ||
      line.match(/^#+\s*(.+?)\s+(\d+):(\d+)\s*$/);
    if (!match) continue;
    const book = match[1].trim();
    const chapter = Number(match[2]);
    const verse = Number(match[3]);
    const text = (match[4] || "").trim();
    if (!book || !chapter || !verse) continue;
    verses.push({ book, chapter, verse, text });
  }
  return verses;
}

function wordId(chapter, verse, index) {
  return `${chapter}:${verse}:${index}`;
}

function finiteAlignmentId(chapter, verse, token) {
  return `${chapter}:${verse}:${token}`;
}

function normalize(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");
}

function spanishHintParts(value) {
  return String(value || "")
    .replace(/·/g, " ")
    .split(/\s+/)
    .map(normalize)
    .filter(Boolean);
}

function tokenizeVerse(verse) {
  const words = [];
  let index = 0;
  const pattern = new RegExp(WORD_PATTERN.source, WORD_PATTERN.flags);

  for (let match = pattern.exec(verse.text); match; match = pattern.exec(verse.text)) {
    const piece = match[0];
    if (!/[\wáéíóúüñÁÉÍÓÚÜÑ]/i.test(piece)) continue;
    words.push({
      id: wordId(verse.chapter, verse.verse, index),
      chapter: verse.chapter,
      verse: verse.verse,
      index,
      text: piece,
      finiteVerbId: null,
      greekSurface: null,
      greekMorph: null,
      startChar: match.index,
      endChar: match.index + piece.length
    });
    index += 1;
  }

  return words;
}

function parseFiniteAlignments(raw) {
  return raw
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map(line => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .filter(row => {
      return (
        row.book === "tito" &&
        typeof row.ch === "number" &&
        typeof row.vs === "number" &&
        typeof row.tok === "number" &&
        typeof row.surface === "string" &&
        typeof row.morph === "string" &&
        typeof row.es === "string" &&
        /^V-[123]/.test(row.morph)
      );
    })
    .map(row => ({
      id: finiteAlignmentId(row.ch, row.vs, row.tok),
      chapter: row.ch,
      verse: row.vs,
      token: row.tok,
      greekSurface: row.surface,
      greekMorph: row.morph,
      spanishHint: row.es
    }));
}

function findAnchorIndex(alignment, words, cursor) {
  const override = FINITE_ANCHOR_OVERRIDES[alignment.id];
  if (override) {
    const wanted = normalize(override.text);
    const matches = words.filter(word => normalize(word.text) === wanted);
    return matches[override.occurrence ?? 0]?.index ?? -1;
  }

  const parts = spanishHintParts(alignment.spanishHint);
  for (const part of parts) {
    const exact = words.find(word => word.index >= cursor && normalize(word.text) === part);
    if (exact) return exact.index;
  }

  for (const part of parts) {
    if (part.length < 4) continue;
    const soft = words.find(word => {
      if (word.index < cursor) return false;
      const text = normalize(word.text);
      return text.startsWith(part.slice(0, 4)) || part.startsWith(text.slice(0, 4));
    });
    if (soft) return soft.index;
  }

  return -1;
}

export async function loadTitusClauseVerses() {
  const nblaPath = join(getCgvDataPath(), "bibles/NBLA/tito.nbla.md");
  const nblaContent = await readFile(nblaPath, "utf8");
  const tokensPath = resolveMnaTokensPath();
  const tokensContent = await readFile(tokensPath, "utf8").catch(() => "");

  const verses = parseNblaContent(nblaContent).map(verse => ({
    chapter: verse.chapter,
    verse: verse.verse,
    label: `Tito ${verse.chapter}:${verse.verse}`,
    text: verse.text,
    words: tokenizeVerse(verse)
  }));

  const verseByKey = new Map(verses.map(verse => [`${verse.chapter}:${verse.verse}`, verse]));
  const cursors = new Map();

  for (const alignment of parseFiniteAlignments(tokensContent)) {
    const key = `${alignment.chapter}:${alignment.verse}`;
    const verse = verseByKey.get(key);
    if (!verse) continue;
    const anchorIndex = findAnchorIndex(alignment, verse.words, cursors.get(key) ?? 0);
    if (anchorIndex < 0) continue;
    const anchor = verse.words[anchorIndex];
    anchor.finiteVerbId = alignment.id;
    anchor.greekSurface = alignment.greekSurface;
    anchor.greekMorph = alignment.greekMorph;
    cursors.set(key, anchor.index + 1);
  }

  return verses;
}
