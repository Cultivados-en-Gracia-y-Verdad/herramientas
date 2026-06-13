import type { BibleIndex } from "./types";

export interface InlineBibleMatch {
  start: number;
  end: number;
  reference: string;
  book: string;
  referenceList: string;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildInlineReferencePattern(index: BibleIndex): RegExp | null {
  if (!index.bookPatterns.length) return null;

  const bookPattern = index.bookPatterns.map(escapeRegExp).join("|");
  return new RegExp(
    `\\b(${bookPattern})\\s+((?:\\d{1,3}(?::\\d{1,3})?(?:[-–](?:(?:\\d{1,3}:)?\\d{1,3}))?)(?:\\s*(?:,|y)\\s*(?:(?:\\d{1,3}:)?\\d{1,3})(?:[-–](?:(?:\\d{1,3}:)?\\d{1,3}))?)*)`,
    "gi"
  );
}

export function findInlineBibleReferenceMatches(
  text: string,
  index: BibleIndex
): InlineBibleMatch[] {
  const pattern = buildInlineReferencePattern(index);
  if (!pattern || !text) return [];

  const matches: InlineBibleMatch[] = [];

  for (const match of text.matchAll(pattern)) {
    if (match.index === undefined) continue;

    matches.push({
      start: match.index,
      end: match.index + match[0].length,
      reference: match[0],
      book: match[1],
      referenceList: match[2]
    });
  }

  return matches;
}

export function getInlineBibleReferenceAtPosition(
  text: string,
  offset: number,
  index: BibleIndex
): InlineBibleMatch | null {
  if (offset < 0) return null;

  return (
    findInlineBibleReferenceMatches(text, index).find(
      match => offset >= match.start && offset < match.end
    ) ?? null
  );
}
