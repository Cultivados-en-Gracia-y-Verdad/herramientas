import { useCallback, useEffect, useMemo, useState, type MouseEvent } from "react";
import {
  deriveGreekClauseRange,
  formatClauseSpan,
  getClauseBeginningTokens,
  loadTitusClauseVerses,
  readClauseAssignments,
  readMarkedAlignmentIds,
  spanFromRange,
  wordInSpan,
  writeClauseAssignments,
  type ClauseAssignments,
  type ClauseBeginningToken,
  type GreekClauseRange,
  type SpanishWord
} from "./clause-data";
import {
  detectClauseSignal,
  isLikelyContentParent,
  FRAME_PARTICLES,
  type ClauseSignal,
  type ClauseSignalInput,
  type FrameType
} from "./clause-signals";
import { deriveOutline, deriveSkeleton, deriveTelos, type ClauseSpanInfo, type SkeletonNode } from "./clause-tree";

type ClauseView = "passage" | "clauses";
type ObservationAnswer = "yes" | "no" | "unsure";
type ClauseReviewState = "Unreviewed" | "Reviewed" | "Attached" | "Not sure";

interface ClauseObservation {
  describesNoun?: ObservationAnswer;
  describedNounSpan?: string[];
  isWhatWasExpressed?: ObservationAnswer;
  expressedParentClauseId?: string;
  tellsWhenOrIf?: ObservationAnswer;
  whenIfParentClauseId?: string;
  frameType?: FrameType;
}

type ClauseObservations = Record<string, ClauseObservation>;

interface ClauseOutputRow {
  finiteVerb: SpanishWord;
  reference: string;
  spanText: string;
  selectedWords: SpanishWord[];
  greekRange: GreekClauseRange | null;
  beginningTokens: ClauseBeginningToken[];
  hasDependentIntroducer: boolean;
}

const CLAUSE_OBSERVATIONS_KEY = "the-reader:spanish-clause-builder:titus:statement-command-review:v1";
const COMMAND_MARKS_KEY = "roots:titus:brick2:mood:imperativeCandidates";
const STATEMENT_MARKS_KEY = "roots:titus:brick2c:mood:statementCandidates";
const SUBJUNCTIVE_MARKS_KEY = "roots:titus:brick3:mood:subjunctiveCandidates";
const OPTATIVE_MARKS_KEY = "roots:titus:brick3c:mood:optativeCandidates";

function readClauseObservations(): ClauseObservations {
  try {
    const stored = window.localStorage.getItem(CLAUSE_OBSERVATIONS_KEY);
    const parsed = stored ? JSON.parse(stored) : {};
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};

    const observations: ClauseObservations = {};
    for (const [finiteVerbId, value] of Object.entries(parsed)) {
      if (!value || typeof value !== "object" || Array.isArray(value)) continue;
      const record = value as {
        describesNoun?: unknown;
        describedNounSpan?: unknown;
        isWhatWasExpressed?: unknown;
        expressedParentClauseId?: unknown;
        tellsWhenOrIf?: unknown;
        whenIfParentClauseId?: unknown;
        frameType?: unknown;
      };
      const validFrameTypes = new Set(["time", "reason", "condition", "purpose"]);
      observations[finiteVerbId] = {
        ...(record.describesNoun === "yes" || record.describesNoun === "no" || record.describesNoun === "unsure"
          ? { describesNoun: record.describesNoun }
          : {}),
        ...(Array.isArray(record.describedNounSpan)
          ? { describedNounSpan: record.describedNounSpan.filter((id): id is string => typeof id === "string") }
          : {}),
        ...(record.isWhatWasExpressed === "yes" || record.isWhatWasExpressed === "no" || record.isWhatWasExpressed === "unsure"
          ? { isWhatWasExpressed: record.isWhatWasExpressed }
          : {}),
        ...(typeof record.expressedParentClauseId === "string"
          ? { expressedParentClauseId: record.expressedParentClauseId }
          : {}),
        ...(record.tellsWhenOrIf === "yes" || record.tellsWhenOrIf === "no" || record.tellsWhenOrIf === "unsure"
          ? { tellsWhenOrIf: record.tellsWhenOrIf }
          : {}),
        ...(typeof record.whenIfParentClauseId === "string"
          ? { whenIfParentClauseId: record.whenIfParentClauseId }
          : {}),
        ...(typeof record.frameType === "string" && validFrameTypes.has(record.frameType)
          ? { frameType: record.frameType as FrameType }
          : {})
      };
    }
    return observations;
  } catch {
    return {};
  }
}

function writeClauseObservations(observations: ClauseObservations): void {
  window.localStorage.setItem(CLAUSE_OBSERVATIONS_KEY, JSON.stringify(observations));
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
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

  // Skeleton/outline/telos need every mood-tagged finite clause, not just
  // statement/command — purpose clauses (ἵνα) are subjunctive, and telos is
  // unreachable if subjunctive clauses never enter the review workspace.
  const moodReviewedVerbIds = useMemo(() => {
    const ids = new Set<string>();
    readMarkedAlignmentIds(COMMAND_MARKS_KEY).forEach(id => ids.add(id));
    readMarkedAlignmentIds(STATEMENT_MARKS_KEY).forEach(id => ids.add(id));
    readMarkedAlignmentIds(SUBJUNCTIVE_MARKS_KEY).forEach(id => ids.add(id));
    readMarkedAlignmentIds(OPTATIVE_MARKS_KEY).forEach(id => ids.add(id));
    return ids;
  }, []);

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
  const [activeBeginningVerbId, setActiveBeginningVerbId] = useState<string | null>(null);
  const [observations, setObservations] = useState<ClauseObservations>(readClauseObservations);
  const [nounAnchorId, setNounAnchorId] = useState<string | null>(null);
  const [forceChoices, setForceChoices] = useState(false);
  const [showGreekBeginning, setShowGreekBeginning] = useState(false);

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
      const greekRange =
        assignment?.greekStartTokenId && assignment.greekEndTokenId
          ? {
              greekStartTokenId: assignment.greekStartTokenId,
              greekEndTokenId: assignment.greekEndTokenId
            }
          : assignment
            ? deriveGreekClauseRange(assignment.selectedSpan, verseWords, finiteVerb.finiteVerbId ?? "")
            : null;

      return {
        finiteVerb,
        reference: `Tito ${finiteVerb.chapter}:${finiteVerb.verse}`,
        spanText: assignment ? formatClauseSpan(assignment.selectedSpan, verseWords, verseText) : "",
        selectedWords,
        greekRange,
        beginningTokens: getClauseBeginningTokens(greekRange),
        hasDependentIntroducer: selectedWords.some(word => word.dependentIntroducerId)
      };
    });
  }, [assignments, finiteVerbs, verseTextByKey, wordById, wordsByVerse]);

  const savedClauseRows = useMemo(
    () => clauseRows.filter(row => row.spanText),
    [clauseRows]
  );

  const reviewClauseRows = useMemo(
    () => savedClauseRows.filter(row => {
      const finiteVerbId = row.finiteVerb.finiteVerbId;
      return Boolean(finiteVerbId && statementCommandVerbIds.has(finiteVerbId));
    }),
    [savedClauseRows, statementCommandVerbIds]
  );

  useEffect(() => {
    let changed = false;
    const next = { ...assignments };

    for (const row of clauseRows) {
      const finiteVerbId = row.finiteVerb.finiteVerbId;
      if (!finiteVerbId || !row.greekRange) continue;
      const assignment = next[finiteVerbId];
      if (!assignment || (assignment.greekStartTokenId && assignment.greekEndTokenId)) continue;
      next[finiteVerbId] = {
        ...assignment,
        ...row.greekRange
      };
      changed = true;
    }

    if (!changed) return;
    setAssignments(next);
    writeClauseAssignments(next);
  }, [assignments, clauseRows]);

  const activeBeginningRow = useMemo(
    () => reviewClauseRows.find(row => row.finiteVerb.finiteVerbId === activeBeginningVerbId) ?? null,
    [activeBeginningVerbId, reviewClauseRows]
  );

  const activeObservation = activeBeginningVerbId ? observations[activeBeginningVerbId] ?? {} : {};

  const getClauseReviewState = useCallback(
    (row: ClauseOutputRow): ClauseReviewState => {
      const finiteVerbId = row.finiteVerb.finiteVerbId;
      const observation = finiteVerbId ? observations[finiteVerbId] ?? {} : {};
      const isAttached =
        Boolean(observation.describedNounSpan?.length) ||
        Boolean(observation.expressedParentClauseId) ||
        Boolean(observation.whenIfParentClauseId);
      if (isAttached) return "Attached";
      if (
        observation.describesNoun === "unsure" ||
        observation.isWhatWasExpressed === "unsure" ||
        observation.tellsWhenOrIf === "unsure"
      ) {
        return "Not sure";
      }
      if (observation.describesNoun && observation.isWhatWasExpressed && observation.tellsWhenOrIf) {
        return "Reviewed";
      }
      return "Unreviewed";
    },
    [observations]
  );

  const workspaceClauseRows = useMemo(
    () => reviewClauseRows.filter(row => showDependentLines || getClauseReviewState(row) !== "Attached"),
    [getClauseReviewState, reviewClauseRows, showDependentLines]
  );

  const reviewedCount = useMemo(
    () => reviewClauseRows.filter(row => getClauseReviewState(row) !== "Unreviewed").length,
    [getClauseReviewState, reviewClauseRows]
  );

  const nearbyParentClauseRows = useMemo(() => {
    if (!activeBeginningRow) return [];
    const nearby = reviewClauseRows.filter(row => {
      if (row.finiteVerb.finiteVerbId === activeBeginningRow.finiteVerb.finiteVerbId) return false;
      if (row.finiteVerb.chapter !== activeBeginningRow.finiteVerb.chapter) return false;
      return Math.abs(row.finiteVerb.verse - activeBeginningRow.finiteVerb.verse) <= 2;
    });

    return nearby.length
      ? nearby
      : reviewClauseRows.filter(row => row.finiteVerb.finiteVerbId !== activeBeginningRow.finiteVerb.finiteVerbId);
  }, [activeBeginningRow, reviewClauseRows]);

  const clauseSpanInfos = useMemo<ClauseSpanInfo[]>(
    () =>
      reviewClauseRows
        .filter(row => row.finiteVerb.finiteVerbId)
        .map(row => ({
          finiteVerbId: row.finiteVerb.finiteVerbId as string,
          reference: row.reference,
          spanText: row.spanText,
          wordIds: row.selectedWords.map(word => word.id),
          order: row.finiteVerb.chapter * 100000 + row.finiteVerb.verse * 1000 + row.finiteVerb.index
        })),
    [reviewClauseRows]
  );

  const skeleton = useMemo(() => deriveSkeleton(clauseSpanInfos, observations), [clauseSpanInfos, observations]);
  const outline = useMemo(() => deriveOutline(clauseSpanInfos, observations), [clauseSpanInfos, observations]);
  const telos = useMemo(() => deriveTelos(clauseSpanInfos, observations), [clauseSpanInfos, observations]);

  const clauseSignalInputs = useMemo<ClauseSignalInput[]>(
    () =>
      reviewClauseRows.map(row => ({
        finiteVerbId: row.finiteVerb.finiteVerbId ?? "",
        chapter: row.finiteVerb.chapter,
        verse: row.finiteVerb.verse,
        finiteVerbLemma: row.finiteVerb.greekLemma,
        beginningTokens: row.beginningTokens
      })),
    [reviewClauseRows]
  );

  const activeSignal = useMemo<ClauseSignal | null>(() => {
    const finiteVerbId = activeBeginningRow?.finiteVerb.finiteVerbId;
    if (!finiteVerbId) return null;
    const input = clauseSignalInputs.find(candidate => candidate.finiteVerbId === finiteVerbId);
    if (!input) return null;
    return detectClauseSignal(input, clauseSignalInputs);
  }, [activeBeginningRow, clauseSignalInputs]);

  const activeFrameType = useMemo<FrameType | undefined>(() => {
    const first = activeBeginningRow?.beginningTokens[0];
    if (!first) return undefined;
    return FRAME_PARTICLES[first.lemma.trim()];
  }, [activeBeginningRow]);

  const isActiveClauseRoot =
    activeObservation.describesNoun === "no" &&
    activeObservation.isWhatWasExpressed === "no" &&
    activeObservation.tellsWhenOrIf === "no";

  const activeObservationContextVerses = useMemo(() => {
    if (!activeBeginningRow) return [];
    return verses.filter(verse => {
      if (verse.chapter !== activeBeginningRow.finiteVerb.chapter) return false;
      return Math.abs(verse.verse - activeBeginningRow.finiteVerb.verse) <= 1;
    });
  }, [activeBeginningRow, verses]);

  const describedNounText = useMemo(() => {
    const span = activeObservation.describedNounSpan ?? [];
    if (!span.length) return "";
    const firstWord = wordById.get(span[0]);
    if (!firstWord) return "";
    const verseWords = wordsByVerse.get(`${firstWord.chapter}:${firstWord.verse}`) ?? [];
    const verseText = verseTextByKey.get(`${firstWord.chapter}:${firstWord.verse}`) ?? "";
    return formatClauseSpan(span, verseWords, verseText);
  }, [activeObservation.describedNounSpan, verseTextByKey, wordById, wordsByVerse]);

  useEffect(() => {
    if (view !== "clauses" || activeBeginningVerbId || !reviewClauseRows.length) return;
    const firstOpenRow =
      reviewClauseRows.find(row => getClauseReviewState(row) === "Unreviewed") ?? reviewClauseRows[0];
    setActiveBeginningVerbId(firstOpenRow.finiteVerb.finiteVerbId ?? null);
  }, [activeBeginningVerbId, getClauseReviewState, reviewClauseRows, view]);

  useEffect(() => {
    setForceChoices(false);
    setShowGreekBeginning(false);
    setNounAnchorId(null);
  }, [activeBeginningVerbId]);

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
    const greekRange = deriveGreekClauseRange(draftSpan, activeVerseWords, activeVerbId);
    setAssignments(current => {
      const next = {
        ...current,
        [activeVerbId]: {
          finiteVerbId: activeVerbId,
          selectedSpan: draftSpan,
          ...(greekRange ?? {})
        }
      };
      writeClauseAssignments(next);
      return next;
    });
    setActiveVerbId(null);
    setDraftSpan([]);
    setRangeAnchorId(null);
  }, [activeVerbId, activeVerseWords, draftSpan]);

  useEffect(() => {
    if (!activeVerbId) return;
    setDraftSpan(assignments[activeVerbId]?.selectedSpan ?? []);
  }, [activeVerbId, assignments]);

  const inspectClauseBeginning = useCallback((row: ClauseOutputRow) => {
    if (!row.finiteVerb.finiteVerbId) return;
    setActiveBeginningVerbId(row.finiteVerb.finiteVerbId);
  }, []);

  const updateActiveObservation = useCallback(
    (patch: ClauseObservation) => {
      if (!activeBeginningVerbId) return;
      setObservations(current => {
        const next = {
          ...current,
          [activeBeginningVerbId]: {
            ...(current[activeBeginningVerbId] ?? {}),
            ...patch
          }
        };
        writeClauseObservations(next);
        return next;
      });
    },
    [activeBeginningVerbId]
  );

  const moveToNextClause = useCallback(() => {
    if (!activeBeginningRow) return;
    const currentIndex = reviewClauseRows.findIndex(
      row => row.finiteVerb.finiteVerbId === activeBeginningRow.finiteVerb.finiteVerbId
    );
    const nextOpenRow =
      reviewClauseRows
        .slice(currentIndex + 1)
        .find(row => getClauseReviewState(row) === "Unreviewed") ??
      reviewClauseRows.find(row => getClauseReviewState(row) === "Unreviewed") ??
      reviewClauseRows[currentIndex + 1] ??
      reviewClauseRows[0];
    setActiveBeginningVerbId(nextOpenRow?.finiteVerb.finiteVerbId ?? null);
  }, [activeBeginningRow, getClauseReviewState, reviewClauseRows]);

  // Single-choice classification: pick one shape, first-yes-wins, no separate
  // question for the other two. Choosing "describes"/"content"/"frame" only sets
  // that field to "yes" — the other two stay unset, which is what lets the tree
  // treat a clause as resolved via any one relation rather than requiring all
  // three answered like the old fixed-order flow did.
  const chooseRoot = useCallback(() => {
    updateActiveObservation({ describesNoun: "no", isWhatWasExpressed: "no", tellsWhenOrIf: "no" });
    moveToNextClause();
  }, [moveToNextClause, updateActiveObservation]);

  const chooseDescribes = useCallback(() => {
    setForceChoices(false);
    updateActiveObservation({ describesNoun: "yes" });
  }, [updateActiveObservation]);

  const chooseContent = useCallback(() => {
    setForceChoices(false);
    updateActiveObservation({ isWhatWasExpressed: "yes" });
  }, [updateActiveObservation]);

  const chooseFrame = useCallback(() => {
    setForceChoices(false);
    updateActiveObservation({ tellsWhenOrIf: "yes" });
  }, [updateActiveObservation]);

  const acceptSignal = useCallback(
    (signal: ClauseSignal) => {
      if (signal.kind !== "confident") return;
      if (signal.choice === "describes") {
        updateActiveObservation({ describesNoun: "yes" });
      } else if (signal.choice === "content") {
        updateActiveObservation({ isWhatWasExpressed: "yes", expressedParentClauseId: signal.target });
        moveToNextClause();
      } else if (signal.choice === "frame") {
        updateActiveObservation({
          tellsWhenOrIf: "yes",
          whenIfParentClauseId: signal.target,
          frameType: signal.frameType
        });
        moveToNextClause();
      }
    },
    [moveToNextClause, updateActiveObservation]
  );

  const selectExpressedParent = useCallback(
    (parentClauseId: string) => {
      updateActiveObservation({ expressedParentClauseId: parentClauseId });
    },
    [updateActiveObservation]
  );

  const selectWhenIfParent = useCallback(
    (parentClauseId: string) => {
      updateActiveObservation({ whenIfParentClauseId: parentClauseId, frameType: activeFrameType ?? "reason" });
    },
    [activeFrameType, updateActiveObservation]
  );

  const selectNounWord = useCallback(
    (word: SpanishWord, event: MouseEvent<HTMLButtonElement>) => {
      if (event.shiftKey && nounAnchorId) {
        const anchor = wordById.get(nounAnchorId);
        if (anchor) {
          const span = spanFromRange(anchor, word);
          if (span) updateActiveObservation({ describedNounSpan: span });
          return;
        }
      }

      setNounAnchorId(word.id);
      updateActiveObservation({ describedNounSpan: [word.id] });
    },
    [activeBeginningRow, nounAnchorId, updateActiveObservation, wordById]
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

  const renderSkeletonNode = useCallback(
    (node: SkeletonNode) => {
      const tagLabel =
        node.relation === "describes"
          ? "Relative clause"
          : node.relation === "content"
            ? "Content clause"
            : node.relation === "frame"
              ? `${capitalize(node.frameType ?? "reason")} clause`
              : node.relation === null
                ? "Not yet classified"
                : null;
      return (
        <div className="clause-tree-node-wrap" key={node.finiteVerbId}>
          <button
            type="button"
            className={[
              "clause-tree-node",
              node.relation === null ? "clause-tree-node--placeholder" : "",
              node.finiteVerbId === activeBeginningVerbId ? "clause-tree-node--active" : ""
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => setActiveBeginningVerbId(node.finiteVerbId)}
          >
            {tagLabel ? <span className="clause-tree-tag">{tagLabel}</span> : null}
            <span className="clause-tree-text">{node.spanText || node.reference}</span>
          </button>
          {node.children.length ? (
            <div className="clause-tree-children">{node.children.map(renderSkeletonNode)}</div>
          ) : null}
        </div>
      );
    },
    [activeBeginningVerbId]
  );

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
          Clause Workspace
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
              <h2 id="clause-only-heading">Clause Workspace</h2>
              <p>{reviewedCount} of {reviewClauseRows.length} statement/command clauses reviewed</p>
            </div>
            <label className="clause-dependent-toggle">
              <input
                type="checkbox"
                checked={showDependentLines}
                onChange={event => setShowDependentLines(event.currentTarget.checked)}
              />
              <span>Show attached clauses</span>
            </label>
            <button type="button" className="clause-clear" onClick={() => setView("passage")}>
              Back to Passage
            </button>
          </div>

          <div className="clause-only-workspace">
          <div className="clause-only-main">
            {activeBeginningRow ? (
              <section className="clause-review-panel" aria-label="Clause observation">
                <div className="clause-review-progress">
                  <span>{reviewedCount} of {reviewClauseRows.length} statement/command clauses reviewed</span>
                </div>

                <article className="clause-active-card">
                  <div className="clause-active-card-header">
                    <span>{activeBeginningRow.reference}</span>
                    <button
                      type="button"
                      className="clause-greek-toggle"
                      onClick={() => setShowGreekBeginning(current => !current)}
                    >
                      {showGreekBeginning ? "Hide Greek" : "View Greek"}
                    </button>
                  </div>
                  <p className="clause-active-span">{renderClauseLine(activeBeginningRow)}</p>
                </article>

                {showGreekBeginning && activeBeginningRow.beginningTokens.length ? (
                  <div
                    className="clause-beginning-grid clause-beginning-grid--inline"
                    style={{ gridTemplateColumns: `auto repeat(${activeBeginningRow.beginningTokens.length}, max-content)` }}
                  >
                    <span className="clause-beginning-label">Greek</span>
                    {activeBeginningRow.beginningTokens.map((token, index) => (
                      <span
                        className={index === 0 ? "clause-beginning-token clause-beginning-token--first" : "clause-beginning-token"}
                        key={`greek-${token.id}`}
                      >
                        {token.greek}
                      </span>
                    ))}
                    <span className="clause-beginning-label">BLE</span>
                    {activeBeginningRow.beginningTokens.map(token => (
                      <span className="clause-beginning-token clause-beginning-token--ble" key={`ble-${token.id}`}>
                        {token.ble}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="clause-context-panel" aria-label="Surrounding Spanish context">
                  {activeObservationContextVerses.map(verse => (
                    <p className="clause-noun-verse" key={`${verse.chapter}:${verse.verse}`}>
                      <span className="clause-noun-verse-label">{verse.verse}</span>
                      <span>
                        {verse.words.map((word, position) => {
                          const canSelectNoun = activeObservation.describesNoun === "yes";
                          const isSelected = Boolean(activeObservation.describedNounSpan?.includes(word.id));
                          return (
                            <span key={word.id}>
                              {position > 0 ? " " : null}
                              {canSelectNoun ? (
                                <button
                                  type="button"
                                  className={isSelected ? "clause-noun-word clause-noun-word--selected" : "clause-noun-word"}
                                  onClick={event => selectNounWord(word, event)}
                                >
                                  {word.text}
                                </button>
                              ) : (
                                <span className={activeBeginningRow.selectedWords.some(selected => selected.id === word.id) ? "clause-context-word clause-context-word--active" : "clause-context-word"}>
                                  {word.text}
                                </span>
                              )}
                            </span>
                          );
                        })}
                      </span>
                    </p>
                  ))}
                </div>

                <section className="clause-observation" aria-label="Current observation">
                  {activeObservation.describesNoun === "yes" ? (
                    <div className="clause-noun-picker">
                      <p className="clause-observation-term">Relative clause</p>
                      <p>Select the noun this clause describes, in the text above.</p>
                      {describedNounText ? <p className="clause-noun-selection">{describedNounText}</p> : null}
                      <div className="clause-step-actions">
                        <button
                          type="button"
                          className="clause-step-save"
                          disabled={!activeObservation.describedNounSpan?.length}
                          onClick={moveToNextClause}
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          className="clause-reconsider"
                          onClick={() => {
                            setNounAnchorId(null);
                            updateActiveObservation({ describesNoun: undefined, describedNounSpan: [] });
                          }}
                        >
                          Not this — reconsider
                        </button>
                      </div>
                    </div>
                  ) : activeObservation.isWhatWasExpressed === "yes" ? (
                    <div className="clause-parent-picker">
                      <p className="clause-observation-term">Content clause</p>
                      <p>Select the clause this is the content of.</p>
                      <div className="clause-parent-list">
                        {nearbyParentClauseRows.map(row => (
                          <button
                            type="button"
                            className={[
                              "clause-parent-option",
                              activeObservation.expressedParentClauseId === row.finiteVerb.finiteVerbId
                                ? "clause-parent-option--selected"
                                : "",
                              isLikelyContentParent({ finiteVerbLemma: row.finiteVerb.greekLemma })
                                ? "clause-parent-option--likely"
                                : ""
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            key={row.finiteVerb.finiteVerbId}
                            onClick={() => row.finiteVerb.finiteVerbId && selectExpressedParent(row.finiteVerb.finiteVerbId)}
                          >
                            <span>{row.reference}</span>
                            {row.spanText}
                          </button>
                        ))}
                      </div>
                      <div className="clause-step-actions">
                        <button
                          type="button"
                          className="clause-step-save"
                          disabled={!activeObservation.expressedParentClauseId}
                          onClick={moveToNextClause}
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          className="clause-reconsider"
                          onClick={() => updateActiveObservation({ isWhatWasExpressed: undefined, expressedParentClauseId: "" })}
                        >
                          Not this — reconsider
                        </button>
                      </div>
                    </div>
                  ) : activeObservation.tellsWhenOrIf === "yes" ? (
                    <div className="clause-parent-picker">
                      <p className="clause-observation-term">
                        {activeObservation.frameType ? `${capitalize(activeObservation.frameType)} clause` : "Adverbial clause"}
                      </p>
                      <p>Select the clause this explains — its time, reason, condition, or purpose.</p>
                      <div className="clause-parent-list">
                        {nearbyParentClauseRows.map(row => (
                          <button
                            type="button"
                            className={activeObservation.whenIfParentClauseId === row.finiteVerb.finiteVerbId ? "clause-parent-option clause-parent-option--selected" : "clause-parent-option"}
                            key={row.finiteVerb.finiteVerbId}
                            onClick={() => row.finiteVerb.finiteVerbId && selectWhenIfParent(row.finiteVerb.finiteVerbId)}
                          >
                            <span>{row.reference}</span>
                            {row.spanText}
                          </button>
                        ))}
                      </div>
                      <div className="clause-step-actions">
                        <button
                          type="button"
                          className="clause-step-save"
                          disabled={!activeObservation.whenIfParentClauseId}
                          onClick={moveToNextClause}
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          className="clause-reconsider"
                          onClick={() => updateActiveObservation({ tellsWhenOrIf: undefined, whenIfParentClauseId: "", frameType: undefined })}
                        >
                          Not this — reconsider
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {isActiveClauseRoot ? (
                        <p className="clause-tutor-note">Currently: stands on its own (independent clause).</p>
                      ) : null}

                      {!forceChoices && !isActiveClauseRoot && activeSignal && activeSignal.kind === "confident" ? (
                        <div className="clause-proposal">
                          <p className="clause-proposal-label">
                            {activeSignal.choice === "describes"
                              ? "Relative clause"
                              : activeSignal.choice === "content"
                                ? "Content clause"
                                : `${capitalize(activeSignal.frameType)} clause`}
                          </p>
                          <p className="clause-proposal-reason">{activeSignal.reason}</p>
                          <div className="clause-step-actions">
                            <button type="button" className="clause-step-save" onClick={() => acceptSignal(activeSignal)}>
                              Yes, that's it
                            </button>
                            <button type="button" className="clause-reconsider" onClick={() => setForceChoices(true)}>
                              Not quite — show me the options
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          {!forceChoices && !isActiveClauseRoot && activeSignal?.kind === "uncertain" ? (
                            <p className="clause-uncertain-note">{activeSignal.reason}</p>
                          ) : null}
                          {!forceChoices && !isActiveClauseRoot && activeSignal?.kind === "none" ? (
                            <p className="clause-tutor-note">{activeSignal.reason}</p>
                          ) : null}
                          {forceChoices ? (
                            <p className="clause-tutor-note">No problem — pick the shape that actually fits.</p>
                          ) : null}

                          <div className="clause-choice-grid">
                            <button type="button" className="clause-choice-btn" onClick={chooseDescribes}>
                              <span className="clause-choice-term">Relative clause</span>
                              Describes something nearby
                            </button>
                            <button type="button" className="clause-choice-btn" onClick={chooseContent}>
                              <span className="clause-choice-term">Content clause</span>
                              Reports what was said or thought
                            </button>
                            <button type="button" className="clause-choice-btn" onClick={chooseFrame}>
                              <span className="clause-choice-term">Adverbial clause</span>
                              Gives a when, why, if, or so-that
                            </button>
                            <button type="button" className="clause-choice-btn" onClick={chooseRoot}>
                              <span className="clause-choice-term">Independent clause</span>
                              Stands on its own
                            </button>
                          </div>
                        </>
                      )}
                    </>
                  )}
                </section>
              </section>
            ) : (
              <p className="clause-output-empty">No statement or command clauses ready for review.</p>
            )}

            {workspaceClauseRows.length ? (
              <div className="clause-only-list" aria-label="Saved clause spans">
                {workspaceClauseRows.map(row => {
                  const reviewState = getClauseReviewState(row);
                  return (
                    <button
                      type="button"
                      className={[
                        "clause-only-item",
                        row.finiteVerb.finiteVerbId === activeBeginningVerbId ? "clause-only-item--inspecting" : ""
                      ].filter(Boolean).join(" ")}
                      key={row.finiteVerb.finiteVerbId}
                      onClick={() => inspectClauseBeginning(row)}
                    >
                      <span className="clause-line-reference">{row.reference}</span>
                      <span className="clause-only-text">{renderClauseLine(row)}</span>
                      <span className={`clause-review-state clause-review-state--${reviewState.toLowerCase().replace(/\s/g, "-")}`}>
                        {reviewState}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="clause-output-empty">No visible statement or command clauses.</p>
            )}
          </div>

          <aside className="clause-skeleton-panel" aria-label="Skeleton">
            <div className="clause-skeleton-header">
              <h2>Skeleton</h2>
              {skeleton.roots.length ? (
                <span className="clause-skeleton-count">
                  {skeleton.roots.length} root{skeleton.roots.length === 1 ? "" : "s"}
                </span>
              ) : null}
            </div>

            {skeleton.roots.length ? (
              <div className="clause-tree">{skeleton.roots.map(renderSkeletonNode)}</div>
            ) : (
              <p className="clause-output-empty">
                Nothing placed yet. Classify a clause as Independent, or as content/frame pointing at one, and it
                shows up here.
              </p>
            )}

            {outline.length ? (
              <div className="clause-outline-section">
                <h3>Outline</h3>
                <p className="clause-section-note">
                  Just the root clauses, book order — everything indented stripped out of the skeleton above.
                </p>
                {outline.map(clause => (
                  <p className="clause-outline-item" key={clause.finiteVerbId}>
                    <span>{clause.reference}</span>
                    {clause.spanText}
                  </p>
                ))}
              </div>
            ) : null}

            {skeleton.parked.length ? (
              <div className="clause-parked-section">
                <h3>Not yet placed in the skeleton</h3>
                <p className="clause-section-note">
                  These describe a noun that isn't inside any indexed clause yet — often material like Tito 1:1 that
                  has no finite verb of its own. Nothing to do here now; they get connected during closer clause-level
                  work later, once the skeleton around them is settled.
                </p>
                {skeleton.parked.map(parked => (
                  <p className="clause-parked-item" key={parked.finiteVerbId}>
                    <span>{parked.reference}</span>
                    {parked.spanText}
                  </p>
                ))}
              </div>
            ) : null}

            {telos ? (
              <div className="clause-telos-section">
                <h3>Candidate telos</h3>
                <p className="clause-telos-item">{telos.purposeClause.spanText}</p>
                {telos.lastOutlineClause ? (
                  <>
                    <p className="clause-telos-vs">compare with the outline's last point</p>
                    <p className="clause-telos-item clause-telos-item--outline">{telos.lastOutlineClause.spanText}</p>
                  </>
                ) : null}
                <p className="clause-telos-note">
                  Does this look like the book's stated purpose? That's your call, not something the software concludes.
                </p>
              </div>
            ) : null}
          </aside>
        </div>
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
