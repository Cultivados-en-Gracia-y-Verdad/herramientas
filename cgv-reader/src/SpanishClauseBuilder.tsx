import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import {
  formatClauseSpan,
  loadTitusClauseVerses,
  readClauseAssignments,
  spanFromRange,
  wordInSpan,
  writeClauseAssignments,
  type ClauseAssignments,
  type SpanishWord
} from "./clause-data";

export default function SpanishClauseBuilder({ onBack }: { onBack: () => void }) {
  const verses = useMemo(() => loadTitusClauseVerses(), []);

  const wordById = useMemo(() => {
    const index = new Map<string, SpanishWord>();
    for (const verse of verses) {
      for (const word of verse.words) index.set(word.id, word);
    }
    return index;
  }, [verses]);

  const finiteVerbs = useMemo(
    () => verses.flatMap(verse => verse.words.filter(word => word.finiteVerbId)),
    [verses]
  );

  const wordsByVerse = useMemo(() => {
    const index = new Map<string, SpanishWord[]>();
    for (const verse of verses) {
      index.set(`${verse.chapter}:${verse.verse}`, verse.words);
    }
    return index;
  }, [verses]);

  const verseTextByKey = useMemo(() => {
    const index = new Map<string, string>();
    for (const verse of verses) {
      index.set(`${verse.chapter}:${verse.verse}`, verse.text);
    }
    return index;
  }, [verses]);

  const [assignments, setAssignments] = useState<ClauseAssignments>(readClauseAssignments);
  const [activeVerbId, setActiveVerbId] = useState<string | null>(
    () => finiteVerbs[0]?.finiteVerbId ?? null
  );
  const [draftSpan, setDraftSpan] = useState<string[]>(() => {
    const firstId = finiteVerbs[0]?.finiteVerbId;
    return firstId ? assignments[firstId]?.selectedSpan ?? [] : [];
  });
  const [rangeAnchorId, setRangeAnchorId] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const isDraggingRef = useRef(false);
  const dragStartIdRef = useRef<string | null>(null);
  const didDragRef = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  const activeVerb = useMemo(
    () => finiteVerbs.find(verb => verb.finiteVerbId === activeVerbId) ?? null,
    [activeVerbId, finiteVerbs]
  );

  const activeVerbPosition = useMemo(() => {
    if (!activeVerbId) return -1;
    return finiteVerbs.findIndex(verb => verb.finiteVerbId === activeVerbId);
  }, [activeVerbId, finiteVerbs]);

  const activeVerseWords = useMemo(() => {
    if (!activeVerb) return [];
    return wordsByVerse.get(`${activeVerb.chapter}:${activeVerb.verse}`) ?? [];
  }, [activeVerb, wordsByVerse]);

  const activeVerseText = useMemo(() => {
    if (!activeVerb) return "";
    return verseTextByKey.get(`${activeVerb.chapter}:${activeVerb.verse}`) ?? "";
  }, [activeVerb, verseTextByKey]);

  const completedCount = useMemo(
    () => finiteVerbs.filter(verb => verb.finiteVerbId && assignments[verb.finiteVerbId]?.selectedSpan.length).length,
    [assignments, finiteVerbs]
  );

  const overlapWordIds = useMemo(() => {
    const counts = new Map<string, number>();
    for (const assignment of Object.values(assignments)) {
      for (const id of assignment.selectedSpan) {
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return new Set(Array.from(counts.entries()).filter(([, count]) => count > 1).map(([id]) => id));
  }, [assignments]);

  const draftText = useMemo(
    () => (draftSpan.length ? formatClauseSpan(draftSpan, activeVerseWords, activeVerseText) : ""),
    [activeVerseText, activeVerseWords, draftSpan]
  );

  const selectVerb = useCallback(
    (verb: SpanishWord) => {
      if (!verb.finiteVerbId) return;
      setActiveVerbId(verb.finiteVerbId);
      setDraftSpan(assignments[verb.finiteVerbId]?.selectedSpan ?? []);
      setRangeAnchorId(null);
      setSavedAt(null);
    },
    [assignments]
  );

  const moveVerb = useCallback(
    (direction: -1 | 1) => {
      if (!finiteVerbs.length) return;
      const current = activeVerbPosition >= 0 ? activeVerbPosition : 0;
      const next = Math.min(Math.max(current + direction, 0), finiteVerbs.length - 1);
      selectVerb(finiteVerbs[next]);
    },
    [activeVerbPosition, finiteVerbs, selectVerb]
  );

  const applySpan = useCallback(
    (start: SpanishWord, end: SpanishWord) => {
      if (!activeVerb) return;
      if (start.chapter !== activeVerb.chapter || start.verse !== activeVerb.verse) return;
      const span = spanFromRange(start, end);
      if (span) setDraftSpan(span);
    },
    [activeVerb]
  );

  const handlePointerDown = useCallback(
    (word: SpanishWord, event: PointerEvent<HTMLButtonElement>) => {
      if (!activeVerb) return;
      if (word.chapter !== activeVerb.chapter || word.verse !== activeVerb.verse) return;
      event.preventDefault();
      didDragRef.current = false;
      setRangeAnchorId(word.id);
      dragStartIdRef.current = word.id;
      isDraggingRef.current = true;
      setIsDragging(true);
      event.currentTarget.setPointerCapture(event.pointerId);
      applySpan(word, word);
    },
    [activeVerb, applySpan]
  );

  const handlePointerEnter = useCallback(
    (word: SpanishWord) => {
      if (!isDraggingRef.current || !dragStartIdRef.current) return;
      const start = wordById.get(dragStartIdRef.current);
      if (!start) return;
      if (start.id !== word.id) didDragRef.current = true;
      applySpan(start, word);
    },
    [applySpan, wordById]
  );

  const handlePointerUp = useCallback((event: PointerEvent<HTMLButtonElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    isDraggingRef.current = false;
    dragStartIdRef.current = null;
    setIsDragging(false);
  }, []);

  const handleWordClick = useCallback(
    (word: SpanishWord, event: MouseEvent<HTMLButtonElement>) => {
      if (word.finiteVerbId) {
        selectVerb(word);
        if (!event.shiftKey) return;
      }
      if (!activeVerb) return;
      if (word.chapter !== activeVerb.chapter || word.verse !== activeVerb.verse) return;
      if (didDragRef.current) {
        didDragRef.current = false;
        return;
      }

      const anchor = event.shiftKey && rangeAnchorId ? wordById.get(rangeAnchorId) : word;
      if (anchor) applySpan(anchor, word);
      setRangeAnchorId(word.id);
    },
    [activeVerb, applySpan, rangeAnchorId, selectVerb, wordById]
  );

  const clearDraft = useCallback(() => {
    setDraftSpan([]);
    setRangeAnchorId(null);
  }, []);

  const saveActive = useCallback(() => {
    if (!activeVerbId || !draftSpan.length) return;
    setAssignments(current => {
      const next = {
        ...current,
        [activeVerbId]: {
          finiteVerbId: activeVerbId,
          selectedSpan: draftSpan
        }
      };
      writeClauseAssignments(next);
      return next;
    });
    setSavedAt(new Date().toLocaleTimeString());
  }, [activeVerbId, draftSpan]);

  useEffect(() => {
    if (!activeVerbId) return;
    setDraftSpan(assignments[activeVerbId]?.selectedSpan ?? []);
  }, [activeVerbId, assignments]);

  return (
    <main className="clause-builder">
      <button type="button" className="prototype-link" onClick={onBack}>
        Reader
      </button>

      <header className="clause-builder-header">
        <p className="reader-kicker">Prototype</p>
        <h1>Spanish Clause Builder</h1>
        <p className="clause-builder-scope">Titus · NBLA</p>
      </header>

      <section className="clause-builder-body" aria-label="Spanish text of Titus">
        {verses.map(verse => (
          <article className="clause-verse" key={`${verse.chapter}:${verse.verse}`}>
            <p className="clause-verse-label">{verse.verse}</p>
            <p className={`clause-verse-text${isDragging ? " clause-verse-text--dragging" : ""}`}>
              {verse.words.map((word, position) => {
                const isActiveVerb = word.finiteVerbId === activeVerbId;
                const inDraft = wordInSpan(word, draftSpan);
                const savedForThisVerb = word.finiteVerbId ? assignments[word.finiteVerbId]?.selectedSpan ?? [] : [];
                const inSaved = wordInSpan(word, savedForThisVerb);
                const overlaps = overlapWordIds.has(word.id);

                let className = "clause-word";
                if (word.finiteVerbId) className += " clause-word--verb";
                if (isActiveVerb) className += " clause-word--active-verb";
                if (inDraft) className += " clause-word--belonging";
                if (inSaved && !inDraft && !isActiveVerb) className += " clause-word--saved";
                if (overlaps) className += " clause-word--overlap";

                return (
                  <span key={word.id}>
                    {position > 0 ? " " : null}
                    <button
                      type="button"
                      className={className}
                      onClick={event => handleWordClick(word, event)}
                      onPointerDown={event => handlePointerDown(word, event)}
                      onPointerEnter={() => handlePointerEnter(word)}
                      onPointerUp={handlePointerUp}
                      aria-pressed={isActiveVerb || inDraft}
                      disabled={
                        !word.finiteVerbId &&
                        (!activeVerb ||
                          word.chapter !== activeVerb.chapter ||
                          word.verse !== activeVerb.verse)
                      }
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
        <div className="clause-panel-topline">
          <div>
            <p className="clause-panel-label">Finite Verbs</p>
            <h2>{completedCount} / {finiteVerbs.length} completed</h2>
          </div>
          <div className="clause-panel-actions">
            <button type="button" onClick={() => moveVerb(-1)} disabled={activeVerbPosition <= 0}>
              Previous Verb
            </button>
            <button
              type="button"
              onClick={() => moveVerb(1)}
              disabled={activeVerbPosition < 0 || activeVerbPosition >= finiteVerbs.length - 1}
            >
              Next Verb
            </button>
          </div>
        </div>

        {activeVerb ? (
          <>
            <p className="clause-active-verb">
              Tito {activeVerb.chapter}:{activeVerb.verse} — <strong>{activeVerb.text}</strong>
            </p>
            <p className="clause-prompt">What words belong to this verb?</p>
            {draftText ? (
              <p className="clause-belonging-list">{draftText}</p>
            ) : (
              <p className="clause-empty">No words selected yet.</p>
            )}
            <div className="clause-panel-actions">
              <button type="button" className="clause-save" onClick={saveActive} disabled={!draftSpan.length}>
                Save
              </button>
              <button type="button" className="clause-clear" onClick={clearDraft}>
                Clear
              </button>
            </div>
            {savedAt ? <p className="clause-saved">Saved {savedAt}</p> : null}
            {draftSpan.some(id => overlapWordIds.has(id)) ? (
              <p className="clause-overlap-note">Overlap noted.</p>
            ) : null}
          </>
        ) : (
          <p className="clause-empty">Click a finite verb to begin.</p>
        )}

        <div className="clause-saved-list" aria-label="Finite verb list">
          {finiteVerbs.map(verb => {
            const assignment = verb.finiteVerbId ? assignments[verb.finiteVerbId] : null;
            const verseWords = wordsByVerse.get(`${verb.chapter}:${verb.verse}`) ?? [];
            const verseText = verseTextByKey.get(`${verb.chapter}:${verb.verse}`) ?? "";
            const spanText = assignment ? formatClauseSpan(assignment.selectedSpan, verseWords, verseText) : "";
            return (
              <button
                type="button"
                className={
                  verb.finiteVerbId === activeVerbId
                    ? "clause-saved-verb clause-saved-verb--active"
                    : "clause-saved-verb"
                }
                key={verb.finiteVerbId}
                onClick={() => selectVerb(verb)}
              >
                <span>{verb.text}</span>
                {spanText ? <small>{spanText}</small> : null}
              </button>
            );
          })}
        </div>
      </aside>
    </main>
  );
}
