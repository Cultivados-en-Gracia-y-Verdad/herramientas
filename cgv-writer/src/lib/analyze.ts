const QUIZ_MARKER = /<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->/;
const ILLUSTRATION_MARKER = /<!--\s*@illustration\s+#?([A-Za-z0-9_.:-]+)\s*-->/;
const FRONT_MATTER = /^---\n([\s\S]*?)\n---\n?/;

export type CheckLevel = "ok" | "warn";

export interface CheckItem {
  level: CheckLevel;
  text: string;
}

export interface SlideOutline {
  index: number;
  title: string;
  isQuiz: boolean;
  isIllustration: boolean;
}

export interface HeadingOutlineItem {
  id: string;
  level: 1 | 2 | 3;
  title: string;
  /** Character offset at the start of this heading line in the document body. */
  bodyOffset: number;
  /** 1-based index among headings of the same level (for duplicate titles). */
  ordinal: number;
}

export type HeadingOutlineNode = HeadingOutlineItem & { children: HeadingOutlineNode[] };

export function splitFrontMatter(text: string) {
  const match = String(text || "").match(FRONT_MATTER);
  if (!match) return { meta: "", body: text || "" };
  return { meta: match[1], body: text.slice(match[0].length) };
}

/** Blank-line slides — same rule CGV Presenter uses. */
export function parseSlideBlocks(body: string) {
  return String(body || "")
    .split(/\n\s*\n/)
    .map(block =>
      block
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean)
    )
    .filter(slide => slide.length > 0);
}

function summarizeSlide(lines: string[]) {
  const heading = lines.find(line => /^#{1,6}\s/.test(line));
  if (heading) return heading.replace(/^#+\s*/, "").slice(0, 80);

  for (const line of lines) {
    if (/^>\s*En S[ií]ntesis/i.test(line.trim())) {
      return line.replace(/^>\s?/, "").trim().slice(0, 80);
    }
    const quiz = line.match(QUIZ_MARKER);
    if (quiz) return `Quiz: ${quiz[1]}`;
    const ill = line.match(ILLUSTRATION_MARKER);
    if (ill) return `Ilustración: ${ill[1]}`;
  }

  return (lines[0] || "(vacía)").slice(0, 80);
}

function stripHeadingMarkdown(title: string): string {
  return title
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .trim();
}

/** H1/H2/H3 hierarchy for the sidebar outline. */
export function parseHeadingOutline(body: string): HeadingOutlineItem[] {
  const items: HeadingOutlineItem[] = [];
  const ordinals: Record<1 | 2 | 3, number> = { 1: 0, 2: 0, 3: 0 };
  let offset = 0;

  for (const line of String(body || "").split("\n")) {
    const match = line.match(/^(#{1,3})\s+(.+)$/);
    if (match) {
      const level = match[1].length as 1 | 2 | 3;
      ordinals[level] += 1;
      items.push({
        id: `h${level}-${offset}`,
        level,
        title: stripHeadingMarkdown(match[2]).slice(0, 120),
        bodyOffset: offset,
        ordinal: ordinals[level]
      });
    }
    offset += line.length + 1;
  }

  return items;
}

export function buildHeadingOutlineTree(items: HeadingOutlineItem[]): HeadingOutlineNode[] {
  const roots: HeadingOutlineNode[] = [];
  const stack: HeadingOutlineNode[] = [];

  for (const item of items) {
    const node: HeadingOutlineNode = { ...item, children: [] };

    while (stack.length > 0 && stack[stack.length - 1].level >= item.level) {
      stack.pop();
    }

    if (stack.length === 0) {
      roots.push(node);
    } else {
      stack[stack.length - 1].children.push(node);
    }

    stack.push(node);
  }

  return roots;
}

export function analyzeDocument(text: string) {
  const { meta, body } = splitFrontMatter(text);
  const slides = parseSlideBlocks(body);
  const checks: CheckItem[] = [];

  if (!meta.trim()) {
    checks.push({ level: "warn", text: "Sin YAML inicial (title, cover, …)." });
  } else {
    if (!/^title:/m.test(meta)) checks.push({ level: "warn", text: "Falta title: en el YAML." });
    if (!/^cover:/m.test(meta)) checks.push({ level: "warn", text: "Falta cover: en el YAML." });
  }

  if (!slides.length) {
    checks.push({ level: "warn", text: "Sin diapositivas — ¿contenido después del YAML?" });
  } else {
    checks.push({ level: "ok", text: `${slides.length} bloques (separados por línea en blanco).` });
  }

  const quizCount = (body.match(/<!--\s*@quiz/g) || []).length;
  if (quizCount) checks.push({ level: "ok", text: `${quizCount} marcador(es) @quiz.` });

  const illCount = (body.match(/<!--\s*@illustration/g) || []).length;
  if (illCount) checks.push({ level: "ok", text: `${illCount} marcador(es) @illustration (futuro).` });

  if (/^####\s+.+$\n(?!\s*#####)/m.test(body)) {
    checks.push({
      level: "warn",
      text: "Hay #### sin ##### siguiente (un solo paso de revelado)."
    });
  }

  if (/\b(Rom|Mat|Mrk|Luk|Jn|1Co|2Co)\b/.test(body)) {
    checks.push({ level: "warn", text: "Posibles abreviaturas bíblicas." });
  }

  const outline: SlideOutline[] = slides.map((lines, index) => ({
    index: index + 1,
    title: summarizeSlide(lines),
    isQuiz: lines.some(line => QUIZ_MARKER.test(line)),
    isIllustration: lines.some(line => ILLUSTRATION_MARKER.test(line))
  }));

  const headingOutline = parseHeadingOutline(body);

  return { outline, headingOutline, checks };
}
