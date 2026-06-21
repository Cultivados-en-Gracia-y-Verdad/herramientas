import type { Editor } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

export interface ManualBlockStyle {
  id: string;
  label: string;
  markdown: string;
  shortcut?: string;
}

export const DEFAULT_MANUAL_BLOCK_STYLE: ManualBlockStyle = {
  id: "paragraph",
  label: "Párrafo",
  markdown: "—"
};

export const MANUAL_BLOCK_STYLES: Record<string, ManualBlockStyle> = {
  h1: { id: "h1", label: "Contexto", markdown: "#", shortcut: "⌘1" },
  h2: { id: "h2", label: "Sección", markdown: "##", shortcut: "⌘2" },
  h3: { id: "h3", label: "Referencia", markdown: "###", shortcut: "⌘3" },
  h4: { id: "h4", label: "Texto ancla", markdown: "####", shortcut: "⌘4" },
  h5: { id: "h5", label: "Comentario 1", markdown: "#####", shortcut: "⌘5" },
  h6: { id: "h6", label: "Comentario 2", markdown: "######", shortcut: "⌘6" },
  list: { id: "list", label: "Lista (comentario 3)", markdown: "-   ", shortcut: "⌘7" },
  synthesis: { id: "synthesis", label: "En Síntesis", markdown: ">" },
  scripture: { id: "scripture", label: "Versículo", markdown: "texto" },
  definition: { id: "definition", label: "Definición", markdown: "término / :" },
  quiz: { id: "quiz", label: "Quiz", markdown: "<!-- @quiz -->" },
  slideBreak: { id: "slideBreak", label: "Diapositiva", markdown: "—" },
  paragraph: DEFAULT_MANUAL_BLOCK_STYLE
};

function nodeClass(node: ProseMirrorNode): string {
  return String(node.attrs.class || "");
}

function hasClass(node: ProseMirrorNode, token: string): boolean {
  return nodeClass(node).split(/\s+/).filter(Boolean).includes(token);
}

/** CGV block style at the cursor — for toolbar feedback in Manual view. */
export function getManualBlockStyleAtCursor(editor: Editor): ManualBlockStyle {
  const { $from } = editor.state.selection;

  for (let depth = $from.depth; depth > 0; depth--) {
    const node = $from.node(depth);
    const name = node.type.name;

    if (name === "heading") {
      const level = Number(node.attrs.level);
      return MANUAL_BLOCK_STYLES[`h${level}`] ?? DEFAULT_MANUAL_BLOCK_STYLE;
    }

    if (name === "bulletList") {
      return MANUAL_BLOCK_STYLES.list;
    }

    if (name === "blockquote") {
      return MANUAL_BLOCK_STYLES.synthesis;
    }

    if (name === "horizontalRule") {
      return MANUAL_BLOCK_STYLES.slideBreak;
    }

    if (name === "paragraph") {
      if (hasClass(node, "cgv-scripture")) return MANUAL_BLOCK_STYLES.scripture;
      if (hasClass(node, "cgv-quiz")) return MANUAL_BLOCK_STYLES.quiz;
      if (hasClass(node, "definition-term") || hasClass(node, "definition-text")) {
        return MANUAL_BLOCK_STYLES.definition;
      }
    }
  }

  return DEFAULT_MANUAL_BLOCK_STYLE;
}
