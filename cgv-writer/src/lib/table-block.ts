import { renderMarkdownInline } from "./marked-gfm";

/** Pipe-table row with an opening and closing pipe. */
export function isTableLine(line: string): boolean {
  const trimmed = String(line || "").trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.length >= 2;
}

export function collectTableLines(lines: string[], start: number): { markdown: string; next: number } {
  const rows: string[] = [lines[start].trimEnd()];
  let index = start + 1;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) break;
    if (!isTableLine(line)) break;
    rows.push(line.trimEnd());
    index++;
  }

  return { markdown: rows.join("\n"), next: index };
}

export function encodeTableMarkdown(markdown: string): string {
  return encodeURIComponent(markdown);
}

export function decodeTableMarkdown(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function splitPipeRow(line: string): string[] {
  const trimmed = String(line || "").trim();
  if (!trimmed.includes("|")) return [];

  let inner = trimmed;
  if (inner.startsWith("|")) inner = inner.slice(1);
  if (inner.endsWith("|")) inner = inner.slice(0, -1);

  return inner.split("|").map(cell => cell.trim());
}

/** CGV manuals use loose separator rows (e.g. `| -- |  |  | - |`) that GFM parsers reject. */
function isSeparatorCell(cell: string): boolean {
  if (!cell) return true;
  if (/^:?-{1,}:?$/.test(cell)) return true;
  if (/^[-:]+$/.test(cell)) return true;
  return false;
}

export function isTableSeparatorRow(line: string): boolean {
  const cells = splitPipeRow(line);
  return cells.length > 0 && cells.every(isSeparatorCell);
}

export function isTableStart(lines: string[], start: number): boolean {
  if (start < 0 || start + 1 >= lines.length) return false;
  return isTableLine(lines[start]) && isTableSeparatorRow(lines[start + 1]);
}

function renderTableCell(text: string, tag: "th" | "td"): string {
  const trimmed = String(text || "").trim();
  const inner = trimmed ? renderMarkdownInline(trimmed) : "";
  return `<${tag}>${inner}</${tag}>`;
}

/** Parse pipe-table markdown into HTML without relying on strict GFM separator syntax. */
export function pipeTableMarkdownToHtml(markdown: string): string {
  const lines = String(markdown || "")
    .trim()
    .split("\n")
    .map(line => line.trimEnd())
    .filter(line => line.trim());

  if (!lines.length) return "";

  const rows = lines.map(splitPipeRow).filter(row => row.length > 0);
  if (!rows.length) return "";

  let headerRow: string[] | null = null;
  let bodyRows = rows;

  if (rows.length >= 2 && isTableSeparatorRow(lines[1])) {
    headerRow = rows[0];
    bodyRows = rows.slice(2);
  }

  const columnCount = Math.max(...rows.map(row => row.length), 1);
  const parts: string[] = ['<table class="cgv-markdown-table">'];

  if (headerRow) {
    parts.push("<thead><tr>");
    for (let column = 0; column < columnCount; column++) {
      parts.push(renderTableCell(headerRow[column] ?? "", "th"));
    }
    parts.push("</tr></thead>");
  }

  parts.push("<tbody>");
  for (const row of bodyRows) {
    parts.push("<tr>");
    for (let column = 0; column < columnCount; column++) {
      parts.push(renderTableCell(row[column] ?? "", "td"));
    }
    parts.push("</tr>");
  }
  parts.push("</tbody></table>");

  return parts.join("");
}

export function renderTableHtml(markdown: string): string {
  const trimmed = markdown.trim();
  if (!trimmed) return "";
  return pipeTableMarkdownToHtml(trimmed);
}

export function tableElementToMarkdown(table: HTMLTableElement): string {
  const rows = Array.from(table.querySelectorAll("tr"));
  if (!rows.length) return "";

  return rows
    .map(row => {
      const cells = Array.from(row.querySelectorAll("th, td"));
      const parts = cells.map(cell =>
        String(cell.textContent || "")
          .replace(/\|/g, "\\|")
          .replace(/\n+/g, " ")
          .trim()
      );
      return `| ${parts.join(" | ")} |`;
    })
    .join("\n");
}

export function tableWrapperToMarkdown(element: Element): string {
  const encoded = element.getAttribute("data-markdown");
  if (encoded) return decodeTableMarkdown(encoded);

  const table = element.tagName === "TABLE" ? element : element.querySelector("table");
  if (table instanceof HTMLTableElement) {
    return tableElementToMarkdown(table);
  }

  return "";
}
