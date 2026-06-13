import { useMemo, useState } from "react";
import { analyzeDocument } from "../lib/analyze";
import { splitYamlBody, joinYamlBody } from "../lib/markdown-html";
import { compileBlocks } from "../lib/blocks/compile";
import { createBlock } from "../lib/blocks/factory";
import type { ContentBlock } from "../lib/blocks/types";
import "./PresentationPanel.css";

interface PresentationPanelProps {
  content: string;
  onContentChange: (content: string) => void;
  variant?: "full" | "sidebar";
}

export function PresentationPanel({
  content,
  onContentChange,
  variant = "full"
}: PresentationPanelProps) {
  const [verseRef, setVerseRef] = useState("Santiago 1:1");
  const [verseText, setVerseText] = useState("");
  const [focus, setFocus] = useState("");
  const [comment, setComment] = useState("");
  const [quizId, setQuizId] = useState("santiago-1-1-27");

  const analysis = useMemo(() => analyzeDocument(content), [content]);

  const appendMarkdown = (chunk: string) => {
    const { frontMatter, body } = splitYamlBody(content);
    const nextBody = body.trim() ? `${body.trim()}\n\n${chunk.trim()}` : chunk.trim();
    onContentChange(joinYamlBody(frontMatter, nextBody));
  };

  const appendSlideUnit = () => {
    const blocks: ContentBlock[] = [createBlock("slideBreak")];
    const verse = createBlock("verse");
    if (verse.type === "verse") {
      verse.reference = verseRef;
      verse.scripture = verseText || "Texto del versículo.";
      blocks.push(verse);
    }
    if (focus.trim()) {
      const focusBlock = createBlock("focus");
      if (focusBlock.type === "focus") {
        focusBlock.phrase = focus.trim();
        blocks.push(focusBlock);
      }
    }
    if (comment.trim()) {
      const commentary = createBlock("commentary");
      if (commentary.type === "commentary") {
        commentary.title = "Comentario";
        commentary.bullets = [comment.trim()];
        blocks.push(commentary);
      }
    }
    appendMarkdown(compileBlocks(blocks));
    setVerseText("");
    setFocus("");
    setComment("");
  };

  const appendQuiz = () => {
    if (!quizId.trim()) return;
    appendMarkdown(`<!-- @quiz ${quizId.trim()} -->`);
  };

  const appendSlideBreak = () => {
    const { frontMatter, body: docBody } = splitYamlBody(content);
    const nextBody = docBody.trim() ? `${docBody.trim()}\n\n` : "";
    onContentChange(joinYamlBody(frontMatter, nextBody));
  };

  const sidebar = variant === "sidebar";

  return (
    <div className={`presentation-panel${sidebar ? " presentation-panel--sidebar" : ""}`}>
      {!sidebar && (
        <header className="presentation-intro">
          <h2>Presentación / diapositivas</h2>
          <p>
            Añada <strong>marcas de Presenter</strong> (quiz, salto de diapositiva) al final del
            manual. El texto del curso se escribe en <strong>Manual</strong>.
          </p>
        </header>
      )}

      <section className="presentation-card">
        <h3>Agregar diapositiva de enseñanza</h3>
        <label>Referencia</label>
        <input
          type="text"
          value={verseRef}
          onChange={e => setVerseRef(e.target.value)}
          placeholder="Santiago 1:1"
        />
        <label>Texto del versículo</label>
        <textarea
          rows={3}
          value={verseText}
          onChange={e => setVerseText(e.target.value)}
          placeholder="Texto del versículo (sin cursiva)."
        />
        <label>Palabra clave (opcional)</label>
        <input type="text" value={focus} onChange={e => setFocus(e.target.value)} />
        <label>Comentario (opcional)</label>
        <input type="text" value={comment} onChange={e => setComment(e.target.value)} />
        <button type="button" className="primary" onClick={appendSlideUnit}>
          Añadir al final del manual
        </button>
      </section>

      <section className="presentation-card presentation-card--row">
        <div>
          <h3>Quiz</h3>
          <input
            type="text"
            value={quizId}
            onChange={e => setQuizId(e.target.value)}
            placeholder="santiago-1-1-27"
          />
        </div>
        <button type="button" onClick={appendQuiz}>
          Insertar marcador @quiz
        </button>
      </section>

      <section className="presentation-card">
        <h3>Salto de diapositiva</h3>
        <p className="hint">Inserta una línea en blanco entre bloques (nueva diapositiva en Presenter).</p>
        <button type="button" onClick={appendSlideBreak}>
          Nueva diapositiva
        </button>
      </section>

      {!sidebar && (
        <section className="presentation-card">
          <h3>Esquema actual ({analysis.outline.length})</h3>
          <ol className="presentation-outline">
            {analysis.outline.map(slide => (
              <li key={slide.index} className={slide.isQuiz ? "quiz" : undefined}>
                {slide.index}. {slide.title}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
