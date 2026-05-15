const socket = io();

const defaultSongs = [
  {
    id: "sample-amazing-grace",
    title: "Amazing Grace",
    lyrics: "Amazing grace, how sweet the sound\nThat saved a wretch like me\n\nI once was lost, but now am found\nWas blind, but now I see"
  },
  {
    id: "sample-santo-santo",
    title: "Santo, Santo, Santo",
    lyrics: "Santo, santo, santo\nSeñor omnipotente\n\nDios en tres personas\nBendita Trinidad"
  }
];

let controllerState = {
  active: false,
  title: "",
  sections: [],
  step: 0,
  background: "#0f172a",
  textColor: "#ffffff",
  accentColor: "#38bdf8"
};
let songs = loadSongs();
let selectedSongId = songs[0]?.id || null;
let editingSongId = null;

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

function loadSongs() {
  try {
    const stored = JSON.parse(localStorage.getItem("cgvControllerSongs") || "[]");
    if (Array.isArray(stored) && stored.length) return stored;
  } catch {
    // Ignore invalid local song cache.
  }

  return defaultSongs;
}

function saveSongs() {
  localStorage.setItem("cgvControllerSongs", JSON.stringify(songs));
}

function parseSections(text) {
  return String(text || "")
    .replace(/\r\n/g, "\n")
    .trim()
    .split(/\n\s*\n/)
    .map(section => section
      .split("\n")
      .map(line => line.trim())
      .filter(Boolean)
    )
    .filter(section => section.length);
}

function getSelectedSong() {
  return songs.find(song => song.id === selectedSongId) || songs[0] || null;
}

function getSongPayload(song = getSelectedSong()) {
  return {
    title: song?.title || "Song",
    lyrics: song?.lyrics || "",
    background: byId("backgroundColor").value,
    textColor: byId("textColor").value,
    accentColor: byId("accentColor").value
  };
}

function createSongId(title) {
  const slug = String(title || "song")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 44) || "song";

  return `${slug}-${Date.now().toString(36)}`;
}

function sendLive() {
  const song = getSelectedSong();
  if (!song) return;
  socket.emit("controller-set-song", getSongPayload(song));
}

function clearLive() {
  socket.emit("controller-clear");
}

function nextSection() {
  socket.emit("controller-next");
}

function previousSection() {
  socket.emit("controller-previous");
}

function applyStyle() {
  socket.emit("controller-style", {
    background: byId("backgroundColor").value,
    textColor: byId("textColor").value,
    accentColor: byId("accentColor").value
  });
}

function openEditor(songId = null) {
  editingSongId = songId;
  const song = songs.find(item => item.id === songId) || { title: "", lyrics: "" };
  byId("songTitle").value = song.title;
  byId("songLyrics").value = song.lyrics;
  byId("songEditor").classList.remove("hidden");
  byId("songTitle").focus();
}

function closeEditor() {
  editingSongId = null;
  byId("songEditor").classList.add("hidden");
}

function saveCurrentSong() {
  const title = byId("songTitle").value.trim() || "Untitled Song";
  const lyrics = byId("songLyrics").value.trim();
  if (!lyrics) return;

  if (editingSongId) {
    songs = songs.map(song => song.id === editingSongId ? { ...song, title, lyrics } : song);
    selectedSongId = editingSongId;
  } else {
    const song = { id: createSongId(title), title, lyrics };
    songs = [...songs, song];
    selectedSongId = song.id;
  }

  saveSongs();
  closeEditor();
  renderSongList();
  renderPreview();
}

function renderSongList() {
  const list = byId("songList");

  if (!songs.length) {
    list.innerHTML = `
      <div class="empty-state">
        No songs loaded. Click New Song to add one.
      </div>
    `;
    return;
  }

  list.innerHTML = songs.map(song => {
    const selected = song.id === selectedSongId ? " selected" : "";
    const stanzaCount = parseSections(song.lyrics).length;
    return `
      <article class="song-item${selected}" data-song-id="${escapeHtml(song.id)}">
        <button type="button" class="song-select">
          <strong>${escapeHtml(song.title)}</strong>
          <span>${stanzaCount} screen${stanzaCount === 1 ? "" : "s"}</span>
        </button>
        <button type="button" class="song-edit">Edit Song</button>
      </article>
    `;
  }).join("");
}

function renderPreview() {
  const preview = byId("controllerPreview");
  const status = byId("liveStatus");
  const selectedSong = getSelectedSong();
  const previewSections = controllerState.active
    ? controllerState.sections || []
    : selectedSong
      ? parseSections(selectedSong.lyrics)
      : [];
  const activeIndex = controllerState.active ? controllerState.step : 0;
  const activeSection = previewSections[activeIndex] || [];

  preview.style.setProperty("--preview-background", byId("backgroundColor").value);
  preview.style.setProperty("--preview-color", byId("textColor").value);
  preview.style.setProperty("--preview-accent", byId("accentColor").value);
  preview.classList.toggle("teaching-mode", !controllerState.active);
  preview.innerHTML = controllerState.active
    ? activeSection.map(line => `<div>${escapeHtml(line)}</div>`).join("")
    : `
      <div class="teaching-mode-preview">
        <strong>Teaching mode</strong>
        <span>The teacher currently has the projector.</span>
      </div>
    `;

  renderThumbnails(previewSections, activeIndex);

  status.textContent = controllerState.active
    ? `Projector: ${controllerState.title} (${controllerState.step + 1}/${controllerState.sections.length})`
    : "Projector: teaching mode";
  status.classList.toggle("active", controllerState.active);
}

function renderThumbnails(sections, activeIndex) {
  const thumbnailHost = byId("songThumbnails");
  if (!thumbnailHost) return;

  if (!sections.length) {
    thumbnailHost.innerHTML = `<div class="empty-state compact">No song screens.</div>`;
    return;
  }

  thumbnailHost.innerHTML = sections.map((section, index) => {
    const active = controllerState.active && index === activeIndex ? " active" : "";
    const firstLine = section[0] || `Screen ${index + 1}`;
    return `
      <button type="button" class="song-thumbnail${active}" data-screen-index="${index}">
        <b>${index + 1}</b>
        <span>${escapeHtml(firstLine)}</span>
      </button>
    `;
  }).join("");
}

function hydrateColorsFromState() {
  byId("backgroundColor").value = controllerState.background || "#0f172a";
  byId("textColor").value = controllerState.textColor || "#ffffff";
  byId("accentColor").value = controllerState.accentColor || "#38bdf8";
}

socket.on("state", data => {
  controllerState = data.controllerState || controllerState;
  hydrateColorsFromState();
  renderPreview();
});

byId("songList").addEventListener("click", event => {
  const songItem = event.target.closest("[data-song-id]");
  if (!songItem) return;

  const songId = songItem.dataset.songId;
  if (event.target.closest(".song-edit")) {
    openEditor(songId);
    return;
  }

  selectedSongId = songId;
  renderSongList();
  renderPreview();
});

byId("songList").addEventListener("dblclick", event => {
  const songItem = event.target.closest("[data-song-id]");
  if (!songItem || event.target.closest(".song-edit")) return;

  selectedSongId = songItem.dataset.songId;
  renderSongList();
  renderPreview();
  sendLive();
});

byId("songThumbnails").addEventListener("click", event => {
  const thumbnail = event.target.closest("[data-screen-index]");
  if (!thumbnail || !controllerState.active) return;

  const targetIndex = Number(thumbnail.dataset.screenIndex);
  if (!Number.isInteger(targetIndex)) return;

  const currentIndex = controllerState.step;
  if (targetIndex === currentIndex) return;

  const direction = targetIndex > currentIndex ? "controller-next" : "controller-previous";
  const distance = Math.abs(targetIndex - currentIndex);
  for (let index = 0; index < distance; index += 1) {
    socket.emit(direction);
  }
});

byId("newSongButton").addEventListener("click", () => openEditor());
byId("closeEditorButton").addEventListener("click", closeEditor);
byId("cancelEditorButton").addEventListener("click", closeEditor);
byId("saveSongButton").addEventListener("click", saveCurrentSong);
byId("goLiveButton").addEventListener("click", sendLive);
byId("clearButton").addEventListener("click", clearLive);
byId("nextButton").addEventListener("click", nextSection);
byId("previousButton").addEventListener("click", previousSection);
byId("applyStyleButton").addEventListener("click", applyStyle);
byId("backgroundColor").addEventListener("input", renderPreview);
byId("textColor").addEventListener("input", renderPreview);
byId("accentColor").addEventListener("input", renderPreview);

window.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea")) return;

  if (event.key === "ArrowRight" || event.key === " ") {
    event.preventDefault();
    nextSection();
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    previousSection();
  }
});

renderSongList();
renderPreview();
