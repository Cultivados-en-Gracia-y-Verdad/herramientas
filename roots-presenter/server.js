const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const sessionsDir = path.join(__dirname, "data", "sessions");

app.use(express.static(path.join(__dirname, "public")));

let slides = [];
let presentationMeta = {};
let quizBank = [];
let state = {
  slide: 0,
  step: 0
};

let quizState = {
  active: false,
  quizId: null,
  quiz: null,
  launchedFromSlide: null,
  counts: {},
  answers: {}
};

let currentSession = createSession();

function createSession() {
  const startedAt = new Date().toISOString();
  const safeTimestamp = startedAt.replace(/[:.]/g, "-");

  return {
    id: safeTimestamp,
    title: `ROOTS Session ${startedAt.slice(0, 10)}`,
    startedAt,
    participants: {},
    responses: []
  };
}

function saveSession() {
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.writeFileSync(
    path.join(sessionsDir, `${currentSession.id}.json`),
    JSON.stringify(currentSession, null, 2)
  );
}

function cleanText(value, fallback) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  return text.slice(0, 80) || fallback;
}

function getSessionSummary() {
  return {
    id: currentSession.id,
    title: currentSession.title,
    startedAt: currentSession.startedAt,
    participantCount: Object.keys(currentSession.participants).length,
    responseCount: currentSession.responses.length
  };
}

function registerParticipant(socket, participant = {}) {
  const participantId = cleanText(participant.id, socket.id);
  const now = new Date().toISOString();

  currentSession.participants[participantId] = {
    id: participantId,
    name: cleanText(participant.name, "Anonymous"),
    joinedAt: currentSession.participants[participantId]?.joinedAt || now,
    lastSeenAt: now
  };

  socket.participantId = participantId;
  saveSession();

  return currentSession.participants[participantId];
}

function recordResponse(participantId, quiz, answerIndex) {
  const participant = currentSession.participants[participantId] || {
    id: participantId,
    name: "Anonymous"
  };

  const answeredAt = new Date().toISOString();
  const response = {
    participantId,
    participantName: participant.name,
    quizId: quiz.id,
    quizTitle: quiz.title,
    slide: quizState.launchedFromSlide ? quizState.launchedFromSlide + 1 : "",
    question: quiz.question,
    answerIndex,
    answer: quiz.choices[answerIndex],
    answeredAt
  };

  const existingIndex = currentSession.responses.findIndex(
    item => item.participantId === participantId && item.quizId === quiz.id
  );

  if (existingIndex >= 0) {
    currentSession.responses[existingIndex] = response;
  } else {
    currentSession.responses.push(response);
  }

  saveSession();
}

function clearResponsesForCurrentQuiz() {
  if (!quizState.quizId) return;

  currentSession.responses = currentSession.responses.filter(
    response => response.quizId !== quizState.quizId
  );
  saveSession();
}

function csvValue(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

function buildSessionCsv() {
  const headers = [
    "session_id",
    "session_title",
    "student_id",
    "student_name",
    "quiz_id",
    "quiz_title",
    "slide",
    "question",
    "answer_index",
    "answer",
    "answered_at"
  ];

  const rows = currentSession.responses.map(response => [
    currentSession.id,
    currentSession.title,
    response.participantId,
    response.participantName,
    response.quizId,
    response.quizTitle,
    response.slide,
    response.question,
    response.answerIndex + 1,
    response.answer,
    response.answeredAt
  ]);

  return [headers, ...rows]
    .map(row => row.map(csvValue).join(","))
    .join("\n");
}

function renderLine(line) {
  return marked.parse(line).trim();
}

function parseFrontMatter(markdown) {
  if (!markdown.startsWith("---\n")) {
    return { meta: {}, body: markdown };
  }

  const closingMarker = markdown.indexOf("\n---", 4);
  if (closingMarker === -1) {
    return { meta: {}, body: markdown };
  }

  const yaml = markdown.slice(4, closingMarker).trim();
  const body = markdown.slice(closingMarker + 4).trim();

  return {
    meta: parseSimpleYaml(yaml),
    body
  };
}

function parseSimpleYaml(yaml) {
  const result = {};
  let activeKey = null;

  yaml.split("\n").forEach(rawLine => {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) return;

    if (line.startsWith("- ") && activeKey) {
      result[activeKey].push(unquote(line.slice(2)));
      return;
    }

    const match = line.match(/^([^:]+):\s*(.*)$/);
    if (!match) return;

    const key = match[1].trim();
    const value = match[2].trim();

    if (!value) {
      result[key] = [];
      activeKey = key;
    } else {
      result[key] = unquote(value);
      activeKey = null;
    }
  });

  return result;
}

function unquote(value) {
  return String(value || "").replace(/^["']|["']$/g, "");
}

function getQuizFiles(meta) {
  if (!meta.quizzes) return [];
  return Array.isArray(meta.quizzes) ? meta.quizzes : [meta.quizzes];
}

function parseQuizFile(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const quizzes = [];
  let currentQuiz = null;
  let activeList = null;

  content.split("\n").forEach(rawLine => {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line === "quizzes:") return;

    const newQuizMatch = line.match(/^-\s+id:\s*(.+)$/);
    if (newQuizMatch) {
      currentQuiz = {
        id: unquote(newQuizMatch[1]),
        title: "",
        question: "",
        choices: []
      };
      quizzes.push(currentQuiz);
      activeList = null;
      return;
    }

    if (!currentQuiz) return;

    const listItemMatch = line.match(/^-\s+(.+)$/);
    if (listItemMatch && activeList) {
      currentQuiz[activeList].push(unquote(listItemMatch[1]));
      return;
    }

    const fieldMatch = line.match(/^([^:]+):\s*(.*)$/);
    if (!fieldMatch) return;

    const key = fieldMatch[1].trim();
    const value = fieldMatch[2].trim();

    if (key === "choices") {
      currentQuiz.choices = [];
      activeList = "choices";
      return;
    }

    if (["title", "question"].includes(key)) {
      currentQuiz[key] = unquote(value);
      activeList = null;
    }
  });

  return quizzes.filter(quiz => quiz.id && quiz.question && quiz.choices.length);
}

function loadQuizBank(meta) {
  const externalQuizzes = getQuizFiles(meta).flatMap(relativePath => {
    const quizPath = path.resolve(__dirname, relativePath);
    if (!fs.existsSync(quizPath)) {
      console.warn(`Quiz file not found: ${relativePath}`);
      return [];
    }

    return parseQuizFile(quizPath);
  });

  return externalQuizzes.map((quiz, index) => ({
    ...quiz,
    title: quiz.title || `Quiz ${index + 1}`
  }));
}

function parseSlide(lines) {
  const quizLine = lines.find(line => line.startsWith("? "));
  const choiceLines = lines.filter(line => line.startsWith("- "));

  const quiz = quizLine && choiceLines.length
    ? {
        question: quizLine.slice(2).trim(),
        choices: choiceLines.map(choice => choice.slice(2).trim())
      }
    : null;

  const displayLines = quiz
    ? lines.filter(line => !line.startsWith("? ") && !line.startsWith("- "))
    : lines;

  return { lines: displayLines, quiz };
}

function initQuizCounts(quiz) {
  if (!quiz || !quiz.choices) return {};
  return quiz.choices.reduce((acc, _, index) => {
    acc[index] = 0;
    return acc;
  }, {});
}

function resetQuiz() {
  quizState = {
    active: false,
    quizId: null,
    quiz: null,
    launchedFromSlide: null,
    counts: {},
    answers: {}
  };
}

function startNewSession() {
  currentSession = createSession();
  state.slide = 0;
  state.step = 0;
  resetQuiz();
  saveSession();
}

function loadSlides() {
  const filePath = path.join(__dirname, "markdown.md");
  const md = fs.readFileSync(filePath, "utf-8");
  const parsedDocument = parseFrontMatter(md);

  presentationMeta = parsedDocument.meta;

  slides = parsedDocument.body
    .split(/\n\s*\n/)
    .map(block =>
      block
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean)
    )
    .filter(slide => slide.length > 0)
    .map(parseSlide);

  const inlineQuizzes = slides
    .filter(slide => slide.quiz)
    .map((slide, index) => ({
      id: `inline-slide-${index + 1}`,
      title: `Slide ${index + 1}`,
      question: slide.quiz.question,
      choices: slide.quiz.choices
    }));

  quizBank = [...loadQuizBank(presentationMeta), ...inlineQuizzes];
}

function buildPayload() {
  return {
    session: getSessionSummary(),
    presentation: presentationMeta,
    quizzes: quizBank.map(quiz => ({
      id: quiz.id,
      title: quiz.title,
      question: quiz.question,
      choices: quiz.choices
    })),
    slides: slides.map(slide => ({ quiz: slide.quiz })),
    renderedSlides: slides.map(slide => slide.lines.map(renderLine)),
    slide: state.slide,
    step: state.step,
    quizState: {
      active: quizState.active,
      quizId: quizState.quizId,
      quiz: quizState.quiz,
      launchedFromSlide: quizState.launchedFromSlide,
      counts: quizState.counts
    }
  };
}

function sendState() {
  io.emit("state", buildPayload());
}

app.get("/session.csv", (req, res) => {
  const filename = `${currentSession.id}-responses.csv`;

  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
  res.send(buildSessionCsv());
});

loadSlides();
saveSession();

io.on("connection", socket => {
  socket.emit("state", buildPayload());

  socket.on("join-session", participant => {
    const registeredParticipant = registerParticipant(socket, participant);
    socket.emit("participant-ack", registeredParticipant);
    sendState();
  });

  socket.on("next", () => {
    const current = slides[state.slide];
    if (!current) return;

    if (state.step < current.lines.length - 1) {
      state.step++;
    } else if (state.slide < slides.length - 1) {
      state.slide++;
      state.step = 0;
      resetQuiz();
    }

    sendState();
  });

  socket.on("prev", () => {
    if (state.step > 0) {
      state.step--;
    } else if (state.slide > 0) {
      state.slide--;
      state.step = slides[state.slide].lines.length - 1;
      resetQuiz();
    }

    sendState();
  });

  socket.on("reload-slides", () => {
    loadSlides();
    state.slide = 0;
    state.step = 0;
    resetQuiz();
    sendState();
  });

  socket.on("new-session", () => {
    startNewSession();
    sendState();
  });

  socket.on("start-quiz", quizId => {
    const quiz = quizBank.find(item => item.id === quizId) || quizBank[0];
    if (!quiz) return;

    quizState.active = true;
    quizState.quizId = quiz.id;
    quizState.quiz = quiz;
    quizState.launchedFromSlide = state.slide;
    quizState.counts = initQuizCounts(quiz);
    quizState.answers = {};

    sendState();
  });

  socket.on("end-quiz", () => {
    if (!quizState.active) return;
    quizState.active = false;
    sendState();
  });

  socket.on("clear-quiz", () => {
    if (!quizState.quiz) return;
    quizState.counts = initQuizCounts(quizState.quiz);
    quizState.answers = {};
    clearResponsesForCurrentQuiz();

    sendState();
  });

  socket.on("submit-answer", index => {
    const activeQuiz = quizState.quiz;
    if (!quizState.active || !activeQuiz) {
      socket.emit("answer-ack", { accepted: false });
      return;
    }

    const parsedIndex = Number(index);
    if (
      Number.isNaN(parsedIndex) ||
      parsedIndex < 0 ||
      parsedIndex >= activeQuiz.choices.length
    ) {
      socket.emit("answer-ack", { accepted: false });
      return;
    }

    const participantId = socket.participantId || socket.id;
    if (!currentSession.participants[participantId]) {
      registerParticipant(socket, { id: participantId, name: "Anonymous" });
    }

    if (quizState.answers[participantId] !== undefined) {
      const previous = quizState.answers[participantId];
      if (previous === parsedIndex) {
        socket.emit("answer-ack", { accepted: true, answer: parsedIndex });
        return;
      }

      if (quizState.counts[previous] > 0) {
        quizState.counts[previous]--;
      }
    }

    quizState.answers[participantId] = parsedIndex;
    quizState.counts[parsedIndex] = (quizState.counts[parsedIndex] || 0) + 1;
    recordResponse(participantId, activeQuiz, parsedIndex);

    socket.emit("answer-ack", { accepted: true, answer: parsedIndex });
    sendState();
  });
});

server.listen(3000, "0.0.0.0", () => {
  console.log("ROOTS Presenter running at http://localhost:3000");
  console.log("Audience pages available at http://<your-ip>:3000/audience.html");
});
