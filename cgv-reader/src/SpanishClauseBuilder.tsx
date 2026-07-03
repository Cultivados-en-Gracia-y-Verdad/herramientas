import { useCallback, useEffect, useMemo, useState } from "react";
import {
  loadTitusClauseVerses,
  readClauseAssignments,
  writeClauseAssignments,
  type ClauseAssignments,
  type SpanishWord
} from "./clause-data";

export default function SpanishClauseBuilder({ onBack }: { onBack: () => void }) {
  const verses = useMemo(() => loadTitusClauseVerses(), []);
  const finiteVerbs = useMemo(
    () => verses.flatMap(verse => verse.words.filter(word => word.isFiniteVerb)),
    [verses]
  );

  const [assignments, setAssignments] = useState<ClauseAssignments>(readClauseAssignments);
  const [activeVerbId, setActiveVerbId] = useState<string | null>(null);
  const [draftWordIds, setDraftWordIds] = useState<Set<string>>(new Set());
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const activeVerb = useMemo(
    () => finiteVerbs.find(verb => verb.id === activeVerbId) ?? null,
    [activeVerbId, finiteVerbs]
  );

  const selectVerb = useCallback(
    (verb: SpanishWord) => {
      setActiveVerbId(verb.id);
      setDraftWordIds(new Set(assignments[verb.id] ?? []));
    },
    [assignments]
  );

  const toggleBelongingWord = useCallback((word: SpanishWord) => {
    if (!activeVerbId || word.id === activeVerbId) return;
    setDraftWordIds(current => {
      const next = new Set(current);
      if (next.has(word.id)) next.delete(word.id);
      else next.add(word.id);
      return next;
    });
  }, [activeVerbId]);

  const saveActive = useCallback(() => {
    if (!activeVerbId) return;
    setAssignments(current => {
      const next = { ...current, [activeVerbId]: Array.from(draftWordIds).sort() };
      writeClauseAssignments(next);
      return next;
    });
    setSavedAt(new Date().toLocaleTimeString());
  }, [activeVerbId, draftWordIds]);

  useEffect(() => {
    if (!activeVerbId) return;
    setDraftWordIds(new Set(assignments[activeVerbId] ?? []));
  }, [activeVerbId, assignments]);

  const wordById = useMemo(() => {
    const index = new Map<string, SpanishWord>();
    for (const verse of verses) {
      for (const word of verse.words) index.set(word.id, word);
    }
    return index;
  }, [verses]);

  const draftWords = useMemo(() => {
    return Array.from(draftWordIds)
      .map(id => wordById.get(id))
      .filter((word): word is SpanishWord => Boolean(word))
      .sort((a, b) => a.chapter - b.chapter || a.verse - b.verse || a.index - b.index);
  }, [draftWordIds, wordById]);

  return (
    <main className="clause-builder">
      <button type="button" className="prototype-link" onClick={onBack}>
        ← Reader
      </button>

      <header className="clause-builder-header">
        <p className="reader-kicker">Prototype</p>
        <h1>Spanish Clause Builder</h1>
        <p className="clause-builder-scope">Tito 1:1–4 · NBLA</p>
        <p className="clause-builder-hint">
          Click a finite verb (underlined), then click the words that belong to it. Guardar.
        </p>
      </header>

      <section className="clause-builder-body">
        {verses.map(verse => (
          <article className="clause-verse" key={`${verse.chapter}:${verse.verse}`}>
            <p className="clause-verse-label">{verse.verse}</p>
            <p className="clause-verse-text">
              {verse.words.map((word, position) => {
                const isActive = word.id === activeVerbId;
                const isBelonging = draftWordIds.has(word.id);
                const isSaved =
                  activeVerbId !== word.id &&
                  Object.entries(assignments).some(
                    ([verbId, ids]) => verbId !== activeVerbId && ids.includes(word.id)
                  );

                let className = "clause-word";
                if (word.isFiniteVerb) className += " clause-word--verb";
                if (isActive) className += " clause-word--active-verb";
                if (isBelonging) className += " clause-word--belonging";
                if (isSaved && !isBelonging && !isActive) className += " clause-word--saved";

                return (
                  <span key={word.id}>
                    {position > 0 ? " " : null}
                    <button
                      type="button"
                      className={className}
                      onClick={() =>
                        word.isFiniteVerb ? selectVerb(word) : toggleBelongingWord(word)
                      }
                      aria-pressed={isActive || isBelonging}
                      disabled={!word.isFiniteVerb && !activeVerbId}
                      title={word.isFiniteVerb ? "Finite verb" : "Belonging word"}
                    >
                      {word.text}
                    </button>
                  </span>
                );
              })}
            </p>
          </article>
        ))}
      </section>

      <aside className="clause-builder-panel">
        <h2>Active verb</h2>
        {activeVerb ? (
          <>
            <p className="clause-active-verb">
              Tito {activeVerb.chapter}:{activeVerb.verse} — <strong>{activeVerb.text}</strong>
            </p>
            <p className="clause-panel-label">Belonging words</p>
            {draftWords.length ? (
              <p className="clause-belonging-list">
                {draftWords.map(word => word.text).join(" · ")}
              </p>
            ) : (
              <p className="clause-empty">No words selected yet.</p>
            )}
            <button type="button" className="clause-save" onClick={saveActive}>
              Guardar
            </button>
            {savedAt ? <p className="clause-saved">Guardado {savedAt}</p> : null}
          </>
        ) : (
          <p className="clause-empty">Click a finite verb to begin.</p>
        )}

        <h2>Saved</h2>
        {finiteVerbs.length ? (
          <ul className="clause-saved-list">
            {finiteVerbs.map(verb => {
              const words = assignments[verb.id] ?? [];
              return (
                <li key={verb.id}>
                  <button type="button" className="clause-saved-verb" onClick={() => selectVerb(verb)}>
                    {verb.text}
                  </button>
                  {words.length ? (
                    <span>
                      {" "}
                      → {words.map(id => wordById.get(id)?.text ?? id).join(", ")}
                    </span>
                  ) : (
                    <span className="clause-empty"> (vacío)</span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="clause-empty">No finite verbs in 1:1–4.</p>
        )}
      </aside>
    </main>
  );
}
