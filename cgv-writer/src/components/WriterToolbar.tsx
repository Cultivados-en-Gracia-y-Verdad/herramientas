import type { BlockType } from "../lib/blocks/types";
import { BLOCK_LABELS } from "../lib/blocks/types";

const INSERT_TYPES: BlockType[] = [
  "h1",
  "h2",
  "verse",
  "focus",
  "commentary",
  "synthesis",
  "definition",
  "quiz",
  "slideBreak",
  "paragraph"
];

interface WriterToolbarProps {
  onInsert: (type: BlockType) => void;
}

export function WriterToolbar({ onInsert }: WriterToolbarProps) {
  return (
    <div className="writer-toolbar">
      <span className="writer-toolbar-label">Añadir:</span>
      {INSERT_TYPES.map(type => (
        <button
          key={type}
          type="button"
          className={type === "verse" ? "accent" : undefined}
          onClick={() => onInsert(type)}
        >
          {type === "verse" ? "+ Versículo" : `+ ${BLOCK_LABELS[type]}`}
        </button>
      ))}
    </div>
  );
}
