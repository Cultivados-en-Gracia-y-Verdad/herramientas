export const CLAUSE_STORAGE_KEY = "cgv-translator:spanish-clause-builder:titus:v1";
const LEGACY_CLAUSE_STORAGE_KEYS = [
  "the-reader:spanish-clause-builder:titus:v1",
  "the-reader:clause-builder:titus:1:1-4:v2",
  "the-reader:clause-builder:titus:1:1-4"
];

export function wordInSpan(word, selectedSpan) {
  return Boolean(selectedSpan?.includes(word.id));
}

export function spanFromRange(start, end) {
  if (start.chapter !== end.chapter || start.verse !== end.verse) return null;
  const low = Math.min(start.index, end.index);
  const high = Math.max(start.index, end.index);
  const ids = [];
  for (let index = low; index <= high; index += 1) {
    ids.push(`${start.chapter}:${start.verse}:${index}`);
  }
  return ids;
}

export function mergeSpan(current, start, end, mode) {
  const next = spanFromRange(start, end);
  if (!next) return current ?? [];
  if (mode === "replace" || !current?.length) return next;

  const indices = new Set([
    ...current.map(id => Number(id.split(":")[2])),
    ...next.map(id => Number(id.split(":")[2]))
  ]);
  const low = Math.min(...indices);
  const high = Math.max(...indices);
  const ids = [];
  for (let index = low; index <= high; index += 1) {
    ids.push(`${start.chapter}:${start.verse}:${index}`);
  }
  return ids;
}

export function formatClauseSpan(selectedSpan, verseWords, verseText) {
  const selected = selectedSpan
    .map(id => verseWords.find(word => word.id === id))
    .filter(Boolean)
    .sort((a, b) => a.index - b.index);
  if (!selected.length) return "";
  if (verseText) {
    return verseText.slice(selected[0].startChar, selected[selected.length - 1].endChar);
  }
  return selected.map(word => word.text).join(" ");
}

function legacySpanToIds(value) {
  if (!value || typeof value !== "object") return [];
  if (
    typeof value.chapter !== "number" ||
    typeof value.verse !== "number" ||
    typeof value.startIndex !== "number" ||
    typeof value.endIndex !== "number"
  ) {
    return [];
  }
  const low = Math.min(value.startIndex, value.endIndex);
  const high = Math.max(value.startIndex, value.endIndex);
  const ids = [];
  for (let index = low; index <= high; index += 1) {
    ids.push(`${value.chapter}:${value.verse}:${index}`);
  }
  return ids;
}

function parseStoredClauseAssignments(stored) {
  if (!stored) return {};
  try {
    const parsed = JSON.parse(stored);
    if (!parsed || typeof parsed !== "object") return {};
    const out = {};

    for (const [finiteVerbId, value] of Object.entries(parsed)) {
      if (typeof finiteVerbId !== "string") continue;
      if (Array.isArray(value)) {
        const selectedSpan = value.filter(id => typeof id === "string");
        if (selectedSpan.length) out[finiteVerbId] = { finiteVerbId, selectedSpan };
        continue;
      }
      if (!value || typeof value !== "object") continue;
      if (Array.isArray(value.selectedSpan)) {
        const selectedSpan = value.selectedSpan.filter(id => typeof id === "string");
        if (selectedSpan.length) {
          out[finiteVerbId] = {
            finiteVerbId: typeof value.finiteVerbId === "string" ? value.finiteVerbId : finiteVerbId,
            selectedSpan
          };
        }
        continue;
      }
      const selectedSpan = legacySpanToIds(value);
      if (selectedSpan.length) out[finiteVerbId] = { finiteVerbId, selectedSpan };
    }

    return out;
  } catch {
    return {};
  }
}

export function readClauseAssignments() {
  const current = parseStoredClauseAssignments(window.localStorage.getItem(CLAUSE_STORAGE_KEY));
  if (Object.keys(current).length) return current;

  for (const key of LEGACY_CLAUSE_STORAGE_KEYS) {
    const legacy = parseStoredClauseAssignments(window.localStorage.getItem(key));
    if (Object.keys(legacy).length) {
      writeClauseAssignments(legacy);
      return legacy;
    }
  }

  return {};
}

export function writeClauseAssignments(assignments) {
  window.localStorage.setItem(CLAUSE_STORAGE_KEY, JSON.stringify(assignments));
}

export async function initClauseBuilder(root) {
  const response = await fetch("/api/clause/titus", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load clause data (${response.status})`);
  }
  const { verses } = await response.json();

  const wordById = new Map();
  const wordsByVerse = new Map();
  const verseTextByKey = new Map();
  const finiteVerbs = [];

  for (const verse of verses) {
    wordsByVerse.set(`${verse.chapter}:${verse.verse}`, verse.words);
    verseTextByKey.set(`${verse.chapter}:${verse.verse}`, verse.text);
    for (const word of verse.words) {
      wordById.set(word.id, word);
      if (word.finiteVerbId) finiteVerbs.push(word);
    }
  }

  const state = {
    assignments: readClauseAssignments(),
    activeFiniteVerbId: null,
    draftSpan: null,
    rangeAnchorId: null,
    savedAt: null,
    isDragging: false
  };

  const drag = {
    active: false,
    startId: null,
    didDrag: false
  };

  function activeVerb() {
    return finiteVerbs.find(verb => verb.finiteVerbId === state.activeFiniteVerbId) ?? null;
  }

  function activeVerseWords() {
    const verb = activeVerb();
    if (!verb) return [];
    return wordsByVerse.get(`${verb.chapter}:${verb.verse}`) ?? [];
  }

  function activeVerseText() {
    const verb = activeVerb();
    if (!verb) return "";
    return verseTextByKey.get(`${verb.chapter}:${verb.verse}`) ?? "";
  }

  function updateWordHighlights() {
    const verb = activeVerb();
    root.querySelectorAll("[data-word-id]").forEach(button => {
      const word = wordById.get(button.dataset.wordId);
      if (!word) return;

      const isActiveVerb = word.finiteVerbId && word.finiteVerbId === state.activeFiniteVerbId;
      const isAnchor = word.id === state.rangeAnchorId;
      const inDraft = wordInSpan(word, state.draftSpan);
      const inSaved =
        word.finiteVerbId !== state.activeFiniteVerbId &&
        Object.entries(state.assignments).some(
          ([verbId, assignment]) =>
            verbId !== state.activeFiniteVerbId && wordInSpan(word, assignment.selectedSpan)
        );

      button.className = "clause-word";
      if (word.finiteVerbId) button.classList.add("clause-word--verb");
      if (isActiveVerb) button.classList.add("clause-word--active-verb");
      if (isAnchor && !isActiveVerb) button.classList.add("clause-word--anchor");
      if (inDraft) button.classList.add("clause-word--belonging");
      if (inSaved && !inDraft && !isActiveVerb) button.classList.add("clause-word--saved");
      button.setAttribute("aria-pressed", isActiveVerb || inDraft ? "true" : "false");
      button.disabled =
        !word.finiteVerbId &&
        (!verb || word.chapter !== verb.chapter || word.verse !== verb.verse);
    });

    root.querySelectorAll(".clause-verse-text").forEach(element => {
      element.classList.toggle("clause-verse-text--dragging", state.isDragging);
    });
  }

  function applySpan(start, end, mode) {
    const verb = activeVerb();
    if (!verb) return;
    if (start.chapter !== verb.chapter || start.verse !== verb.verse) return;
    state.draftSpan = mergeSpan(state.draftSpan, start, end, mode);
    updateWordHighlights();
    renderPanel();
  }

  function selectVerb(verb) {
    state.activeFiniteVerbId = verb.finiteVerbId;
    state.draftSpan = state.assignments[verb.finiteVerbId]?.selectedSpan ?? null;
    state.rangeAnchorId = null;
    renderVerses();
    renderPanel();
  }

  function renderPanel() {
    const verb = activeVerb();
    const panel = root.querySelector(".clause-builder-panel");
    if (!verb) {
      panel.innerHTML = `
        <h2>Active verb</h2>
        <p class="clause-empty">Click a finite verb to begin.</p>
        <h2>Saved</h2>
        ${renderSavedList()}
      `;
      return;
    }

    const draftClause = state.draftSpan
      ? formatClauseSpan(state.draftSpan, activeVerseWords(), activeVerseText())
      : "";

    panel.innerHTML = `
      <h2>Active verb</h2>
      <p class="clause-active-verb">
        Tito ${verb.chapter}:${verb.verse} — <strong>${verb.text}</strong>
        ${verb.greekSurface ? `<span class="clause-greek"> (${verb.greekSurface})</span>` : ""}
      </p>
      <p class="clause-panel-label">Selected clause (verse order)</p>
      ${
        draftClause
          ? `<p class="clause-belonging-list">${escapeHtml(draftClause)}</p>`
          : `<p class="clause-empty">No span selected yet.</p>`
      }
      <div class="clause-panel-actions">
        <button type="button" class="clause-save"${state.draftSpan?.length ? "" : " disabled"}>Guardar</button>
        <button type="button" class="clause-clear">Limpiar</button>
      </div>
      ${state.savedAt ? `<p class="clause-saved">Guardado ${escapeHtml(state.savedAt)}</p>` : ""}
      <h2>Saved</h2>
      ${renderSavedList()}
    `;

    panel.querySelector(".clause-save")?.addEventListener("click", () => {
      if (!state.activeFiniteVerbId || !state.draftSpan?.length) return;
      state.assignments = {
        ...state.assignments,
        [state.activeFiniteVerbId]: {
          finiteVerbId: state.activeFiniteVerbId,
          selectedSpan: state.draftSpan
        }
      };
      writeClauseAssignments(state.assignments);
      state.savedAt = new Date().toLocaleTimeString();
      updateWordHighlights();
      renderPanel();
    });

    panel.querySelector(".clause-clear")?.addEventListener("click", () => {
      state.draftSpan = null;
      state.rangeAnchorId = null;
      updateWordHighlights();
      renderPanel();
    });

    panel.querySelectorAll(".clause-saved-verb").forEach(button => {
      button.addEventListener("click", () => {
        const verbId = button.dataset.verbId;
        const match = finiteVerbs.find(item => item.finiteVerbId === verbId);
        if (match) selectVerb(match);
      });
    });
  }

  function renderSavedList() {
    if (!finiteVerbs.length) {
      return `<p class="clause-empty">No finite verbs found.</p>`;
    }

    const items = finiteVerbs.map(verb => {
      const assignment = state.assignments[verb.finiteVerbId];
      const verseWords = wordsByVerse.get(`${verb.chapter}:${verb.verse}`) ?? [];
      const verseText = verseTextByKey.get(`${verb.chapter}:${verb.verse}`) ?? "";
      const clause = assignment?.selectedSpan?.length
        ? formatClauseSpan(assignment.selectedSpan, verseWords, verseText)
        : "";
      return `
        <li>
          <button type="button" class="clause-saved-verb" data-verb-id="${escapeHtml(verb.finiteVerbId)}">
            ${escapeHtml(verb.text)}
          </button>
          ${clause ? `<span> → ${escapeHtml(clause)}</span>` : `<span class="clause-empty"> (vacío)</span>`}
        </li>
      `;
    });

    return `<ul class="clause-saved-list">${items.join("")}</ul>`;
  }

  function renderVerses() {
    const body = root.querySelector(".clause-builder-body");
    body.innerHTML = verses
      .map(verse => {
        const wordsHtml = verse.words
          .map((word, position) => {
            const verb = activeVerb();
            const isActiveVerb = word.finiteVerbId && word.finiteVerbId === state.activeFiniteVerbId;
            const isAnchor = word.id === state.rangeAnchorId;
            const inDraft = wordInSpan(word, state.draftSpan);
            const inSaved =
              word.finiteVerbId !== state.activeFiniteVerbId &&
              Object.entries(state.assignments).some(
                ([verbId, assignment]) =>
                  verbId !== state.activeFiniteVerbId &&
                  wordInSpan(word, assignment.selectedSpan)
              );

            let className = "clause-word";
            if (word.finiteVerbId) className += " clause-word--verb";
            if (isActiveVerb) className += " clause-word--active-verb";
            if (isAnchor && !isActiveVerb) className += " clause-word--anchor";
            if (inDraft) className += " clause-word--belonging";
            if (inSaved && !inDraft && !isActiveVerb) className += " clause-word--saved";

            const disabled =
              !word.finiteVerbId &&
              (!verb || word.chapter !== verb.chapter || word.verse !== verb.verse);

            return `
              <span>
                ${position > 0 ? " " : ""}
                <button
                  type="button"
                  class="${className}"
                  data-word-id="${escapeHtml(word.id)}"
                  aria-pressed="${isActiveVerb || inDraft ? "true" : "false"}"
                  ${disabled ? "disabled" : ""}
                  title="${word.finiteVerbId ? "Finite verb" : "Span: click anchor, shift-click end, or drag"}"
                >${escapeHtml(word.text)}</button>
              </span>
            `;
          })
          .join("");

        return `
          <article class="clause-verse">
            <p class="clause-verse-label">${verse.verse}</p>
            <p class="clause-verse-text${state.isDragging ? " clause-verse-text--dragging" : ""}">${wordsHtml}</p>
          </article>
        `;
      })
      .join("");

    body.querySelectorAll("[data-word-id]").forEach(button => {
      const word = wordById.get(button.dataset.wordId);
      if (!word) return;

      button.addEventListener("click", event => {
        if (word.finiteVerbId) {
          selectVerb(word);
          return;
        }

        const verb = activeVerb();
        if (!verb) return;
        if (word.chapter !== verb.chapter || word.verse !== verb.verse) return;
        if (drag.didDrag) {
          drag.didDrag = false;
          return;
        }

        if (event.shiftKey) {
          const anchor = state.rangeAnchorId ? wordById.get(state.rangeAnchorId) : word;
          if (anchor) applySpan(anchor, word, "merge");
          state.rangeAnchorId = word.id;
          return;
        }

        if (state.rangeAnchorId && state.rangeAnchorId !== word.id) {
          const anchor = wordById.get(state.rangeAnchorId);
          if (anchor) {
            applySpan(anchor, word, "replace");
            state.rangeAnchorId = word.id;
            return;
          }
        }

        state.rangeAnchorId = word.id;
        applySpan(word, word, "replace");
      });

      button.addEventListener("pointerdown", event => {
        const verb = activeVerb();
        if (!verb) return;
        if (word.finiteVerbId && word.finiteVerbId !== verb.finiteVerbId) return;
        if (word.chapter !== verb.chapter || word.verse !== verb.verse) return;
        event.preventDefault();
        drag.didDrag = false;
        state.rangeAnchorId = word.id;
        drag.startId = word.id;
        drag.active = true;
        state.isDragging = true;
        button.setPointerCapture(event.pointerId);
        updateWordHighlights();
      });

      button.addEventListener("pointerenter", () => {
        if (!drag.active || !drag.startId) return;
        const start = wordById.get(drag.startId);
        if (!start || start.id === word.id) return;
        drag.didDrag = true;
        applySpan(start, word, "replace");
      });

      button.addEventListener("pointerup", event => {
        if (button.hasPointerCapture(event.pointerId)) {
          button.releasePointerCapture(event.pointerId);
        }
        drag.active = false;
        drag.startId = null;
        state.isDragging = false;
        updateWordHighlights();
      });
    });
  }

  renderVerses();
  renderPanel();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
