import type { ContentBlock } from "../lib/blocks/types";
import type { BlockType } from "../lib/blocks/types";
import { createBlock } from "../lib/blocks/factory";
import { BlockEditor } from "./blocks/BlockEditor";
import { WriterToolbar } from "./WriterToolbar";

interface StructuredEditorProps {
  blocks: ContentBlock[];
  frontMatter: string;
  onBlocksChange: (blocks: ContentBlock[]) => void;
  onFrontMatterChange: (frontMatter: string) => void;
}

export function StructuredEditor({
  blocks,
  frontMatter,
  onBlocksChange,
  onFrontMatterChange
}: StructuredEditorProps) {
  const updateBlock = (index: number, block: ContentBlock) => {
    const next = [...blocks];
    next[index] = block;
    onBlocksChange(next);
  };

  const removeBlock = (index: number) => {
    onBlocksChange(blocks.filter((_, i) => i !== index));
  };

  const moveBlock = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= blocks.length) return;
    const next = [...blocks];
    [next[index], next[target]] = [next[target], next[index]];
    onBlocksChange(next);
  };

  const insertBlock = (type: BlockType) => {
    onBlocksChange([...blocks, createBlock(type)]);
  };

  return (
    <div className="structured-editor">
      <WriterToolbar onInsert={insertBlock} />

      <details className="front-matter-panel">
        <summary>Información del curso (YAML)</summary>
        <textarea
          className="front-matter-input"
          rows={8}
          value={frontMatter}
          onChange={e => onFrontMatterChange(e.target.value)}
          spellCheck={false}
          placeholder={'title: "Mi curso"\ncover: "images/portada.png"'}
        />
      </details>

      <div className="block-list">
        {blocks.length === 0 ? (
          <p className="empty-hint">
            Use <strong>+ Versículo</strong> o los botones de arriba para empezar. No necesita
            escribir markdown.
          </p>
        ) : (
          blocks.map((block, index) => (
            <BlockEditor
              key={block.id}
              block={block}
              index={index}
              total={blocks.length}
              onChange={updated => updateBlock(index, updated)}
              onRemove={() => removeBlock(index)}
              onMoveUp={() => moveBlock(index, -1)}
              onMoveDown={() => moveBlock(index, 1)}
            />
          ))
        )}
      </div>
    </div>
  );
}
