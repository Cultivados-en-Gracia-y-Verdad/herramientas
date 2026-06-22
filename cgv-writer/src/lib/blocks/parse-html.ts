import TurndownService from "turndown";
import { sanitizeH4AnchorText } from "../markdown-html";
import { tableWrapperToMarkdown } from "../table-block";
import {
  isSynthesisBulletText,
  isSynthesisTitleText,
  stripBulletPrefix
} from "../synthesis-block";
import { markH6Bullet } from "./commentary-helpers";
import type { ContentBlock } from "./types";
import { newBlockId } from "./types";

let inlineTurndown: TurndownService | null = null;

function getInlineTurndown(): TurndownService {
  if (!inlineTurndown) {
    inlineTurndown = new TurndownService({
      headingStyle: "atx",
      emDelimiter: "*",
      strongDelimiter: "**"
    });
    inlineTurndown.escape = text => text;
    inlineTurndown.addRule("cgvUnderline", {
      filter: ["u"],
      replacement: content => `<u>${content}</u>`
    });
  }
  return inlineTurndown;
}

function inlineMarkdown(el: Element): string {
  return getInlineTurndown().turndown(el.innerHTML).trim();
}

function isSpacer(el: Element): boolean {
  return el.tagName === "P" && el.classList.contains("cgv-md-spacer");
}

function isQuizParagraph(el: Element): boolean {
  return el.tagName === "P" && (el.classList.contains("cgv-quiz") || Boolean(el.getAttribute("data-quiz-id")));
}

function isScriptureParagraph(el: Element): boolean {
  return el.tagName === "P" && el.classList.contains("cgv-scripture");
}

function isBulletList(el: Element): boolean {
  return (
    el.tagName === "UL" &&
    (el.classList.contains("cgv-h6-bullets") || el.classList.contains("cgv-comment-3"))
  );
}

function collectCommentaryBullets(elements: Element[], startIndex: number): { bullets: string[]; nextIndex: number } {
  const bullets: string[] = [];
  let i = startIndex;

  while (i < elements.length) {
    const next = elements[i];
    const tag = next.tagName;

    if (isSpacer(next)) {
      i++;
      continue;
    }

    if (tag === "H6") {
      bullets.push(markH6Bullet(inlineMarkdown(next)));
      i++;
      continue;
    }

    if (isBulletList(next)) {
      next.querySelectorAll("li").forEach(li => {
        const text = inlineMarkdown(li);
        if (text) bullets.push(text);
      });
      i++;
      continue;
    }

    if (tag === "H5" || tag === "H4" || tag === "H3" || tag === "H2" || tag === "H1" || tag === "HR") {
      break;
    }

    break;
  }

  return { bullets, nextIndex: i };
}

/** Parse TipTap HTML back into CGV blocks — inverse of blocksToEditorHtml. */
export function htmlToBlocks(html: string): ContentBlock[] {
  const doc = new DOMParser().parseFromString(`<div id="cgv-root">${html || ""}</div>`, "text/html");
  const root = doc.getElementById("cgv-root");
  if (!root) return [];

  const blocks: ContentBlock[] = [];
  const elements = Array.from(root.children);
  let i = 0;

  while (i < elements.length) {
    const el = elements[i];

    if (isSpacer(el)) {
      i++;
      continue;
    }

    switch (el.tagName) {
      case "H1":
        blocks.push({ id: newBlockId(), type: "h1", text: inlineMarkdown(el) });
        i++;
        continue;
      case "H2":
        blocks.push({ id: newBlockId(), type: "h2", text: inlineMarkdown(el) });
        i++;
        continue;
      case "H3": {
        const reference = inlineMarkdown(el);
        i++;
        const scriptureLines: string[] = [];
        while (i < elements.length) {
          const next = elements[i];
          if (isSpacer(next)) {
            i++;
            break;
          }
          if (["H1", "H2", "H3", "H4", "H5", "H6", "HR"].includes(next.tagName) || isQuizParagraph(next)) {
            break;
          }
          if (next.tagName === "P") {
            const text = inlineMarkdown(next);
            if (!text.trim()) {
              i++;
              continue;
            }
            scriptureLines.push(text);
            i++;
            break;
          }
          break;
        }
        blocks.push({
          id: newBlockId(),
          type: "verse",
          reference,
          scripture: scriptureLines.join("\n")
        });
        continue;
      }
      case "H4":
        blocks.push({
          id: newBlockId(),
          type: "focus",
          phrase: sanitizeH4AnchorText(inlineMarkdown(el))
        });
        i++;
        continue;
      case "H5": {
        const title = inlineMarkdown(el);
        i++;
        const { bullets, nextIndex } = collectCommentaryBullets(elements, i);
        blocks.push({ id: newBlockId(), type: "commentary", title, bullets });
        i = nextIndex;
        continue;
      }
      case "H6": {
        const h6 = inlineMarkdown(el);
        i++;
        const { bullets, nextIndex } = collectCommentaryBullets(elements, i);
        blocks.push({ id: newBlockId(), type: "commentary", title: "", h6, bullets });
        i = nextIndex;
        continue;
      }
      case "UL": {
        const bullets: string[] = [];
        el.querySelectorAll("li").forEach(li => {
          const text = inlineMarkdown(li);
          if (text) bullets.push(text);
        });
        blocks.push({ id: newBlockId(), type: "commentary", title: "", bullets });
        i++;
        continue;
      }
      case "BLOCKQUOTE": {
        const paragraphs = Array.from(el.querySelectorAll(":scope > p"));
        let title = "";

        const titled = el.querySelector(".cgv-synthesis-title");
        if (titled) {
          title = inlineMarkdown(titled).trim();
        }

        if (!title) {
          for (const para of paragraphs) {
            const text = inlineMarkdown(para).trim();
            if (text && isSynthesisTitleText(text)) {
              title = text;
              break;
            }
          }
        }

        if (!title) {
          for (const para of paragraphs) {
            const text = inlineMarkdown(para).trim();
            if (text && !isSynthesisBulletText(text)) {
              title = text;
              break;
            }
          }
        }

        const bullets: string[] = [];
        el.querySelectorAll(".cgv-synthesis-bullets li, :scope > ul li").forEach(li => {
          const text = inlineMarkdown(li as Element);
          if (text) bullets.push(text);
        });

        for (const para of paragraphs) {
          const text = inlineMarkdown(para).trim();
          if (!text || text === title) continue;
          if (isSynthesisBulletText(text)) {
            bullets.push(stripBulletPrefix(text));
          }
        }

        blocks.push({ id: newBlockId(), type: "synthesis", title, bullets });
        i++;
        continue;
      }
      case "DIV": {
        if (el.classList.contains("cgv-table")) {
          const markdown = tableWrapperToMarkdown(el);
          if (markdown.trim()) {
            blocks.push({ id: newBlockId(), type: "table", markdown: markdown.trim() });
          }
          i++;
          continue;
        }
        if (el.classList.contains("cgv-definition")) {
          const term = el.querySelector(".definition-term")?.textContent?.trim() ?? "";
          const defText = el.querySelector(".definition-text")?.textContent?.trim() ?? "";
          const gloss = defText.startsWith(":") ? defText : `: ${defText.replace(/^:\s*/, "")}`;
          blocks.push({ id: newBlockId(), type: "definition", term, definition: gloss });
          i++;
          continue;
        }
        break;
      }
      case "TABLE": {
        const markdown = tableWrapperToMarkdown(el);
        if (markdown.trim()) {
          blocks.push({ id: newBlockId(), type: "table", markdown: markdown.trim() });
        }
        i++;
        continue;
      }
      case "P": {
        if (isQuizParagraph(el)) {
          const id =
            el.getAttribute("data-quiz-id")?.trim() ||
            (el.textContent?.trim().match(/^Quiz:\s*(.+)$/i)?.[1] ?? "");
          blocks.push({ id: newBlockId(), type: "quiz", quizId: id });
          i++;
          continue;
        }
        if (isScriptureParagraph(el)) {
          blocks.push({
            id: newBlockId(),
            type: "verse",
            reference: "",
            scripture: inlineMarkdown(el)
          });
          i++;
          continue;
        }
        const text = inlineMarkdown(el);
        if (text) {
          blocks.push({ id: newBlockId(), type: "paragraph", text });
        }
        i++;
        continue;
      }
      case "HR":
        blocks.push({ id: newBlockId(), type: "slideBreak" });
        i++;
        continue;
      default:
        i++;
    }
  }

  return blocks;
}
