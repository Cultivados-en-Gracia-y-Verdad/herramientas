import type { Editor } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import {
  countReferenceOccurrenceBeforePos,
  findVerseReferenceAtPos,
  normalizeReferenceText
} from "./h3-reference-click";
import {
  coerceQuizMarkersInMarkdown,
  editorHtmlToMarkdown,
  sanitizeCgvMarkdown,
  quizMarkerComment
} from "./markdown-html";

export function quizMarkerMarkdown(quizId: string): string {
  return quizMarkerComment(quizId);
}

/** Split markdown body into Presenter slides (blank-line separated). */
export function splitMarkdownSlidesRaw(body: string): { slides: string[]; starts: number[] } {
  const slides: string[] = [];
  const starts: number[] = [];

  if (!body) {
    return { slides: [], starts: [0] };
  }

  const re = /\n\s*\n/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(body)) !== null) {
    slides.push(body.slice(last, match.index));
    starts.push(last);
    last = match.index + match[0].length;
  }

  slides.push(body.slice(last));
  starts.push(last);
  return { slides, starts };
}

function isPassageBoundaryLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  if (/^#{1,3}\s/.test(trimmed) && !trimmed.startsWith("####")) return true;
  return false;
}

function isReferenceLine(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("### ") && !trimmed.startsWith("#### ");
}

function lineOffsetInBody(lines: string[], lineIndex: number): number {
  let offset = 0;
  for (let i = 0; i < lineIndex; i++) {
    offset += lines[i].length + 1;
  }
  return offset + lines[lineIndex].length;
}

/** End of a ### … passage (before the next ### / # / ## header). */
export function passageEndOffsetFromRefLine(lines: string[], refLineIndex: number): number {
  let endLineIndex = refLineIndex;

  for (let i = refLineIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;
    if (isPassageBoundaryLine(line)) break;
    endLineIndex = i;
  }

  return lineOffsetInBody(lines, endLineIndex);
}

/** Insert after the Nth occurrence of a ### reference in markdown (0-based). */
export function findPassageInsertPointInMarkdown(
  body: string,
  reference: string,
  occurrenceIndex = 0
): number | null {
  const target = normalizeReferenceText(reference);
  if (!target) return null;

  const lines = body.split("\n");
  let seen = 0;

  for (let i = 0; i < lines.length; i++) {
    if (!isReferenceLine(lines[i])) continue;

    const ref = normalizeReferenceText(lines[i].slice(4));
    if (ref !== target) continue;

    if (seen === occurrenceIndex) {
      return passageEndOffsetFromRefLine(lines, i);
    }

    seen += 1;
  }

  return null;
}

function topLevelBlockCount(doc: ProseMirrorNode): number {
  let count = 0;
  doc.forEach(() => {
    count += 1;
  });
  return count;
}

function blocksBeforePos(doc: ProseMirrorNode, pos: number): number {
  let count = 0;
  doc.forEach((_node, offset) => {
    if (offset < pos) count += 1;
  });
  return count;
}

/** Fallback when there is no ### reference — end of the estimated Presenter slide. */
export function findSlideEndInsertPoint(doc: ProseMirrorNode, pos: number, body: string): number {
  const { slides, starts } = splitMarkdownSlidesRaw(body);
  if (!slides.length) return 0;

  const total = topLevelBlockCount(doc);
  const before = blocksBeforePos(doc, pos);
  const slideIndex =
    total > 0
      ? Math.min(slides.length - 1, Math.max(0, Math.floor((before / total) * slides.length)))
      : 0;

  const slideStart = starts[slideIndex] ?? 0;
  const slide = slides[slideIndex] ?? "";
  return slideStart + slide.length;
}

export function markdownInsertPointFromEditor(
  doc: ProseMirrorNode,
  pos: number,
  body: string
): number {
  const verse = findVerseReferenceAtPos(doc, pos);
  if (verse) {
    const occurrence = Math.max(0, countReferenceOccurrenceBeforePos(doc, pos, verse.text) - 1);
    const insertAt = findPassageInsertPointInMarkdown(body, verse.text, occurrence);
    if (insertAt !== null) return insertAt;
  }

  return findSlideEndInsertPoint(doc, pos, body);
}

export function insertQuizIntoMarkdownBody(body: string, quizId: string, insertAt: number): string {
  const marker = quizMarkerMarkdown(quizId);
  if (!marker) return body;

  const at = Math.max(0, Math.min(body.length, insertAt));
  const before = body.slice(0, at);
  const after = body.slice(at);
  const gapBefore = before.endsWith("\n\n") || !before.trim() ? "" : "\n\n";
  const gapAfter = after.startsWith("\n\n") || !after.trim() ? "" : "\n\n";
  const inserted = `${before}${gapBefore}${marker}${gapAfter}${after}`;

  return coerceQuizMarkersInMarkdown(sanitizeCgvMarkdown(inserted));
}

export function insertQuizIntoEditorMarkdown(
  editor: Editor,
  quizId: string,
  pos = editor.state.selection.from,
  currentBody = ""
): string | null {
  const id = quizId.trim();
  if (!id) return null;

  const md = currentBody.trim()
    ? coerceQuizMarkersInMarkdown(sanitizeCgvMarkdown(currentBody))
    : editorHtmlToMarkdown(editor.getHTML());
  const insertAt = markdownInsertPointFromEditor(editor.state.doc, pos, md);
  return insertQuizIntoMarkdownBody(md, id, insertAt);
}
