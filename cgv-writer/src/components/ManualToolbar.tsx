import { memo, useEffect, useRef, useState } from "react";
import type { Editor } from "@tiptap/react";
import {
  applyCommentBulletList,
  applyHeadingStyle,
  applyScriptureStyle
} from "../lib/manual-comments";
import { applyReferenceHeading } from "../lib/manual-passage-layout";
import {
  DEFAULT_MANUAL_BLOCK_STYLE,
  getManualBlockStyleAtCursor,
  type ManualBlockStyle
} from "../lib/manual-block-style";
import { isManualCommandVisible } from "../lib/manual-toolbar-config";

function useManualBlockStyle(editor: Editor | null): ManualBlockStyle {
  const [blockStyle, setBlockStyle] = useState<ManualBlockStyle>(DEFAULT_MANUAL_BLOCK_STYLE);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!editor) return;

    const update = () => {
      if (timer.current) return;
      timer.current = window.setTimeout(() => {
        timer.current = null;
        const next = getManualBlockStyleAtCursor(editor);
        setBlockStyle(prev => (prev.id === next.id && prev.label === next.label ? prev : next));
      }, 120);
    };

    update();
    editor.on("selectionUpdate", update);
    return () => {
      editor.off("selectionUpdate", update);
      if (timer.current) {
        clearTimeout(timer.current);
        timer.current = null;
      }
    };
  }, [editor]);

  return blockStyle;
}

interface ManualStyleChipProps {
  editor: Editor | null;
  className?: string;
}

export const ManualStyleChip = memo(function ManualStyleChip({ editor, className }: ManualStyleChipProps) {
  const blockStyle = useManualBlockStyle(editor);
  if (!editor) return null;

  const title = blockStyle.shortcut ? `${blockStyle.label} (${blockStyle.shortcut})` : blockStyle.label;

  return (
    <span
      className={`manual-style-indicator${className ? ` ${className}` : ""}`}
      aria-live="polite"
      title={title}
    >
      <span className="manual-style-indicator-mark">{blockStyle.markdown}</span>
    </span>
  );
});

interface ManualToolbarProps {
  editor: Editor | null;
  underlinePaintMode?: boolean;
  onToggleUnderlinePaintMode?: () => void;
}

function ManualToolbarInner({
  editor,
  underlinePaintMode = false,
  onToggleUnderlinePaintMode
}: ManualToolbarProps) {
  const blockStyle = useManualBlockStyle(editor);

  if (!editor) return null;

  const styleButtonClass = (id: string) =>
    blockStyle.id === id ? "manual-toolbar-btn is-active" : "manual-toolbar-btn";

  const blockStyleTitle = blockStyle.shortcut
    ? `${blockStyle.label} (${blockStyle.shortcut})`
    : blockStyle.label;

  const toolbarBtn = (
    id: string,
    label: string,
    onClick: () => void,
    title: string,
    opts?: { accent?: boolean; mono?: boolean }
  ) => {
    const classes = [
      styleButtonClass(id),
      opts?.accent ? "accent" : "",
      opts?.mono ? "manual-toolbar-btn--mono" : ""
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <button type="button" className={classes} onClick={onClick} title={title} aria-label={title}>
        {label}
      </button>
    );
  };

  return (
    <div className="manual-toolbar">
      <span className="manual-style-indicator" aria-live="polite" title={blockStyleTitle}>
        <span className="manual-style-indicator-mark">{blockStyle.markdown}</span>
      </span>
      <span className="manual-toolbar-sep" aria-hidden="true" />
      <div className="manual-toolbar-group">
        {toolbarBtn("h1", "H1", () => editor.chain().focus().toggleHeading({ level: 1 }).run(), "Contexto (⌘1)", {
          mono: true
        })}
        {toolbarBtn("h2", "H2", () => editor.chain().focus().toggleHeading({ level: 2 }).run(), "Sección (⌘2)", {
          mono: true
        })}
        {toolbarBtn(
          "h3",
          "H3",
          () => applyReferenceHeading(editor),
          "Referencia bíblica + versículo (⌘3)",
          { mono: true }
        )}
        {toolbarBtn("h4", "H4", () => applyHeadingStyle(editor, 4), "Texto ancla (⌘4)", {
          mono: true
        })}
        {toolbarBtn("h5", "H5", () => applyHeadingStyle(editor, 5), "Comentario 1 (⌘5)", { mono: true })}
        {toolbarBtn("h6", "H6", () => applyHeadingStyle(editor, 6), "Comentario 2 (⌘6)", { mono: true })}
        {toolbarBtn("list", "•", () => applyCommentBulletList(editor), "Lista — comentario 3 (⌘7)", {
          mono: true
        })}
      </div>
      <span className="manual-toolbar-sep" aria-hidden="true" />
      <div className="manual-toolbar-group">
        {toolbarBtn("scripture", "Vs", () => applyScriptureStyle(editor), "Versículo bajo referencia")}
        {toolbarBtn(
          "definition",
          "Def",
          () => {
            editor
              .chain()
              .focus()
              .insertContent(
                `<div class="cgv-definition"><p class="definition-term">término - TERMINO</p><p class="definition-text">: definición en español</p></div>`
              )
              .run();
          },
          "Definición léxica"
        )}
      </div>
      <span className="manual-toolbar-sep" aria-hidden="true" />
      <div className="manual-toolbar-group">
        <button
          type="button"
          className="manual-toolbar-btn manual-toolbar-btn--icon manual-toolbar-btn--icon-i"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Cursiva — en comentarios = escritura"
          aria-label="Cursiva — en comentarios = escritura"
        >
          I
        </button>
        <button
          type="button"
          className={`manual-toolbar-btn manual-toolbar-btn--icon manual-toolbar-btn--icon-u${
            underlinePaintMode ? " is-active" : ""
          }`}
          onClick={() => onToggleUnderlinePaintMode?.()}
          title={
            underlinePaintMode
              ? "Modo espacio en blanco activo — clic en palabras · Escape para salir"
              : "Modo espacio en blanco — clic en cada palabra (⌘⇧U · Escape para salir)"
          }
          aria-label={
            underlinePaintMode
              ? "Salir del modo espacio en blanco"
              : "Modo espacio en blanco — clic en cada palabra"
          }
          aria-pressed={underlinePaintMode}
        >
          U
        </button>
        <button
          type="button"
          className="manual-toolbar-btn manual-toolbar-btn--icon manual-toolbar-btn--icon-b"
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Negrita"
          aria-label="Negrita"
        >
          B
        </button>
      </div>
      {isManualCommandVisible("slideBreak") && (
        <>
          <span className="manual-toolbar-sep" aria-hidden="true" />
          {toolbarBtn(
            "slideBreak",
            "—",
            () => editor.chain().focus().setHorizontalRule().run(),
            "Salto de diapositiva",
            { mono: true }
          )}
        </>
      )}
    </div>
  );
}

export const ManualToolbar = memo(ManualToolbarInner);
