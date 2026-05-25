const socket = io();

let controllerState = {
  active: false,
  title: "",
  sections: [],
  chordSections: [],
  step: 0,
  background: "#0f172a",
  backgroundMedia: "",
  textColor: "#ffffff",
  accentColor: "#38bdf8"
};
let songs = [];
let backgrounds = [];
let latestState = {};
let selectedSongId = null;
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

function isVideoMedia(value) {
  return /\.(mp4|webm|ogg|mov)(?:[?#].*)?$/i.test(String(value || "").trim());
}

function stripChordProChords(line) {
  return String(line || "")
    .replace(/\[[^\]]+\]/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function isChordToken(value) {
  return /^[A-G](?:#|b)?(?:m|min|maj|dim|aug|sus|add|\d|\/|\(|\)|\+|-)*$/i.test(String(value || "").trim());
}

function getBracketSectionLabel(line) {
  const match = String(line || "").trim().match(/^\[([^\]]+)\]$/);
  if (!match) return "";

  const label = match[1].trim();
  return label && !isChordToken(label) ? label : "";
}

async function loadSongs() {
  const response = await fetch("/songs");
  songs = response.ok ? await response.json() : [];
  if (!selectedSongId || !songs.some(song => song.id === selectedSongId)) {
    selectedSongId = songs[0]?.id || null;
  }
  renderSongList();
  renderPreview();
}

async function loadBackgrounds() {
  const response = await fetch("/backgrounds");
  backgrounds = response.ok ? await response.json() : [];
  renderBackgroundGallery();
  renderSongBackgroundSelect();
}

function parseSections(text) {
  const sections = [];
  let currentSection = [];

  String(text || "").replace(/\r\n/g, "\n").split("\n").forEach(rawLine => {
    const line = rawLine.trim();
    const label = getBracketSectionLabel(line);

    if (!line || label) {
      if (currentSection.length) sections.push(currentSection);
      currentSection = [];
      return;
    }

    const lyricLine = stripChordProChords(line);
    if (lyricLine) currentSection.push(lyricLine);
  });

  if (currentSection.length) sections.push(currentSection);
  return sections;
}

function parseChordSections(text) {
  const sections = [];
  let currentSection = [];

  String(text || "").replace(/\r\n/g, "\n").split("\n").forEach(rawLine => {
    const line = rawLine.trim();
    const label = getBracketSectionLabel(line);

    if (!line || label) {
      if (currentSection.length) sections.push(currentSection);
      currentSection = [];
      return;
    }

    if (line) currentSection.push(line);
  });

  if (currentSection.length) sections.push(currentSection);
  return sections;
}

function getSelectedSong() {
  return songs.find(song => song.id === selectedSongId) || songs[0] || null;
}

function getSongLibraryName(song) {
  const parts = String(song?.file || "").split("/").filter(Boolean);
  return parts.length > 1 ? parts.slice(0, -1).join(" / ") : t("songs");
}

function getSongNumber(song, fallbackIndex = 0) {
  const fileName = String(song?.file || "").split("/").pop() || "";
  return fileName.match(/^[A-Za-z]*(\d+)/)?.[1] || String(fallbackIndex + 1).padStart(3, "0");
}

function getSongPayload(song = getSelectedSong()) {
  return {
    title: song?.title || t("songs"),
    lyrics: song?.lyrics || "",
    chordLyrics: song?.chordLyrics || song?.lyrics || "",
    sectionLabels: song?.sectionLabels || [],
    sections: song?.sections || parseSections(song?.lyrics || ""),
    chordSections: song?.chordSections || parseChordSections(song?.chordLyrics || song?.lyrics || ""),
    background: byId("backgroundColor").value,
    backgroundMedia: song?.backgroundMedia || byId("backgroundMedia").value.trim(),
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

function blankLive() {
  socket.emit("controller-blank", {
    background: byId("backgroundColor").value,
    backgroundMedia: byId("backgroundMedia").value.trim(),
    textColor: byId("textColor").value,
    accentColor: byId("accentColor").value
  });
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
    backgroundMedia: byId("backgroundMedia").value.trim(),
    textColor: byId("textColor").value,
    accentColor: byId("accentColor").value
  });
}

function openEditor(songId = null) {
  editingSongId = songId;
  const song = songs.find(item => item.id === songId) || { title: "", lyrics: "" };
  byId("songTitle").value = song.title;
  byId("songLyrics").value = song.chordLyrics || song.lyrics;
  renderSongBackgroundSelect(song.backgroundMedia || "");
  byId("songEditor").classList.remove("hidden");
  byId("songTitle").focus();
}

function closeEditor() {
  editingSongId = null;
  byId("songEditor").classList.add("hidden");
}

async function saveCurrentSong() {
  const title = byId("songTitle").value.trim() || t("untitledSong");
  const lyrics = byId("songLyrics").value.trim();
  if (!lyrics) return;

  const existingSong = songs.find(song => song.id === editingSongId);
  const response = await fetch("/songs/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      id: existingSong?.id || createSongId(title),
      file: existingSong?.file || "",
      title,
      chordLyrics: lyrics,
      backgroundMedia: byId("songBackgroundMedia").value.trim()
    })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    window.alert(error.error || t("couldNotSaveSong"));
    return;
  }

  const savedSong = await response.json();
  const existingIndex = songs.findIndex(song => song.id === savedSong.id || song.file === savedSong.file);
  if (existingIndex >= 0) {
    songs = songs.map((song, index) => index === existingIndex ? savedSong : song);
  } else {
    songs = [...songs, savedSong];
  }

  selectedSongId = savedSong.id;
  editingSongId = savedSong.id;
  closeEditor();
  renderSongList();
  renderPreview();
}

function renderSongList() {
  const list = byId("songList");
  const query = byId("songSearch").value.trim().toLowerCase();
  const visibleSongs = query
    ? songs.filter(song =>
        `${song.file}\n${song.title}\n${song.lyrics}`.toLowerCase().includes(query)
      )
    : songs;

  if (!visibleSongs.length) {
    list.innerHTML = `
      <div class="empty-state">
        ${songs.length ? t("noSongsMatch") : t("noSongsLoaded")}
      </div>
    `;
    return;
  }

  let previousLibrary = "";
  list.innerHTML = visibleSongs.map((song, index) => {
    const selected = song.id === selectedSongId ? " selected" : "";
    const stanzaCount = parseSections(song.lyrics).length;
    const screenLabel = stanzaCount === 1 ? t("screen") : t("screens");
    const libraryName = getSongLibraryName(song);
    const libraryHeader = libraryName !== previousLibrary
      ? `<div class="song-library-heading">${escapeHtml(libraryName)}</div>`
      : "";
    previousLibrary = libraryName;

    return `
      ${libraryHeader}
      <article class="song-item${selected}" data-song-id="${escapeHtml(song.id)}">
        <button type="button" class="song-select">
          <strong><span>${escapeHtml(getSongNumber(song, index))}</span>${escapeHtml(song.title)}</strong>
          <span>${escapeHtml(libraryName)} · ${stanzaCount} ${screenLabel}</span>
        </button>
        <button type="button" class="song-edit">${t("editSong")}</button>
      </article>
    `;
  }).join("");
}

function renderBackgroundGallery() {
  const gallery = byId("backgroundGallery");
  const selectedUrl = byId("backgroundMedia").value.trim();

  if (!backgrounds.length) {
    gallery.innerHTML = `
      <div class="empty-state compact">
        ${t("addBackgrounds")}
      </div>
    `;
    return;
  }

  gallery.innerHTML = backgrounds.map((background, index) => {
    const selected = background.url === selectedUrl ? " selected" : "";
    const media = background.type === "video"
      ? `<div class="background-video-thumb">${t("video")}</div>`
      : `<img src="${escapeHtml(background.url)}" alt="">`;
    const shortcut = index < 9 ? String(index + 1) : index === 9 ? "0" : "";

    return `
      <button type="button" class="background-choice${selected}" data-background-url="${escapeHtml(background.url)}">
        ${shortcut ? `<kbd>${shortcut}</kbd>` : ""}
        ${media}
        <span>${escapeHtml(background.name)}</span>
      </button>
    `;
  }).join("");
}

function renderCourseSections(headings = latestState.headings || []) {
  const host = byId("courseSections");
  if (!host) return;

  if (!headings.length) {
    host.innerHTML = `<div class="empty-state compact">${t("noCourseSections")}</div>`;
    return;
  }

  host.innerHTML = headings.map(heading => {
    const active = Number(latestState.slide) === Number(heading.slide) ? " active" : "";
    return `
      <button type="button" class="course-section-choice level-${heading.level}${active}" data-slide-index="${heading.slide}">
        <span>H${heading.level}</span>
        <b>${escapeHtml(heading.title)}</b>
      </button>
    `;
  }).join("");
}

async function jumpToCourseSlide(slideIndex) {
  const response = await fetch(`/jump/${encodeURIComponent(slideIndex)}`, { method: "POST" });
  if (!response.ok) return;
  renderCourseSections();
}

function renderSongBackgroundSelect(selectedUrl = byId("songBackgroundMedia")?.value || "") {
  const select = byId("songBackgroundMedia");
  if (!select) return;

  select.replaceChildren();

  const noneOption = document.createElement("option");
  noneOption.value = "";
  noneOption.textContent = t("none");
  select.appendChild(noneOption);

  backgrounds.forEach(background => {
    const option = document.createElement("option");
    option.value = background.url;
    option.textContent = background.name;
    select.appendChild(option);
  });

  select.value = selectedUrl;
}

function selectBackground(url) {
  byId("backgroundMedia").value = url || "";
  renderBackgroundGallery();
  renderPreview();
  applyStyle();
}

function getBackgroundShortcutIndex(event) {
  if (event.altKey || event.ctrlKey || event.metaKey) return -1;

  const digitMatch = event.code?.match(/^(?:Digit|Numpad)(\d)$/);
  const key = digitMatch ? digitMatch[1] : event.key;

  if (!/^\d$/.test(key)) return -1;
  return key === "0" ? 9 : Number(key) - 1;
}

function selectBackgroundFromShortcut(event) {
  const index = getBackgroundShortcutIndex(event);
  const background = index >= 0 ? backgrounds[index] : null;
  if (!background) return false;

  event.preventDefault();
  selectBackground(background.url);
  return true;
}

function renderPreview() {
  const preview = byId("controllerPreview");
  const status = byId("liveStatus");
  const selectedSong = getSelectedSong();
  const media = controllerState.active
    ? controllerState.backgroundMedia || ""
    : selectedSong?.backgroundMedia || byId("backgroundMedia").value.trim();
  const previewSections = controllerState.active
    && !controllerState.blank
    ? controllerState.sections || []
    : selectedSong
      ? parseSections(selectedSong.lyrics)
      : [];
  const activeIndex = controllerState.active ? controllerState.step : 0;
  const activeSection = previewSections[activeIndex] || [];

  preview.style.setProperty("--preview-background", byId("backgroundColor").value);
  preview.style.setProperty("--preview-color", byId("textColor").value);
  preview.style.setProperty("--preview-accent", byId("accentColor").value);
  preview.style.setProperty("--preview-media", media && !isVideoMedia(media)
    ? `url("${media.replace(/"/g, '\\"')}")`
    : "none");
  preview.classList.toggle("has-media", !!media && !isVideoMedia(media));
  preview.classList.toggle("teaching-mode", !controllerState.active);
  preview.innerHTML = controllerState.active
    ? controllerState.blank
      ? `<div class="teaching-mode-preview"><strong>${t("blankScreenPreview")}</strong><span>${t("projectorBlank")}</span></div>`
      : `
      ${media && isVideoMedia(media) ? `<video class="preview-video" src="${escapeHtml(media)}" autoplay muted loop playsinline></video>` : ""}
      <div class="preview-lines">
        ${activeSection.map(line => `<div>${escapeHtml(line)}</div>`).join("")}
      </div>
    `
    : `
      <div class="teaching-mode-preview">
        <strong>${t("teachingMode")}</strong>
        <span>${t("teacherHasProjector")}</span>
      </div>
    `;

  renderThumbnails(previewSections, activeIndex, controllerState.sectionLabels || selectedSong?.sectionLabels || []);

  status.textContent = controllerState.active
    ? controllerState.blank
      ? t("projectorBlankScreen")
      : t("projectorSong", { title: controllerState.title, current: controllerState.step + 1, total: controllerState.sections.length })
    : t("projectorTeachingMode");
  status.classList.toggle("active", controllerState.active);
}

function renderThumbnails(sections, activeIndex, labels = []) {
  const thumbnailHost = byId("songThumbnails");
  if (!thumbnailHost) return;

  if (!sections.length) {
    thumbnailHost.innerHTML = `<div class="empty-state compact">${t("noSongScreens")}</div>`;
    return;
  }

  thumbnailHost.innerHTML = sections.map((section, index) => {
    const active = controllerState.active && index === activeIndex ? " active" : "";
    const firstLine = section[0] || `${t("screen")} ${index + 1}`;
    const label = labels[index] || `${t("screen")} ${index + 1}`;
    return `
      <button type="button" class="song-thumbnail${active}" data-screen-index="${index}">
        <b>${escapeHtml(label)}</b>
        <span>${escapeHtml(firstLine)}</span>
      </button>
    `;
  }).join("");
}

function hydrateColorsFromState() {
  byId("backgroundColor").value = controllerState.background || "#0f172a";
  if (!controllerState.blank) {
    byId("backgroundMedia").value = controllerState.backgroundMedia || "";
  }
  byId("textColor").value = controllerState.textColor || "#ffffff";
  byId("accentColor").value = controllerState.accentColor || "#38bdf8";
  renderBackgroundGallery();
}

socket.on("state", data => {
  latestState = data || {};
  controllerState = data.controllerState || controllerState;
  hydrateColorsFromState();
  renderCourseSections(data.headings || []);
  renderPreview();
});
socket.on("songs-updated", loadSongs);

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

byId("courseSections").addEventListener("click", event => {
  const section = event.target.closest("[data-slide-index]");
  if (!section) return;
  jumpToCourseSlide(section.dataset.slideIndex);
});

byId("newSongButton").addEventListener("click", () => openEditor());
byId("closeEditorButton").addEventListener("click", closeEditor);
byId("cancelEditorButton").addEventListener("click", closeEditor);
byId("saveSongButton").addEventListener("click", saveCurrentSong);
byId("importSongBackgroundButton").addEventListener("click", () => {
  byId("songBackgroundFile").click();
});
byId("songBackgroundFile").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;

  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

  const response = await fetch("/backgrounds/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: file.name,
      dataUrl
    })
  });

  if (!response.ok) return;

  const imported = await response.json();
  await loadBackgrounds();
  renderSongBackgroundSelect(imported.url || "");
  event.target.value = "";
});
byId("goLiveButton").addEventListener("click", sendLive);
byId("clearButton").addEventListener("click", clearLive);
byId("blankButton").addEventListener("click", blankLive);
byId("nextButton").addEventListener("click", nextSection);
byId("previousButton").addEventListener("click", previousSection);
byId("applyStyleButton").addEventListener("click", applyStyle);
byId("songSearch").addEventListener("input", renderSongList);
byId("toggleBackgroundButton").addEventListener("click", () => {
  const controls = byId("backgroundControls");
  controls.open = !controls.open;
});
byId("backgroundGallery").addEventListener("click", event => {
  const choice = event.target.closest("[data-background-url]");
  if (!choice) return;
  selectBackground(choice.dataset.backgroundUrl || "");
});
byId("clearBackgroundButton").addEventListener("click", () => selectBackground(""));
byId("backgroundColor").addEventListener("input", renderPreview);
byId("textColor").addEventListener("input", renderPreview);
byId("accentColor").addEventListener("input", renderPreview);

window.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea, select") || event.target.isContentEditable) return;

  if (selectBackgroundFromShortcut(event)) return;

  if (event.key === "Escape") {
    event.preventDefault();
    blankLive();
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
    sendLive();
    return;
  }

  if (event.key === "ArrowRight" || event.key === " ") {
    event.preventDefault();
    nextSection();
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    previousSection();
  }
});

window.CGVI18N.loadLanguage().then(() => {
  renderSongList();
  renderPreview();
  loadSongs();
  loadBackgrounds();
});
