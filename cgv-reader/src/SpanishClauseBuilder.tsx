import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
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

type ClauseView = "passage" | "clauses";

interface ClauseOutputRow {
  finiteVerb: SpanishWord;
  reference: string;
  spanText: string;
  selectedWords: SpanishWord[];
  hasDependentIntroducer: boolean;
}

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
  const [activeVerbId, setActiveVerbId] = useState<string | null>(null);
  const [draftSpan, setDraftSpan] = useState<string[]>([]);
  const [rangeAnchorId, setRangeAnchorId] = useState<string | null>(null);
  const [view, setView] = useState<ClauseView>("passage");
  const [showDependentLines, setShowDependentLines] = useState(true);

  const activeVerb = useMemo(
    () => finiteVerbs.find(verb => verb.finiteVerbId === activeVerbId) ?? null,
    [activeVerbId, finiteVerbs]
  );

  const activeVerseWords = useMemo(() => {
    if (!activeVerb) return [];
    return wordsByVerse.get(`${activeVerb.chapter}:${activeVerb.verse}`) ?? [];
  }, [activeVerb, wordsByVerse]);

  const activeVerseText = useMemo(() => {
    if (!activeVerb) return "";
    return verseTextByKey.get(`${activeVerb.chapter}:${activeVerb.verse}`) ?? "";
  }, [activeVerb, verseTextByKey]);

  const overlapWordIds = useMemo(() => {
    const counts = new Map<string, number>();
    for (const assignment of Object.values(assignments)) {
      for (const id of assignment.selectedSpan) {
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return new Set(Array.from(counts.entries()).filter(([, count]) => count > 1).map(([id]) => id));
  }, [assignments]);

  const savedWordIds = useMemo(() => {
    const ids = new Set<string>();
    for (const assignment of Object.values(assignments)) {
      assignment.selectedSpan.forEach(id => ids.add(id));
    }
    return ids;
  }, [assignments]);

  const draftText = useMemo(
    () => (draftSpan.length ? formatClauseSpan(draftSpan, activeVerseWords, activeVerseText) : ""),
    [activeVerseText, activeVerseWords, draftSpan]
  );

  const clauseRows = useMemo<ClauseOutputRow[]>(() => {
    return finiteVerbs.map(finiteVerb => {
      const assignment = finiteVerb.finiteVerbId ? assignments[finiteVerb.finiteVerbId] : null;
      const verseKey = `${finiteVerb.chapter}:${finiteVerb.verse}`;
      const verseWords = wordsByVerse.get(verseKey) ?? [];
      const verseText = verseTextByKey.get(verseKey) ?? "";
      const selectedWords = assignment
        ? assignment.selectedSpan
            .map(id => wordById.get(id))
            .filter((word): word is SpanishWord => Boolean(word))
            .sort((a, b) => a.index - b.index)
        : [];

      return {
        finiteVerb,
        reference: `Tito ${finiteVerb.chapter}:${finiteVerb.verse}`,
        spanText: assignment ? formatClauseSpan(assignment.selectedSpan, verseWords, verseText) : "",
        selectedWords,
        hasDependentIntroducer: selectedWords.some(word => word.dependentIntroducerId)
      };
    });
  }, [assignments, finiteVerbs, verseTextByKey, wordById, wordsByVerse]);

  const savedClauseRows = useMemo(
    () => clauseRows.filter(row => row.spanText),
    [clauseRows]
  );

  const workspaceClauseRows = useMemo(
    () => savedClauseRows.filter(row => showDependentLines || !row.hasDependentIntroducer),
    [savedClauseRows, showDependentLines]
  );

  const selectVerb = useCallback(
    (verb: SpanishWord) => {
      if (!verb.finiteVerbId) return;
      setActiveVerbId(verb.finiteVerbId);
      setDraftSpan(assignments[verb.finiteVerbId]?.selectedSpan ?? []);
      setRangeAnchorId(verb.id);

      window.setTimeout(() => {
        document
          .querySelector<HTMLElement>(`[data-clause-word-id="${verb.id}"]`)
          ?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
      }, 20);
    },
    [assignments]
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

  const handleWordClick = useCallback(
    (word: SpanishWord, event: MouseEvent<HTMLButtonElement>) => {
      const isInActiveVerse =
        activeVerb && word.chapter === activeVerb.chapter && word.verse === activeVerb.verse;

      if (event.shiftKey && isInActiveVerse) {
        const anchor = rangeAnchorId ? wordById.get(rangeAnchorId) : activeVerb;
        if (anchor) applySpan(anchor, word);
        return;
      }

      if (word.finiteVerbId) {
        selectVerb(word);
        return;
      }

      if (!isInActiveVerse) return;
      applySpan(word, word);
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
    setActiveVerbId(null);
    setDraftSpan([]);
    setRangeAnchorId(null);
  }, [activeVerbId, draftSpan]);

  useEffect(() => {
    if (!activeVerbId) return;
    setDraftSpan(assignments[activeVerbId]?.selectedSpan ?? []);
  }, [activeVerbId, assignments]);

  const openPassageForVerb = useCallback(
    (verb: SpanishWord) => {
      setView("passage");
      selectVerb(verb);
    },
    [selectVerb]
  );

  const renderClauseLine = useCallback((row: ClauseOutputRow) => {
    return row.selectedWords.map((word, index) => {
      let className = "";
      if (word.finiteVerbId === row.finiteVerb.finiteVerbId) className += " clause-line-token--finite";
      if (word.dependentIntroducerId) className += " clause-line-token--dependent";

      return (
        <span className={className.trim() || undefined} key={word.id}>
          {index > 0 ? " " : null}
          {word.text}
        </span>
      );
    });
  }, []);

  return (
    <main className="clause-builder">
      <button type="button" className="prototype-link" onClick={onBack}>
        Reader
      </button>

      <header className="clause-builder-header">
        <p className="reader-kicker">Prototype</p>
        <h1>Tito</h1>
        <p className="clause-builder-scope">Titus · NBLA</p>
      </header>

      <div className="clause-view-switch" aria-label="Clause workspace view">
        <button
          type="button"
          className={view === "passage" ? "clause-view-option clause-view-option--active" : "clause-view-option"}
          onClick={() => setView("passage")}
        >
          Passage
        </button>
        <button
          type="button"
          className={view === "clauses" ? "clause-view-option clause-view-option--active" : "clause-view-option"}
          onClick={() => setView("clauses")}
          disabled={!savedClauseRows.length}
        >
          Clauses
        </button>
      </div>

      {view === "passage" ? (
        <div className="clause-workspace">
        <section className="clause-builder-body" aria-label="Spanish text of Titus">
          {verses.map(verse => (
            <article className="clause-verse" key={`${verse.chapter}:${verse.verse}`}>
              <p className="clause-verse-label">{verse.verse}</p>
              <p className="clause-verse-text">
                {verse.words.map((word, position) => {
                  const isActiveVerb = Boolean(activeVerbId && word.finiteVerbId === activeVerbId);
                  const inDraft = wordInSpan(word, draftSpan);
                  const isSavedVerb = Boolean(word.finiteVerbId && assignments[word.finiteVerbId]?.selectedSpan.length);
                  const inSaved = savedWordIds.has(word.id);
                  const overlaps = overlapWordIds.has(word.id);

                  let className = "clause-word";
                  if (word.finiteVerbId) className += " clause-word--verb";
                  if (isSavedVerb) className += " clause-word--verb-saved";
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
                        aria-pressed={isActiveVerb || inDraft}
                        data-clause-word-id={word.id}
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

        <aside className="clause-output" aria-label="Clause output">
          <section className="clause-output-section" aria-labelledby="clause-register-heading">
            <h2 id="clause-register-heading">Clause Register</h2>
            <div className="clause-register-list">
              {clauseRows.length ? (
                clauseRows.map(row => (
                  <button
                    type="button"
                    className={`clause-register-item${row.finiteVerb.finiteVerbId === activeVerbId ? " clause-register-item--active" : ""}`}
                    key={row.finiteVerb.finiteVerbId}
                    onClick={() => selectVerb(row.finiteVerb)}
                  >
                    <span className="clause-output-meta">
                      {row.reference} · {row.finiteVerb.text}
                    </span>
                    <span className={row.spanText ? "clause-register-span" : "clause-register-span clause-register-span--empty"}>
                      {row.spanText || "Unsaved"}
                    </span>
                  </button>
                ))
              ) : (
                <p className="clause-output-empty">No Brick 1 finite verbs marked yet.</p>
              )}
            </div>
          </section>

          <section className="clause-output-section" aria-labelledby="clause-reader-heading">
            <h2 id="clause-reader-heading">Clause Reader</h2>
            <div className="clause-chain">
              {savedClauseRows.length ? (
                savedClauseRows.map(row => (
                  <p
                    className="clause-chain-line"
                    key={row.finiteVerb.finiteVerbId}
                  >
                    <span className="clause-output-meta">
                      {row.reference} · {row.finiteVerb.text}
                    </span>
                    <span>{row.spanText}</span>
                  </p>
                ))
              ) : (
                <p className="clause-output-empty">No saved spans yet.</p>
              )}
            </div>
          </section>
        </aside>
        </div>
      ) : (
        <section className="clause-only-view" aria-labelledby="clause-only-heading">
          <div className="clause-only-header">
            <div>
              <h2 id="clause-only-heading">Clause Chain</h2>
            </div>
            <label className="clause-dependent-toggle">
              <input
                type="checkbox"
                checked={showDependentLines}
                onChange={event => setShowDependentLines(event.currentTarget.checked)}
              />
              <span>Show dependent lines</span>
            </label>
            <button type="button" className="clause-clear" onClick={() => setView("passage")}>
              Back to Passage
            </button>
          </div>

          {workspaceClauseRows.length ? (
            <div className="clause-only-list" aria-label="Saved clause spans">
              {workspaceClauseRows.map(row => (
                <button
                  type="button"
                  className={`clause-only-item${row.hasDependentIntroducer ? " clause-only-item--dependent" : ""}`}
                  key={row.finiteVerb.finiteVerbId}
                  onClick={() => openPassageForVerb(row.finiteVerb)}
                >
                  <span className="clause-only-meta">{row.reference} · {row.finiteVerb.text}</span>
                  <span className="clause-only-text">{renderClauseLine(row)}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="clause-output-empty">No active saved clauses.</p>
          )}
        </section>
      )}

      {view === "passage" && activeVerb ? (
        <aside className="clause-selection-panel" aria-live="polite">
          <p className="clause-active-verb">
            <span>Tito {activeVerb.chapter}:{activeVerb.verse}</span>
            <strong>{activeVerb.text}</strong>
          </p>
          {draftText ? (
            <p className="clause-belonging-list">{draftText}</p>
          ) : (
            <p className="clause-empty">No words selected.</p>
          )}
          <div className="clause-panel-actions">
            <button type="button" className="clause-save" onClick={saveActive} disabled={!draftSpan.length}>
              Save
            </button>
            <button type="button" className="clause-clear" onClick={clearDraft}>
              Clear
            </button>
          </div>
          {draftSpan.some(id => overlapWordIds.has(id)) ? (
            <p className="clause-overlap-note">Overlap noted.</p>
          ) : null}
        </aside>
      ) : null}
    </main>
  );
}
