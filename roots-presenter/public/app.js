const socket = io({ transports: ["websocket", "polling"] });
window.CGV_SOCKET = socket;

const isPresenter = document.body.classList.contains("presenter");
const isAudience = document.body.classList.contains("audience");
const isProjector = document.body.classList.contains("projector");
const isTablet = document.body.classList.contains("tablet");
const projectorMode = new URLSearchParams(window.location.search).get("mode") || "extended";

if (isProjector || isTablet) {
  document.body.classList.add(`projector-${projectorMode}`);
}

let renderedSlides = [];
let slideCount = 0;
let slides = [];
let headings = [];
let quizzes = [];
let slide = 0;
let step = 0;
let quizState = { active: false, quizId: null, quiz: null, counts: {} };
let controllerState = { active: false, title: "", sections: [], step: 0 };
let userAnswer = null;
let session = null;
let connection = { url: "/audience.html" };
let audienceQrVisible = false;
let appLanguage = "es";
let participant = null;
let activeQuizKey = null;
let popupState = { reference: null, scrollRatio: 0, verseIndex: 0 };
let completedQuizIds = new Set();
let suppressPopupScrollSync = false;
let lastPopupScrollSentAt = 0;

const storedParticipantId = localStorage.getItem("rootsParticipantId")
  || (window.crypto?.randomUUID
    ? window.crypto.randomUUID()
    : `student-${Date.now()}-${Math.random()}`);
localStorage.setItem("rootsParticipantId", storedParticipantId);

socket.on("state", data => {
  session = data.session || null;
  connection = data.connection || connection;
  appLanguage = data.language || "es";
  window.CGVI18N?.setLanguage(appLanguage);
  syncRenderedSlides(data);
  slides = data.slides || [];
  headings = data.headings || [];
  quizzes = data.quizzes || [];
  slide = data.slide || 0;
  step = data.step || 0;
  quizState = data.quizState || { active: false, quizId: null, quiz: null, counts: {} };
  controllerState = data.controllerState || { active: false, title: "", sections: [], step: 0 };
  popupState = data.popupState || { reference: null, scrollRatio: 0, verseIndex: 0 };
  audienceQrVisible = !!data.audienceQrVisible;

  const nextQuizKey = quizState.active ? quizState.quizId : null;
  if (nextQuizKey !== activeQuizKey) {
    userAnswer = null;
    completedQuizIds = new Set();
    activeQuizKey = nextQuizKey;
  }

  render();
});

socket.on("participant-ack", data => {
  participant = data;
  localStorage.setItem("rootsParticipantName", participant.name);
  renderJoinForm();
  render();
});

socket.on("answer-ack", ack => {
  if (ack.accepted) {
    userAnswer = ack.answer;
    if (ack.quizId) {
      completedQuizIds.add(ack.quizId);
      userAnswer = null;
    }
  }
  render();
});

socket.on("style-settings-updated", data => {
  const link = document.querySelector('link[href^="style-settings.css"]');
  if (!link) return;

  link.href = `style-settings.css?v=${data?.updatedAt || Date.now()}`;
});

socket.on("popup-scroll", data => {
  popupState = {
    reference: data.reference ?? popupState.reference,
    scrollRatio: typeof data.scrollRatio === "number" ? data.scrollRatio : popupState.scrollRatio,
    verseIndex: Number.isInteger(data.verseIndex) ? data.verseIndex : popupState.verseIndex
  };
  applySharedPopupState();
});

function syncRenderedSlides(data = {}) {
  if (data.renderedSlideWindow) {
    const windowData = data.renderedSlideWindow;
    slideCount = Number(windowData.count) || 0;

    if (!renderedSlides.length || renderedSlides.length !== slideCount) {
      renderedSlides = Array.from({ length: slideCount }, () => ({ sticky: [], lines: [] }));
    }

    const currentSlide = Number(windowData.slide) || 0;
    renderedSlides[currentSlide] = windowData.current || { sticky: [], lines: [] };

    if (windowData.next && currentSlide + 1 < slideCount) {
      renderedSlides[currentSlide + 1] = windowData.next;
    }

    if (windowData.previous && currentSlide > 0) {
      renderedSlides[currentSlide - 1] = windowData.previous;
    }

    return;
  }

  renderedSlides = data.renderedSlides || [];
  slideCount = Number(data.slideCount) || renderedSlides.length;
}

function render() {
  const currentSlide = normalizeRenderedSlide(renderedSlides[slide]);
  const visible = currentSlide.lines.slice(0, step + 1);
  const html = renderEntries([...currentSlide.sticky, ...visible]);

  if (isPresenter) {
    const currentEl = document.getElementById("current");
    currentEl.innerHTML = html;

    const nextSlide = normalizeRenderedSlide(renderedSlides[slide + 1]);
    const nextEl = document.getElementById("next");
    nextEl.innerHTML = nextSlide.lines.length
      ? renderEntries([...nextSlide.sticky, ...nextSlide.lines])
      : `<em>${t("noNextSlide")}</em>`;

    renderPresenterQuiz();
    renderSessionStatus();
    renderPresenterSectionSelect();
    renderAudienceQrToggle();
    fitSlideText(currentEl, { baseSize: 46, minSize: 20 });
    fitSlideText(nextEl, { baseSize: 32, minSize: 16 });
    applySharedPopupState();
  }

  if (isProjector) {
    const projectorSlide = document.getElementById("projectorSlide");
    if (!projectorSlide) return;

    if (controllerState.active) {
      renderControllerProjector(projectorSlide);
      if (!isTablet) {
        renderProjectorQuiz();
        renderAudienceQrOverlay();
      }
      applySharedPopupState();
      if (isTablet) applyTabletPreviewScale();
      return;
    }

    projectorSlide.innerHTML = html;
    projectorSlide.classList.remove("song-output");
    projectorSlide.removeAttribute("style");
    applySlideLayoutClass(projectorSlide);
    if (!isTablet) {
      renderProjectorQuiz();
      renderAudienceQrOverlay();
    }
    fitProjectorSlide(projectorSlide);
    applySharedPopupState();
    if (isTablet) applyTabletPreviewScale();
  }

  if (isAudience) {
    const audienceSlide = document.getElementById("audienceSlide");
    audienceSlide.innerHTML = html;
    applySlideLayoutClass(audienceSlide);
    renderAudienceQuiz();
    fitSlideText(audienceSlide, {
      baseSize: 42,
      minSize: 20,
      maxHeight: Math.max(220, window.innerHeight * 0.48),
      maxWidth: audienceSlide.clientWidth
    });
    applySharedPopupState();
  }
}

function renderAudienceQrToggle() {
  const button = document.getElementById("audienceQrToggle");
  if (!button) return;

  button.classList.toggle("active", audienceQrVisible);
  button.textContent = audienceQrVisible ? t("hideAudienceQr") : t("showAudienceQr");
}

function renderAudienceQrOverlay() {
  const overlay = document.getElementById("audienceQrOverlay");
  if (!overlay) return;

  overlay.hidden = !audienceQrVisible;
  if (!audienceQrVisible) {
    overlay.innerHTML = "";
    return;
  }

  const joinUrl = getAudienceJoinUrl();
  overlay.innerHTML = `
    <div class="audience-qr-card">
      <strong>${escapeHtml(t("audienceQrTitle"))}</strong>
      <img src="/connection-qr.svg?path=/audience.html&t=${Date.now()}" alt="${escapeHtml(t("connectionQrAlt"))}">
      <code>${escapeHtml(joinUrl.replace(/^https?:\/\//, ""))}</code>
      <span>${escapeHtml(t("sameWifiHelp"))}</span>
    </div>
  `;
}

function getAudienceJoinUrl() {
  if (connection?.url) return connection.url;

  if (connection?.host && connection?.port) {
    return `http://${connection.host}:${connection.port}/audience.html`;
  }

  return `${window.location.origin}/audience.html`;
}

function renderControllerProjector(projectorSlide) {
  const section = controllerState.sections?.[controllerState.step] || [];
  const media = String(controllerState.backgroundMedia || "").trim();
  projectorSlide.classList.remove("title-slide");
  projectorSlide.classList.add("song-output");
  projectorSlide.style.setProperty("--song-background", controllerState.background || "#0f172a");
  projectorSlide.style.setProperty("--song-color", controllerState.textColor || "#ffffff");
  projectorSlide.style.setProperty("--song-accent", controllerState.accentColor || "#38bdf8");
  projectorSlide.classList.toggle("song-has-media", !controllerState.blank && !!media && !isVideoMedia(media));
  projectorSlide.classList.toggle("song-has-video", !controllerState.blank && !!media && isVideoMedia(media));

  if (controllerState.blank) {
    projectorSlide.classList.add("blank-output");
    projectorSlide.innerHTML = `
      ${media && !isVideoMedia(media) ? `<div class="song-background-image" style="background-image: url('${escapeHtml(media).replace(/'/g, "&#39;")}')"></div>` : ""}
      ${media && isVideoMedia(media) ? `<video class="song-background-video" src="${escapeHtml(media)}" autoplay muted loop playsinline></video>` : ""}
    `;
    return;
  }

  projectorSlide.classList.remove("blank-output");
  projectorSlide.innerHTML = `
    ${media && !isVideoMedia(media) ? `<div class="song-background-image" style="background-image: url('${escapeHtml(media).replace(/'/g, "&#39;")}')"></div>` : ""}
    ${media && isVideoMedia(media) ? `<video class="song-background-video" src="${escapeHtml(media)}" autoplay muted loop playsinline></video>` : ""}
    ${controllerState.title ? `<div class="song-output-title">${escapeHtml(controllerState.title)}</div>` : ""}
    <div class="song-output-inner">
      <div class="song-output-lines">
        ${section.map(line => `<div class="song-output-line">${escapeHtml(line)}</div>`).join("")}
      </div>
    </div>
  `;

  fitSongOutputText(projectorSlide);
}

function applySlideLayoutClass(element) {
  if (!element) return;

  const clone = element.cloneNode(true);
  clone.querySelectorAll(".bible-popup, .popup-controls").forEach(node => node.remove());

  const hasOnlyTitleContent =
    !!clone.querySelector("h1, h2, .manual-title, .manual-subtitle") &&
    !clone.querySelector("h3, h4, h5, h6, p:not(.manual-title):not(.manual-subtitle), ul, ol, blockquote, .definition, .synthesis-box");

  element.classList.toggle("title-slide", hasOnlyTitleContent);
}

function normalizeRenderedSlide(renderedSlide) {
  if (Array.isArray(renderedSlide)) {
    return { sticky: [], lines: renderedSlide };
  }

  return {
    sticky: renderedSlide?.sticky || [],
    lines: renderedSlide?.lines || []
  };
}

function getEntryHtml(entry) {
  if (isPresenter && entry?.presenterHtml) return entry.presenterHtml;
  if (isProjector && projectorMode === "mirrored" && entry?.presenterHtml) return entry.presenterHtml;
  if (entry?.teacherOnly && !isPresenter) return "";
  return typeof entry === "string" ? entry : entry?.html || "";
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

function renderEntries(entries) {
  const rendered = [];
  const replaceIndexes = {};
  const lastEntryIndex = entries.length - 1;

  entries.forEach((entry, index) => {
    const html = entry?.h4Intro && index < lastEntryIndex
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

function getPopupVerseBlocks(popup) {
  return Array.from(popup?.querySelectorAll(":scope > div") || []);
}

function getPopupVerseIndex(popup) {
  const blocks = getPopupVerseBlocks(popup);
  if (!blocks.length) return 0;

  let activeIndex = 0;
  let bestDistance = Infinity;

  blocks.forEach((block, index) => {
    const distance = Math.abs(block.offsetTop - popup.scrollTop);
    if (distance < bestDistance) {
      bestDistance = distance;
      activeIndex = index;
    }
  });

  return activeIndex;
}

function scrollPopupToVerseIndex(popup, verseIndex = 0, fallbackRatio = 0) {
  if (!popup) return;

  const blocks = getPopupVerseBlocks(popup);
  const maxScroll = Math.max(0, popup.scrollHeight - popup.clientHeight);
  let nextScrollTop = maxScroll * (fallbackRatio || 0);

  if (blocks.length) {
    const boundedIndex = Math.min(blocks.length - 1, Math.max(0, Number(verseIndex) || 0));
    nextScrollTop = blocks[boundedIndex].offsetTop;
  }

  popup.scrollTop = Math.min(maxScroll, Math.max(0, nextScrollTop));
}

function applySharedPopupState() {
  const activeReference = popupState.reference;
  let activePopup = null;

  ensurePresenterPopupControls();
  renderSharedPopupOverlay();

  document.querySelectorAll(".bible-ref.open").forEach(reference => {
    reference.classList.remove("open");
  });

  if ((isProjector || isAudience) && document.getElementById("sharedPopupOverlay")) {
    return;
  }

  if (!activeReference) return;

  document.querySelectorAll(".bible-ref").forEach(reference => {
    if (reference.dataset.reference === activeReference) {
      reference.classList.add("open");
      activePopup = reference.querySelector(".bible-popup");
    }
  });

  if (!activePopup) return;

  requestAnimationFrame(() => {
    suppressPopupScrollSync = true;
    scrollPopupToVerseIndex(activePopup, popupState.verseIndex, popupState.scrollRatio);
    requestAnimationFrame(() => {
      suppressPopupScrollSync = false;
    });
  });
}

function renderSharedPopupOverlay() {
  const overlay = document.getElementById("sharedPopupOverlay");
  if (!overlay) return;

  overlay.innerHTML = "";
  overlay.classList.toggle("open", !!popupState.reference);

  if (!popupState.reference) return;

  const sourcePopup = Array.from(document.querySelectorAll(".bible-ref"))
    .find(reference => reference.dataset.reference === popupState.reference)
    ?.querySelector(".bible-popup");

  if (!sourcePopup) return;

  overlay.innerHTML = sourcePopup.innerHTML;

  requestAnimationFrame(() => {
    scrollPopupToVerseIndex(overlay, popupState.verseIndex, popupState.scrollRatio);
  });
}

function ensurePresenterPopupControls() {
  if (!isPresenter) return;

  document.querySelectorAll(".bible-ref").forEach(reference => {
    if (reference.querySelector(".popup-controls")) return;

    const controls = document.createElement("span");
    controls.className = "popup-controls";
    controls.innerHTML = `
      <button class="popup-scroll-button" type="button" data-popup-scroll="-1">Up</button>
      <button class="popup-scroll-button" type="button" data-popup-scroll="1">Down</button>
    `;
    reference.appendChild(controls);
  });
}

function syncPopupScrollFromElement(popup, force = false) {
  if (!isPresenter || suppressPopupScrollSync || !popup) return;

  const now = Date.now();
  if (!force && now - lastPopupScrollSentAt < 80) return;

  const maxScroll = Math.max(0, popup.scrollHeight - popup.clientHeight);
  const scrollRatio = maxScroll ? popup.scrollTop / maxScroll : 0;
  const verseIndex = getPopupVerseIndex(popup);

  lastPopupScrollSentAt = now;
  socket.emit("set-popup-scroll", { scrollRatio, verseIndex });
}

function getProjectorBaseSize(element) {
  const clone = element.cloneNode(true);
  clone.querySelectorAll(".bible-popup, .popup-controls").forEach(node => node.remove());

  const textLength = clone.textContent.trim().length;
  const blockCount = clone.querySelectorAll("p, li, blockquote, h1, h2, h3, h4, h5, h6").length;
  const hasMajorHeading = !!clone.querySelector("h1, h2");

  const modeBoost = projectorMode === "extended" ? 8 : 0;

  if (hasMajorHeading && textLength < 90 && blockCount <= 2) return 68 + modeBoost;
  if (hasMajorHeading && textLength < 180 && blockCount <= 3) return 60 + modeBoost;
  return 52 + modeBoost;
}

const TABLET_SURFACE_W = 1920;
const TABLET_SURFACE_H = 1080;

function getProjectorLayoutSize() {
  if (isTablet) {
    return { width: TABLET_SURFACE_W, height: TABLET_SURFACE_H };
  }

  return {
    width: window.innerWidth,
    height: window.innerHeight
  };
}

function fitProjectorSlide(slideEl) {
  if (!slideEl) return;

  if (isTablet) {
    fitSlideText(slideEl, {
      baseSize: getProjectorBaseSize(slideEl),
      minSize: projectorMode === "extended" ? 40 : 32,
      hardMinSize: 28,
      maxHeight: slideEl.clientHeight,
      maxWidth: slideEl.clientWidth,
      densityFactor: projectorMode === "extended" ? 0.12 : 0.25,
      sizeBoost: projectorMode === "extended" ? 12 : 0
    });
    return;
  }

  const viewport = getProjectorLayoutSize();

  fitSlideText(slideEl, {
    baseSize: getProjectorBaseSize(slideEl),
    minSize: projectorMode === "extended" ? 40 : 32,
    hardMinSize: 28,
    maxHeight: viewport.height - 160,
    maxWidth: Math.min(slideEl.clientWidth || viewport.width * 0.78, viewport.width - 140),
    densityFactor: projectorMode === "extended" ? 0.12 : 0.25,
    sizeBoost: projectorMode === "extended" ? 12 : 0
  });
}

function applyTabletPreviewScale() {
  if (!isTablet) return;

  const viewport = document.querySelector(".tablet-viewport");
  const root = document.querySelector(".tablet-scale-root");
  if (!viewport || !root) return;

  root.style.width = `${TABLET_SURFACE_W}px`;
  root.style.height = `${TABLET_SURFACE_H}px`;

  const scale = Math.min(
    viewport.clientWidth / TABLET_SURFACE_W,
    viewport.clientHeight / TABLET_SURFACE_H
  );
  root.style.transform = `scale(${scale})`;
}

function scrollActivePresenterPopup(direction) {
  const popup = document.querySelector(".bible-ref.open .bible-popup");
  if (!popup) return;

  const blocks = getPopupVerseBlocks(popup);
  if (blocks.length) {
    const nextIndex = Math.min(
      blocks.length - 1,
      Math.max(0, getPopupVerseIndex(popup) + direction)
    );
    scrollPopupToVerseIndex(popup, nextIndex);
  } else {
    popup.scrollTop += direction * Math.max(80, popup.clientHeight * 0.65);
  }

  syncPopupScrollFromElement(popup, true);
}

function fitSlideText(element, options = {}) {
  if (!element) return;

  const baseSize = options.baseSize || 46;
  const minSize = options.minSize || 18;
  const hardMinSize = options.hardMinSize || minSize;
  const maxHeight = options.maxHeight || element.clientHeight || 350;
  const maxWidth = options.maxWidth || element.clientWidth || window.innerWidth;
  const densityPenalty = getSlideDensityPenalty(element) * (options.densityFactor ?? 1);
  let size = Math.max(minSize, baseSize + (options.sizeBoost || 0) - densityPenalty);

  element.style.setProperty("--fit-size", `${size}px`);

  requestAnimationFrame(() => {
    while (
      size > hardMinSize &&
      (
        element.scrollHeight > maxHeight ||
        element.scrollWidth > maxWidth ||
        element.offsetHeight > maxHeight ||
        element.offsetWidth > maxWidth
      )
    ) {
      size -= 2;
      if (size < hardMinSize) size = hardMinSize;
      element.style.setProperty("--fit-size", `${size}px`);
    }
  });
}

function fitSongOutputText(element) {
  if (!element) return;

  const lines = element.querySelector(".song-output-lines");
  if (!lines) return;

  element.classList.remove("song-allow-wrap");

  const baseSize = 154;
  const hardMinSize = 52;
  const maxWidth = Math.max(320, Math.min(window.innerWidth * 0.84, element.clientWidth || window.innerWidth));
  const maxHeight = Math.max(220, window.innerHeight * 0.78);
  let size = baseSize;

  element.style.setProperty("--fit-size", `${size}px`);

  requestAnimationFrame(() => {
    const isOverflowing = () => {
      const widestLine = [...element.querySelectorAll(".song-output-line")]
        .reduce((width, line) => Math.max(width, line.scrollWidth, line.getBoundingClientRect().width), 0);

      return (
        widestLine > maxWidth ||
        lines.scrollWidth > maxWidth ||
        lines.scrollHeight > maxHeight ||
        lines.getBoundingClientRect().height > maxHeight
      );
    };

    while (size > hardMinSize && isOverflowing()) {
      size -= 2;
      element.style.setProperty("--fit-size", `${size}px`);
    }

    if (isOverflowing()) {
      element.classList.add("song-allow-wrap");
    }
  });
}

function getSlideDensityPenalty(element) {
  const clone = element.cloneNode(true);
  clone.querySelectorAll(".bible-popup").forEach(popup => popup.remove());

  const textLength = clone.textContent.trim().length;
  const blockCount = element.querySelectorAll("p, li, blockquote, h1, h2, h3, h4, h5, h6").length;
  const heading = element.querySelector("h1, h2, h3, h4, h5, h6");
  const headingLevel = heading ? Number(heading.tagName.slice(1)) : 0;
  const textPenalty = Math.max(0, Math.ceil((textLength - 120) / 90)) * 3;
  const blockPenalty = Math.max(0, blockCount - 3) * 2;
  const headingPenalty = headingLevel ? Math.max(0, headingLevel - 3) * 2 : 0;

  return Math.min(30, textPenalty + blockPenalty + headingPenalty);
}

function renderSessionStatus() {
  const statusEl = document.getElementById("sessionStatus");
  if (!statusEl || !session) return;

  const started = new Date(session.startedAt).toLocaleString();
  statusEl.innerHTML = `
    <div><strong>${session.title}</strong></div>
    <div>${t("started")}: ${started}</div>
    <div>${t("students")}: ${session.participantCount}</div>
    <div>${t("savedResponses")}: ${session.responseCount}</div>
  `;
}

function getActiveQuiz() {
  return quizState.quiz || quizzes.find(quiz => quiz.id === quizState.quizId) || null;
}

function getActiveQuizSequence() {
  const sequenceIds = quizState.sequence?.length
    ? quizState.sequence
    : quizState.quizId
      ? quizzes.slice(Math.max(0, quizzes.findIndex(quiz => quiz.id === quizState.quizId))).map(quiz => quiz.id)
      : [];

  return sequenceIds
    .map(quizId => quizzes.find(quiz => quiz.id === quizId))
    .filter(Boolean);
}

function getAudienceQuiz() {
  return getActiveQuizSequence().find(quiz => !completedQuizIds.has(quiz.id)) || null;
}

function getQuizReviewItems() {
  return Array.isArray(quizState.review) ? quizState.review : [];
}

function renderQuizReviewList(items, options = {}) {
  if (!items.length) return "";

  return `
    <div class="${options.compact ? "quiz-review compact" : "quiz-review"}">
      <div class="quiz-review-title">${t("reviewAnswers")}</div>
      ${items
        .map((quiz, index) => {
          const correctAnswer = quiz.correctAnswer || quiz.choices?.[quiz.correctIndex] || t("answerNotMarked");
          return `
            <article class="quiz-review-item">
              <div class="quiz-review-question">${index + 1}. ${escapeHtml(quiz.question)}</div>
              <div class="quiz-review-answer"><b>${t("correctAnswer")}:</b> ${escapeHtml(correctAnswer)}</div>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderStudentGrade(result) {
  if (!result || !result.total) return "";

  return `
    <div class="quiz-grade">
      <div class="quiz-grade-label">${t("yourScore")}</div>
      <div class="quiz-grade-score">${result.correct}/${result.total}</div>
      <div class="quiz-grade-percent">${result.percentage}%</div>
      <div class="quiz-grade-detail">${result.answered}/${result.total} ${t("answered")}</div>
    </div>
  `;
}

function getTotalQuizResponses() {
  if (quizState.countsByQuiz && Object.keys(quizState.countsByQuiz).length) {
    return Object.values(quizState.countsByQuiz)
      .flatMap(counts => Object.values(counts || {}))
      .reduce((sum, value) => sum + value, 0);
  }

  return Object.values(quizState.counts || {}).reduce((sum, value) => sum + value, 0);
}

function stableHash(value) {
  return String(value || "").split("").reduce((hash, char) => {
    return ((hash << 5) - hash + char.charCodeAt(0)) | 0;
  }, 0);
}

function getShuffledChoiceIndexes(quiz) {
  const indexes = quiz.choices.map((_, index) => index);
  let seed = Math.abs(stableHash(`${storedParticipantId}:${quiz.id}`)) || 1;

  for (let index = indexes.length - 1; index > 0; index -= 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    const swapIndex = seed % (index + 1);
    [indexes[index], indexes[swapIndex]] = [indexes[swapIndex], indexes[index]];
  }

  return indexes;
}

function renderPresenterQuiz() {
  const activeQuiz = getActiveQuiz();
  const error = quizState.error;
  const statusEl = document.getElementById("quizStatus");
  const controlsEl = document.getElementById("quizControls");
  const resultsEl = document.getElementById("quizResults");

  if (!statusEl || !controlsEl || !resultsEl) return;

  if (!quizzes.length) {
    statusEl.innerHTML = `<em>${t("noQuizFilesLoaded")}</em>`;
    controlsEl.innerHTML = `<div>${t("addQuizYaml")}</div>`;
    resultsEl.innerHTML = "";
    return;
  }

  const selectedQuizId = activeQuiz?.id || quizzes[0].id;

  statusEl.innerHTML = error
    ? `<strong>${t("quizProblem")}:</strong> ${escapeHtml(error.message)}`
    : activeQuiz
      ? `<strong>${t("active")}:</strong> ${activeQuiz.title}<br>${activeQuiz.question}`
      : `<em>${t("noQuizRunning")}</em>`;

  controlsEl.innerHTML = `
    <select id="quizSelect" class="quiz-select">
      ${quizzes
        .map(quiz => {
          const selected = quiz.id === selectedQuizId ? " selected" : "";
          return `<option value="${quiz.id}"${selected}>${quiz.title}</option>`;
        })
        .join("")}
    </select>
    <button onclick="startQuiz()">${t("launchQuiz")}</button>
    <button onclick="endQuiz()">${t("endQuiz")}</button>
    <button onclick="clearQuiz()">${t("clearAnswers")}</button>
  `;

  if (!activeQuiz) {
    resultsEl.innerHTML = "";
    return;
  }

  const counts = quizState.counts || {};
  const total = quizState.active
    ? Object.values(counts).reduce((sum, value) => sum + value, 0)
    : getTotalQuizResponses();
  const reviewItems = getQuizReviewItems();

  resultsEl.innerHTML = `
    <div class="quiz-results-title">${t("responses")}: ${total}</div>
    <ul class="quiz-results-list">
      ${activeQuiz.choices
        .map((choice, index) => {
          const count = counts[index] || 0;
          const percentage = total ? Math.round((count / total) * 100) : 0;
          return `<li>${choice}: ${count} (${percentage}%)</li>`;
        })
        .join("")}
    </ul>
    ${renderQuizReviewList(reviewItems, { compact: true })}
  `;
}

function renderProjectorQuiz() {
  const quiz = getActiveQuiz();
  const error = quizState.error;
  const resultsEl = document.getElementById("projectorQuiz");
  if (!resultsEl) return;
  if (!resultsEl) return;
  const joinUrl = connection?.url || "/audience.html";
  const joinCode = connection?.host && connection?.port
    ? `${connection.host}:${connection.port}`
    : joinUrl.replace(/^https?:\/\//, "").replace(/\/audience\.html$/, "");

  if (error) {
    resultsEl.innerHTML = `
      <div class="projector-quiz-copy">
        <strong>${t("quizNotAvailable")}</strong>
        <span>${escapeHtml(error.message)}</span>
      </div>
    `;
    return;
  }

  if (!quiz) {
    resultsEl.innerHTML = "";
    return;
  }

  if (controllerState.active) {
    resultsEl.innerHTML = "";
    return;
  }

  if (quizState.active) {
    resultsEl.innerHTML = `
      <div class="projector-quiz-copy">
        <strong>${t("quizLiveNow")}</strong>
        <span>${escapeHtml(quiz.question)}</span>
        <div class="projector-quiz-join">
          <b>${t("joinLabel")}:</b>
          <code>${escapeHtml(joinCode)}</code>
        </div>
        <small>${escapeHtml(joinUrl)}</small>
      </div>
      <img class="projector-quiz-qr" src="/quiz-join.svg?${Date.now()}" alt="QR code to join quiz">
    `;
  } else {
    const total = getTotalQuizResponses();
    const reviewItems = getQuizReviewItems();
    resultsEl.innerHTML = `
      <div class="projector-quiz-copy">
        <strong>${t("quizClosed")}</strong>
        <span>${t("responses")}: ${total}</span>
      </div>
      ${renderQuizReviewList(reviewItems)}
    `;
  }
}

function renderAudienceQuiz() {
  const launchedQuiz = getActiveQuiz();
  const quiz = quizState.active ? getAudienceQuiz() : launchedQuiz;
  const quizArea = document.getElementById("quizArea");

  if (!participant) {
    quizArea.innerHTML = `
      <div class="quiz-message">${t("enterNameToAnswer")}</div>
    `;
    return;
  }

  if (!launchedQuiz) {
    quizArea.innerHTML = `
      <div class="quiz-message">${t("waitingForQuiz")}</div>
    `;
    return;
  }

  if (!quizState.active) {
    const reviewItems = getQuizReviewItems();
    if (reviewItems.length) {
      quizArea.innerHTML = `
        <div class="quiz-waiting">
          <div class="quiz-question">${t("quizCompleted")}</div>
          <div class="quiz-message">${t("thanksAnswersSaved")}</div>
          ${renderStudentGrade(quizState.participantResult)}
          ${renderQuizReviewList(reviewItems, { compact: true })}
        </div>
      `;
      return;
    }

    quizArea.innerHTML = `
      <div class="quiz-waiting">
        <div class="quiz-question">${launchedQuiz.question}</div>
        <div class="quiz-message">${t("waitingForPresenterStart")}</div>
      </div>
    `;
    return;
  }

  if (!quiz) {
    quizArea.innerHTML = `
      <div class="quiz-waiting">
        <div class="quiz-question">${t("quizCompleted")}</div>
        <div class="quiz-message">${t("thanksAnswersSaved")}</div>
        ${renderStudentGrade(quizState.participantResult)}
        ${renderQuizReviewList(getQuizReviewItems(), { compact: true })}
      </div>
    `;
    return;
  }

  const counts = quizState.countsByQuiz?.[quiz.id] || {};
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  const sequence = getActiveQuizSequence();
  const questionNumber = sequence.findIndex(item => item.id === quiz.id) + 1;
  const questionTotal = sequence.length;

  quizArea.innerHTML = `
    <div class="quiz-results-summary">${t("questionOf", { current: questionNumber, total: questionTotal })}</div>
    <div class="quiz-question">${quiz.question}</div>
    <div class="quiz-options">
      ${getShuffledChoiceIndexes(quiz)
        .map(originalIndex => {
          const selected = userAnswer === originalIndex ? " selected" : "";
          return `<button class="quiz-option${selected}" onclick="submitAnswer(${originalIndex})">${quiz.choices[originalIndex]}</button>`;
        })
        .join("")}
    </div>
    <div class="quiz-your-answer">${t("selectAnswer")}</div>
    <div class="quiz-results-summary">${t("responses")}: ${total}</div>
  `;
}

function next() {
  socket.emit("next");
}

function prev() {
  socket.emit("prev");
}

function reloadSlides() {
  socket.emit("reload-slides");
}

function renderPresenterSectionSelect() {
  const select = document.getElementById("presenterSectionSelect");
  if (!select) return;

  if (!headings.length) {
    select.innerHTML = `<option value="">${t("noCourseSections")}</option>`;
    select.disabled = true;
    return;
  }

  const currentValue = String(slide);
  select.disabled = false;
  select.innerHTML = headings
    .map(heading => {
      const selected = String(heading.slide) === currentValue ? " selected" : "";
      const prefix = heading.level === 2 ? "  H2 " : "H1 ";
      return `<option value="${heading.slide}"${selected}>${escapeHtml(prefix + heading.title)}</option>`;
    })
    .join("");
}

async function jumpToPresenterSection() {
  const select = document.getElementById("presenterSectionSelect");
  if (!select?.value) return;
  await fetch(`/jump/${encodeURIComponent(select.value)}`, { method: "POST" });
}

function newSession() {
  userAnswer = null;
  socket.emit("new-session");
}

function startQuiz() {
  const select = document.getElementById("quizSelect");
  socket.emit("start-quiz", select?.value);
}

function launchQuiz(quizId) {
  socket.emit("start-quiz", quizId);
}

function endQuiz() {
  socket.emit("end-quiz");
}

function clearQuiz() {
  socket.emit("clear-quiz");
  userAnswer = null;
}

function joinSession(event) {
  event.preventDefault();

  const nameInput = document.getElementById("participantName");
  const name = nameInput.value.trim();
  if (!name) return;

  socket.emit("join-session", {
    id: storedParticipantId,
    name
  });
}

function renderJoinForm() {
  if (!isAudience) return;

  const form = document.getElementById("joinForm");
  const input = document.getElementById("participantName");
  const greeting = document.getElementById("joinGreeting");
  const storedName = localStorage.getItem("rootsParticipantName") || "";
  const activeName = participant?.name || storedName;

  if (!form || !input) return;

  input.value = activeName;
  form.classList.toggle("joined", !!activeName);

  if (greeting) {
    greeting.textContent = activeName ? t("helloName", { name: activeName }) : "";
    greeting.classList.toggle("joined", !!activeName);
  }
}

function submitAnswer(answerIndex) {
  const quiz = isAudience ? getAudienceQuiz() : getActiveQuiz();
  if (!quiz) return;

  socket.emit("submit-answer", {
    quizId: quiz.id,
    answerIndex,
    participant: {
      id: storedParticipantId,
      name: participant?.name || localStorage.getItem("rootsParticipantName") || "Anonymous"
    }
  });
}

function toggleAudienceQr() {
  socket.emit("set-audience-qr-visible", !audienceQrVisible);
}

document.addEventListener("click", event => {
  const scrollButton = event.target.closest("[data-popup-scroll]");
  if (isPresenter && scrollButton) {
    event.preventDefault();
    event.stopPropagation();
    scrollActivePresenterPopup(Number(scrollButton.dataset.popupScroll));
    return;
  }

  const reference = event.target.closest(".bible-ref");

  if (isPresenter && reference) {
    event.preventDefault();
    socket.emit("set-popup-reference", reference.dataset.reference || null);
    return;
  }

  if ((isProjector || isAudience) && reference && document.getElementById("sharedPopupOverlay")) {
    event.preventDefault();
    const nextReference = reference.dataset.reference || null;
    popupState = {
      reference: popupState.reference === nextReference ? null : nextReference,
      scrollRatio: 0,
      verseIndex: 0
    };
    renderSharedPopupOverlay();
    return;
  }

  if (isProjector && popupState.reference) {
    popupState = { reference: null, scrollRatio: 0, verseIndex: 0 };
    renderSharedPopupOverlay();
    return;
  }

  if (isPresenter && !event.target.closest("button, a, select, input, .quiz-panel, .session-panel, footer")) {
    socket.emit("set-popup-reference", null);
    return;
  }

  if (!reference) return;

  event.preventDefault();
  document.querySelectorAll(".bible-ref.open").forEach(openReference => {
    if (openReference !== reference) {
      openReference.classList.remove("open");
    }
  });
  reference.classList.toggle("open");
});

document.addEventListener("scroll", event => {
  if (!isPresenter || suppressPopupScrollSync) return;

  const popup = event.target.closest?.(".bible-popup");
  if (!popup) return;

  const reference = popup.closest(".bible-ref");
  if (!reference?.classList.contains("open")) return;

  const now = Date.now();
  if (now - lastPopupScrollSentAt < 80) return;
  syncPopupScrollFromElement(popup);
}, true);

if (isAudience) {
  renderJoinForm();

  socket.on("connect", () => {
    const storedName = localStorage.getItem("rootsParticipantName");
    if (!storedName) return;

    socket.emit("join-session", {
      id: storedParticipantId,
      name: storedName
    });
  });
}

document.getElementById("presenterSectionSelect")?.addEventListener("change", jumpToPresenterSection);
document.getElementById("audienceQrToggle")?.addEventListener("click", toggleAudienceQr);

window.addEventListener("resize", () => {
  render();
  applyTabletPreviewScale();
});

if (isPresenter || (isProjector && !isTablet)) {
  window.addEventListener("keydown", e => {
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "ArrowRight" || e.key === " ") next();
    if (e.key === "ArrowLeft") prev();
    if (isProjector && e.key === "Escape") {
      popupState = { reference: null, scrollRatio: 0, verseIndex: 0 };
      renderSharedPopupOverlay();
    }
  });
}

const DRAW_W = 1920;
const DRAW_H = 1080;
const DRAW_COLOR = "#facc15";
const PEN_WIDTH = 6;
const ERASER_WIDTH = 36;

let drawingMode = "pen";
let drawingActive = false;

function initDrawingCanvas(canvas) {
  if (!canvas) return;

  canvas.width = DRAW_W;
  canvas.height = DRAW_H;
}

function getDrawPoint(event, canvas) {
  const rect = canvas.getBoundingClientRect();

  if (!rect.width || !rect.height) {
    return { x: 0, y: 0 };
  }

  return {
    x: ((event.clientX - rect.left) / rect.width) * DRAW_W,
    y: ((event.clientY - rect.top) / rect.height) * DRAW_H
  };
}

function prepareDrawingContext(ctx, erase) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = erase ? ERASER_WIDTH : PEN_WIDTH;

  if (erase) {
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "rgba(0,0,0,1)";
  } else {
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = DRAW_COLOR;
  }
}

function drawPoint(ctx, point) {
  ctx.lineTo(point.x, point.y);
}

function applyDrawPoint(point, canvas, erase) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  prepareDrawingContext(ctx, erase);

  if (!point.drawing) {
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    return;
  }

  drawPoint(ctx, point);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(point.x, point.y);
}

function setDrawingMode(mode) {
  drawingMode = mode === "eraser" ? "eraser" : "pen";

  document.querySelectorAll(".tablet-toolbar button").forEach(button => {
    const label = button.textContent.trim().toLowerCase();
    button.classList.toggle("active", label === drawingMode);
  });
}

function clearDrawing() {
  const canvas = document.getElementById("projectorCanvas");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, DRAW_W, DRAW_H);
  }

  socket.emit("draw-clear");
}

function emitDrawPoint(point) {
  socket.emit("draw-point", point);
}

function handleDrawingPointerDown(event) {
  if (!isTablet || event.button !== 0) return;

  const canvas = document.getElementById("projectorCanvas");
  if (!canvas) return;

  event.preventDefault();
  drawingActive = true;

  const point = {
    ...getDrawPoint(event, canvas),
    drawing: false,
    erase: drawingMode === "eraser"
  };

  applyDrawPoint(point, canvas, point.erase);
  emitDrawPoint(point);
  event.currentTarget.setPointerCapture(event.pointerId);
}

function handleDrawingPointerMove(event) {
  if (!isTablet || !drawingActive) return;

  const canvas = document.getElementById("projectorCanvas");
  if (!canvas) return;

  event.preventDefault();

  const point = {
    ...getDrawPoint(event, canvas),
    drawing: true,
    erase: drawingMode === "eraser"
  };

  applyDrawPoint(point, canvas, point.erase);
  emitDrawPoint(point);
}

function finishDrawingPointer(event) {
  if (!isTablet || !drawingActive) return;

  drawingActive = false;

  if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
    event.currentTarget.releasePointerCapture(event.pointerId);
  }
}

if (isTablet) {
  window.setDrawingMode = setDrawingMode;
  window.clearDrawing = clearDrawing;

  const drawingCanvas = document.getElementById("projectorCanvas");
  initDrawingCanvas(drawingCanvas);

  drawingCanvas?.addEventListener("pointerdown", handleDrawingPointerDown);
  drawingCanvas?.addEventListener("pointermove", handleDrawingPointerMove);
  drawingCanvas?.addEventListener("pointerup", finishDrawingPointer);
  drawingCanvas?.addEventListener("pointercancel", finishDrawingPointer);

  applyTabletPreviewScale();
}

if (isProjector && !isTablet) {
  const projectorCanvas = document.getElementById("projectorCanvas");
  initDrawingCanvas(projectorCanvas);

  socket.on("draw-point", point => {
    if (!projectorCanvas || !point || point.meta) return;

    applyDrawPoint(point, projectorCanvas, !!point.erase);
  });

  socket.on("draw-clear", () => {
    if (!projectorCanvas) return;

    const ctx = projectorCanvas.getContext("2d");
    ctx.clearRect(0, 0, DRAW_W, DRAW_H);
  });
}
