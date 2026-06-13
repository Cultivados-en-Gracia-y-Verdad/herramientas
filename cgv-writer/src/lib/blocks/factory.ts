import type { BlockType, ContentBlock } from "./types";
import { newBlockId } from "./types";

export function createBlock(type: BlockType): ContentBlock {
  const id = newBlockId();

  switch (type) {
    case "h1":
      return { id, type: "h1", text: "Contexto amplio" };
    case "h2":
      return { id, type: "h2", text: "Nueva sección" };
    case "verse":
      return {
        id,
        type: "verse",
        reference: "Santiago 1:1",
        scripture: "Texto del versículo (sin cursiva ni comillas)."
      };
    case "focus":
      return { id, type: "focus", phrase: "Palabra clave" };
    case "commentary":
      return {
        id,
        type: "commentary",
        title: "Comentario",
        bullets: ["Primer punto del comentario."]
      };
    case "synthesis":
      return {
        id,
        type: "synthesis",
        title: "En Síntesis",
        bullets: ["Primer punto del resumen.", "Segundo punto del resumen."]
      };
    case "definition":
      return {
        id,
        type: "definition",
        term: "término - TERMINO",
        definition: ": definición en español"
      };
    case "quiz":
      return { id, type: "quiz", quizId: "ejemplo-1-1" };
    case "paragraph":
      return { id, type: "paragraph", text: "" };
    case "slideBreak":
      return { id, type: "slideBreak" };
    default:
      return { id, type: "paragraph", text: "" };
  }
}
