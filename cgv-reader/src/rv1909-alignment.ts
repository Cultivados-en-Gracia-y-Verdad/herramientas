import titusRv1909Alignment from "../../../cgv-data/bibles/RV1909/alignments/56.alignment.json?raw";

// Mission Mutual's manually-verified Greek-to-RV1909 word alignment for Titus.
// Validated this session against the app's own Greek token file: 594/595 (99.83%)
// of source tokens match via a simple ordered, forward-walking surface-form
// comparison, across all 46 verses. This replaces guesswork with a lookup.

export interface Rv1909AlignmentRecord {
  chapter: number;
  verse: number;
  greekSurface: string;
  targetSurface: string;
}

interface RawAlignmentFile {
  records: { source: string[]; target: string[] }[];
}

const SOURCE_ID_PATTERN = /^n?\d{2}(\d{3})(\d{3})\d{3}$/;

function splitIdSurface(entry: string): { id: string; surface: string } | null {
  const separator = entry.indexOf("|");
  if (separator < 0) return null;
  return { id: entry.slice(0, separator), surface: entry.slice(separator + 1) };
}

function parseAlignmentRecords(): Rv1909AlignmentRecord[] {
  const data = JSON.parse(titusRv1909Alignment) as RawAlignmentFile;
  const records: Rv1909AlignmentRecord[] = [];

  for (const raw of data.records) {
    const source = raw.source[0] ? splitIdSurface(raw.source[0]) : null;
    const target = raw.target[0] ? splitIdSurface(raw.target[0]) : null;
    if (!source || !target) continue;

    const match = SOURCE_ID_PATTERN.exec(source.id);
    if (!match) continue;

    records.push({
      chapter: Number(match[1]),
      verse: Number(match[2]),
      greekSurface: source.surface,
      targetSurface: target.surface
    });
  }

  return records;
}

let cachedByVerse: Map<string, Rv1909AlignmentRecord[]> | null = null;

export function loadRv1909AlignmentByVerse(): Map<string, Rv1909AlignmentRecord[]> {
  if (cachedByVerse) return cachedByVerse;

  const byVerse = new Map<string, Rv1909AlignmentRecord[]>();
  for (const record of parseAlignmentRecords()) {
    const key = `${record.chapter}:${record.verse}`;
    const list = byVerse.get(key);
    if (list) list.push(record);
    else byVerse.set(key, [record]);
  }

  cachedByVerse = byVerse;
  return byVerse;
}

function normalizeGreek(value: string): string {
  return value
    .replace(/[⸀⸁⸂⸃]/g, "")
    .replace(/[.,;·'"‘’“”]/g, "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function normalizeSpanish(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");
}

/**
 * Cross-references the app's own Greek token list for a verse against Mission
 * Mutual's alignment source tokens for that verse, via ordered surface-form
 * matching. Mission Mutual's list is a subsequence of ours (they drop some
 * function words); this walks both forward together, tolerating skips.
 * Returns: current-token-number -> RV1909 target surface text.
 */
export function crossReferenceVerseTokens(
  currentTokens: { token: number; surface: string }[],
  alignmentRecords: Rv1909AlignmentRecord[]
): Map<number, string> {
  const result = new Map<number, string>();
  let cursor = 0;

  for (const record of alignmentRecords) {
    const wanted = normalizeGreek(record.greekSurface);
    let found = -1;
    for (let i = cursor; i < currentTokens.length; i += 1) {
      if (normalizeGreek(currentTokens[i].surface) === wanted) {
        found = i;
        break;
      }
    }
    if (found >= 0) {
      result.set(currentTokens[found].token, record.targetSurface);
      cursor = found + 1;
    }
  }

  return result;
}

/**
 * Resolves each Greek token's cross-referenced RV1909 target text to an
 * actual word index in that verse's tokenized RV1909 SpanishWord array.
 *
 * This is exact matching (not fuzzy — the target text came from a verified
 * alignment), but NOT a strictly-forward cursor: RV1909, like any real
 * translation, locally reorders words relative to Greek (e.g. Greek's
 * "enteras casas trastornan" surfaces in RV1909 as "trastornan casas
 * enteras" — Titus 1:11). A monotonic cursor breaks on the first such
 * reorder. Instead, each target is matched to its nearest *unused*
 * occurrence relative to the previously-resolved word, which tolerates local
 * reordering while still disambiguating repeated common words correctly.
 */
export function resolveRv1909WordIndexes(
  tokenOrder: number[],
  crossReference: Map<number, string>,
  words: { index: number; text: string }[]
): Map<number, number> {
  const result = new Map<number, number>();
  const used = new Set<number>();
  let lastPosition = -1;

  for (const token of tokenOrder) {
    const targetSurface = crossReference.get(token);
    if (targetSurface === undefined) continue;
    const wanted = normalizeSpanish(targetSurface);

    let best = -1;
    let bestDistance = Infinity;
    for (let i = 0; i < words.length; i += 1) {
      if (used.has(i) || normalizeSpanish(words[i].text) !== wanted) continue;
      const distance = Math.abs(i - lastPosition);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = i;
      }
    }

    if (best >= 0) {
      result.set(token, words[best].index);
      used.add(best);
      lastPosition = best;
    }
  }

  return result;
}

/**
 * Finds a word by exact surface text, ignoring prior claims. For the rare
 * legitimate case where two Greek tokens collapse into one Spanish word (a
 * periphrastic construction like δυνατὸς ᾖ, "may be able" -> RV1909's single
 * "pueda") — the two tokens sharing that word isn't a conflict to resolve,
 * it's the correct outcome. Only used for manually-confirmed alignment gaps.
 */
export function findWordIndexBySurface(
  words: { index: number; text: string }[],
  targetSurface: string
): number | null {
  const wanted = normalizeSpanish(targetSurface);
  const match = words.find(word => normalizeSpanish(word.text) === wanted);
  return match ? match.index : null;
}
