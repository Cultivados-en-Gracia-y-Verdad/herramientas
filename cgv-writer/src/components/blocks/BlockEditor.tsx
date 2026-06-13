import type { ReactNode } from "react";
import type { ContentBlock } from "../../lib/blocks/types";
import { BLOCK_LABELS } from "../../lib/blocks/types";

interface BlockEditorProps {
  block: ContentBlock;
  index: number;
  total: number;
  onChange: (block: ContentBlock) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function FieldLabel({ children }: { children: ReactNode }) {
  return <label className="field-label">{children}</label>;
}

export function BlockEditor({
  block,
  index,
  total,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown
}: BlockEditorProps) {
  if (block.type === "slideBreak") {
    return (
      <div className="block-card block-card--slide-break">
        <span className="slide-break-label">— Nueva diapositiva (Presenter) —</span>
        <div className="block-actions">
          <button type="button" onClick={onMoveUp} disabled={index === 0} title="Subir">
            ↑
          </button>
          <button type="button" onClick={onMoveDown} disabled={index >= total - 1} title="Bajar">
            ↓
          </button>
          <button type="button" className="danger" onClick={onRemove} title="Quitar">
            ×
          </button>
        </div>
      </div>
    );
  }

  return (
    <article className={`block-card block-card--${block.type}`}>
      <header className="block-card-header">
        <span className="block-type">{BLOCK_LABELS[block.type]}</span>
        <div className="block-actions">
          <button type="button" onClick={onMoveUp} disabled={index === 0} title="Subir">
            ↑
          </button>
          <button type="button" onClick={onMoveDown} disabled={index >= total - 1} title="Bajar">
            ↓
          </button>
          <button type="button" className="danger" onClick={onRemove} title="Eliminar bloque">
            ×
          </button>
        </div>
      </header>

      <div className="block-card-body">
        {block.type === "h1" && (
          <>
            <FieldLabel>Contexto amplio (H1)</FieldLabel>
            <input
              type="text"
              value={block.text}
              onChange={e => onChange({ ...block, text: e.target.value })}
            />
          </>
        )}

        {block.type === "h2" && (
          <>
            <FieldLabel>Sección (H2)</FieldLabel>
            <input
              type="text"
              value={block.text}
              onChange={e => onChange({ ...block, text: e.target.value })}
            />
          </>
        )}

        {block.type === "verse" && (
          <>
            <FieldLabel>Referencia (ej. Santiago 1:1)</FieldLabel>
            <input
              type="text"
              value={block.reference}
              onChange={e => onChange({ ...block, reference: e.target.value })}
              placeholder="Santiago 1:1"
            />
            <FieldLabel>Texto del versículo</FieldLabel>
            <textarea
              rows={3}
              value={block.scripture}
              onChange={e => onChange({ ...block, scripture: e.target.value })}
              placeholder="Sin cursiva ni comillas en el versículo."
            />
          </>
        )}

        {block.type === "focus" && (
          <>
            <FieldLabel>Palabra o frase de enfoque</FieldLabel>
            <input
              type="text"
              value={block.phrase}
              onChange={e => onChange({ ...block, phrase: e.target.value })}
            />
          </>
        )}

        {block.type === "commentary" && (
          <>
            <FieldLabel>Título del comentario</FieldLabel>
            <input
              type="text"
              value={block.title}
              onChange={e => onChange({ ...block, title: e.target.value })}
            />
            <FieldLabel>Puntos</FieldLabel>
            {block.bullets.map((bullet, bulletIndex) => (
              <div key={bulletIndex} className="bullet-row">
                <input
                  type="text"
                  value={bullet}
                  onChange={e => {
                    const bullets = [...block.bullets];
                    bullets[bulletIndex] = e.target.value;
                    onChange({ ...block, bullets });
                  }}
                />
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    const bullets = block.bullets.filter((_, i) => i !== bulletIndex);
                    onChange({ ...block, bullets: bullets.length ? bullets : [""] });
                  }}
                  disabled={block.bullets.length <= 1}
                >
                  ×
                </button>
              </div>
            ))}
            <button
              type="button"
              className="ghost"
              onClick={() => onChange({ ...block, bullets: [...block.bullets, ""] })}
            >
              + Añadir punto
            </button>
          </>
        )}

        {block.type === "synthesis" && (
          <>
            <FieldLabel>Título (blockquote)</FieldLabel>
            <input
              type="text"
              value={block.title}
              onChange={e => onChange({ ...block, title: e.target.value })}
              placeholder="En Síntesis (1:1–7)"
            />
            <FieldLabel>Puntos del resumen</FieldLabel>
            {block.bullets.map((bullet, bulletIndex) => (
              <div key={bulletIndex} className="bullet-row">
                <input
                  type="text"
                  value={bullet}
                  onChange={e => {
                    const bullets = [...block.bullets];
                    bullets[bulletIndex] = e.target.value;
                    onChange({ ...block, bullets });
                  }}
                />
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    const bullets = block.bullets.filter((_, i) => i !== bulletIndex);
                    onChange({ ...block, bullets: bullets.length ? bullets : [""] });
                  }}
                  disabled={block.bullets.length <= 1}
                >
                  ×
                </button>
              </div>
            ))}
            <button
              type="button"
              className="ghost"
              onClick={() => onChange({ ...block, bullets: [...block.bullets, ""] })}
            >
              + Añadir punto
            </button>
          </>
        )}

        {block.type === "definition" && (
          <>
            <FieldLabel>Término (griego / transliteración)</FieldLabel>
            <input
              type="text"
              value={block.term}
              onChange={e => onChange({ ...block, term: e.target.value })}
            />
            <FieldLabel>Definición (segunda línea con «:»)</FieldLabel>
            <textarea
              rows={2}
              value={block.definition}
              placeholder=": definición en español"
              onChange={e => onChange({ ...block, definition: e.target.value })}
            />
          </>
        )}

        {block.type === "quiz" && (
          <>
            <FieldLabel>ID del quiz (archivo YAML)</FieldLabel>
            <input
              type="text"
              value={block.quizId}
              onChange={e => onChange({ ...block, quizId: e.target.value })}
              placeholder="santiago-1-1-27"
            />
          </>
        )}

        {block.type === "paragraph" && (
          <>
            <FieldLabel>Párrafo</FieldLabel>
            <textarea
              rows={3}
              value={block.text}
              onChange={e => onChange({ ...block, text: e.target.value })}
            />
          </>
        )}
      </div>
    </article>
  );
}
