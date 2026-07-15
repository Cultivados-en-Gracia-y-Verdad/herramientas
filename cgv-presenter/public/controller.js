const socket = io({ transports: ["websocket", "polling"] });

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
let selectedSongId = null;
let previewStep = 0;
let editingSongId = null;
let selectedLibrary = "all";
const ROOT_SONG_LIBRARY_KEY = "__root__";
let defaultSongRepository = {
  repository: "Cultivados-en-Gracia-y-Verdad/canciones",
  url: "https://github.com/Cultivados-en-Gracia-y-Verdad/canciones/",
  branch: "main",
  songsPath: "songs/chordpro"
};

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
  renderSongLibraryFilter();
  if (!selectedSongId || !songs.some(song => song.id === selectedSongId)) {
    selectedSongId = getVisibleSongs()[0]?.id || songs[0]?.id || null;
  }
  renderSongList();
  renderPreview();
}

async function loadDefaultSongRepository() {
  try {
    const response = await fetch("/songs/repository");
    if (!response.ok) return;

    const config = await response.json();
    defaultSongRepository = {
      ...defaultSongRepository,
      ...config,
      url: config.url || `https://github.com/${config.repository || defaultSongRepository.repository}/`
    };
  } catch {
    // Keep the built-in CGV canciones suggestion.
  }

  const input = byId("downloadSongsRepository");
  if (input) {
    input.value = input.value.trim() || defaultSongRepository.url;
    input.placeholder = defaultSongRepository.url;
  }
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

function getSongLibraryKey(song) {
  const parts = String(song?.file || "").split("/").filter(Boolean);
  return parts.length > 1 ? parts.slice(0, -1).join("/").toLowerCase() : ROOT_SONG_LIBRARY_KEY;
}

function getSongLibraries() {
  const libraries = new Map();
  songs.forEach(song => {
    const key = getSongLibraryKey(song);
    const name = getSongLibraryName(song);
    libraries.set(key, name);
  });

  return [...libraries.entries()]
    .sort(([, a], [, b]) => a.localeCompare(b, undefined, { numeric: true }))
    .map(([key, name]) => ({ key, name }));
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
  controllerState = {
    ...controllerState,
    active: false,
    blank: false,
    title: "",
    sections: [],
    chordSections: [],
    sectionLabels: [],
    step: 0
  };
  renderPreview();
  socket.emit("controller-clear");
}

/** "off" | "native" | "css" — prevents native exit events from wiping CSS-only fullscreen on phones. */
let controllerFullscreenMode = "off";

function isControllerFullscreen() {
  return controllerFullscreenMode !== "off" || !!(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.body.classList.contains("controller-fullscreen")
  );
}

function syncFullscreenButton() {
  const button = byId("fullscreenButton");
  if (!button) return;
  const active = isControllerFullscreen();
  const label = active ? t("exitFullscreen") : t("fullscreen");
  button.setAttribute("aria-label", label);
  button.setAttribute("title", label);
  button.classList.toggle("active", active);
}

function setControllerFullscreenClass(active) {
  document.body.classList.toggle("controller-fullscreen", active);
  if (!active) controllerFullscreenMode = "off";
  syncFullscreenButton();
  const previewCard = document.querySelector(".preview-card");
  if (previewCard) previewCard.scrollTop = 0;
  const thumbs = byId("songThumbnails");
  if (thumbs) thumbs.scrollLeft = 0;
  requestAnimationFrame(() => {
    const preview = byId("controllerPreview");
    if (preview?.classList.contains("song-output") && !preview.classList.contains("blank-output")) {
      fitPreviewSongText(preview);
    }
  });
}

async function requestNativeFullscreen(target) {
  if (!target) return false;

  if (typeof target.requestFullscreen === "function") {
    try {
      await target.requestFullscreen({ navigationUI: "hide" });
    } catch {
      await target.requestFullscreen();
    }
    return !!(document.fullscreenElement || document.webkitFullscreenElement);
  }

  if (typeof target.webkitRequestFullscreen === "function") {
    target.webkitRequestFullscreen();
    return !!document.webkitFullscreenElement;
  }

  if (typeof target.webkitRequestFullScreen === "function") {
    target.webkitRequestFullScreen();
    return !!document.webkitFullscreenElement;
  }

  if (typeof target.msRequestFullscreen === "function") {
    target.msRequestFullscreen();
    return !!document.msFullscreenElement;
  }

  return false;
}

async function enterControllerFullscreen() {
  let native = false;

  try {
    native = await requestNativeFullscreen(document.documentElement);
  } catch {
    native = false;
  }

  if (!native) {
    try {
      native = await requestNativeFullscreen(document.body);
    } catch {
      native = false;
    }
  }

  controllerFullscreenMode = native ? "native" : "css";
  setControllerFullscreenClass(true);
}

async function exitControllerFullscreen() {
  try {
    if (document.exitFullscreen && document.fullscreenElement) {
      await document.exitFullscreen();
    } else if (document.webkitExitFullscreen && document.webkitFullscreenElement) {
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen && document.msFullscreenElement) {
      document.msExitFullscreen();
    }
  } catch {
    // Keep CSS fallback exit below.
  }

  controllerFullscreenMode = "off";
  setControllerFullscreenClass(false);
}

async function toggleControllerFullscreen() {
  if (isControllerFullscreen()) {
    await exitControllerFullscreen();
  } else {
    await enterControllerFullscreen();
  }
}

function blankLive({ useDefaultBackground = true } = {}) {
  socket.emit("controller-blank", {
    background: byId("backgroundColor").value,
    // Default blank uses Settings → blank background image, not the last gallery pick.
    backgroundMedia: useDefaultBackground ? "" : byId("backgroundMedia").value.trim(),
    textColor: byId("textColor").value,
    accentColor: byId("accentColor").value,
    useConfiguredBlankMedia: useDefaultBackground
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

function setDownloadStatus(message, isError = false) {
  const status = byId("downloadSongsStatus");
  if (!status) return;

  status.textContent = message;
  status.classList.toggle("error", isError);
}

async function downloadSongsFromGithub(event) {
  event.preventDefault();

  const button = byId("downloadSongsButton");
  const input = byId("downloadSongsRepository");
  const repository = input.value.trim() || defaultSongRepository.url;

  button.disabled = true;
  setDownloadStatus(t("songsDownloading"));

  try {
    const response = await fetch("/songs/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository,
        branch: defaultSongRepository.branch,
        songsPath: defaultSongRepository.songsPath
      })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || response.statusText);

    setDownloadStatus(t("songsDownloadedMessage").replace("{count}", result.fileCount || 0));
    await loadSongs();
  } catch (error) {
    setDownloadStatus(error.message || t("songsDownloadFailedTitle"), true);
  } finally {
    button.disabled = false;
  }
}

function toggleGithubSongForm() {
  const form = byId("downloadSongsForm");
  form.classList.toggle("hidden");

  if (!form.classList.contains("hidden")) {
    const input = byId("downloadSongsRepository");
    input.value = input.value.trim() || defaultSongRepository.url;
    input.focus();
    input.select();
  }
}

function isEditingText(event) {
  const tagName = event.target?.tagName?.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select" || event.target?.isContentEditable;
}

function isSongSearchTarget(event) {
  return event.target?.id === "songSearch";
}

/** True when shortcuts should stay out of the way (song editor, GitHub form, etc.). Search is exempt so Esc can still blank when the query is empty. */
function shouldIgnorePresentationShortcut(event) {
  return isEditingText(event) && !isSongSearchTarget(event);
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
  const visibleSongs = getVisibleSongs();

  if (!visibleSongs.some(song => song.id === selectedSongId)) {
    selectedSongId = visibleSongs[0]?.id || null;
  }

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
    const showLibraryHeader = selectedLibrary === "all" && libraryName !== previousLibrary;
    const libraryHeader = showLibraryHeader
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

function getVisibleSongs() {
  const query = byId("songSearch").value;
  const librarySongs = selectedLibrary === "all"
    ? songs
    : songs.filter(song => getSongLibraryKey(song) === selectedLibrary);

  return query.trim()
    ? librarySongs.filter(song => songMatchesQuery(song, query))
    : librarySongs;
}

function renderSongLibraryFilter() {
  const select = byId("songLibraryFilter");
  if (!select) return;

  const libraries = getSongLibraries();
  const previousValue = selectedLibrary;
  select.replaceChildren();

  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = t("allSongLibraries");
  select.appendChild(allOption);

  libraries.forEach(library => {
    const option = document.createElement("option");
    option.value = library.key;
    option.textContent = library.name;
    select.appendChild(option);
  });

  selectedLibrary = previousValue === "all" || libraries.some(library => library.key === previousValue)
    ? previousValue
    : "all";
  select.value = selectedLibrary;
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
    renderBackgroundQuickKeys();
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

  renderBackgroundQuickKeys();
}

function renderBackgroundQuickKeys() {
  const host = byId("backgroundQuickKeys");
  if (!host) return;

  const selectedUrl = byId("backgroundMedia").value.trim();
  const slots = Array.from({ length: 10 }, (_, index) => {
    const background = backgrounds[index] || null;
    const key = index === 9 ? "0" : String(index + 1);
    const selected = background && background.url === selectedUrl ? " selected" : "";
    const disabled = background ? "" : " disabled";
    const label = background?.name || key;
    return `
      <button
        type="button"
        class="background-key${selected}"
        data-background-index="${index}"
        ${disabled}
        title="${escapeHtml(label)}"
        aria-label="${escapeHtml(label)}"
      >${key}</button>
    `;
  });

  host.innerHTML = slots.join("");
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

function selectBackground(url, { goBlank = false } = {}) {
  byId("backgroundMedia").value = url || "";
  renderBackgroundGallery();
  renderPreview();
  if (goBlank) {
    blankLive({ useDefaultBackground: false });
    return;
  }
  applyStyle();
}

function selectBackgroundByIndex(index, { goBlank = false } = {}) {
  const background = backgrounds[index];
  if (!background) return false;
  selectBackground(background.url, { goBlank });
  return true;
}

function getBackgroundShortcutIndex(event) {
  if (shouldIgnorePresentationShortcut(event)) return -1;
  // Numbers must type into song search (e.g. "002"), not switch backgrounds.
  if (isSongSearchTarget(event)) return -1;
  if (event.altKey || event.ctrlKey || event.metaKey) return -1;

  const digitMatch = event.code?.match(/^(?:Digit|Numpad)(\d)$/);
  const key = digitMatch ? digitMatch[1] : event.key;

  if (!/^\d$/.test(key)) return -1;
  return key === "0" ? 9 : Number(key) - 1;
}

function selectBackgroundFromShortcut(event) {
  const index = getBackgroundShortcutIndex(event);
  if (index < 0) return false;
  if (!selectBackgroundByIndex(index)) return false;
  event.preventDefault();
  return true;
}

function renderPreview() {
  const preview = byId("controllerPreview");
  const status = byId("liveStatus");
  const selectedSong = getSelectedSong();
  const isLive = !!controllerState.active;
  const showBlank = isLive && !!controllerState.blank;
  const liveMedia = controllerState.backgroundMedia || "";
  const media = isLive
    ? liveMedia
    : "";
  // Preview mirrors the projector: teaching when not live, otherwise the live song/blank.
  const liveSections = isLive && !showBlank ? controllerState.sections || [] : [];
  const selectedSections = selectedSong ? parseSections(selectedSong.lyrics) : [];
  const thumbnailSections = isLive && !showBlank ? liveSections : selectedSections;

  if (previewStep >= thumbnailSections.length) {
    previewStep = Math.max(0, thumbnailSections.length - 1);
  }

  const activeIndex = isLive ? controllerState.step : previewStep;
  const activeSection = liveSections[activeIndex] || [];
  const title = isLive ? controllerState.title || "" : "";
  const showSongStage = isLive && (showBlank || liveSections.length > 0);
  const background = isLive
    ? controllerState.background || byId("backgroundColor").value
    : byId("backgroundColor").value;
  const textColor = isLive
    ? controllerState.textColor || byId("textColor").value
    : byId("textColor").value;
  const accentColor = isLive
    ? controllerState.accentColor || byId("accentColor").value
    : byId("accentColor").value;

  preview.style.setProperty("--song-background", background);
  preview.style.setProperty("--song-color", textColor);
  preview.style.setProperty("--song-accent", accentColor);
  preview.classList.toggle("has-media", !!media && !isVideoMedia(media) && !showBlank);
  preview.classList.toggle("has-video", !!media && isVideoMedia(media) && !showBlank);
  preview.classList.toggle("blank-output", showBlank);
  preview.classList.toggle("teaching-mode", !isLive);
  preview.classList.toggle("song-output", showSongStage);

  if (!isLive) {
    preview.innerHTML = `
      <div class="teaching-mode-preview">
        <strong>${t("teachingMode")}</strong>
        <span>${t("teacherHasProjector")}</span>
      </div>
    `;
  } else if (showBlank) {
    preview.innerHTML = `
      ${media && !isVideoMedia(media) ? `<div class="song-background-image" style="background-image: url('${escapeHtml(media).replace(/'/g, "&#39;")}')"></div>` : ""}
      ${media && isVideoMedia(media) ? `<video class="song-background-video" src="${escapeHtml(media)}" autoplay muted loop playsinline></video>` : ""}
    `;
  } else {
    preview.innerHTML = `
      ${media && !isVideoMedia(media) ? `<div class="song-background-image" style="background-image: url('${escapeHtml(media).replace(/'/g, "&#39;")}')"></div>` : ""}
      ${media && isVideoMedia(media) ? `<video class="song-background-video" src="${escapeHtml(media)}" autoplay muted loop playsinline></video>` : ""}
      ${title ? `<div class="song-output-title">${escapeHtml(title)}</div>` : ""}
      <div class="song-output-inner">
        <div class="song-output-lines">
          ${activeSection.map(line => `<div class="song-output-line">${escapeHtml(line)}</div>`).join("")}
        </div>
      </div>
    `;
    fitPreviewSongText(preview);
  }

  renderThumbnails(thumbnailSections, activeIndex, controllerState.sectionLabels || selectedSong?.sectionLabels || []);

  status.textContent = isLive
    ? showBlank
      ? t("projectorBlankScreen")
      : t("projectorSong", { title: controllerState.title, current: controllerState.step + 1, total: controllerState.sections.length })
    : t("projectorTeachingMode");
  status.classList.toggle("active", isLive);
}

/** Fit lyrics to the preview content box so they can stay truly centered. */
function fitPreviewSongText(element) {
  if (!element) return;

  const lines = element.querySelector(".song-output-lines");
  if (!lines) return;

  element.classList.remove("song-allow-wrap");

  const bounds = element.querySelector(".song-output-inner") || element;
  const width = bounds.clientWidth;
  const height = bounds.clientHeight;
  if (width < 2 || height < 2) {
    requestAnimationFrame(() => fitPreviewSongText(element));
    return;
  }

  const isDesktop = window.matchMedia("(min-width: 901px)").matches;
  const scale = width / 1920;
  const baseSize = Math.max(isDesktop ? 32 : 28, (isDesktop ? 176 : 168) * scale);
  const hardMinSize = Math.max(16, 52 * scale);
  // Stay inside the padded content box — oversized text overflows and looks top/side biased.
  const maxWidth = Math.max(40, width * (isDesktop ? 0.92 : 0.88));
  const maxHeight = Math.max(40, height * (isDesktop ? 0.82 : 0.78));
  const step = Math.max(0.5, 2 * scale);
  let size = baseSize;

  element.style.setProperty("--fit-size", `${size}px`);

  requestAnimationFrame(() => {
    const isOverflowing = () => {
      const widestLine = [...element.querySelectorAll(".song-output-line")]
        .reduce((widest, line) => Math.max(widest, line.scrollWidth, line.getBoundingClientRect().width), 0);

      return (
        widestLine > maxWidth ||
        lines.scrollWidth > maxWidth ||
        lines.scrollHeight > maxHeight ||
        lines.getBoundingClientRect().height > maxHeight
      );
    };

    while (size > hardMinSize && isOverflowing()) {
      size -= step;
      element.style.setProperty("--fit-size", `${size}px`);
    }

    if (isOverflowing()) {
      element.classList.add("song-allow-wrap");
    }
  });
}

function renderThumbnails(sections, activeIndex, labels = []) {
  const thumbnailHost = byId("songThumbnails");
  if (!thumbnailHost) return;

  if (!sections.length) {
    thumbnailHost.innerHTML = `<div class="empty-state compact">${t("noSongScreens")}</div>`;
    return;
  }

  const titleOnly = window.matchMedia("(max-width: 900px)").matches;
  thumbnailHost.classList.toggle("title-only", titleOnly);

  thumbnailHost.innerHTML = sections.map((section, index) => {
    const active = index === activeIndex ? " active" : "";
    const firstLine = section[0] || `${t("screen")} ${index + 1}`;
    const label = labels[index] || `${t("screen")} ${index + 1}`;
    return `
      <button type="button" class="song-thumbnail${active}" data-screen-index="${index}" title="${escapeHtml(firstLine)}">
        <b>${escapeHtml(label)}</b>
        ${titleOnly ? "" : `<span>${escapeHtml(firstLine)}</span>`}
      </button>
    `;
  }).join("");

  const activeThumbnail = thumbnailHost.querySelector(".song-thumbnail.active");
  if (activeThumbnail) {
    const hostLeft = thumbnailHost.scrollLeft;
    const hostRight = hostLeft + thumbnailHost.clientWidth;
    const thumbLeft = activeThumbnail.offsetLeft;
    const thumbRight = thumbLeft + activeThumbnail.offsetWidth;
    if (thumbLeft < hostLeft) {
      thumbnailHost.scrollLeft = thumbLeft - 8;
    } else if (thumbRight > hostRight) {
      thumbnailHost.scrollLeft = thumbRight - thumbnailHost.clientWidth + 8;
    }
  }
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
  controllerState = data.controllerState || controllerState;
  hydrateColorsFromState();
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

  // Device stand-in for Enter: tap the already-selected song again to go live.
  if (songId === selectedSongId) {
    byId("songSearch")?.blur();
    sendLive();
    return;
  }

  selectedSongId = songId;
  previewStep = 0;
  renderSongList();
  renderPreview();
  byId("songSearch")?.blur();
});

byId("songList").addEventListener("dblclick", event => {
  const songItem = event.target.closest("[data-song-id]");
  if (!songItem || event.target.closest(".song-edit")) return;

  selectedSongId = songItem.dataset.songId;
  previewStep = 0;
  renderSongList();
  renderPreview();
  byId("songSearch")?.blur();
  sendLive();
});

byId("songThumbnails").addEventListener("click", event => {
  const thumbnail = event.target.closest("[data-screen-index]");
  if (!thumbnail) return;

  const targetIndex = Number(thumbnail.dataset.screenIndex);
  if (!Number.isInteger(targetIndex)) return;

  if (!controllerState.active) {
    previewStep = targetIndex;
    renderPreview();
    return;
  }

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
byId("fullscreenButton").addEventListener("click", toggleControllerFullscreen);
byId("nextButton").addEventListener("click", nextSection);
byId("previousButton").addEventListener("click", previousSection);
byId("applyStyleButton").addEventListener("click", applyStyle);
byId("songSearch").addEventListener("input", renderSongList);
byId("songLibraryFilter").addEventListener("change", event => {
  selectedLibrary = event.target.value || "all";
  const visibleSongs = getVisibleSongs();
  if (!visibleSongs.some(song => song.id === selectedSongId)) {
    selectedSongId = visibleSongs[0]?.id || null;
    previewStep = 0;
  }
  renderSongList();
  renderPreview();
});
byId("toggleBackgroundButton").addEventListener("click", () => {
  const controls = byId("backgroundControls");
  controls.open = !controls.open;
});
byId("backgroundGallery").addEventListener("click", event => {
  const choice = event.target.closest("[data-background-url]");
  if (!choice) return;
  // Device stand-in for digit + Esc: one tap selects the background and blanks live.
  selectBackground(choice.dataset.backgroundUrl || "", { goBlank: true });
});
byId("backgroundQuickKeys").addEventListener("click", event => {
  const key = event.target.closest("[data-background-index]");
  if (!key || key.disabled) return;
  const index = Number(key.dataset.backgroundIndex);
  if (!Number.isInteger(index)) return;
  // Change background under the current song/blank — never replace lyrics with blank.
  selectBackgroundByIndex(index, { goBlank: false });
});
byId("clearBackgroundButton").addEventListener("click", () => selectBackground(""));
byId("backgroundColor").addEventListener("input", renderPreview);
byId("textColor").addEventListener("input", renderPreview);
byId("accentColor").addEventListener("input", renderPreview);
byId("downloadSongsToggle").addEventListener("click", toggleGithubSongForm);
byId("downloadSongsForm").addEventListener("submit", downloadSongsFromGithub);

window.addEventListener("keydown", event => {
  // Song search stays focused for typing; Esc still drives the stage when search is empty.
  if (shouldIgnorePresentationShortcut(event)) return;
  if (selectBackgroundFromShortcut(event)) return;

  const inSongSearch = isSongSearchTarget(event);

  if (event.key === "Escape") {
    event.preventDefault();
    if (inSongSearch && byId("songSearch").value) {
      byId("songSearch").value = "";
      renderSongList();
      return;
    }
    blankLive();
    return;
  }

  // Enter in search must not Send Live — leave the field for filtering/selection.
  if (event.key === "Enter") {
    if (inSongSearch) return;
    event.preventDefault();
    sendLive();
    return;
  }

  // Leave arrow/space behavior to the search caret/typing while filtering.
  if (inSongSearch) return;

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
  loadDefaultSongRepository();
  loadSongs();
  loadBackgrounds();
});

const previewStage = document.querySelector(".preview-stage");
if (previewStage && typeof ResizeObserver !== "undefined") {
  let resizeFitTimer = 0;
  new ResizeObserver(() => {
    window.clearTimeout(resizeFitTimer);
    resizeFitTimer = window.setTimeout(() => {
      const preview = byId("controllerPreview");
      if (preview?.classList.contains("song-output") && !preview.classList.contains("blank-output")) {
        fitPreviewSongText(preview);
      }
    }, 50);
  }).observe(previewStage);
}

document.addEventListener("fullscreenchange", () => {
  if (document.fullscreenElement) {
    controllerFullscreenMode = "native";
    setControllerFullscreenClass(true);
    return;
  }
  // Ignore native "exit" events when we are in CSS-only fullscreen (common on phones).
  if (controllerFullscreenMode === "native") {
    controllerFullscreenMode = "off";
    setControllerFullscreenClass(false);
  }
});
document.addEventListener("webkitfullscreenchange", () => {
  if (document.webkitFullscreenElement) {
    controllerFullscreenMode = "native";
    setControllerFullscreenClass(true);
    return;
  }
  if (controllerFullscreenMode === "native") {
    controllerFullscreenMode = "off";
    setControllerFullscreenClass(false);
  }
});

const compactThumbnailQuery = window.matchMedia("(max-width: 900px)");
const refreshThumbnailsForViewport = () => {
  const preview = byId("controllerPreview");
  if (!preview) return;
  renderPreview();
};
if (compactThumbnailQuery.addEventListener) {
  compactThumbnailQuery.addEventListener("change", refreshThumbnailsForViewport);
} else if (compactThumbnailQuery.addListener) {
  compactThumbnailQuery.addListener(refreshThumbnailsForViewport);
}
