const socket = io({ transports: ["websocket", "polling"] });

(function ensurePencilFilter() {
  if (document.getElementById("cgv-pencil-filter")) return;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.id = "cgv-pencil-filter";
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.setAttribute("aria-hidden", "true");
  svg.style.position = "absolute";
  svg.innerHTML = `
    <filter id="cgv-pencil-wobble" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed="3" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.35" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  `;
  document.body.prepend(svg);
})();

function fitMarkdownAnimations(root) {
  if (!root) return;

  root.querySelectorAll(".markdown-animation").forEach(chain => {
    chain.style.removeProperty("font-size");
    const parent = chain.parentElement;
    const available = Math.max(
      40,
      (parent?.clientWidth || root.clientWidth || 0) - (Number.parseFloat(getComputedStyle(chain).marginLeft) || 0) - 8
    );
    if (available < 40) return;

    const natural = Number.parseFloat(getComputedStyle(chain).fontSize) || 16;
    if (chain.scrollWidth <= available + 1) return;

    let size = natural;
    const min = Math.max(10, natural * 0.55);
    while (size > min && chain.scrollWidth > available + 1) {
      size -= 0.5;
      chain.style.fontSize = `${size}px`;
    }
  });
}

let latestState = {};
let songs = [];
let selectedSongId = null;
let selectedLibrary = "all";
const ROOT_SONG_LIBRARY_KEY = "__root__";
let swipeStart = null;

// Accent-fold search must work even if song-utils.js failed to load (stale cache / old build).
if (typeof normalizeForSearch !== "function") {
  window.normalizeForSearch = function normalizeForSearch(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  };
}

if (typeof getSongSearchHaystack !== "function") {
  window.getSongSearchHaystack = function getSongSearchHaystack(song) {
    if (!song || typeof song !== "object") return "";
    if (typeof song._searchHaystack === "string") return song._searchHaystack;
    song._searchHaystack = normalizeForSearch(
      `${song.file || ""}\n${song.title || ""}\n${song.lyrics || ""}\n${song.chordLyrics || ""}`
    );
    return song._searchHaystack;
  };
}

if (typeof songMatchesQuery !== "function") {
  window.songMatchesQuery = function songMatchesQuery(song, query) {
    const normalizedQuery = normalizeForSearch(query).trim();
    if (!normalizedQuery) return true;
    return getSongSearchHaystack(song).includes(normalizedQuery);
  };
}

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

function flattenRevealEntries(entries = []) {
  return entries.flatMap(entry => (
    Array.isArray(entry?.batch) ? entry.batch : [entry]
  ));
}

function renderEntries(entries = [], { stickyCount = 0 } = {}) {
  const rendered = [];
  const replaceIndexes = {};
  const flatEntries = flattenRevealEntries(entries);

  flatEntries.forEach((entry, index) => {
    const html = entry?.h4Intro && index < flatEntries.length - 1
      ? entry.h4OnlyHtml
      : getEntryHtml(entry);
    const replaceGroup = typeof entry === "string" ? null : entry?.replaceGroup;
    const key = replaceGroup || `entry-${index}`;
    const wrapped = `<div class="reveal-entry${index < stickyCount ? " reveal-sticky" : ""}" data-reveal-key="${escapeHtml(key)}">${html}</div>`;

    if (replaceGroup && replaceIndexes[replaceGroup] !== undefined) {
      const slot = replaceIndexes[replaceGroup];
      rendered[slot] = `<div class="reveal-entry${slot < stickyCount ? " reveal-sticky" : ""}" data-reveal-key="${escapeHtml(key)}">${html}</div>`;
      return;
    }

    if (replaceGroup) {
      replaceIndexes[replaceGroup] = rendered.length;
    }

    rendered.push(wrapped);
  });

  return rendered.join("");
}

function getVisibleTeachingHtml(state = {}) {
  const windowData = state.renderedSlideWindow;
  const renderedSlide = windowData?.current
    || state.renderedSlides?.[state.slide]
    || { sticky: [], lines: [] };
  const stickyEntries = flattenRevealEntries(renderedSlide.sticky || []);
  const visible = [
    ...stickyEntries,
    ...flattenRevealEntries((renderedSlide.lines || []).slice(0, (Number(state.step) || 0) + 1))
  ];

  return renderEntries(visible, { stickyCount: stickyEntries.length });
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

async function loadSongs({ renderList = false } = {}) {
  const response = await fetch("/songs");
  songs = response.ok ? await response.json() : [];
  // Keep search haystacks lazy — precomputing ~700 full lyric strings freezes phones.
  renderSongLibraryFilter();
  if (!selectedSongId || !songs.some(song => song.id === selectedSongId)) {
    selectedSongId = songs[0]?.id || null;
  }
  if (renderList || byId("songDrawer")?.classList.contains("open")) {
    if (selectedSongId && !getVisibleSongs().some(song => song.id === selectedSongId)) {
      selectedSongId = getVisibleSongs()[0]?.id || songs[0]?.id || null;
    }
    renderSongList();
  }
}

let songsLoadPromise = null;

function ensureSongsLoaded() {
  if (songs.length) return Promise.resolve(songs);
  if (!songsLoadPromise) {
    songsLoadPromise = loadSongs()
      .catch(() => {
        songs = [];
      })
      .finally(() => {
        songsLoadPromise = null;
      });
  }
  return songsLoadPromise;
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
    libraries.set(getSongLibraryKey(song), getSongLibraryName(song));
  });

  return [...libraries.entries()]
    .sort(([, a], [, b]) => a.localeCompare(b, undefined, { numeric: true }))
    .map(([key, name]) => ({ key, name }));
}

function getSongNumber(song, fallbackIndex = 0) {
  const fileName = String(song?.file || "").split("/").pop() || "";
  return fileName.match(/^[A-Za-z]*(\d+)/)?.[1] || String(fallbackIndex + 1).padStart(3, "0");
}

function getVisibleSongs() {
  const query = byId("songSearch")?.value || "";
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
  const visibleSongs = getVisibleSongs();

  let previousLibrary = "";
  list.innerHTML = visibleSongs.length
    ? visibleSongs.map((song, index) => {
        const libraryName = getSongLibraryName(song);
        const showLibraryHeader = selectedLibrary === "all" && libraryName !== previousLibrary;
        const libraryHeader = showLibraryHeader
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
    : `<div class="empty compact">${songs.length ? t("noSongsMatch") : t("noSongsFound")}</div>`;
}

let cachedSectionHeadingsKey = null;
let lastDirectorContentHtml = "";
let lastDirectorContentMode = null;
let lastDirectorPopupReference = undefined;
let lastDirectorPopupVerseIndex = undefined;
let directorFitFrame = 0;

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
  ensureSongsLoaded().then(() => {
    renderSongList();
    byId("songSearch")?.focus();
  });
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
  const isCompact = width <= 900 || height <= 560;

  if (isDesktop) {
    return isSongMode
      ? { max: 52, min: 22 }
      : { max: 38, min: 18 };
  }

  if (isCompact) {
    return isSongMode
      ? { max: 56, min: 18 }
      : { max: 42, min: 16 };
  }

  return isSongMode
    ? { max: 68, min: 24 }
    : { max: 52, min: 20 };
}

let lastFitContext = { slide: -1, step: -1, songMode: false, size: null };
let directorFitRetry = false;
const directorSlideFitCache = new Map();

function scheduleDirectorFit() {
  if (directorFitFrame) cancelAnimationFrame(directorFitFrame);

  directorFitFrame = requestAnimationFrame(() => {
    directorFitFrame = requestAnimationFrame(() => {
      directorFitFrame = 0;
      fitDirectorText();
    });
  });
}

function measureDirectorFitSize(content, html, minSize, maxSize) {
  const host = content.parentElement || document.body;
  const probe = content.cloneNode(false);
  probe.className = content.className;
  probe.removeAttribute("id");
  probe.innerHTML = html;
  probe.setAttribute("aria-hidden", "true");
  const maxWidth = Math.max(1, content.clientWidth);
  const maxHeight = Math.max(1, content.clientHeight);
  Object.assign(probe.style, {
    position: "absolute",
    left: "-100000px",
    top: "0",
    width: `${maxWidth}px`,
    height: "auto",
    maxHeight: "none",
    overflow: "visible",
    visibility: "hidden",
    pointerEvents: "none",
    zIndex: "-1"
  });
  host.appendChild(probe);

  const overflows = () => (
    probe.scrollHeight > maxHeight + 1
    || probe.scrollWidth > maxWidth + 1
  );

  let best = minSize;
  let low = minSize;
  let top = maxSize;
  while (low <= top) {
    const mid = (low + top) >> 1;
    probe.style.setProperty("--director-fit-size", `${mid}px`);
    if (overflows()) {
      top = mid - 1;
    } else {
      best = mid;
      low = mid + 1;
    }
  }

  probe.remove();
  return best;
}

function getDirectorLookaheadFitSize(content, state, minSize, maxSize) {
  const slideIndex = Number(state.slide) || 0;
  const cacheKey = `${slideIndex}|${content.clientWidth}x${content.clientHeight}|${minSize}-${maxSize}`;
  if (directorSlideFitCache.has(cacheKey)) {
    return directorSlideFitCache.get(cacheKey);
  }

  const windowData = state.renderedSlideWindow;
  const renderedSlide = windowData?.current
    || state.renderedSlides?.[slideIndex]
    || { sticky: [], lines: [] };
  const stickyEntries = flattenRevealEntries(renderedSlide.sticky || []);
  const lineEntries = flattenRevealEntries(renderedSlide.lines || []);
  if (!lineEntries.length && !stickyEntries.length) return null;

  let tightest = null;
  for (let stepIndex = 0; stepIndex < Math.max(1, lineEntries.length); stepIndex += 1) {
    const html = renderEntries([
      ...stickyEntries,
      ...lineEntries.slice(0, stepIndex + 1)
    ], { stickyCount: stickyEntries.length });
    if (!html) continue;
    const size = measureDirectorFitSize(content, html, minSize, maxSize);
    tightest = tightest == null ? size : Math.min(tightest, size);
  }

  if (tightest == null) return null;
  directorSlideFitCache.set(cacheKey, tightest);
  return tightest;
}

function fitDirectorText() {
  const content = byId("directorContent");
  if (!content) return;

  const isSongMode = content.classList.contains("song-mode");
  const sizing = getDirectorSizing(isSongMode);
  const minSize = sizing.min;
  const maxSize = sizing.max;

  // If the content box has no measurable height yet, try again once next frame.
  if (content.clientHeight < 32 || content.clientWidth < 32) {
    if (!directorFitRetry) {
      directorFitRetry = true;
      scheduleDirectorFit();
    }
    return;
  }
  directorFitRetry = false;

  if (!isSongMode) {
    const lookahead = getDirectorLookaheadFitSize(content, latestState, minSize, maxSize);
    if (lookahead != null) {
      content.style.setProperty("--director-fit-size", `${lookahead}px`);
      lastFitContext = {
        slide: Number(latestState.slide),
        step: Number(latestState.step),
        songMode: false,
        size: lookahead
      };
      fitMarkdownAnimations(content);
      return;
    }
  }

  const sameSlide = lastFitContext.songMode === isSongMode
    && lastFitContext.slide === Number(latestState.slide);
  const stepIncreased = sameSlide && Number(latestState.step) > lastFitContext.step;
  // Growing the same slide: start from the previous size (content only got larger).
  // New slide / mode: start from the max and binary-search down.
  let high = stepIncreased && lastFitContext.size
    ? lastFitContext.size
    : maxSize;
  high = Math.min(maxSize, Math.max(minSize, high));

  const overflows = () => (
    content.scrollHeight > content.clientHeight + 1 ||
    content.scrollWidth > content.clientWidth + 1
  );

  content.style.setProperty("--director-fit-size", `${high}px`);
  if (!overflows()) {
    lastFitContext = {
      slide: Number(latestState.slide),
      step: Number(latestState.step),
      songMode: isSongMode,
      size: high
    };
    fitMarkdownAnimations(content);
    return;
  }

  let best = minSize;
  let low = minSize;
  let top = high - 1;
  while (low <= top) {
    const mid = (low + top) >> 1;
    content.style.setProperty("--director-fit-size", `${mid}px`);
    if (overflows()) {
      top = mid - 1;
    } else {
      best = mid;
      low = mid + 1;
    }
  }

  content.style.setProperty("--director-fit-size", `${best}px`);
  lastFitContext = {
    slide: Number(latestState.slide),
    step: Number(latestState.step),
    songMode: isSongMode,
    size: best
  };
  fitMarkdownAnimations(content);
}

function renderDirector(state = {}) {
  latestState = state;
  if (byId("sectionDrawer")?.classList.contains("open")) {
    renderSectionList(state.headings || []);
  }

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
  const contentHtml = isSongMode
    ? controllerState.blank
      ? `<div class="empty">${t("blankScreenLive")}</div>`
      : getSongHtml(controllerState)
    : getVisibleTeachingHtml(state) || `<div class="empty">${t("noTeachingSlide")}</div>`;
  const contentChanged = contentHtml !== lastDirectorContentHtml || isSongMode !== lastDirectorContentMode;

  if (contentChanged) {
    content.innerHTML = contentHtml;
    lastDirectorContentHtml = contentHtml;
    lastDirectorContentMode = isSongMode;
    scheduleDirectorFit();
  }

  applyDirectorPopupState(contentChanged);
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
socket.on("songs-updated", () => {
  songs = [];
  ensureSongsLoaded().then(() => {
    if (byId("songDrawer")?.classList.contains("open")) renderSongList();
  });
});
socket.on("popup-scroll", data => {
  latestState.popupState = {
    ...(latestState.popupState || {}),
    reference: data.reference ?? latestState.popupState?.reference ?? null,
    scrollRatio: typeof data.scrollRatio === "number" ? data.scrollRatio : latestState.popupState?.scrollRatio || 0,
    verseIndex: Number.isInteger(data.verseIndex) ? data.verseIndex : latestState.popupState?.verseIndex || 0
  };
  applyDirectorPopupState(true);
});

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
byId("songLibraryFilter")?.addEventListener("change", event => {
  selectedLibrary = event.target.value || "all";
  if (selectedSongId && !getVisibleSongs().some(song => song.id === selectedSongId)) {
    selectedSongId = getVisibleSongs()[0]?.id || null;
  }
  renderSongList();
});
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

function getDirectorPopupVerseBlocks(popup) {
  return Array.from(popup?.querySelectorAll(":scope > .bible-popup-verse") || []);
}

function applyDirectorPopupVerseVisibility(popup, verseIndex = 0) {
  if (!popup) return 0;

  const blocks = getDirectorPopupVerseBlocks(popup);
  if (!blocks.length) return 0;

  const boundedIndex = Math.min(blocks.length - 1, Math.max(0, Number(verseIndex) || 0));

  blocks.forEach((block, index) => {
    const isActive = index === boundedIndex;
    block.classList.toggle("is-active", isActive);
    block.hidden = !isActive;
    if (isActive) block.setAttribute("data-active", "true");
    else block.removeAttribute("data-active");
  });

  const current = popup.querySelector("[data-popup-verse-current]");
  if (current) current.textContent = String(boundedIndex + 1);

  popup.querySelectorAll("[data-popup-verse]").forEach(button => {
    const delta = Number(button.dataset.popupVerse);
    const disabled = (delta < 0 && boundedIndex <= 0) || (delta > 0 && boundedIndex >= blocks.length - 1);
    button.disabled = disabled;
  });

  const nav = popup.querySelector(".bible-popup-nav");
  if (nav) nav.hidden = blocks.length <= 1;

  return boundedIndex;
}

function stepDirectorPopupVerse(direction) {
  const reference = latestState.popupState?.reference;
  if (!reference) return;

  const popup = document.querySelector(".bible-ref.open .bible-popup");
  const blocks = getDirectorPopupVerseBlocks(popup);
  const total = blocks.length || Number(
    document.querySelector(`.bible-ref.open`)?.dataset.verseCount
  ) || 1;
  const currentIndex = latestState.popupState?.verseIndex || 0;
  const nextIndex = Math.min(total - 1, Math.max(0, currentIndex + direction));
  if (nextIndex === currentIndex) return;

  applyDirectorPopupVerseVisibility(popup, nextIndex);
  latestState.popupState = {
    ...(latestState.popupState || {}),
    verseIndex: nextIndex,
    scrollRatio: 0
  };
  lastDirectorPopupVerseIndex = nextIndex;
  socket.emit("set-popup-verse", nextIndex);
}

function applyDirectorPopupState(force = false) {
  const activeReference = latestState.popupState?.reference;
  const verseIndex = latestState.popupState?.verseIndex || 0;
  if (
    !force &&
    activeReference === lastDirectorPopupReference &&
    verseIndex === lastDirectorPopupVerseIndex
  ) {
    return;
  }

  lastDirectorPopupReference = activeReference;
  lastDirectorPopupVerseIndex = verseIndex;
  document.querySelectorAll(".bible-ref.open").forEach(reference => reference.classList.remove("open"));
  if (!activeReference) return;

  document.querySelectorAll(".bible-ref").forEach(reference => {
    const isActive = reference.dataset.reference === activeReference;
    reference.classList.toggle("open", isActive);
    if (isActive) {
      applyDirectorPopupVerseVisibility(reference.querySelector(".bible-popup"), verseIndex);
    }
  });
}

document.addEventListener("click", event => {
  const verseButton = event.target.closest("[data-popup-verse]");
  if (verseButton) {
    event.preventDefault();
    event.stopPropagation();
    stepDirectorPopupVerse(Number(verseButton.dataset.popupVerse));
    return;
  }

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

window.addEventListener("resize", () => {
  lastFitContext = { slide: -1, step: -1, songMode: false, size: null };
  directorFitRetry = false;
  scheduleDirectorFit();
});
window.addEventListener("orientationchange", () => {
  lastFitContext = { slide: -1, step: -1, songMode: false, size: null };
  directorFitRetry = false;
  scheduleDirectorFit();
});
window.addEventListener("keydown", event => {
  if (event.target.matches("input, textarea, select")) return;

  if (latestState.popupState?.reference) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      stepDirectorPopupVerse(1);
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      stepDirectorPopupVerse(-1);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      socket.emit("set-popup-reference", null);
      return;
    }
  }

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
  // Defer song catalog until idle / drawer open so long sessions stay responsive.
  const schedule = window.requestIdleCallback || (cb => setTimeout(cb, 2500));
  schedule(() => {
    ensureSongsLoaded();
  });
});
