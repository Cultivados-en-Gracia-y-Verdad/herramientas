import { sanitizeH4AnchorText } from "../markdown-html";
import {
  isBlockquoteLine,
  isSynthesisTitleLine,
  parseSynthesisLines
} from "../synthesis-block";
import type { ContentBlock } from "./types";
import { newBlockId } from "./types";
import { splitFrontMatter } from "../analyze";

const QUIZ_LINE = /^<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->$/;

function parseLinesInChunk(lines: string[]): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

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
      while (
        i < lines.length &&
        !/^#{1,6}\s/.test(lines[i]) &&
        !QUIZ_LINE.test(lines[i]) &&
        !(lines[i + 1]?.startsWith(": "))
      ) {
        scriptureLines.push(lines[i]);
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

    if (line.startsWith("##### ")) {
      const title = line.slice(6).trim();
      i++;
      const bullets: string[] = [];
      while (
        i < lines.length &&
        (lines[i].startsWith("###### ") || lines[i].startsWith("- "))
      ) {
        if (lines[i].startsWith("###### ")) {
          bullets.push(lines[i].slice(7).trim());
        } else {
          bullets.push(lines[i].slice(2).trim());
        }
        i++;
      }
      blocks.push({
        id: newBlockId(),
        type: "commentary",
        title,
        bullets
      });
      continue;
    }

    if (isSynthesisTitleLine(line)) {
      const group = [line];
      i++;
      while (i < lines.length && isBlockquoteLine(lines[i])) {
        group.push(lines[i]);
        i++;
      }
      const parsed = parseSynthesisLines(group);
      if (parsed) {
        blocks.push({
          id: newBlockId(),
          type: "synthesis",
          title: parsed.title,
          bullets: parsed.bullets
        });
        continue;
      }
    }

    if (line.startsWith("- ")) {
      const bullets: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        bullets.push(lines[i].slice(2).trim());
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

    if (i + 1 < lines.length && lines[i + 1].startsWith(": ")) {
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
  const trimmed = String(body || "").trim();
  if (!trimmed) return [];

  const chunks = trimmed.split(/\n\s*\n/);
  const blocks: ContentBlock[] = [];

  chunks.forEach((chunk, index) => {
    if (index > 0) {
      blocks.push({ id: newBlockId(), type: "slideBreak" });
    }
    const lines = chunk
      .split("\n")
      .map(l => l.trim())
      .filter(Boolean);
    const parsed = parseLinesInChunk(lines.filter(Boolean));
    blocks.push(...parsed);
  });

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
