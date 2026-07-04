import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { BibleVerse } from "cgv-bible";
import { dependentThoughtIntroducers } from "./o-brick-config";
import SpanishClauseBuilder from "./SpanishClauseBuilder";
import { loadTitus } from "./reader-data";
import { loadTitusData, type GreekToken, type GreekVerse } from "./o-data";

interface ReaderNote {
  id: string;
  target: string;
  label: string;
  text: string;
  updatedAt: string;
}

interface NoteTarget {
  key: string;
  label: string;
}

type ViewMode = "reader" | "o" | "clause";
type ParticipationMode =
  | "finite"
  | "mood-commands"
  | "mood-statements"
  | "command-recipients"
  | "dependent-thoughts";
type StatementLens = "All finite verbs" | "Statements only" | "Commands only";

interface CommandRecipientGroup {
  id: string;
  recipient: string;
  tokenIds: string[];
}

const NOTES_KEY = "the-reader:titus:notes";
const MARKS_KEY = "o-prototype:titus:finite-verb-marks";
const COMMAND_MARKS_KEY = "roots:titus:brick2:mood:imperativeCandidates";
const STATEMENT_MARKS_KEY = "roots:titus:brick2c:mood:statementCandidates";
const COMMAND_RECIPIENTS_KEY = "roots:titus:brick2b:commandRecipients";
const DEPENDENT_THOUGHT_MARKS_KEY = "roots:titus:brick3:dependentThoughtIntroducers";
const STATEMENT_LENSES: StatementLens[] = ["All finite verbs", "Statements only", "Commands only"];
const RECIPIENTS = [
  "Titus",
  "Elders",
  "Older Men",
  "Older Women",
  "Younger Women",
  "Younger Men",
  "Bondservants",
  "Everyone",
  "Other"
];
const DEPENDENT_THOUGHT_CANDIDATES = new Map(
  dependentThoughtIntroducers.map(candidate => [
    candidate.surface,
    candidate.tokenIds ? new Set(candidate.tokenIds) : null
  ])
);

function readViewFromHash(): ViewMode {
  if (window.location.hash === "#o") return "o";
  if (window.location.hash === "#clause") return "clause";
  return "reader";
}

function verseKey(verse: BibleVerse): string {
  return `${verse.book}.${verse.chapter}.${verse.verse}`;
}

function verseLabel(verse: BibleVerse): string {
  return `${verse.book} ${verse.chapter}:${verse.verse}`;
}

function targetContainsVerse(target: string, key: string): boolean {
  const [start, end] = target.split("--");
  if (!end) return target === key;
  return key >= start && key <= end;
}

function readNotes(): ReaderNote[] {
  try {
    const stored = window.localStorage.getItem(NOTES_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function makeNoteId(): string {
  if ("crypto" in window && "randomUUID" in window.crypto) {
    return window.crypto.randomUUID();
  }
  return `note-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function makeLocalId(prefix: string): string {
  if ("crypto" in window && "randomUUID" in window.crypto) {
    return `${prefix}-${window.crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function readMarks(storageKey: string): string[] {
  try {
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed.filter(item => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function readCommandRecipientGroups(): CommandRecipientGroup[] {
  try {
    const stored = window.localStorage.getItem(COMMAND_RECIPIENTS_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is CommandRecipientGroup => {
      return (
        item &&
        typeof item.id === "string" &&
        typeof item.recipient === "string" &&
        Array.isArray(item.tokenIds) &&
        item.tokenIds.every((tokenId: unknown) => typeof tokenId === "string")
      );
    });
  } catch {
    return [];
  }
}

function stripCriticalMarks(value: string): string {
  return value.replace(/[⸀⸁⸂⸃,.;·]/g, "");
}

function tokenText(token: GreekToken): string {
  return stripCriticalMarks(token.surface);
}

function tokenLabel(token: GreekToken): string {
  return `${tokenText(token)} ${token.rmac}`;
}

function isDependentThoughtCandidate(token: GreekToken): boolean {
  const configuredTokenIds = DEPENDENT_THOUGHT_CANDIDATES.get(tokenText(token));
  if (configuredTokenIds === undefined) return false;
  return configuredTokenIds === null || configuredTokenIds.has(token.id);
}

function personNumberMeaning(rmac: string): string | null {
  const match = rmac.match(/^V-[A-Z]{3}-(1|2|3)(S|P)$/);
  if (!match) return null;

  const [, person, number] = match;
  const meanings: Record<string, string> = {
    "1S": "I",
    "1P": "we",
    "2S": "you (singular)",
    "2P": "you (plural)",
    "3S": "he/she/it",
    "3P": "they"
  };

  const code = `${person}${number}`;
  return `${code} means ${meanings[code]}`;
}

interface GreekTokenButtonProps {
  disabled?: boolean;
  isPressed: boolean;
  markClassName: string;
  onToggle: (token: GreekToken, verse: GreekVerse) => void;
  token: GreekToken;
  verse: GreekVerse;
}

const GreekTokenButton = memo(function GreekTokenButton({
  disabled = false,
  isPressed,
  markClassName,
  onToggle,
  token,
  verse
}: GreekTokenButtonProps) {
  return (
    <button
      type="button"
      className={`greek-token${markClassName ? ` ${markClassName}` : ""}`}
      disabled={disabled}
      onClick={() => onToggle(token, verse)}
      aria-pressed={isPressed}
      aria-label={tokenLabel(token)}
      title={`${token.rmac} (RMAC/Robinson)`}
      data-token-id={token.id}
    >
      <span className="token-surface">{token.surface}</span>
      <span className="token-morph">{token.rmac}</span>
    </button>
  );
});

export default function ReaderApp() {
  const [view, setView] = useState<ViewMode>(readViewFromHash);

  useEffect(() => {
    const onHashChange = () => setView(readViewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function openView(nextView: ViewMode) {
    if (nextView === "o") {
      window.location.hash = "o";
    } else if (nextView === "clause") {
      window.location.hash = "clause";
    } else {
      window.history.pushState(null, "", window.location.pathname);
    }
    setView(nextView);
  }

  if (view === "clause") {
    return <SpanishClauseBuilder onBack={() => openView("reader")} />;
  }

  return view === "o" ? (
    <OPrototype onBackToReader={() => openView("reader")} />
  ) : (
    <ReaderView onOpenO={() => openView("o")} onOpenClause={() => openView("clause")} />
  );
}

function ReaderView({ onOpenO, onOpenClause }: { onOpenO: () => void; onOpenClause: () => void }) {
  const book = useMemo(() => loadTitus(), []);
  const [notes, setNotes] = useState<ReaderNote[]>(readNotes);
  const [activeTarget, setActiveTarget] = useState<NoteTarget | null>(null);
  const [draft, setDraft] = useState("");
  const noteInputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    window.localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
  }, [notes]);

  useEffect(() => {
    if (!activeTarget) return;
    const existing = notes.find(note => note.target === activeTarget.key);
    setDraft(existing?.text ?? "");
    window.setTimeout(() => noteInputRef.current?.focus(), 60);
  }, [activeTarget, notes]);

  const chapters = useMemo(() => {
    const grouped = new Map<number, BibleVerse[]>();
    for (const verse of book.verses) {
      const chapter = grouped.get(verse.chapter) ?? [];
      chapter.push(verse);
      grouped.set(verse.chapter, chapter);
    }
    return Array.from(grouped.entries());
  }, [book.verses]);

  const notesByVerse = useMemo(() => {
    const grouped = new Map<string, ReaderNote[]>();
    for (const verse of book.verses) {
      const key = verseKey(verse);
      grouped.set(
        key,
        notes.filter(note => targetContainsVerse(note.target, key))
      );
    }
    return grouped;
  }, [book.verses, notes]);

  function openVerseNote(verse: BibleVerse) {
    setActiveTarget({ key: verseKey(verse), label: verseLabel(verse) });
  }

  function saveDraft() {
    if (!activeTarget) return;

    const text = draft.trim();
    setNotes(current => {
      const withoutTarget = current.filter(note => note.target !== activeTarget.key);
      if (!text) return withoutTarget;
      return [
        ...withoutTarget,
        {
          id: current.find(note => note.target === activeTarget.key)?.id ?? makeNoteId(),
          target: activeTarget.key,
          label: activeTarget.label,
          text,
          updatedAt: new Date().toISOString()
        }
      ];
    });
    setActiveTarget(null);
    setDraft("");
  }

  function removeActiveNote() {
    if (!activeTarget) return;
    setNotes(current => current.filter(note => note.target !== activeTarget.key));
    setActiveTarget(null);
    setDraft("");
  }

  return (
    <main className="reader-shell">
      <button type="button" className="prototype-link" onClick={onOpenO}>
        O Prototype
      </button>
      <button type="button" className="prototype-link clause-link" onClick={onOpenClause}>
        Clause Builder
      </button>
      <article className="reader-page" aria-label="The Reader">
        <header className="reader-header">
          <p className="reader-kicker">The Reader</p>
          <h1>{book.title}</h1>
          <p className="reader-version">{book.version}</p>
        </header>

        <div className="reader-book">
          {chapters.map(([chapter, verses]) => (
            <section className="reader-chapter" key={chapter} aria-labelledby={`chapter-${chapter}`}>
              <h2 id={`chapter-${chapter}`}>{chapter}</h2>
              {verses.map(verse => {
                const key = verseKey(verse);
                const verseNotes = notesByVerse.get(key) ?? [];

                return (
                  <div
                    className={`reader-line${activeTarget?.key === key ? " reader-line--active" : ""}`}
                    key={key}
                  >
                    <button
                      type="button"
                      className={`reader-note-mark${verseNotes.length ? " reader-note-mark--has-note" : ""}`}
                      onClick={() => openVerseNote(verse)}
                      aria-label={`Nota para ${verseLabel(verse)}`}
                    >
                      {verseNotes.length ? "*" : "+"}
                    </button>
                    <p className="reader-verse" onClick={() => openVerseNote(verse)}>
                      <sup>{verse.verse}</sup>
                      {verse.text}
                    </p>
                    <aside className="reader-margin-notes" aria-label={`Notas de ${verseLabel(verse)}`}>
                      {verseNotes.map(note => (
                        <button
                          type="button"
                          className="reader-note"
                          key={note.id}
                          onClick={() => setActiveTarget({ key: note.target, label: note.label })}
                        >
                          {note.text}
                        </button>
                      ))}
                    </aside>
                  </div>
                );
              })}
            </section>
          ))}
        </div>
      </article>

      {activeTarget && (
        <div className="reader-note-panel" role="dialog" aria-label={`Nota para ${activeTarget.label}`}>
          <div className="reader-note-panel-inner">
            <p>{activeTarget.label}</p>
            <textarea
              ref={noteInputRef}
              value={draft}
              onChange={event => setDraft(event.currentTarget.value)}
              placeholder="Escriba una nota breve..."
            />
            <div className="reader-note-actions">
              <button type="button" onClick={() => setActiveTarget(null)}>
                Cerrar
              </button>
              <button type="button" onClick={removeActiveNote}>
                Borrar
              </button>
              <button type="button" className="reader-note-save" onClick={saveDraft}>
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function OPrototype({ onBackToReader }: { onBackToReader: () => void }) {
  const data = useMemo(() => loadTitusData(), []);
  const [participation, setParticipation] = useState<ParticipationMode>("finite");
  const [finiteMarkedIds, setFiniteMarkedIds] = useState<Set<string>>(
    () => new Set(readMarks(MARKS_KEY))
  );
  const [commandMarkedIds, setCommandMarkedIds] = useState<Set<string>>(
    () => new Set(readMarks(COMMAND_MARKS_KEY))
  );
  const [statementMarkedIds, setStatementMarkedIds] = useState<Set<string>>(
    () => new Set(readMarks(STATEMENT_MARKS_KEY))
  );
  const [dependentThoughtMarkedIds, setDependentThoughtMarkedIds] = useState<Set<string>>(
    () => new Set(readMarks(DEPENDENT_THOUGHT_MARKS_KEY))
  );
  const [commandRecipientGroups, setCommandRecipientGroups] = useState<CommandRecipientGroup[]>(
    readCommandRecipientGroups
  );
  const [statementLens, setStatementLens] = useState<StatementLens>("All finite verbs");
  const [recipientLens, setRecipientLens] = useState("All Commands");
  const [draftGroupTokenIds, setDraftGroupTokenIds] = useState<string[]>([]);
  const [draftRecipient, setDraftRecipient] = useState(RECIPIENTS[0]);
  const tokenById = useMemo(() => {
    const index = new Map<string, GreekToken>();
    for (const [, verses] of data.greek) {
      for (const verse of verses) {
        for (const token of verse.tokens) {
          index.set(token.id, token);
        }
      }
    }
    return index;
  }, [data.greek]);
  const [activeVerse, setActiveVerse] = useState<GreekVerse | null>(
    () => data.greek[0]?.[1][0] ?? null
  );

  useEffect(() => {
    window.localStorage.setItem(MARKS_KEY, JSON.stringify(Array.from(finiteMarkedIds)));
  }, [finiteMarkedIds]);

  useEffect(() => {
    window.localStorage.setItem(COMMAND_MARKS_KEY, JSON.stringify(Array.from(commandMarkedIds)));
  }, [commandMarkedIds]);

  useEffect(() => {
    window.localStorage.setItem(STATEMENT_MARKS_KEY, JSON.stringify(Array.from(statementMarkedIds)));
  }, [statementMarkedIds]);

  useEffect(() => {
    window.localStorage.setItem(
      DEPENDENT_THOUGHT_MARKS_KEY,
      JSON.stringify(Array.from(dependentThoughtMarkedIds))
    );
  }, [dependentThoughtMarkedIds]);

  useEffect(() => {
    window.localStorage.setItem(COMMAND_RECIPIENTS_KEY, JSON.stringify(commandRecipientGroups));
  }, [commandRecipientGroups]);

  const spanishVerse = useMemo(() => {
    if (!activeVerse) return null;
    return data.spanish.find(
      verse => verse.chapter === activeVerse.chapter && verse.verse === activeVerse.verse
    );
  }, [activeVerse, data.spanish]);

  const activeMarkedIds =
    participation === "finite"
      ? finiteMarkedIds
      : participation === "mood-statements"
        ? statementMarkedIds
        : participation === "dependent-thoughts"
          ? dependentThoughtMarkedIds
        : commandMarkedIds;
  const activeLabel =
    participation === "finite"
      ? "Finite verbs"
      : participation === "mood-commands"
        ? "Commands"
        : participation === "mood-statements"
          ? "Statements"
          : participation === "dependent-thoughts"
            ? "Dependent thought introducers"
            : "Command groups";

  const commandTokens = useMemo(() => {
    const ordered: GreekToken[] = [];
    for (const [, verses] of data.greek) {
      for (const verse of verses) {
        for (const token of verse.tokens) {
          if (commandMarkedIds.has(token.id)) ordered.push(token);
        }
      }
    }
    return ordered;
  }, [commandMarkedIds, data.greek]);

  const commandTokenIndex = useMemo(() => {
    const index = new Map<string, number>();
    commandTokens.forEach((token, position) => index.set(token.id, position));
    return index;
  }, [commandTokens]);

  const allAssignedCommandTokenIds = useMemo(() => {
    const assigned = new Set<string>();
    for (const group of commandRecipientGroups) {
      group.tokenIds.forEach(tokenId => assigned.add(tokenId));
    }
    return assigned;
  }, [commandRecipientGroups]);

  const displayedCommandTokens = useMemo(() => {
    if (recipientLens === "All Commands") return commandTokens;

    const visibleIds = new Set<string>();
    for (const group of commandRecipientGroups) {
      if (group.recipient !== recipientLens) continue;
      group.tokenIds.forEach(tokenId => visibleIds.add(tokenId));
    }
    return commandTokens.filter(token => visibleIds.has(token.id));
  }, [commandRecipientGroups, commandTokens, recipientLens]);

  const groupedTokenIds = useMemo(() => {
    const grouped = new Set<string>();
    for (const group of commandRecipientGroups) {
      if (recipientLens !== "All Commands" && group.recipient !== recipientLens) continue;
      group.tokenIds.forEach(tokenId => grouped.add(tokenId));
    }
    return grouped;
  }, [commandRecipientGroups, recipientLens]);

  const selectedTokens = useMemo(() => {
    return Array.from(activeMarkedIds)
      .map(id => tokenById.get(id))
      .filter((token): token is GreekToken => Boolean(token));
  }, [activeMarkedIds, tokenById]);

  const draftGroupTokens = useMemo(() => {
    return draftGroupTokenIds
      .map(id => tokenById.get(id))
      .filter((token): token is GreekToken => Boolean(token));
  }, [draftGroupTokenIds, tokenById]);

  const draftPersonNumberNotes = useMemo(() => {
    const notes = new Map<string, string>();
    for (const token of draftGroupTokens) {
      const meaning = personNumberMeaning(token.rmac);
      if (meaning) notes.set(token.rmac, meaning);
    }
    return Array.from(notes.entries()).map(([rmac, meaning]) => ({ rmac, meaning }));
  }, [draftGroupTokens]);

  const focusCommandToken = useCallback((token: GreekToken) => {
    const verse = data.greek
      .flatMap(([, verses]) => verses)
      .find(candidate => candidate.chapter === token.chapter && candidate.verse === token.verse);
    if (verse) setActiveVerse(verse);

    window.setTimeout(() => {
      const target = document.querySelector<HTMLElement>(`[data-token-id="${token.id}"]`);
      target?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
      target?.focus({ preventScroll: true });
    }, 40);
  }, [data.greek]);

  useEffect(() => {
    if (participation !== "command-recipients" || !commandTokens.length) return;
    const firstUnassigned = commandTokens.find(token => !allAssignedCommandTokenIds.has(token.id));
    focusCommandToken(firstUnassigned ?? commandTokens[0]);
  }, [allAssignedCommandTokenIds, commandTokens, focusCommandToken, participation]);

  const toggleToken = useCallback((token: GreekToken, verse: GreekVerse) => {
    setActiveVerse(verse);
    const updateMarks = (current: Set<string>) => {
      const next = new Set(current);
      if (next.has(token.id)) {
        next.delete(token.id);
      } else {
        next.add(token.id);
      }
      return next;
    };

    if (participation === "finite") {
      setFiniteMarkedIds(updateMarks);
    } else if (participation === "dependent-thoughts") {
      if (isDependentThoughtCandidate(token)) {
        setDependentThoughtMarkedIds(updateMarks);
      }
    } else if (finiteMarkedIds.has(token.id)) {
      if (participation === "mood-statements") {
        setStatementMarkedIds(updateMarks);
      } else {
        setCommandMarkedIds(updateMarks);
      }
    }
  }, [finiteMarkedIds, participation]);

  const selectCommandGroupToken = useCallback((token: GreekToken, verse: GreekVerse) => {
    setActiveVerse(verse);
    if (!commandMarkedIds.has(token.id)) return;

    setDraftGroupTokenIds(current => {
      if (!current.length) return [token.id];
      const start = commandTokenIndex.get(current[0]);
      const end = commandTokenIndex.get(token.id);
      if (start === undefined || end === undefined) return [token.id];
      const low = Math.min(start, end);
      const high = Math.max(start, end);
      return commandTokens.slice(low, high + 1).map(commandToken => commandToken.id);
    });
  }, [commandMarkedIds, commandTokenIndex, commandTokens]);

  const clearMarks = useCallback(() => {
    if (participation === "finite") {
      setFiniteMarkedIds(new Set());
    } else if (participation === "mood-commands") {
      setCommandMarkedIds(new Set());
    } else if (participation === "mood-statements") {
      setStatementMarkedIds(new Set());
      setStatementLens("All finite verbs");
    } else if (participation === "dependent-thoughts") {
      setDependentThoughtMarkedIds(new Set());
    } else {
      if (draftGroupTokenIds.length) {
        setDraftGroupTokenIds([]);
      } else {
        setCommandRecipientGroups([]);
        setRecipientLens("All Commands");
      }
    }
  }, [draftGroupTokenIds.length, participation]);

  const saveCommandRecipientGroup = useCallback(() => {
    if (!draftGroupTokenIds.length) return;
    const selectedIds = new Set(draftGroupTokenIds);
    setCommandRecipientGroups(current => {
      const withoutSelected = current
        .map(group => ({
          ...group,
          tokenIds: group.tokenIds.filter(tokenId => !selectedIds.has(tokenId))
        }))
        .filter(group => group.tokenIds.length);

      return [
        ...withoutSelected,
        {
          id: makeLocalId("command-group"),
          recipient: draftRecipient,
          tokenIds: draftGroupTokenIds
        }
      ];
    });
    setDraftGroupTokenIds([]);
    setRecipientLens(draftRecipient);
  }, [draftGroupTokenIds, draftRecipient]);

  const cancelCommandRecipientGroup = useCallback(() => {
    setDraftGroupTokenIds([]);
  }, []);

  const getTokenMarkClassName = useCallback(
    (token: GreekToken) => {
      if (participation === "finite") {
        return finiteMarkedIds.has(token.id) ? "greek-token--finite-marked" : "";
      }

      if (participation === "command-recipients") {
        return [
          commandMarkedIds.has(token.id) ? "greek-token--command-marked" : "",
          groupedTokenIds.has(token.id) ? "greek-token--recipient-grouped" : "",
          draftGroupTokenIds.includes(token.id) ? "greek-token--recipient-draft" : ""
        ].filter(Boolean).join(" ");
      }

      if (participation === "mood-statements") {
        if (!finiteMarkedIds.has(token.id)) return "";
        if (statementLens === "Statements only") {
          return statementMarkedIds.has(token.id) ? "greek-token--statement-marked" : "";
        }
        if (statementLens === "Commands only") {
          return commandMarkedIds.has(token.id) ? "greek-token--command-marked" : "";
        }
        return [
          "greek-token--finite-candidate",
          commandMarkedIds.has(token.id) ? "greek-token--command-marked" : "",
          statementMarkedIds.has(token.id) ? "greek-token--statement-marked" : ""
        ].filter(Boolean).join(" ");
      }

      if (participation === "dependent-thoughts") {
        if (!isDependentThoughtCandidate(token)) return "";
        return [
          "greek-token--dependent-candidate",
          dependentThoughtMarkedIds.has(token.id) ? "greek-token--dependent-marked" : ""
        ].filter(Boolean).join(" ");
      }

      return [
        finiteMarkedIds.has(token.id) ? "greek-token--finite-candidate" : "",
        commandMarkedIds.has(token.id) ? "greek-token--command-marked" : ""
      ].filter(Boolean).join(" ");
    },
    [
      commandMarkedIds,
      draftGroupTokenIds,
      dependentThoughtMarkedIds,
      finiteMarkedIds,
      groupedTokenIds,
      participation,
      statementLens,
      statementMarkedIds
    ]
  );

  return (
    <main className="o-shell">
      <header className="o-header">
        <div>
          <p className="o-kicker">O Prototype 0.2</p>
          <h1>Greek Participation Environment</h1>
        </div>
        <div className="o-header-meta">
          <span>Titus</span>
          <span>Greek + RMAC morphology</span>
          <span>NBLA result</span>
          <button type="button" onClick={onBackToReader}>
            Back to The Reader
          </button>
        </div>
      </header>

      <section className="o-layout">
        <article
          className="greek-panel"
          aria-label="Greek text of Titus"
        >
          <div className="participation-switch" aria-label="Participation">
            <button
              type="button"
              className={`participation-option${
                participation === "finite" ? " participation-option--active" : ""
              }`}
              onClick={() => setParticipation("finite")}
              aria-pressed={participation === "finite"}
            >
              Brick 1 — Finite Verbs
            </button>
            <button
              type="button"
              className={`participation-option${
                participation === "mood-commands" ? " participation-option--active" : ""
              }`}
              onClick={() => setParticipation("mood-commands")}
              aria-pressed={participation === "mood-commands"}
            >
              Brick 2 — Commands
            </button>
            <button
              type="button"
              className={`participation-option${
                participation === "mood-statements" ? " participation-option--active" : ""
              }`}
              disabled={!finiteMarkedIds.size}
              onClick={() => setParticipation("mood-statements")}
              aria-pressed={participation === "mood-statements"}
            >
              Brick 2C — Statements
            </button>
            <button
              type="button"
              className={`participation-option${
                participation === "command-recipients" ? " participation-option--active" : ""
              }`}
              disabled={!commandMarkedIds.size}
              onClick={() => setParticipation("command-recipients")}
              aria-pressed={participation === "command-recipients"}
            >
              Brick 2B — Recipients
            </button>
            <button
              type="button"
              className={`participation-option${
                participation === "dependent-thoughts" ? " participation-option--active" : ""
              }`}
              onClick={() => setParticipation("dependent-thoughts")}
              aria-pressed={participation === "dependent-thoughts"}
            >
              Brick 3 — Dependent Thoughts
            </button>
          </div>

          {data.greek.map(([chapter, verses]) => (
              <section className="greek-chapter" key={chapter} aria-labelledby={`o-chapter-${chapter}`}>
                <h2 id={`o-chapter-${chapter}`}>{chapter}</h2>
                {verses.map(verse => (
                  <section
                    className={`greek-verse${
                      activeVerse?.chapter === verse.chapter && activeVerse?.verse === verse.verse
                        ? " greek-verse--active"
                        : ""
                    }`}
                    key={verse.label}
                  >
                    <button
                      type="button"
                      className="verse-label"
                      onClick={() => setActiveVerse(verse)}
                      aria-label={`Show Spanish result for ${verse.label}`}
                    >
                      {verse.verse}
                    </button>
                    <div className="token-flow">
                      {verse.tokens.map(token => (
                        <GreekTokenButton
                          disabled={
                            ((participation === "mood-commands" || participation === "mood-statements") &&
                              !finiteMarkedIds.has(token.id)) ||
                            (participation === "command-recipients" && !commandMarkedIds.has(token.id)) ||
                            (participation === "dependent-thoughts" && !isDependentThoughtCandidate(token))
                          }
                          key={token.id}
                          isPressed={activeMarkedIds.has(token.id)}
                          markClassName={getTokenMarkClassName(token)}
                          onToggle={participation === "command-recipients" ? selectCommandGroupToken : toggleToken}
                          token={token}
                          verse={verse}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </section>
          ))}
        </article>

        <aside className="result-panel" aria-label="Participation result">
          {participation === "mood-commands" && (
            <section className="result-card participation-card">
              <p className="result-label">Current Participation</p>
              <h2>Brick 2 — Commands</h2>
              <p className="participation-note">Find every finite verb that is a command.</p>
              {commandMarkedIds.size > 0 && (
                <p className="terminology-note">Term: imperative mood</p>
              )}
            </section>
          )}

          {participation === "mood-statements" && (
            <section className="result-card participation-card">
              <p className="result-label">Current Participation</p>
              <h2>Brick 2C — Statements</h2>
              <p className="participation-note">Find the finite verbs that make statements.</p>
              {statementMarkedIds.size > 0 && (
                <>
                  <p className="terminology-note">These statement verbs are called Indicatives.</p>
                  <div className="lens-control" aria-label="Statement view">
                    {STATEMENT_LENSES.map(option => (
                      <button
                        type="button"
                        className={statementLens === option ? "lens-option lens-option--active" : "lens-option"}
                        key={option}
                        onClick={() => setStatementLens(option)}
                        aria-pressed={statementLens === option}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </section>
          )}

          {participation === "command-recipients" && (
            <section className="result-card participation-card">
              <p className="result-label">Current Participation</p>
              <h2>Brick 2B — Who receives these commands?</h2>
              <div className="lens-control" aria-label="Command recipient view">
                {["All Commands", ...RECIPIENTS].map(option => (
                  <button
                    type="button"
                    className={recipientLens === option ? "lens-option lens-option--active" : "lens-option"}
                    key={option}
                    onClick={() => setRecipientLens(option)}
                    aria-pressed={recipientLens === option}
                  >
                    {option === "All Commands" ? option : `Commands to ${option}`}
                  </button>
                ))}
              </div>
              <div className="command-jump-list" aria-label="Command verbs">
                {displayedCommandTokens.length ? (
                  displayedCommandTokens.map(token => (
                    <button
                      type="button"
                      className={
                        allAssignedCommandTokenIds.has(token.id)
                          ? "command-jump command-jump--assigned"
                          : "command-jump"
                      }
                      key={token.id}
                      onClick={() => focusCommandToken(token)}
                    >
                      {stripCriticalMarks(token.surface)}
                    </button>
                  ))
                ) : (
                  <p className="result-placeholder">No commands assigned here yet.</p>
                )}
              </div>
            </section>
          )}

          {participation === "dependent-thoughts" && (
            <section className="result-card participation-card">
              <p className="result-label">Current Participation</p>
              <h2>Brick 3 — Dependent Thoughts</h2>
              <p className="participation-note">Find the words that begin a dependent thought.</p>
              <div className="connector-reference" aria-label="Candidate words">
                {dependentThoughtIntroducers.map(candidate => (
                  <span key={candidate.surface}>{candidate.surface}</span>
                ))}
              </div>
            </section>
          )}

          {participation === "command-recipients" && draftGroupTokenIds.length > 0 && (
            <section className="result-card recipient-card">
              <p className="result-label">Recipient</p>
              <div className="draft-command-group" aria-label="Selected command group">
                {draftGroupTokens.map(token => (
                  <span className="marked-token" key={token.id}>
                    {stripCriticalMarks(token.surface)}
                  </span>
                ))}
              </div>
              {draftPersonNumberNotes.length > 0 && (
                <div className="person-number-reference" aria-label="Person and number">
                  <p className="result-label">Person / number</p>
                  {draftPersonNumberNotes.map(note => (
                    <p key={note.rmac}>
                      <span>{note.rmac}</span>
                      {note.meaning}
                    </p>
                  ))}
                </div>
              )}
              <fieldset className="recipient-options">
                {RECIPIENTS.map(recipient => (
                  <label key={recipient}>
                    <input
                      type="radio"
                      name="command-recipient"
                      value={recipient}
                      checked={draftRecipient === recipient}
                      onChange={() => setDraftRecipient(recipient)}
                    />
                    {recipient}
                  </label>
                ))}
              </fieldset>
              <div className="recipient-actions">
                <button type="button" onClick={cancelCommandRecipientGroup}>
                  Cancel
                </button>
                <button type="button" className="recipient-save" onClick={saveCommandRecipientGroup}>
                  Save
                </button>
              </div>
            </section>
          )}

          <section className="result-card">
            <p className="result-label">Current passage</p>
            <h2>{activeVerse?.label ?? "Tito"}</h2>
            <p className="spanish-result">
              {spanishVerse ? spanishVerse.text : "Select a Greek verse to see the Spanish result."}
            </p>
          </section>

          <section className="result-card">
            <div className="marked-heading">
              <div>
                <p className="result-label">Student markings</p>
                <h2>{activeLabel}</h2>
                <p className="result-count">
                  {participation === "command-recipients"
                    ? `${commandRecipientGroups.length} assigned`
                    : `${activeMarkedIds.size} marked`}
                </p>
              </div>
              <button
                type="button"
                onClick={clearMarks}
                disabled={
                  participation === "command-recipients"
                    ? !draftGroupTokenIds.length && !commandRecipientGroups.length
                    : !activeMarkedIds.size
                }
              >
                Clear
              </button>
            </div>
            <div className="marked-list">
              {participation === "finite" && selectedTokens.length ? (
                selectedTokens.map(token => (
                  <span className="marked-token" key={token.id}>
                    {tokenText(token)}
                  </span>
                ))
              ) : participation === "mood-commands" && selectedTokens.length ? (
                selectedTokens.map(token => (
                  <span className="marked-token" key={token.id}>
                    {tokenText(token)}
                  </span>
                ))
              ) : participation === "mood-statements" && selectedTokens.length ? (
                selectedTokens.map(token => (
                  <span className="marked-token statement-token" key={token.id}>
                    {tokenText(token)}
                  </span>
                ))
              ) : participation === "dependent-thoughts" && selectedTokens.length ? (
                selectedTokens.map(token => (
                  <span className="marked-token dependent-token" key={token.id}>
                    {tokenText(token)}
                  </span>
                ))
              ) : participation === "command-recipients" && commandRecipientGroups.length ? (
                commandRecipientGroups
                  .filter(group => recipientLens === "All Commands" || group.recipient === recipientLens)
                  .map(group => (
                    <span className="marked-token recipient-token" key={group.id}>
                      {group.recipient}: {group.tokenIds.length}
                    </span>
                  ))
              ) : (
                <p>
                  {participation === "finite"
                    ? "No finite verbs marked yet."
                    : participation === "mood-commands"
                      ? "No commands marked yet."
                    : participation === "mood-statements"
                      ? "No statements marked yet."
                      : participation === "dependent-thoughts"
                        ? "No dependent thought introducers marked yet."
                        : "No recipients assigned yet."}
                </p>
              )}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
