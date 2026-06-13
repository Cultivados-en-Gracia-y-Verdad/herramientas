/** En Síntesis — blockquote review block (one unit for Presenter + Writer). */

export function cleanBlockquoteLine(line: string): string {
  return line.replace(/^>\s?/, "").trim();
}

export function isBlockquoteLine(line: string): boolean {
  return String(line || "").trimStart().startsWith(">");
}

export function isSynthesisTitleLine(line: string): boolean {
  return /^En S[ií]ntesis/i.test(cleanBlockquoteLine(line));
}

export function parseSynthesisLines(lines: string[]): { title: string; bullets: string[] } | null {
  if (!lines.length || !isBlockquoteLine(lines[0]) || !isSynthesisTitleLine(lines[0])) {
    return null;
  }

  const title = cleanBlockquoteLine(lines[0]);
  const bullets: string[] = [];

  for (let i = 1; i < lines.length; i++) {
    const cleaned = cleanBlockquoteLine(lines[i]);
    if (!cleaned) continue;

    if (cleaned.startsWith("- ")) {
      bullets.push(cleaned.slice(2).trim());
    } else if (cleaned.startsWith("-")) {
      bullets.push(cleaned.slice(1).trim());
    }
  }

  return { title, bullets };
}

export function compileSynthesisMarkdown(title: string, bullets: string[]): string {
  const trimmedTitle = title.trim();
  if (!trimmedTitle) return "";

  const items = bullets.map(item => item.trim()).filter(Boolean);
  const lines = [`> ${trimmedTitle}`, ...items.map(item => `>- ${item}`)];
  return lines.join("\n");
}

export function isSynthesisMarkdownChunk(chunk: string): boolean {
  const lines = chunk
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean);
  return lines.length > 0 && isSynthesisTitleLine(lines[0]);
}

export function synthesisMarkdownLinesFromChunk(chunk: string): string[] {
  return chunk
    .split("\n")
    .map(line => line.trim())
    .filter(line => isBlockquoteLine(line));
}
