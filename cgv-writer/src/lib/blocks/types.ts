export type BlockType =
  | "h1"
  | "h2"
  | "verse"
  | "focus"
  | "commentary"
  | "synthesis"
  | "definition"
  | "quiz"
  | "paragraph"
  | "slideBreak";

export interface BaseBlock {
  id: string;
  type: BlockType;
}

export interface H1Block extends BaseBlock {
  type: "h1";
  text: string;
}

export interface H2Block extends BaseBlock {
  type: "h2";
  text: string;
}

export interface VerseBlock extends BaseBlock {
  type: "verse";
  reference: string;
  scripture: string;
}

export interface FocusBlock extends BaseBlock {
  type: "focus";
  phrase: string;
}

export interface CommentaryBlock extends BaseBlock {
  type: "commentary";
  title: string;
  bullets: string[];
}

export interface SynthesisBlock extends BaseBlock {
  type: "synthesis";
  title: string;
  bullets: string[];
}

export interface DefinitionBlock extends BaseBlock {
  type: "definition";
  term: string;
  definition: string;
}

export interface QuizBlock extends BaseBlock {
  type: "quiz";
  quizId: string;
}

export interface ParagraphBlock extends BaseBlock {
  type: "paragraph";
  text: string;
}

export interface SlideBreakBlock extends BaseBlock {
  type: "slideBreak";
}

export type ContentBlock =
  | H1Block
  | H2Block
  | VerseBlock
  | FocusBlock
  | CommentaryBlock
  | SynthesisBlock
  | DefinitionBlock
  | QuizBlock
  | ParagraphBlock
  | SlideBreakBlock;

export const BLOCK_LABELS: Record<BlockType, string> = {
  h1: "Contexto amplio",
  h2: "Sección",
  verse: "Versículo",
  focus: "Palabra clave",
  commentary: "Comentario",
  synthesis: "En Síntesis",
  definition: "Definición",
  quiz: "Quiz",
  paragraph: "Párrafo",
  slideBreak: "Nueva diapositiva"
};

export function newBlockId() {
  return `b-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
