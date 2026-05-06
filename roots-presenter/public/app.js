const socket = io();

const isPresenter = document.body.classList.contains("presenter");
const isAudience = document.body.classList.contains("audience");
const isProjector = document.body.classList.contains("projector");

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

  const nextQuizKey = quizState.active ? quizState.quizId : null;
  if (nextQuizKey !== activeQuizKey) {
    userAnswer = null;
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
  }
  render();
});

function render() {
  const currentSlide = renderedSlides[slide] || [];
  const visible = currentSlide.slice(0, step + 1);
  const html = visible.join("");

  if (isPresenter) {
    document.getElementById("current").innerHTML = html;

    const nextSlide = renderedSlides[slide + 1] || [];
    document.getElementById("next").innerHTML = nextSlide.length
      ? nextSlide.join("")
      : "<em>No next slide</em>";

    renderPresenterQuiz();
    renderSessionStatus();
  }

  if (isProjector) {
    document.getElementById("projectorSlide").innerHTML = html;
    renderProjectorQuiz();
  }

  if (isAudience) {
    document.getElementById("audienceSlide").innerHTML = html;
    renderAudienceQuiz();
  }
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

function renderPresenterQuiz() {
  const activeQuiz = getActiveQuiz();
  const statusEl = document.getElementById("quizStatus");
  const controlsEl = document.getElementById("quizControls");
  const resultsEl = document.getElementById("quizResults");

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
  const quiz = getActiveQuiz();
  const quizArea = document.getElementById("quizArea");

  if (!participant) {
    quizArea.innerHTML = `
      <div class="quiz-message">Enter your name or code to answer quizzes.</div>
    `;
    return;
  }

  if (!quiz) {
    quizArea.innerHTML = `
      <div class="quiz-message">Waiting for the presenter to launch a quiz.</div>
    `;
    return;
  }

  if (!quizState.active) {
    quizArea.innerHTML = `
      <div class="quiz-waiting">
        <div class="quiz-question">${quiz.question}</div>
        <div class="quiz-message">Waiting for the presenter to start the quiz...</div>
      </div>
    `;
    return;
  }

  const total = Object.values(quizState.counts).reduce((sum, value) => sum + value, 0);

  quizArea.innerHTML = `
    <div class="quiz-question">${quiz.question}</div>
    <div class="quiz-options">
      ${quiz.choices
        .map((choice, index) => {
          const selected = userAnswer === index ? " selected" : "";
          return `<button class="quiz-option${selected}" onclick="submitAnswer(${index})">${choice}</button>`;
        })
        .join("")}
    </div>
    <div class="quiz-your-answer">${userAnswer !== null ? `You answered: <strong>${quiz.choices[userAnswer]}</strong>` : "Select an answer to participate."}</div>
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
  const storedName = localStorage.getItem("rootsParticipantName") || "";

  if (!form || !input) return;

  input.value = participant?.name || storedName;
  form.classList.toggle("joined", !!participant);
}

function submitAnswer(answerIndex) {
  socket.emit("submit-answer", answerIndex);
}

if (isAudience) {
  renderJoinForm();

  const storedName = localStorage.getItem("rootsParticipantName");
  if (storedName) {
    socket.emit("join-session", {
      id: storedParticipantId,
      name: storedName
    });
  }
}

if (isPresenter) {
  window.addEventListener("keydown", e => {
    if (e.key === "ArrowRight" || e.key === " ") next();
    if (e.key === "ArrowLeft") prev();
  });
}
