export interface TextMatch {
  start: number;
  end: number;
}

export function findAllInText(
  text: string,
  query: string,
  caseSensitive: boolean
): TextMatch[] {
  if (!query) return [];

  const matches: TextMatch[] = [];
  const haystack = caseSensitive ? text : text.toLowerCase();
  const needle = caseSensitive ? query : query.toLowerCase();
  let index = 0;

  while (index <= haystack.length) {
    const hit = haystack.indexOf(needle, index);
    if (hit === -1) break;
    matches.push({ start: hit, end: hit + query.length });
    index = hit + (needle.length || 1);
  }

  return matches;
}

export function replaceAllInText(
  text: string,
  query: string,
  replacement: string,
  caseSensitive: boolean
): string {
  if (!query) return text;

  const matches = findAllInText(text, query, caseSensitive);
  if (!matches.length) return text;

  let result = "";
  let last = 0;
  for (const match of matches) {
    result += text.slice(last, match.start) + replacement;
    last = match.end;
  }
  result += text.slice(last);
  return result;
}
