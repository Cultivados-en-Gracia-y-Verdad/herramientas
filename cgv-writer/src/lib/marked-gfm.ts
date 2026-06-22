import { marked } from "marked";

marked.setOptions({
  gfm: true,
  breaks: false
});

export { marked };

export function renderMarkdownBlock(markdown: string): string {
  return marked.parse(String(markdown || ""), { async: false }) as string;
}

export function renderMarkdownInline(text: string): string {
  return marked.parseInline(String(text || ""), { async: false }) as string;
}
