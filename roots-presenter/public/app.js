const socket = io();

const isPresenter = document.body.classList.contains("presenter");
const isAudience = document.body.classList.contains("audience");
const isProjector = document.body.classList.contains("projector");
const projectorMode = new URLSearchParams(window.location.search).get("mode") || "extended";

if (isProjector) {
  document.body.classList.add(`projector-${projectorMode}`);
}

let renderedSlides = [];
let slides = [];
let quizzes = [];
let slide = 0;
let step = 0;
let quizState = { active: false, quizId: null, quiz: null, counts: {} };
let userAnswer = null;
let session = null;
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
  renderedSlides = data.renderedSlides || [];
  slides = data.slides || [];
  quizzes = data.quizzes || [];
  slide = data.slide || 0;
  step = data.step || 0;
  quizState = data.quizState || { active: false, quizId: null, quiz: null, counts: {} };
  popupState = data.popupState || { reference: null, scrollRatio: 0, verseIndex: 0 };

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
      : "<em>No next slide</em>";

    renderPresenterQuiz();
    renderSessionStatus();
    fitSlideText(currentEl, { baseSize: 46, minSize: 20 });
    fitSlideText(nextEl, { baseSize: 32, minSize: 16 });
    applySharedPopupState();
  }

  if (isProjector) {
    const projectorSlide = document.getElementById("projectorSlide");
    projectorSlide.innerHTML = html;
    applySlideLayoutClass(projectorSlide);
    renderProjectorQuiz();
    fitSlideText(projectorSlide, {
      baseSize: getProjectorBaseSize(projectorSlide),
      minSize: projectorMode === "extended" ? 40 : 32,
      hardMinSize: 28,
      maxHeight: window.innerHeight - 160,
      maxWidth: Math.min(window.innerWidth * (projectorMode === "extended" ? 0.86 : 0.76), 1440),
      densityFactor: projectorMode === "extended" ? 0.12 : 0.25,
      sizeBoost: projectorMode === "extended" ? 12 : 0
    });
    applySharedPopupState();
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
  if (entry?.teacherOnly && !isPresenter) return "";
  return typeof entry === "string" ? entry : entry?.html || "";
}

function renderEntries(entries) {
  const rendered = [];
  const replaceIndexes = {};

  entries.forEach(entry => {
    const html = getEntryHtml(entry);
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
    let rect = element.getBoundingClientRect();

    while (
      size > hardMinSize &&
      (
        element.scrollHeight > maxHeight ||
        element.scrollWidth > maxWidth ||
        rect.height > maxHeight ||
        rect.width > maxWidth
      )
    ) {
      size -= 2;
      if (size < hardMinSize) size = hardMinSize;
      element.style.setProperty("--fit-size", `${size}px`);
      rect = element.getBoundingClientRect();
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
    <div>Started: ${started}</div>
    <div>Students: ${session.participantCount}</div>
    <div>Saved responses: ${session.responseCount}</div>
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
  const statusEl = document.getElementById("quizStatus");
  const controlsEl = document.getElementById("quizControls");
  const resultsEl = document.getElementById("quizResults");

  if (!statusEl || !controlsEl || !resultsEl) return;

  if (!quizzes.length) {
    statusEl.innerHTML = "<em>No quiz files loaded.</em>";
    controlsEl.innerHTML = "<div>Add quiz YAML files in the markdown frontmatter.</div>";
    resultsEl.innerHTML = "";
    return;
  }

  const selectedQuizId = activeQuiz?.id || quizzes[0].id;

  statusEl.innerHTML = activeQuiz
    ? `<strong>Active:</strong> ${activeQuiz.title}<br>${activeQuiz.question}`
    : "<em>No quiz running.</em>";

  controlsEl.innerHTML = `
    <select id="quizSelect" class="quiz-select">
      ${quizzes
        .map(quiz => {
          const selected = quiz.id === selectedQuizId ? " selected" : "";
          return `<option value="${quiz.id}"${selected}>${quiz.title}</option>`;
        })
        .join("")}
    </select>
    <button onclick="startQuiz()">Launch quiz</button>
    <button onclick="endQuiz()">End quiz</button>
    <button onclick="clearQuiz()">Clear answers</button>
  `;

  if (!activeQuiz) {
    resultsEl.innerHTML = "";
    return;
  }

  const counts = quizState.counts || {};
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);

  resultsEl.innerHTML = `
    <div class="quiz-results-title">Responses: ${total}</div>
    <ul class="quiz-results-list">
      ${activeQuiz.choices
        .map((choice, index) => {
          const count = counts[index] || 0;
          const percentage = total ? Math.round((count / total) * 100) : 0;
          return `<li>${choice}: ${count} (${percentage}%)</li>`;
        })
        .join("")}
    </ul>
  `;
}

function renderProjectorQuiz() {
  const quiz = getActiveQuiz();
  const resultsEl = document.getElementById("projectorQuiz");

  if (!quiz) {
    resultsEl.innerHTML = "";
    return;
  }

  if (quizState.active) {
    resultsEl.innerHTML = `<strong>Quiz live now:</strong> ${quiz.question}`;
  } else {
    const counts = quizState.counts || {};
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    resultsEl.innerHTML = `
      <strong>Quiz closed</strong><br>
      <small>Responses: ${total}</small>
    `;
  }
}

function renderAudienceQuiz() {
  const launchedQuiz = getActiveQuiz();
  const quiz = quizState.active ? getAudienceQuiz() : launchedQuiz;
  const quizArea = document.getElementById("quizArea");

  if (!participant) {
    quizArea.innerHTML = `
      <div class="quiz-message">Enter your name or code to answer quizzes.</div>
    `;
    return;
  }

  if (!launchedQuiz) {
    quizArea.innerHTML = `
      <div class="quiz-message">Waiting for the presenter to launch a quiz.</div>
    `;
    return;
  }

  if (!quizState.active) {
    quizArea.innerHTML = `
      <div class="quiz-waiting">
        <div class="quiz-question">${launchedQuiz.question}</div>
        <div class="quiz-message">Waiting for the presenter to start the quiz...</div>
      </div>
    `;
    return;
  }

  if (!quiz) {
    quizArea.innerHTML = `
      <div class="quiz-waiting">
        <div class="quiz-question">Quiz completed</div>
        <div class="quiz-message">Thank you. Your answers have been saved.</div>
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
    <div class="quiz-results-summary">Question ${questionNumber} of ${questionTotal}</div>
    <div class="quiz-question">${quiz.question}</div>
    <div class="quiz-options">
      ${getShuffledChoiceIndexes(quiz)
        .map(originalIndex => {
          const selected = userAnswer === originalIndex ? " selected" : "";
          return `<button class="quiz-option${selected}" onclick="submitAnswer(${originalIndex})">${quiz.choices[originalIndex]}</button>`;
        })
        .join("")}
    </div>
    <div class="quiz-your-answer">Select an answer to continue.</div>
    <div class="quiz-results-summary">Responses: ${total}</div>
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
    greeting.textContent = activeName ? `Hello, ${activeName}` : "";
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

window.addEventListener("resize", () => {
  render();
});

if (isPresenter || isProjector) {
  window.addEventListener("keydown", e => {
    if (e.key === "ArrowRight" || e.key === " ") next();
    if (e.key === "ArrowLeft") prev();
    if (isProjector && e.key === "Escape") {
      popupState = { reference: null, scrollRatio: 0, verseIndex: 0 };
      renderSharedPopupOverlay();
    }
  });
}
