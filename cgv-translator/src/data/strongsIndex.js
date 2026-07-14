/**
 * Lemma → Strong's lookup from MNA grc_lemma_strongs.json (+ accent-insensitive fallback).
 */
import { readFile } from "node:fs/promises";
import { join } from "node:path";

let cachePromise = null;

function stripGreekAccents(text = "") {
  return String(text || "")
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase();
}

export async function loadStrongsIndex(rootDir) {
  if (cachePromise) return cachePromise;
  cachePromise = (async () => {
    const candidates = [
      join(rootDir, "..", "MNA", "datasets", "rules", "grc_lemma_strongs.json"),
      join(rootDir, "..", "MNA", "datasets", "rules", "grc_lemma_strongs_supplement.json")
    ];
    const byLemma = new Map();
    const byFolded = new Map();

    for (const path of candidates) {
      const raw = await readFile(path, "utf8").catch(() => "");
      if (!raw) continue;
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        continue;
      }
      if (!data || typeof data !== "object") continue;
      for (const [lemma, strongs] of Object.entries(data)) {
        const sid = String(strongs || "").trim().toUpperCase();
        if (!sid.startsWith("G")) continue;
        if (!byLemma.has(lemma)) byLemma.set(lemma, sid);
        const folded = stripGreekAccents(lemma);
        if (folded && !byFolded.has(folded)) byFolded.set(folded, sid);
      }
    }

    return { byLemma, byFolded };
  })();
  return cachePromise;
}

export async function strongsForLemma(rootDir, lemma) {
  const index = await loadStrongsIndex(rootDir);
  const exact = index.byLemma.get(lemma);
  if (exact) return exact;
  return index.byFolded.get(stripGreekAccents(lemma)) || "";
}

export function clearStrongsIndexCache() {
  cachePromise = null;
}
