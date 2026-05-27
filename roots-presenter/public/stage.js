const socket = io();
const sharpNotes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const noteIndexes = {
  C: 0,
  "B#": 0,
  "C#": 1,
  Db: 1,
  D: 2,
  "D#": 3,
  Eb: 3,
  E: 4,
  Fb: 4,
  "E#": 5,
  F: 5,
  "F#": 6,
  Gb: 6,
  G: 7,
  "G#": 8,
  Ab: 8,
  A: 9,
  "A#": 10,
  Bb: 10,
  B: 11,
  Cb: 11
};

let transposeOffset = 0;
let latestControllerState = {};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeOffset(value) {
  const normalized = ((value % 12) + 12) % 12;
  return normalized > 6 ? normalized - 12 : normalized;
}

function transposeChord(chord) {
  if (!transposeOffset) return chord;

  return String(chord || "").replace(/(^|\/)([A-G](?:#|b)?)/g, (match, prefix, root) => {
    const index = noteIndexes[root];
    if (index === undefined) return match;
    return `${prefix}${sharpNotes[(index + transposeOffset + 120) % 12]}`;
  });
}

function renderChordLine(line) {
  const parts = String(line || "").split(/(\[[^\]]+\])/g).filter(Boolean);
  let pendingChord = "";

  const rendered = parts.map(part => {
    const chordMatch = part.match(/^\[([^\]]+)\]$/);
    if (chordMatch) {
      const transposedChord = transposeChord(chordMatch[1]);
      pendingChord = pendingChord
        ? `${pendingChord} ${transposedChord}`
        : transposedChord;
      return "";
    }

    const chord = pendingChord;
    pendingChord = "";
    return `
      <span class="chord-token${chord ? " has-chord" : ""}">
        <span class="chord">${chord ? escapeHtml(chord) : "&nbsp;"}</span>
        <span class="lyric">${escapeHtml(part)}</span>
      </span>
    `;
  }).join("");

  if (pendingChord) {
    return `${rendered}<span class="chord-token trailing-chord"><span class="chord">${escapeHtml(pendingChord)}</span></span>`;
  }

  return rendered;
}

function renderSection(lines = [], options = {}) {
  const visibleLines = options.firstLineOnly ? lines.slice(0, 1) : lines;
  if (!visibleLines.length) return `<div class="empty">${t("noSection")}</div>`;

  return visibleLines
    .map(line => `<div class="song-line">${renderChordLine(line)}</div>`)
    .join("");
}

function renderStage(controllerState = {}) {
  latestControllerState = controllerState;
  const active = !!controllerState.active;
  const isBlank = !!controllerState.blank;
  const title = controllerState.title || t("stageView");
  const step = Number(controllerState.step) || 0;
  const chordSections = controllerState.chordSections || controllerState.sections || [];
  const current = active ? chordSections[step] || [] : [];
  const next = active ? chordSections[step + 1] || [] : [];

  byId("stageTitle").textContent = active ? title : t("stageView");
  byId("stageStatus").textContent = active
    ? isBlank ? t("blankScreen") : t("songMode")
    : t("waitingForController");
  byId("stagePosition").textContent = active
    ? isBlank ? "" : `${step + 1}/${chordSections.length}`
    : "";
  byId("transposeStatus").textContent = transposeOffset === 0
    ? t("keyZero")
    : `${t("stageTransposition")} ${transposeOffset > 0 ? "+" : ""}${transposeOffset}`;
  byId("currentSong").innerHTML = isBlank
    ? `<div class="empty">${t("blankScreenLive")}</div>`
    : active
    ? renderSection(current)
    : `<div class="empty">${t("noSongLive")}</div>`;
  byId("nextSong").innerHTML = isBlank
    ? `<div class="empty">${t("noNextSection")}</div>`
    : active
    ? renderSection(next, { firstLineOnly: true })
    : `<div class="empty">${t("noNextSection")}</div>`;
}

socket.on("state", data => {
  renderStage(data.controllerState || {});
});

function setTransposeOffset(nextOffset) {
  transposeOffset = normalizeOffset(nextOffset);
  renderStage(latestControllerState);
}

function nextSection() {
  socket.emit("controller-next");
}

function previousSection() {
  socket.emit("controller-previous");
}

byId("transposeUp").addEventListener("click", () => setTransposeOffset(transposeOffset + 1));
byId("transposeDown").addEventListener("click", () => setTransposeOffset(transposeOffset - 1));
byId("stageNext").addEventListener("click", nextSection);
byId("stagePrevious").addEventListener("click", previousSection);

window.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea, select")) return;

  if (event.key === "+" || event.key === "=") {
    event.preventDefault();
    setTransposeOffset(transposeOffset + 1);
    return;
  }

  if (event.key === "-" || event.key === "_") {
    event.preventDefault();
    setTransposeOffset(transposeOffset - 1);
    return;
  }

  if (event.key === "ArrowRight" || event.key === " " || event.key === "Enter") {
    event.preventDefault();
    nextSection();
    return;
  }

  if (event.key === "ArrowLeft" || event.key === "Backspace") {
    event.preventDefault();
    previousSection();
  }
});

window.CGVI18N.loadLanguage().then(() => renderStage());
