import {
  isCgvBulletLine,
  isDefinitionGlossLine,
  restoreStrayMarkdownComments,
  sanitizeH4AnchorText
} from "../markdown-html";
import { isBlockquoteLine, parseBlockquoteLines } from "../synthesis-block";
import { collectTableLines, isTableStart } from "../table-block";
import { markH6Bullet } from "./commentary-helpers";
import type { ContentBlock } from "./types";
import { newBlockId } from "./types";
import { splitFrontMatter } from "../analyze";

const QUIZ_LINE = /^<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->$/;
const QUIZ_PLAIN_LINE = /^@quiz\s+#?([A-Za-z0-9_.:-]+)\s*$/i;

function isTripleColonFenceStart(line: string): boolean {
  return /^:::/.test(String(line || "").trim());
}

function isTripleColonFenceEnd(line: string): boolean {
  return String(line || "").trim() === ":::";
}

function parseLinesInChunk(lines: string[]): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    if (QUIZ_LINE.test(line)) {
      const match = line.match(QUIZ_LINE);
      blocks.push({
        id: newBlockId(),
        type: "quiz",
        quizId: match?.[1] || ""
      });
      i++;
      continue;
    }

    const plainQuiz = line.match(QUIZ_PLAIN_LINE);
    if (plainQuiz) {
      blocks.push({
        id: newBlockId(),
        type: "quiz",
        quizId: plainQuiz[1] || ""
      });
      i++;
      continue;
    }

    if (isTableStart(lines, i)) {
      const table = collectTableLines(lines, i);
      blocks.push({ id: newBlockId(), type: "table", markdown: table.markdown });
      i = table.next;
      continue;
    }

    if (line.startsWith("# ") && !line.startsWith("## ")) {
      blocks.push({ id: newBlockId(), type: "h1", text: line.slice(2).trim() });
      i++;
      continue;
    }

    if (line.startsWith("## ") && !line.startsWith("### ")) {
      blocks.push({ id: newBlockId(), type: "h2", text: line.slice(3).trim() });
      i++;
      continue;
    }

    if (line.startsWith("### ") && !line.startsWith("#### ")) {
      const reference = line.slice(4).trim();
      i++;
      const scriptureLines: string[] = [];
      if (
        i < lines.length &&
        lines[i].trim() &&
        !/^#{1,6}\s/.test(lines[i]) &&
        !QUIZ_LINE.test(lines[i]) &&
        !isDefinitionGlossLine(lines[i + 1] || "")
      ) {
        scriptureLines.push(lines[i].trim());
        i++;
      }
      blocks.push({
        id: newBlockId(),
        type: "verse",
        reference,
        scripture: scriptureLines.join("\n").trim()
      });
      continue;
    }

    if (line.startsWith("#### ") && !line.startsWith("##### ")) {
      blocks.push({
        id: newBlockId(),
        type: "focus",
        phrase: sanitizeH4AnchorText(line.slice(5).trim())
      });
      i++;
      continue;
    }

    if (line.startsWith("###### ") && !line.startsWith("####### ")) {
      const h6 = line.slice(7).trim();
      i++;
      const bullets: string[] = [];
      while (i < lines.length) {
        if (!lines[i].trim()) {
          i++;
          continue;
        }
        if (isCgvBulletLine(lines[i])) {
          bullets.push(lines[i].replace(/^-\s+/, "").trim());
          i++;
          continue;
        }
        break;
      }
      blocks.push({
        id: newBlockId(),
        type: "commentary",
        title: "",
        h6,
        bullets
      });
      continue;
    }

    if (line.startsWith("##### ")) {
      const title = line.slice(6).trim();
      i++;
      const bullets: string[] = [];
      while (i < lines.length) {
        if (!lines[i].trim()) {
          i++;
          continue;
        }
        if (lines[i].startsWith("###### ") && !lines[i].startsWith("####### ")) {
          bullets.push(markH6Bullet(lines[i].slice(7).trim()));
          i++;
          continue;
        }
        if (isCgvBulletLine(lines[i])) {
          bullets.push(lines[i].replace(/^-\s+/, "").trim());
          i++;
          continue;
        }
        break;
      }
      blocks.push({
        id: newBlockId(),
        type: "commentary",
        title,
        bullets
      });
      continue;
    }

    if (isBlockquoteLine(line)) {
      const group = [line];
      i++;
      while (i < lines.length && isBlockquoteLine(lines[i])) {
        group.push(lines[i]);
        i++;
      }
      const parsed = parseBlockquoteLines(group);
      if (parsed) {
        const bullets = [...parsed.bullets];
        while (i < lines.length) {
          if (!lines[i].trim()) {
            if (!bullets.length) {
              i++;
              continue;
            }
            break;
          }
          if (isCgvBulletLine(lines[i])) {
            bullets.push(lines[i].replace(/^-\s+/, "").trim());
            i++;
            continue;
          }
          break;
        }
        blocks.push({
          id: newBlockId(),
          type: "synthesis",
          title: parsed.title,
          bullets
        });
        continue;
      }
    }

    if (isCgvBulletLine(line)) {
      const bullets: string[] = [];
      while (i < lines.length) {
        if (!lines[i].trim()) {
          i++;
          continue;
        }
        if (!isCgvBulletLine(lines[i])) break;
        bullets.push(lines[i].replace(/^-\s+/, "").trim());
        i++;
      }
      blocks.push({
        id: newBlockId(),
        type: "commentary",
        title: "",
        bullets
      });
      continue;
    }

    if (i + 1 < lines.length && isDefinitionGlossLine(lines[i + 1])) {
      blocks.push({
        id: newBlockId(),
        type: "definition",
        term: line.trim(),
        definition: lines[i + 1].trim().startsWith(":")
          ? lines[i + 1].trim()
          : `: ${lines[i + 1].trim()}`
      });
      i += 2;
      continue;
    }

    blocks.push({
      id: newBlockId(),
      type: "paragraph",
      text: line
    });
    i++;
  }

  return blocks;
}

export function parseBodyToBlocks(body: string): ContentBlock[] {
  const trimmed = restoreStrayMarkdownComments(String(body || "")).trim();
  if (!trimmed) return [];

  const lines = trimmed.split("\n");
  const blocks: ContentBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    if (!lines[i].trim()) {
      let blankRun = 0;
      while (i < lines.length && !lines[i].trim()) {
        blankRun += 1;
        i += 1;
      }
      if (blankRun >= 2 && blocks.length) {
        blocks.push({ id: newBlockId(), type: "slideBreak" });
      }
      continue;
    }

    if (isTripleColonFenceStart(lines[i])) {
      const group = [lines[i]];
      i++;
      while (i < lines.length && !isTripleColonFenceEnd(lines[i])) {
        group.push(lines[i]);
        i++;
      }
      if (i < lines.length) {
        group.push(lines[i]);
        i++;
      }
      blocks.push({ id: newBlockId(), type: "raw", text: group.join("\n") });
      continue;
    }

    const segmentStart = i;
    while (i < lines.length) {
      if (isTripleColonFenceStart(lines[i])) break;
      if (!lines[i].trim() && i + 1 < lines.length && !lines[i + 1].trim()) break;
      i++;
    }

    const segment = lines.slice(segmentStart, i);
    if (segment.some(line => line.trim())) {
      blocks.push(...parseLinesInChunk(segment.map(line => line.trimEnd())));
    }
  }

  return blocks;
}

export function parseDocumentToBlocks(text: string): {
  frontMatter: string;
  blocks: ContentBlock[];
} {
  const { meta, body } = splitFrontMatter(text);
  const blocks = parseBodyToBlocks(body);

  if (!blocks.length && body.trim()) {
    return {
      frontMatter: meta,
      blocks: [{ id: newBlockId(), type: "paragraph", text: body.trim() }]
    };
  }

  return { frontMatter: meta, blocks };
}
