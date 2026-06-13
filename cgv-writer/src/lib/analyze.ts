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

  return { outline, checks };
}
