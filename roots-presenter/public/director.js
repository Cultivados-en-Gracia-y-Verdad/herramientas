const socket = io({ transports: ["websocket", "polling"] });

let latestState = {};
let songs = [];
let selectedSongId = null;
let swipeStart = null;

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

function getEntryHtml(entry) {
  return typeof entry === "string" ? entry : entry?.html || "";
}

function renderEntries(entries = []) {
  const rendered = [];
  const replaceIndexes = {};

  entries.forEach((entry, index) => {
    const html = entry?.h4Intro && index < entries.length - 1
      ? entry.h4OnlyHtml
      : getEntryHtml(entry);
    const replaceGroup = typeof entry === "string" ? null : entry?.replaceGroup;

    if (replaceGroup && replaceIndexes[replaceGroup] !== undefined) {
      rendered[replaceIndexes[replaceGroup]] = html;
      return;
    }

    if (replaceGroup) {
      replaceIndexes[replaceGroup] = rendered.length;
    }

    rendered.push(html);
  });

  return rendered.join("");
}

function getVisibleTeachingHtml(state = {}) {
  const windowData = state.renderedSlideWindow;
  const renderedSlide = windowData?.current
    || state.renderedSlides?.[state.slide]
    || { sticky: [], lines: [] };
  const visible = [
    ...(renderedSlide.sticky || []),
    ...(renderedSlide.lines || []).slice(0, (Number(state.step) || 0) + 1)
  ];

  return renderEntries(visible);
}

function getSongHtml(controllerState = {}) {
  const section = controllerState.sections?.[controllerState.step] || [];
  return section.length
    ? section.map(line => `<div>${escapeHtml(line)}</div>`).join("")
    : `<div class="empty">${t("noSongSectionLive")}</div>`;
}

async function post(path) {
  await fetch(path, { method: "POST" });
}

async function loadSongs() {
  const response = await fetch("/songs");
  songs = response.ok ? await response.json() : [];
  if (!selectedSongId || !songs.some(song => song.id === selectedSongId)) {
    selectedSongId = songs[0]?.id || null;
  }
  renderSongList();
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
  const controllerState = latestState.controllerState || {};

  return {
    title: song?.title || t("songs"),
    lyrics: song?.lyrics || "",
    chordLyrics: song?.chordLyrics || song?.lyrics || "",
    sectionLabels: song?.sectionLabels || [],
    sections: song?.sections || parseSections(song?.lyrics || ""),
    chordSections: song?.chordSections || parseChordSections(song?.chordLyrics || song?.lyrics || ""),
    background: controllerState.background || "#0f172a",
    backgroundMedia: controllerState.backgroundMedia || "",
    textColor: controllerState.textColor || "#ffffff",
    accentColor: controllerState.accentColor || "#38bdf8"
  };
}

function sendSongLive(song = getSelectedSong()) {
  if (!song) return;
  selectedSongId = song.id;
  socket.emit("controller-set-song", getSongPayload(song));
  closeSongDrawer();
}

function showSongListScreen() {
  const controllerState = latestState.controllerState || {};
  socket.emit("controller-song-list", {
    title: t("chooseSong"),
    background: controllerState.background || "#0f172a",
    backgroundMedia: controllerState.backgroundMedia || "",
    textColor: controllerState.textColor || "#ffffff",
    accentColor: controllerState.accentColor || "#38bdf8"
  });
  closeSongDrawer();
}

function renderSongList() {
  const list = byId("songList");
  const query = byId("songSearch").value.trim().toLowerCase();
  const visibleSongs = query
    ? songs.filter(song => `${song.file}\n${song.title}\n${song.lyrics}`.toLowerCase().includes(query))
    : songs;

  let previousLibrary = "";
  list.innerHTML = visibleSongs.length
    ? visibleSongs.map((song, index) => {
        const libraryName = getSongLibraryName(song);
        const libraryHeader = libraryName !== previousLibrary
          ? `<div class="song-library-heading">${escapeHtml(libraryName)}</div>`
          : "";
        previousLibrary = libraryName;

        return `
          ${libraryHeader}
          <button type="button" class="song-choice" data-song-id="${escapeHtml(song.id)}">
            <b>${escapeHtml(getSongNumber(song, index))}</b>
            <span>${escapeHtml(song.title)}</span>
          </button>
        `;
      }).join("")
    : `<div class="empty compact">${t("noSongsFound")}</div>`;
}

let cachedSectionHeadingsKey = null;

function getSectionHeadingsKey(headings = []) {
  return headings.map(heading => `${heading.slide}:${heading.level}:${heading.title}`).join("|");
}

function updateSectionListActive(slideIndex) {
  const list = byId("sectionList");
  if (!list) return;

  list.querySelectorAll(".section-choice").forEach(button => {
    const index = Number(button.dataset.slideIndex);
    button.classList.toggle("active", index === Number(slideIndex));
  });
}

function renderSectionList(headings = latestState.headings || []) {
  const list = byId("sectionList");
  if (!list) return;

  const headingsKey = getSectionHeadingsKey(headings);
  if (headingsKey === cachedSectionHeadingsKey) {
    updateSectionListActive(latestState.slide);
    return;
  }

  cachedSectionHeadingsKey = headingsKey;
  list.innerHTML = headings.length
    ? headings.map(heading => {
        const active = Number(latestState.slide) === Number(heading.slide) ? " active" : "";
        return `
          <button type="button" class="song-choice section-choice level-${heading.level}${active}" data-slide-index="${heading.slide}">
            <b>H${heading.level}</b>
            <span>${escapeHtml(heading.title)}</span>
          </button>
        `;
      }).join("")
    : `<div class="empty compact">${t("noCourseSections")}</div>`;
}

function openSongDrawer() {
  byId("songDrawer").classList.add("open");
  byId("songSearch").focus();
}

function closeSongDrawer() {
  byId("songDrawer").classList.remove("open");
}

function openSectionDrawer() {
  renderSectionList();
  byId("sectionDrawer").classList.add("open");
}

function closeSectionDrawer() {
  byId("sectionDrawer").classList.remove("open");
}

async function jumpToCourseSlide(slideIndex) {
  await post(`/jump/${encodeURIComponent(slideIndex)}`);
  closeSectionDrawer();
}

function goNext() {
  if (latestState.controllerState?.active) {
    post("/controller/next");
  } else {
    post("/control/next");
  }
}

function goPrevious() {
  if (latestState.controllerState?.active) {
    post("/controller/previous");
  } else {
    post("/control/prev");
  }
}

function returnToTeaching() {
  socket.emit("controller-clear");
  closeSongDrawer();
}

function getDirectorSizing(isSongMode) {
  const width = window.innerWidth || document.documentElement.clientWidth || 0;
  const height = window.innerHeight || document.documentElement.clientHeight || 0;
  const hasFinePointer = window.matchMedia?.("(pointer: fine)")?.matches;
  const isDesktop = hasFinePointer && width >= 900 && height >= 560;
  const isCompact = width <= 720 || height <= 520;

  if (isDesktop) {
    return isSongMode
      ? { max: 52, min: 26 }
      : { max: 38, min: 22 };
  }

  if (isCompact) {
    return isSongMode
      ? { max: 64, min: 34 }
      : { max: 50, min: 32 };
  }

  return isSongMode
    ? { max: 68, min: 36 }
    : { max: 52, min: 32 };
}

let lastFitContext = { slide: -1, step: -1, songMode: false, size: null };

function fitDirectorText() {
  const content = byId("directorContent");
  if (!content) return;

  const isSongMode = content.classList.contains("song-mode");
  const sizing = getDirectorSizing(isSongMode);
  const minSize = sizing.min;
  const sameSlide = !isSongMode && lastFitContext.slide === Number(latestState.slide);
  const stepIncreased = sameSlide && Number(latestState.step) > lastFitContext.step;
  let size = stepIncreased && lastFitContext.size ? lastFitContext.size : sizing.max;

  content.style.setProperty("--director-fit-size", `${size}px`);

  while (
    size > minSize &&
    (content.scrollHeight > content.clientHeight || content.scrollWidth > content.clientWidth)
  ) {
    size -= 2;
    content.style.setProperty("--director-fit-size", `${size}px`);
  }

  lastFitContext = {
    slide: Number(latestState.slide),
    step: Number(latestState.step),
    songMode: isSongMode,
    size
  };
}

function renderDirector(state = {}) {
  latestState = state;
  renderSectionList(state.headings || []);

  const controllerState = state.controllerState || {};
  const isSongMode = !!controllerState.active;
  const slideCount = state.slideCount ?? state.renderedSlideWindow?.count ?? state.renderedSlides?.length ?? 0;
  const slideNumber = Math.min(slideCount, (Number(state.slide) || 0) + 1);
  const songTotal = controllerState.sections?.length || 0;
  const songStep = Math.min(songTotal, (Number(controllerState.step) || 0) + 1);

  document.body.classList.toggle("song-mode", isSongMode);
  byId("directorTitle").textContent = isSongMode
    ? controllerState.blank
      ? t("blankScreen")
      : controllerState.title || t("songs")
    : state.course?.title || t("teaching");
  byId("directorMode").textContent = isSongMode
    ? controllerState.blank ? t("blankMode") : t("songMode")
    : t("teachingMode");
  byId("directorPosition").textContent = isSongMode
    ? `${songStep}/${songTotal || "?"}`
    : `${slideNumber}/${slideCount || "?"}`;

  const content = byId("directorContent");
  content.classList.toggle("song-mode", isSongMode);
  content.innerHTML = isSongMode
    ? controllerState.blank
      ? `<div class="empty">${t("blankScreenLive")}</div>`
      : getSongHtml(controllerState)
    : getVisibleTeachingHtml(state) || `<div class="empty">${t("noTeachingSlide")}</div>`;

  requestAnimationFrame(fitDirectorText);
  applyDirectorPopupState();
}

async function toggleFullscreen() {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
    return;
  }

  await document.documentElement.requestFullscreen();
}

function isSwipeIgnoredTarget(target) {
  return !!target.closest("input, textarea, select, button, a, .song-drawer, .bible-popup");
}

function beginSwipe(event) {
  const touch = event.changedTouches?.[0];
  if (!touch || isSwipeIgnoredTarget(event.target)) {
    swipeStart = null;
    return;
  }

  swipeStart = {
    x: touch.clientX,
    y: touch.clientY,
    time: Date.now()
  };
}

function endSwipe(event) {
  const touch = event.changedTouches?.[0];
  if (!touch || !swipeStart || isSwipeIgnoredTarget(event.target)) {
    swipeStart = null;
    return;
  }

  const deltaX = touch.clientX - swipeStart.x;
  const deltaY = touch.clientY - swipeStart.y;
  const elapsed = Date.now() - swipeStart.time;
  swipeStart = null;

  if (elapsed > 900 || Math.abs(deltaX) < 62 || Math.abs(deltaX) < Math.abs(deltaY) * 1.35) {
    return;
  }

  if (deltaX < 0) {
    goNext();
  } else {
    goPrevious();
  }
}

socket.on("state", renderDirector);
socket.on("songs-updated", loadSongs);

byId("nextButton").addEventListener("click", goNext);
byId("previousButton").addEventListener("click", goPrevious);
byId("fullscreenButton").addEventListener("click", toggleFullscreen);
byId("teachingButton").addEventListener("click", returnToTeaching);
byId("sectionsButton").addEventListener("click", openSectionDrawer);
byId("closeSectionsButton").addEventListener("click", closeSectionDrawer);
byId("songsButton").addEventListener("click", openSongDrawer);
byId("closeSongsButton").addEventListener("click", closeSongDrawer);
byId("showSongListButton").addEventListener("click", showSongListScreen);
byId("songSearch").addEventListener("input", renderSongList);
byId("songList").addEventListener("click", event => {
  const choice = event.target.closest("[data-song-id]");
  if (!choice) return;

  const song = songs.find(item => item.id === choice.dataset.songId);
  if (song) sendSongLive(song);
});
byId("sectionList").addEventListener("click", event => {
  const section = event.target.closest("[data-slide-index]");
  if (!section) return;
  jumpToCourseSlide(section.dataset.slideIndex);
});

function applyDirectorPopupState() {
  document.querySelectorAll(".bible-ref.open").forEach(reference => reference.classList.remove("open"));
  const activeReference = latestState.popupState?.reference;
  if (!activeReference) return;

  document.querySelectorAll(".bible-ref").forEach(reference => {
    reference.classList.toggle("open", reference.dataset.reference === activeReference);
  });
}

document.addEventListener("click", event => {
  const reference = event.target.closest(".bible-ref");
  const popup = event.target.closest(".bible-popup");

  if (popup) return;

  if (!reference) {
    if (latestState.popupState?.reference) {
      socket.emit("set-popup-reference", null);
    }
    return;
  }

  event.preventDefault();
  const nextReference = reference.dataset.reference || null;
  const isAlreadyOpen = reference.classList.contains("open");
  socket.emit("set-popup-reference", isAlreadyOpen ? null : nextReference);
});

document.addEventListener("touchstart", beginSwipe, { passive: true });
document.addEventListener("touchend", endSwipe, { passive: true });

window.addEventListener("resize", fitDirectorText);
window.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea, select")) return;

  if (event.key === "ArrowRight" || event.key === " " || event.key === "Enter") {
    event.preventDefault();
    goNext();
    return;
  }

  if (event.key === "ArrowLeft" || event.key === "Backspace") {
    event.preventDefault();
    goPrevious();
    return;
  }

  if (event.key.toLowerCase() === "f") {
    event.preventDefault();
    toggleFullscreen();
  }
});

window.CGVI18N.loadLanguage().then(() => {
  renderDirector();
  loadSongs();
});
