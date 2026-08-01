const express = require("express");
const compression = require("compression");
const http = require("http");
const https = require("https");
const os = require("os");
const { Server } = require("socket.io");
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const QRCode = require("qrcode");
const {
  ensureGreekUsageIndex,
  lookupGreekUsage,
  bibleBookCandidates,
  describeGreekForm
} = require("./greekUsage");

const app = express();
app.use(compression());
const server = http.createServer(app);
const io = new Server(server, {
  transports: ["websocket", "polling"],
  pingInterval: 25000,
  pingTimeout: 20000,
  maxHttpBufferSize: 8 * 1024 * 1024,
  perMessageDeflate: {
    threshold: 1024
  }
});
const serverPort = Number(process.env.PORT || 3000);
const serverEvents = new EventTarget();
const legacyNblaDir = path.join(__dirname, "..", "MNA", "data", "NBLA");
const coursesDir = path.join(__dirname, "courses");
const resourceDefaultCourseDir = process.resourcesPath
  ? path.join(process.resourcesPath, "Romanos")
  : "";
const resourceSongsDir = process.resourcesPath
  ? path.join(process.resourcesPath, "songs")
  : "";
const bundledDefaultCourseDir = firstExistingDirectory([
  resourceDefaultCourseDir,
  path.join(coursesDir, "Romanos")
]) || path.join(coursesDir, "Romanos");
const bundledSongRoots = [
  resourceSongsDir,
  path.join(__dirname, "songs")
].filter(Boolean);
const bundledBackgroundsDir = path.join(__dirname, "backgrounds");
const assetBackgroundsDir = path.join(__dirname, "assets", "backgrounds");
const bundledDataDir = path.join(__dirname, "data");
const starterContentVersion = "1.1.0";
const starterSongLimit = 5;

function getRuntimeDataDir() {
  if (process.env.ROOTS_RUNTIME_DATA_DIR) {
    return process.env.ROOTS_RUNTIME_DATA_DIR;
  }

  const appData =
    process.env.APPDATA ||
    process.env.LOCALAPPDATA ||
    process.env.HOME ||
    process.cwd();

  return path.join(appData, "CGV Presenter");
}

const runtimeDataDir = getRuntimeDataDir();
const defaultCourseLibraryDir = process.env.ROOTS_DEFAULT_COURSE_LIBRARY_DIR || "";
const styleSettingsPath = path.join(runtimeDataDir, "style-settings.json");
const bundledStyleSettingsPath = path.join(bundledDataDir, "style-settings.json");
const appStatePath = path.join(runtimeDataDir, "app-state.json");
const libraryMarkerFileName = ".cgv-presenter-library.json";
const LEGACY_H6_INDENTS = new Set(["3.55em", "3.8em", "4.5em", "5.75em"]);
const LEGACY_BULLET_INDENTS = new Set(["5.1em", "5.6em", "6.25em", "8em"]);
const LEGACY_FLAT_SCRIPTURE_COLORS = new Set(["#111827", "#1f2937", "#374151", "#e8edf4", "#fff0a8", "#8b6f16", "inherit"]);
const DEFAULT_H6_INDENT = "7em";
const DEFAULT_BULLET_INDENT = "9.5em";
seedStarterContent();
const defaultCourseDir = isLoadableCourseDir(getStarterRomanosCourseDir())
  ? getStarterRomanosCourseDir()
  : bundledDefaultCourseDir;
const cgvRepository = {
  owner: "Cultivados-en-Gracia-y-Verdad",
  repo: "curriculo",
  branch: "main",
  coursesPath: "courses"
};
const cgvRepositoryBaseUrl = `https://github.com/${cgvRepository.owner}/${cgvRepository.repo}/tree/${cgvRepository.branch}/${cgvRepository.coursesPath}`;
const cgvApiBaseUrl = `https://api.github.com/repos/${cgvRepository.owner}/${cgvRepository.repo}`;
const cgvRawBaseUrl = `https://raw.githubusercontent.com/${cgvRepository.owner}/${cgvRepository.repo}/${cgvRepository.branch}/${cgvRepository.coursesPath}`;
const defaultSongRepository = {
  owner: "Cultivados-en-Gracia-y-Verdad",
  repo: "canciones",
  branch: "main",
  songsPath: "songs/chordpro"
};
const synthesisMarker = "::roots-synthesis::";
const h4IntroMarker = "::roots-h4-intro::";
const sectionContextMarker = "::roots-section-context::";
const phraseCueMarker = "::roots-phrase-cue::";
const phraseUnitMarker = "::roots-phrase-unit::";
const revealBatchMarker = "::roots-reveal-batch::";
const crossReferenceMarker = "::roots-cross-references::";
const animatedChainMarker = "::roots-animated-chain::";

app.use(express.json({ limit: "30mb" }));
app.use(
  "/fonts/ibm-plex-sans",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "ibm-plex-sans", "files"))
);
app.use(
  "/fonts/instrument-sans",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "instrument-sans", "files"))
);
app.use(
  "/fonts/instrument-serif",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "instrument-serif", "files"))
);
app.use(
  "/fonts/syne",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "syne", "files"))
);
app.use(
  "/fonts/space-grotesk",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "space-grotesk", "files"))
);
app.use(
  "/fonts/ibm-plex-serif",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "ibm-plex-serif", "files"))
);
app.get("/style-settings.css", (req, res) => {
  res.setHeader("Content-Type", "text/css; charset=utf-8");
  res.send(buildStyleSettingsCss());
});
app.get("/style-settings", (req, res) => {
  res.json(loadStyleSettings());
});
app.post("/style-settings", (req, res) => {
  const settings = req.body && typeof req.body === "object" ? req.body : {};
  const previousBibleVersion = getBibleVersion();
  saveStyleSettings(settings);
  const nextBibleVersion = getBibleVersion();

  if (nextBibleVersion !== previousBibleVersion) {
    ensureLibraryFolders();
    seedStarterBible();
    loadBibleReferences();
    loadSlides();
  }

  io.emit("style-settings-updated", { updatedAt: Date.now() });
  sendState();
  res.json(settings);
});
app.post("/audience-qr", (req, res) => {
  audienceQrVisible = !!req.body?.visible;
  sendState();
  res.json({ visible: audienceQrVisible });
});
app.get("/join-info", (req, res) => {
  res.json(getJoinInfo(req.query.path));
});
app.get("/connection-info", (req, res) => {
  res.json({
    controller: getJoinInfo("/controller.html"),
    audience: getJoinInfo("/audience.html"),
    director: getJoinInfo("/director.html"),
    stage: getJoinInfo("/stage.html"),
    tablet: getJoinInfo("/tablet.html")
  });
});
app.get("/connection-qr.svg", async (req, res) => {
  try {
    const svg = await QRCode.toString(getJoinInfo(req.query.path).url, {
      type: "svg",
      margin: 1,
      width: 360,
      color: {
        dark: "#111827",
        light: "#ffffff"
      }
    });

    res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.send(svg);
  } catch (error) {
    res.status(500).send("Could not generate QR code.");
  }
});
app.get("/quiz-join.svg", async (req, res) => {
  try {
    const svg = await QRCode.toString(getJoinInfo().url, {
      type: "svg",
      margin: 1,
      width: 360,
      color: {
        dark: "#111827",
        light: "#ffffff"
      }
    });

    res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.send(svg);
  } catch (error) {
    res.status(500).send("Could not generate QR code.");
  }
});
app.use("/assets", express.static(path.join(__dirname, "assets")));
app.use("/background-media", (req, res, next) => {
  express.static(getBackgroundsDir())(req, res, next);
});
app.use("/bundled-background-media", express.static(bundledBackgroundsDir));
app.use(express.static(path.join(__dirname, "public")));
app.use("/course-assets", serveCourseAsset);

let slides = [];
let presentationMeta = {};
let quizBank = [];
let currentCourse = resolveStartupCourse();
let bibleReferences = {};
let bibleChapterVerseCounts = {};
let bibleBookNames = [];
let bibleBookPatterns = [];
let footnoteDefinitions = new Map();
let state = {
  slide: 0,
  step: 0
};

let quizState = {
  active: false,
  quizId: null,
  quiz: null,
  launchedFromSlide: null,
  sequence: [],
  counts: {},
  countsByQuiz: {},
  answers: {},
  answersByQuiz: {}
};
let quizError = null;

let popupState = {
  reference: null,
  scrollRatio: 0,
  verseIndex: 0,
  verseCount: 0
};

let audienceQrVisible = false;

let controllerState = {
  active: false,
  blank: false,
  title: "",
  sections: [],
  chordSections: [],
  step: 0,
  background: "#0f172a",
  backgroundMedia: "",
  textColor: "#ffffff",
  accentColor: "#38bdf8"
};

let currentSession = createSession();

function createSession() {
  const startedAt = new Date().toISOString();
  const safeTimestamp = startedAt.replace(/[:.]/g, "-");

  return {
    id: safeTimestamp,
    courseId: currentCourse?.id || "legacy",
    title: `${currentCourse?.title || "ROOTS"} Session ${startedAt.slice(0, 10)}`,
    startedAt,
    participants: {},
    responses: []
  };
}

function saveSession() {
  const sessionsDir = currentCourse?.sessionsDir || path.join(__dirname, "data", "sessions");
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.writeFileSync(
    path.join(sessionsDir, `${currentSession.id}.json`),
    JSON.stringify(currentSession, null, 2)
  );
}

function isIPv4Address(address) {
  return address && (address.family === "IPv4" || address.family === 4);
}

function isVirtualInterface(name = "") {
  const lower = String(name).toLowerCase();

  return lower.startsWith("lo")
    || lower.includes("virtual")
    || lower.includes("vethernet")
    || lower.includes("vmware")
    || lower.includes("virtualbox")
    || lower.includes("vboxnet")
    || lower.includes("docker")
    || lower.includes("wsl")
    || lower.includes("hyper-v")
    || lower.includes("npcap")
    || lower.startsWith("utun")
    || lower.startsWith("bridge");
}

function scoreNetworkAddress(name, address) {
  if (!isIPv4Address(address) || address.internal) return -1;
  if (isVirtualInterface(name)) return -1;

  let score = 0;
  const lowerName = String(name).toLowerCase();

  if (/^(en|eth|wlan|wi-fi|wifi|wireless)/.test(lowerName)) score += 100;
  if (address.address.startsWith("192.168.")) score += 50;
  if (address.address.startsWith("10.")) score += 40;

  const secondOctet = Number(address.address.split(".")[1]);
  if (address.address.startsWith("172.") && secondOctet >= 16 && secondOctet <= 31) {
    score += 30;
  }

  return score;
}

function getLocalIpAddress() {
  const interfaces = os.networkInterfaces();
  let bestAddress = "";
  let bestScore = -1;

  for (const [name, addresses] of Object.entries(interfaces)) {
    for (const address of addresses || []) {
      const score = scoreNetworkAddress(name, address);
      if (score > bestScore) {
        bestScore = score;
        bestAddress = address.address;
      }
    }
  }

  if (bestAddress) return bestAddress;

  for (const addresses of Object.values(interfaces)) {
    for (const address of addresses || []) {
      if (isIPv4Address(address) && !address.internal) {
        return address.address;
      }
    }
  }

  return "localhost";
}

function normalizeJoinPath(value) {
  const path = String(value || "/audience.html").trim();
  const allowedPaths = new Set([
    "/audience.html",
    "/controller.html",
    "/director.html",
    "/stage.html",
    "/tablet.html"
  ]);

  return allowedPaths.has(path) ? path : "/audience.html";
}

function getJoinInfo(path = "/audience.html") {
  const host = getLocalIpAddress();
  const joinPath = normalizeJoinPath(path);

  return {
    host,
    port: serverPort,
    path: joinPath,
    url: `http://${host}:${serverPort}${joinPath}`
  };
}

function cleanText(value, fallback) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  return text.slice(0, 80) || fallback;
}

function cleanLongText(value, fallback = "", maxLength = 2000) {
  const text = String(value || "").trim();
  return text.slice(0, maxLength) || fallback;
}

function cleanOptionalLongText(value, maxLength = 2000) {
  return String(value || "").trim().slice(0, maxLength);
}

function getSessionSummary() {
  return {
    id: currentSession.id,
    courseId: currentSession.courseId,
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
    slide: quizState.launchedFromSlide !== null ? quizState.launchedFromSlide + 1 : "",
    question: quiz.question,
    answerIndex,
    answer: quiz.choices[answerIndex],
    correctAnswerIndex: Number.isInteger(quiz.correctIndex) ? quiz.correctIndex : "",
    correctAnswer: Number.isInteger(quiz.correctIndex) ? quiz.choices[quiz.correctIndex] : "",
    isCorrect: Number.isInteger(quiz.correctIndex) ? answerIndex === quiz.correctIndex : "",
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
  const quizIds = new Set(quizState.sequence?.length ? quizState.sequence : [quizState.quizId]);

  currentSession.responses = currentSession.responses.filter(
    response => !quizIds.has(response.quizId)
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
    "correct_answer_index",
    "correct_answer",
    "is_correct",
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
    Number.isInteger(response.correctAnswerIndex) ? response.correctAnswerIndex + 1 : "",
    response.correctAnswer,
    response.isCorrect,
    response.answeredAt
  ]);

  return [headers, ...rows]
    .map(row => row.map(csvValue).join(","))
    .join("\n");
}

function normalizeReferenceText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isExternalOrRootedUrl(value) {
  return /^(?:[a-z][a-z0-9+.-]*:|\/\/|#|\/)/i.test(String(value || ""));
}

function rewriteCourseAssetUrl(value) {
  const url = String(value || "").trim();
  if (!url || isExternalOrRootedUrl(url)) return url;

  const normalized = url.replace(/^\.?\//, "");
  return `/course-assets/${encodeURI(normalized).replace(/%25([0-9a-f]{2})/gi, "%$1")}`;
}

const courseMarkdownRenderer = new marked.Renderer();

courseMarkdownRenderer.image = function image(token) {
  const href = rewriteCourseAssetUrl(token.href);
  const title = token.title ? ` title="${escapeHtml(token.title)}"` : "";
  const alt = token.text || "";

  return `<img src="${escapeHtml(href)}" alt="${escapeHtml(alt)}"${title}>`;
};

courseMarkdownRenderer.blockquote = function blockquote(token) {
  const className = isScriptureBlockquote(token)
    ? ' class="scripture-quote"'
    : ' class="teaching-comment"';

  return `<blockquote${className}>\n${this.parser.parse(token.tokens)}</blockquote>\n`;
};

courseMarkdownRenderer.heading = function heading(token) {
  const depth = Math.min(Math.max(Number(token.depth) || 1, 1), 6);
  // Editorial Architecture:
  // H1–H3 = Layer 2 navigation cues; H4 = Layer 1 inspired independent clause.
  const className = depth === 1
    ? ' class="major-nav"'
    : depth === 2
      ? ' class="development-nav"'
      : depth === 3
        ? ' class="section-nav reference-title"'
        : depth === 4
          ? ' class="independent-clause scripture-heading"'
          : "";

  return `<h${depth}${className}>${this.parser.parseInline(token.tokens)}</h${depth}>\n`;
};

function renderMarkdown(value) {
  return marked.parse(value, { renderer: courseMarkdownRenderer });
}

function renderMarkdownInline(value) {
  return marked.parseInline(value, { renderer: courseMarkdownRenderer });
}

function hasGreekScript(value) {
  return /[\p{Script=Greek}]/u.test(String(value || ""));
}

function isScriptureBlockquote(token) {
  const text = String(token?.text || "")
    .replace(/<[^>]*>/g, "")
    .trim();

  return /^(?:\*\*)?«/.test(text);
}

function uniqueExistingDirectories(directories) {
  const seen = new Set();
  return directories
    .filter(Boolean)
    .map(directory => path.resolve(directory))
    .filter(directory => {
      if (seen.has(directory) || !fs.existsSync(directory)) return false;
      seen.add(directory);
      return true;
    });
}

function serveCourseAsset(req, res, next) {
  const directories = uniqueExistingDirectories([
    currentCourse?.rootDir,
    defaultCourseDir,
    bundledDefaultCourseDir
  ]);
  let index = 0;

  const tryNextDirectory = err => {
    if (err) {
      next(err);
      return;
    }

    const directory = directories[index];
    index += 1;
    if (!directory) {
      next();
      return;
    }

    express.static(directory)(req, res, tryNextDirectory);
  };

  tryNextDirectory();
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function cssValue(value, fallback) {
  return /^[#(),.%\w\s-]+$/.test(String(value || "")) ? value : fallback;
}

function safeDirectoryName(value, fallback = "course") {
  return path.basename(String(value || fallback)).replace(/[^\w.\- ]/g, "_") || fallback;
}

function downloadFile(url, destinationPath, options = {}) {
  return new Promise((resolve, reject) => {
    const timeout = Number(options.timeout || 30000);
    const client = String(url).startsWith("https:") ? https : http;
    const request = client.get(url, { headers: { "User-Agent": "ROOTS-Presenter" } }, response => {
      if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
        response.resume();
        downloadFile(new URL(response.headers.location, url).toString(), destinationPath)
          .then(resolve)
          .catch(reject);
        return;
      }

      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`Download failed with status ${response.statusCode}`));
        return;
      }

      fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
      const file = fs.createWriteStream(destinationPath);
      response.pipe(file);
      file.on("finish", () => {
        file.close(() => resolve(destinationPath));
      });
      file.on("error", reject);
    });

    request.on("error", reject);
    request.setTimeout(timeout, () => {
      request.destroy(new Error("Download timed out."));
    });
  });
}

function fetchText(url) {
  return new Promise((resolve, reject) => {
    const client = String(url).startsWith("https:") ? https : http;
    const request = client.get(url, { headers: { "User-Agent": "ROOTS-Presenter" } }, response => {
      if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
        response.resume();
        fetchText(new URL(response.headers.location, url).toString())
          .then(resolve)
          .catch(reject);
        return;
      }

      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`Request failed with status ${response.statusCode}`));
        return;
      }

      response.setEncoding("utf-8");
      let content = "";
      response.on("data", chunk => {
        content += chunk;
      });
      response.on("end", () => resolve(content));
    });

    request.on("error", reject);
    request.setTimeout(30000, () => {
      request.destroy(new Error("Request timed out."));
    });
  });
}

async function fetchJson(url) {
  return JSON.parse(await fetchText(url));
}

function loadCourseRepositoryConfig() {
  const courseLibraryDir = getCourseLibraryDir();

  return {
    name: "CGV Course Repository",
    url: cgvRepositoryBaseUrl,
    downloadDir: courseLibraryDir,
    suggestedDownloadDir: defaultCourseLibraryDir,
    needsCourseLibrary: !courseLibraryDir,
    locked: true
  };
}

function githubApiUrl(pathname) {
  return `${cgvApiBaseUrl}${pathname}`;
}

function songGithubApiUrl(config, pathname) {
  return `https://api.github.com/repos/${config.owner}/${config.repo}${pathname}`;
}

function rawCgvCourseUrl(relativePath) {
  return `${cgvRawBaseUrl}/${String(relativePath).split("/").map(encodeURIComponent).join("/")}`;
}

function rawSongUrl(config, relativePath) {
  const segments = [config.branch, config.songsPath, relativePath]
    .filter(Boolean)
    .join("/")
    .split("/")
    .map(encodeURIComponent)
    .join("/");

  return `https://raw.githubusercontent.com/${config.owner}/${config.repo}/${segments}`;
}

function isSafeCgvCoursePath(value) {
  return Boolean(
    value &&
    typeof value === "string" &&
    !path.isAbsolute(value) &&
    !value.split("/").some(part => !part || part === "." || part === "..")
  );
}

function cleanCourseTitle(value) {
  return String(value || "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compareVersions(a, b) {
  const left = String(a || "").trim();
  const right = String(b || "").trim();

  if (!left && !right) return 0;
  if (!left) return -1;
  if (!right) return 1;

  const leftParts = left.split(/[.-]/).map(part => Number.parseInt(part, 10));
  const rightParts = right.split(/[.-]/).map(part => Number.parseInt(part, 10));
  const length = Math.max(leftParts.length, rightParts.length);

  for (let index = 0; index < length; index++) {
    const leftNumber = Number.isFinite(leftParts[index]) ? leftParts[index] : 0;
    const rightNumber = Number.isFinite(rightParts[index]) ? rightParts[index] : 0;

    if (leftNumber > rightNumber) return 1;
    if (leftNumber < rightNumber) return -1;
  }

  return left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
}

const installedCoursePathAliases = {
  "Romanos1-8": ["Romanos"],
  Romanos: ["Romanos1-8"]
};

function normalizeCourseIdentity(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "");
}

function courseManifestMatchesCatalogPath(manifest, coursePath) {
  if (!manifest || !coursePath) return false;

  const normalizedCatalogPath = normalizeCourseIdentity(coursePath);
  const manifestValues = [
    manifest.catalogPath,
    manifest.repositoryPath,
    manifest.path,
    manifest.id,
    manifest.title
  ];

  return manifestValues.some(value => normalizeCourseIdentity(value) === normalizedCatalogPath);
}

function findInstalledCourseDir(coursePath) {
  const courseLibraryDir = getCourseLibraryDir();
  if (!courseLibraryDir || !isSafeCgvCoursePath(coursePath)) return "";

  const candidateDirs = [
    path.join(courseLibraryDir, safeDirectoryName(coursePath)),
    ...(installedCoursePathAliases[coursePath] || []).map(alias =>
      path.join(courseLibraryDir, safeDirectoryName(alias))
    )
  ];

  for (const courseDir of candidateDirs) {
    if (isLoadableCourseDir(courseDir)) return courseDir;
  }

  for (const courseDir of getInstalledCourseDirs()) {
    const manifestPath = path.join(courseDir, "manifest.json");
    if (!fs.existsSync(manifestPath)) continue;

    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      if (courseManifestMatchesCatalogPath(manifest, coursePath)) {
        return courseDir;
      }
    } catch (error) {
      console.warn(`Could not inspect installed course manifest: ${error.message}`);
    }
  }

  return "";
}

function readInstalledCourseManifest(coursePath) {
  const installedCourseDir = findInstalledCourseDir(coursePath);
  if (!installedCourseDir) return null;

  const manifestPath = path.join(installedCourseDir, "manifest.json");
  if (!fs.existsSync(manifestPath)) return null;

  try {
    return JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  } catch (error) {
    console.warn(`Could not read installed course manifest: ${error.message}`);
    return null;
  }
}

async function fetchCgvCourseManifest(coursePath) {
  if (!isSafeCgvCoursePath(coursePath)) return null;

  try {
    return await fetchJson(rawCgvCourseUrl(`${coursePath}/manifest.json`));
  } catch {
    return null;
  }
}

async function buildCatalogCourse(item) {
  const remoteManifest = await fetchCgvCourseManifest(item.name);
  const available = Boolean(remoteManifest);
  const installedManifest = readInstalledCourseManifest(item.name);
  const installedCourseDir = findInstalledCourseDir(item.name);
  const remoteVersion = String(remoteManifest?.version || "").trim();
  const localVersion = String(installedManifest?.version || "").trim();
  const installed = Boolean(installedManifest);
  const updateAvailable = installed && remoteVersion && compareVersions(remoteVersion, localVersion) > 0;
  const status = !available && !installed
    ? "coming-soon"
    : updateAvailable
      ? "update-available"
      : installed
        ? "downloaded"
        : "not-downloaded";

  return {
    id: safeDirectoryName(item.name),
    title: remoteManifest?.title || cleanCourseTitle(item.name),
    description: remoteManifest?.description || (available
      ? "Cultivados en Gracia y Verdad course"
      : "Course package coming soon."),
    version: remoteVersion,
    localVersion,
    available,
    installed,
    installedCourseDir: installed ? installedCourseDir : "",
    updateAvailable,
    status,
    path: item.name,
    repositoryUrl: item.html_url
  };
}

function shouldDownloadCourseBlob(relativePath) {
  const lowerPath = relativePath.toLowerCase();
  const fileName = path.basename(relativePath);

  if (fileName === ".DS_Store" || fileName.startsWith("~$")) return false;
  if (lowerPath.includes("/archived/") || lowerPath.includes("/archivado/")) return false;
  if (lowerPath.endsWith(".zip")) return false;
  if (/\.(mov|mp4|m4v|avi|wmv)$/i.test(lowerPath)) return false;

  return true;
}

function shouldDownloadSongBlob(relativePath) {
  const lowerPath = relativePath.toLowerCase();
  const fileName = path.basename(relativePath);

  if (fileName === ".DS_Store" || fileName.startsWith("~$")) return false;
  return /\.(cho|chordpro|chopro|pro)$/i.test(lowerPath);
}

function normalizeSongRepositoryConfig(payload = {}) {
  const input = String(payload.repository || payload.repo || payload.url || "").trim();
  const branch = String(payload.branch || defaultSongRepository.branch).trim() || defaultSongRepository.branch;
  const songsPath = String(payload.songsPath || payload.path || defaultSongRepository.songsPath || "")
    .trim()
    .replace(/^\/+|\/+$/g, "");
  const match = input.match(/github\.com\/([^/\s]+)\/([^/\s#?]+)|^([^/\s]+)\/([^/\s]+)$/i);
  const owner = match?.[1] || match?.[3] || defaultSongRepository.owner;
  const repo = (match?.[2] || match?.[4] || defaultSongRepository.repo).replace(/\.git$/i, "");

  return { owner, repo, branch, songsPath };
}

function chooseCourseEntry(files) {
  const markdownFiles = files
    .filter(file => /\.md$/i.test(file))
    .filter(file => !/preguntas|question|quiz|examen|exam/i.test(path.basename(file)));

  if (!markdownFiles.length) return null;

  const rootMarkdown = markdownFiles.filter(file => !file.includes("/"));
  const candidates = rootMarkdown.length ? rootMarkdown : markdownFiles;

  return candidates
    .sort((a, b) => a.length - b.length)
    .find(file => /manual|romanos|filipenses|efesios|santiago|griego|texto|curso/i.test(file))
    || candidates[0];
}

async function fetchCgvCourseCatalog() {
  const courses = await fetchJson(githubApiUrl(
    `/contents/${encodeURIComponent(cgvRepository.coursesPath)}?ref=${encodeURIComponent(cgvRepository.branch)}`
  ));

  if (!Array.isArray(courses)) {
    throw new Error("The CGV courses repository did not return a course list.");
  }

  return {
    name: "CGV Course Repository",
    url: cgvRepositoryBaseUrl,
    courses: (await Promise.all(
      courses
        .filter(item => item.type === "dir")
        .map(buildCatalogCourse)
    )).sort((a, b) => a.title.localeCompare(b.title, "es"))
  };
}

async function fetchCgvRepositoryTree() {
  const tree = await fetchJson(githubApiUrl(
    `/git/trees/${encodeURIComponent(cgvRepository.branch)}?recursive=1`
  ));

  if (!Array.isArray(tree?.tree)) {
    throw new Error("The CGV repository tree could not be loaded.");
  }

  return tree.tree;
}

async function fetchSongRepositoryTree(config) {
  const tree = await fetchJson(songGithubApiUrl(
    config,
    `/git/trees/${encodeURIComponent(config.branch)}?recursive=1`
  ));

  if (!Array.isArray(tree?.tree)) {
    throw new Error("The song repository tree could not be loaded.");
  }

  return tree.tree;
}

async function downloadCourseFromCgv(course) {
  const courseLibraryDir = getCourseLibraryDir();

  if (!courseLibraryDir) {
    throw new Error("Choose a course library folder before downloading courses.");
  }

  const coursePath = course?.path || course?.id;

  if (!isSafeCgvCoursePath(coursePath)) {
    throw new Error("The selected course path is not valid.");
  }

  const remoteManifest = await fetchCgvCourseManifest(coursePath);
  if (!remoteManifest) {
    throw new Error("This course is not available yet because it does not include manifest.json.");
  }

  const tree = await fetchCgvRepositoryTree();
  const repoPrefix = `${cgvRepository.coursesPath}/${coursePath}/`;
  const files = tree
    .filter(item => item.type === "blob" && item.path.startsWith(repoPrefix))
    .map(item => item.path.slice(repoPrefix.length))
    .filter(shouldDownloadCourseBlob);

  if (!files.length) {
    throw new Error("No downloadable files were found for this course.");
  }

  const entryPath = chooseCourseEntry(files);
  if (!entryPath) {
    throw new Error("This course does not include a markdown file that can be presented yet.");
  }

  const courseId = safeDirectoryName(coursePath);
  const destinationDir = path.join(courseLibraryDir, courseId);
  fs.mkdirSync(destinationDir, { recursive: true });

  for (const relativePath of files) {
    await downloadFile(
      rawCgvCourseUrl(`${coursePath}/${relativePath}`),
      path.join(destinationDir, relativePath)
    );
  }

  const manifest = {
    ...remoteManifest,
    id: courseId,
    title: remoteManifest.title || course?.title || cleanCourseTitle(coursePath),
    subtitle: remoteManifest.subtitle || course?.subtitle || "",
    version: remoteManifest.version || course?.version || "",
    entry: remoteManifest.entry && files.includes(remoteManifest.entry)
      ? remoteManifest.entry
      : entryPath,
    source: cgvRepositoryBaseUrl
  };

  fs.writeFileSync(
    path.join(destinationDir, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`
  );

  return {
    courseDir: destinationDir,
    manifest,
    fileCount: files.length
  };
}

async function syncSongsFromGithub(payload = {}) {
  ensureLibraryFolders();

  const config = normalizeSongRepositoryConfig(payload);
  const songsDir = getSongsDir();
  const tree = await fetchSongRepositoryTree(config);
  const repoPrefix = config.songsPath ? `${config.songsPath}/` : "";
  const files = tree
    .filter(item => item.type === "blob")
    .filter(item => !repoPrefix || item.path.startsWith(repoPrefix))
    .map(item => repoPrefix ? item.path.slice(repoPrefix.length) : item.path)
    .filter(shouldDownloadSongBlob);

  if (!files.length) {
    throw new Error("No downloadable songs were found in the GitHub song repository.");
  }

  fs.mkdirSync(songsDir, { recursive: true });

  for (const relativePath of files) {
    await downloadFile(
      rawSongUrl(config, relativePath),
      path.join(songsDir, relativePath),
      { timeout: 60000 }
    );
  }

  return {
    repository: `https://github.com/${config.owner}/${config.repo}`,
    branch: config.branch,
    songsPath: config.songsPath,
    songsDir,
    fileCount: files.length
  };
}

function loadBundledStyleSettings() {
  if (!fs.existsSync(bundledStyleSettingsPath)) return {};

  try {
    return JSON.parse(fs.readFileSync(bundledStyleSettingsPath, "utf-8"));
  } catch (error) {
    console.warn(`Could not load bundled style settings: ${error.message}`);
    return {};
  }
}

function deepMergeObjects(base, override) {
  if (!override || typeof override !== "object" || Array.isArray(override)) {
    return base;
  }

  const result = { ...(base && typeof base === "object" ? base : {}) };

  Object.entries(override).forEach(([key, value]) => {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      result[key] &&
      typeof result[key] === "object" &&
      !Array.isArray(result[key])
    ) {
      result[key] = deepMergeObjects(result[key], value);
      return;
    }

    result[key] = value;
  });

  return result;
}

function migrateLegacyStyleIndents(settings) {
  if (!settings?.styles) return settings;

  ["main", "presenter", "audience"].forEach(scope => {
    const scoped = settings.styles[scope];
    if (!scoped) return;

    if (scoped.h6?.indent && LEGACY_H6_INDENTS.has(String(scoped.h6.indent).trim())) {
      scoped.h6.indent = DEFAULT_H6_INDENT;
    }

    if (scoped.bullet?.indent && LEGACY_BULLET_INDENTS.has(String(scoped.bullet.indent).trim())) {
      scoped.bullet.indent = DEFAULT_BULLET_INDENT;
    }

    const scriptureColor = String(scoped.scripture?.color || "").trim().toLowerCase();
    if (scoped.scripture?.color && LEGACY_FLAT_SCRIPTURE_COLORS.has(scriptureColor)) {
      scoped.scripture.color = scope === "presenter" ? "#8a5f13" : "#f1d286";
    }

    const h4Color = String(scoped.h4?.color || "").trim().toLowerCase();
    if (scoped.h4?.color && LEGACY_FLAT_SCRIPTURE_COLORS.has(h4Color)) {
      scoped.h4.color = scope === "presenter" ? "#8a5f13" : "#f1d286";
    }
  });

  return settings;
}

function loadStyleSettings() {
  const bundled = loadBundledStyleSettings();

  if (!fs.existsSync(styleSettingsPath)) {
    return migrateLegacyStyleIndents(bundled);
  }

  try {
    const saved = JSON.parse(fs.readFileSync(styleSettingsPath, "utf-8"));
    return migrateLegacyStyleIndents(deepMergeObjects(bundled, saved));
  } catch (error) {
    console.warn(`Could not load style settings: ${error.message}`);
    return migrateLegacyStyleIndents(bundled);
  }
}

function saveStyleSettings(settings) {
  fs.mkdirSync(path.dirname(styleSettingsPath), { recursive: true });
  fs.writeFileSync(styleSettingsPath, `${JSON.stringify(settings, null, 2)}\n`);
}

function getAppLanguage() {
  const language = loadStyleSettings().language;
  return ["es", "en"].includes(language) ? language : "es";
}

function normalizeBibleVersion(value) {
  return String(value || "NBLA")
    .trim()
    .replace(/[^A-Za-z0-9_-]/g, "")
    .toUpperCase() || "NBLA";
}

function getBibleVersion() {
  return normalizeBibleVersion(loadStyleSettings().bibleVersion);
}

function getBibleFileExtension(version = getBibleVersion()) {
  return `.${normalizeBibleVersion(version).toLowerCase()}.md`;
}

function getCgvDataBibleRoot() {
  return path.resolve(__dirname, "..", "..", "cgv-data", "bibles");
}

function serverText(key) {
  const language = getAppLanguage();
  const translations = {
    es: {
      quizReady: "Quiz listo",
      quizNotFound: "Quiz no encontrado",
      launchQuiz: "Iniciar quiz",
      missingQuizFile: "Falta el archivo del quiz",
      scanOrEnter: "Escanee el código o entre a",
      qrAlt: "Código QR para entrar al quiz",
      quizUnavailable: "Quiz no disponible",
      missingYaml: "Falta el archivo YAML correspondiente."
    },
    en: {
      quizReady: "Quiz ready",
      quizNotFound: "Quiz not found",
      launchQuiz: "Launch quiz",
      missingQuizFile: "Missing quiz file",
      scanOrEnter: "Scan the code or go to",
      qrAlt: "QR code to join the quiz",
      quizUnavailable: "Quiz not available",
      missingYaml: "The matching YAML file is missing."
    }
  };

  return translations[language]?.[key] || translations.es[key] || key;
}

function getScopedStyles(settings) {
  const styles = settings.styles || {};

  return {
    main: styles.main || styles,
    presenter: styles.presenter || styles,
    audience: styles.audience || styles.main || styles
  };
}

function buildStyleSettingsCss() {
  const settings = loadStyleSettings();
  const scopedStyles = getScopedStyles(settings);
  const lines = [];

  Object.entries({
    main: ":root",
    presenter: ".presenter",
    audience: ".audience"
  }).forEach(([scope, selector]) => {
    const styles = scopedStyles[scope] || {};
    const synthesis = styles.synthesis || {};
    const popup = styles.popup || {};
    const definition = styles.definition || {};
    const surface = styles.surface || {};
    const comment = styles.comment || {};
    const title = styles.title || {};

    lines.push(`${selector} {`);

    if (styles.background) {
      const fallbackBackground = scope === "presenter" ? "#f4f4f4" : "#000000";
      lines.push(`  --view-background: ${cssValue(styles.background, fallbackBackground)};`);
    }

    ["h1", "h2", "h3", "scripture", "h4", "h5", "h6", "bullet", "reference"].forEach(key => {
      const style = styles[key] || {};

      if (style.size) lines.push(`  --style-${key}-size: ${cssValue(style.size, "1em")};`);
      if (style.color) lines.push(`  --style-${key}-color: ${cssValue(style.color, "inherit")};`);
      if (style.indent) lines.push(`  --style-${key}-indent: ${cssValue(style.indent, "0")};`);
      if (style.lineHeight) lines.push(`  --style-${key}-line-height: ${cssValue(style.lineHeight, "1.35")};`);
    });

    const scriptureColor = styles.scripture?.color || styles.h4?.color;
    if (scriptureColor) {
      lines.push(`  --cgv-scripture-display-color: ${cssValue(scriptureColor, scope === "presenter" ? "#8a5f13" : "#f1d286")};`);
    }

    if (comment.color) {
      lines.push(`  --cgv-comment-color: ${cssValue(comment.color, scope === "presenter" ? "#374151" : "#ffffff")};`);
    }
    if (title.background) {
      lines.push(`  --cgv-h1-title-background: ${cssValue(title.background, "#14532d")};`);
    }
    if (title.border) {
      lines.push(`  --cgv-h1-title-border: ${cssValue(title.border, "#5eead4")};`);
    }
    if (surface.tint) {
      lines.push(`  --cgv-surface-tint: ${cssValue(surface.tint, "#8d6b4d")};`);
    }
    if (surface.shadow) {
      lines.push(`  --cgv-surface-shadow: ${cssValue(surface.shadow, "#1e1711")};`);
    }
    if (surface.grain) {
      lines.push(`  --cgv-surface-grain: ${cssValue(surface.grain, "#6d5542")};`);
    }
    const artwork = surface.artwork === "cover"
      ? rewriteCourseAssetUrl(presentationMeta.cover || "")
      : String(surface.artwork || "");
    if (/^\/course-assets\/[\w./%-]+$/i.test(artwork)) {
      lines.push(`  --cgv-surface-artwork: url("${artwork}");`);
    }
    if (surface.folio || surface.header) {
      lines.push("  --cgv-editorial-header: 1;");
    }
    if (surface.folio) {
      lines.push("  --cgv-folio-marker: 1;");
    }
    if (surface.rule) {
      lines.push(`  --cgv-folio-rule: ${cssValue(surface.rule, "transparent")};`);
    }

    if (synthesis.background) {
      lines.push(`  --synthesis-background: ${cssValue(synthesis.background, "#f5f2e8")};`);
    }
    if (synthesis.color) {
      lines.push(`  --synthesis-color: ${cssValue(synthesis.color, "#1f2937")};`);
    }
    if (synthesis.accent) {
      lines.push(`  --synthesis-accent: ${cssValue(synthesis.accent, "#075985")};`);
    }
    if (synthesis.titleColor) {
      lines.push(`  --synthesis-title-color: ${cssValue(synthesis.titleColor, "#075985")};`);
    }
    if (synthesis.textSize) {
      lines.push(`  --synthesis-text-size: ${cssValue(synthesis.textSize, "0.66em")};`);
    }

    if (definition.accent) {
      lines.push(`  --definition-accent: ${cssValue(definition.accent, "#075985")};`);
    }
    if (definition.termColor) {
      lines.push(`  --definition-term-color: ${cssValue(definition.termColor, "#075985")};`);
    }
    if (definition.textColor) {
      lines.push(`  --definition-text-color: ${cssValue(definition.textColor, "#374151")};`);
    }
    if (definition.background) {
      lines.push(`  --definition-background: ${cssValue(definition.background, "transparent")};`);
    }

    if (popup.background) {
      lines.push(`  --popup-background: ${cssValue(popup.background, scope === "main" ? "#f5f2e8" : "#111111")};`);
    }
    if (popup.color) {
      lines.push(`  --popup-color: ${cssValue(popup.color, scope === "main" ? "#151515" : "#ffffff")};`);
    }
    if (popup.verseBackground) {
      lines.push(`  --popup-verse-background: ${cssValue(popup.verseBackground, "rgba(255,255,255,0.72)")};`);
    }
    if (popup.accent) {
      lines.push(`  --popup-accent: ${cssValue(popup.accent, "#075985")};`);
    }
    if (popup.referenceColor) {
      lines.push(`  --popup-reference-color: ${cssValue(popup.referenceColor, "#075985")};`);
    }
    if (popup.textSize) {
      lines.push(`  --popup-text-size: ${cssValue(popup.textSize, scope === "main" ? "34px" : "24px")};`);
    }

    lines.push("}");
  });

  if (settings.theme === "classic-outline") {
    lines.push(`
:root,
.presenter,
.audience {
  --cgv-classic-outline-active: 1;
}

.slide,
.projector-slide,
.audience-slide {
  --classic-outline-rule: color-mix(in srgb, var(--style-reference-color, #c7a96b) 58%, transparent);
}

.projector-slide h3,
.projector-slide .reference-title,
.audience-slide h3,
.audience-slide .reference-title,
.slide h3,
.slide .reference-title {
  margin: 0 0 0.58em;
  padding: 0.24em 0;
  border-top: 0.045em solid var(--classic-outline-rule);
  border-bottom: 0.045em solid var(--classic-outline-rule);
  color: var(--style-h3-color, #c7a96b);
  font-family: var(--cgv-ui-font);
  font-size: var(--style-h3-size, 0.78em);
  font-style: normal;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-align: center;
  text-transform: uppercase;
}

.projector-slide h3::before,
.projector-slide .reference-title::before,
.audience-slide h3::before,
.audience-slide .reference-title::before,
.slide h3::before,
.slide .reference-title::before {
  content: none;
}

.projector-slide h4,
.projector-slide .independent-clause,
.projector-slide .scripture-heading,
.projector-slide .marker-cue,
.projector-slide .phrase-cue,
.audience-slide h4,
.audience-slide .independent-clause,
.audience-slide .scripture-heading,
.audience-slide .marker-cue,
.audience-slide .phrase-cue,
.slide h4,
.slide .independent-clause,
.slide .scripture-heading,
.slide .marker-cue,
.slide .phrase-cue {
  margin: 0.18em auto 0.34em;
  width: fit-content;
  max-width: min(100%, 24em);
  border: 0;
  border-top: 0.04em solid color-mix(in srgb, var(--style-h4-color, #f5ead2) 52%, transparent);
  border-bottom: 0.04em solid color-mix(in srgb, var(--style-h4-color, #f5ead2) 52%, transparent);
  background: transparent;
  color: var(--style-h4-color, var(--cgv-scripture-display-color, #f5ead2));
  font-family: var(--cgv-scripture-font);
  font-size: var(--style-h4-size, 1.02em);
  font-style: italic;
  font-weight: 600;
  line-height: var(--style-scripture-line-height, 1.5);
  padding: 0.28em 0.42em;
  text-align: center;
  overflow-wrap: normal;
  word-break: normal;
  text-wrap: balance;
}

.projector-slide h3 + p,
.audience-slide h3 + p,
.slide h3 + p,
.projector-slide .scripture-line,
.audience-slide .scripture-line,
.slide .scripture-line,
.projector-slide blockquote.scripture-quote,
.projector-slide blockquote.scripture-quote p,
.audience-slide blockquote.scripture-quote,
.audience-slide blockquote.scripture-quote p,
.slide blockquote.scripture-quote,
.slide blockquote.scripture-quote p {
  max-width: 24em;
  margin: 0.18em auto 0.44em;
  color: var(--cgv-scripture-display-color, #f5ead2);
  font-family: var(--cgv-scripture-font);
  font-size: var(--style-scripture-size, 1.02em);
  font-style: italic;
  font-weight: 500;
  line-height: var(--style-scripture-line-height, 1.54);
  text-align: center;
  overflow-wrap: normal;
  word-break: normal;
  text-wrap: balance;
}

.projector-slide .phrase-cue-minus,
.projector-slide .phrase-cue-dependent,
.projector-slide .phrase-cue-plus,
.audience-slide .phrase-cue-minus,
.audience-slide .phrase-cue-dependent,
.audience-slide .phrase-cue-plus,
.slide .phrase-cue-minus,
.slide .phrase-cue-dependent,
.slide .phrase-cue-plus {
  margin-left: auto;
  margin-right: auto;
}

.projector-slide h5,
.audience-slide h5,
.slide h5 {
  max-width: 25em;
  margin: 0.38em auto 0.12em;
  padding-left: 0.76em;
  border-left: 0.06em solid var(--classic-outline-rule);
  color: var(--style-h5-color, #f8fafc);
  font-family: var(--cgv-ui-font);
  font-size: var(--style-h5-size, 0.82em);
  font-weight: 500;
  line-height: 1.42;
}

.projector-slide h6,
.audience-slide h6,
.slide h6,
.projector-slide blockquote.teaching-comment,
.projector-slide blockquote.teaching-comment p,
.audience-slide blockquote.teaching-comment,
.audience-slide blockquote.teaching-comment p,
.slide blockquote.teaching-comment,
.slide blockquote.teaching-comment p,
.projector-slide .marker-grammar,
.projector-slide .grammar-note,
.audience-slide .marker-grammar,
.audience-slide .grammar-note,
.slide .marker-grammar,
.slide .grammar-note {
  max-width: 25em;
  margin: 0.26em auto;
  border-left: 0;
  padding-left: 0;
  color: var(--style-h6-color, #d1d5db);
  font-family: var(--cgv-ui-font);
  font-size: var(--style-h6-size, 0.74em);
  line-height: 1.48;
  text-align: left;
}

.projector-slide .mechanical-point,
.audience-slide .mechanical-point,
.slide .mechanical-point {
  display: grid;
  grid-template-columns: 1.1em minmax(0, 1fr);
  gap: 0.4em;
  align-items: start;
  color: color-mix(in srgb, var(--style-h6-color, #d1d5db) 86%, var(--style-reference-color, #c7a96b) 14%);
}

.projector-slide .mechanical-point::before,
.audience-slide .mechanical-point::before,
.slide .mechanical-point::before {
  width: 0.46em;
  height: 0.46em;
  margin: 0.42em auto 0;
  border-radius: 0;
  opacity: 0.68;
  transform: rotate(45deg);
}

.projector-slide .markdown-animation,
.audience-slide .markdown-animation,
.slide .markdown-animation {
  max-width: 24em;
  margin: 0.46em auto;
  padding: 0;
}

.projector-slide .markdown-animation-mixed,
.audience-slide .markdown-animation-mixed,
.slide .markdown-animation-mixed {
  --chain-label-width: 4.9em;
  --chain-arrow-width: 0.95em;
  margin-left: auto;
  margin-right: auto;
}

.projector-slide .markdown-animation-mixed .markdown-animation-label,
.audience-slide .markdown-animation-mixed .markdown-animation-label,
.slide .markdown-animation-mixed .markdown-animation-label {
  border: 0.045em solid var(--classic-outline-rule);
  border-radius: 0;
  background: transparent;
  color: var(--style-h3-color, #c7a96b);
  font-size: 0.74em;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.projector-slide .markdown-animation-mixed .markdown-animation-value,
.projector-slide .markdown-animation-mixed .markdown-animation-continuation,
.audience-slide .markdown-animation-mixed .markdown-animation-value,
.audience-slide .markdown-animation-mixed .markdown-animation-continuation,
.slide .markdown-animation-mixed .markdown-animation-value,
.slide .markdown-animation-mixed .markdown-animation-continuation {
  color: var(--cgv-scripture-display-color, #f5ead2);
  font-family: var(--cgv-scripture-font);
  font-size: 0.84em;
  font-style: italic;
  font-weight: 600;
}
`.trim());
  }

  return lines.join("\n");
}

function titleCaseBookName(value) {
  return String(value).replace(/\b\p{L}/gu, letter => letter.toUpperCase());
}

function buildBibleBookAliases(book) {
  const aliases = new Set([book, titleCaseBookName(book)]);
  const spacedNumberMatch = book.match(/^([123])\s*(.+)$/i);

  if (spacedNumberMatch) {
    const number = spacedNumberMatch[1];
    const name = titleCaseBookName(spacedNumberMatch[2].trim());
    aliases.add(`${number}${name}`);
    aliases.add(`${number} ${name}`);
  }

  const normalized = normalizeReferenceText(book);
  const accentAliases = {
    efesios: ["Efésios"],
    galatas: ["Gálatas"],
    genesis: ["Génesis"]
  };

  (accentAliases[normalized] || []).forEach(alias => aliases.add(alias));

  return Array.from(aliases);
}

function loadBibleReferences() {
  const version = getBibleVersion();
  const fileExtension = getBibleFileExtension(version);
  const bibleDir = getActiveBibleDir(version);

  if (!bibleDir) {
    bibleReferences = {};
    bibleChapterVerseCounts = {};
    bibleBookNames = [];
    bibleBookPatterns = [];
    console.warn(`No ${version} Bible data found. Bible reference popups will be disabled.`);
    return;
  }

  bibleReferences = {};
  bibleChapterVerseCounts = {};

  fs.readdirSync(bibleDir)
    .filter(fileName => fileName.toLowerCase().endsWith(fileExtension))
    .forEach(fileName => {
      const filePath = path.join(bibleDir, fileName);
      const content = fs.readFileSync(filePath, "utf-8");

      content
        .replace(/\r\n/g, "\n")
        .split("\n")
        .forEach(line => {
        const match =
          line.match(/^(.+?)\s+(\d+):(\d+)\s+(.+)$/) ||
          line.match(/^#+\s*(.+?)\s+(\d+):(\d+)\s*$/);
        if (!match) return;

        const book = match[1].trim();
        const chapter = Number(match[2]);
        const verse = Number(match[3]);
        const text = match[4].trim();
        const key = `${normalizeReferenceText(book)}.${chapter}.${verse}`;

        bibleReferences[key] = {
          book,
          chapter,
          verse,
          text
        };

        const chapterKey = `${normalizeReferenceText(book)}.${chapter}`;
        bibleChapterVerseCounts[chapterKey] = Math.max(
          bibleChapterVerseCounts[chapterKey] || 0,
          verse
        );
      });
    });

  bibleBookNames = Array.from(
    new Set(Object.values(bibleReferences).map(reference => reference.book))
  ).sort((a, b) => b.length - a.length);

  bibleBookPatterns = bibleBookNames
    .flatMap(buildBibleBookAliases)
    .sort((a, b) => b.length - a.length);

  console.log(`Loaded ${bibleBookNames.length} ${version} Bible books from ${bibleDir}`);
  ensureGreekUsageIndex(__dirname);
}

function getBibleSearchRoots() {
  const appData =
    process.env.APPDATA ||
    process.env.LOCALAPPDATA ||
    process.env.HOME ||
    "";

  return Array.from(new Set([
    path.join(getLibraryRootDir(), "bibles"),
    getCgvDataBibleRoot(),
    process.resourcesPath ? path.join(process.resourcesPath, "bibles") : "",
    process.resourcesPath ? path.join(process.resourcesPath, "app.asar.unpacked", "bibles") : "",
    process.execPath ? path.join(path.dirname(process.execPath), "resources", "bibles") : "",
    process.resourcesPath ? path.join(process.resourcesPath, "app", "bibles") : "",
    process.resourcesPath ? path.join(process.resourcesPath, "app.asar", "bibles") : "",
    appData ? path.join(appData, "ROOTS Presenter", "bibles") : "",
    path.join(__dirname, "bibles"),
    path.join(process.cwd(), "bibles")
  ].filter(Boolean)));
}

function getBibleVersionDirectories(root, version = getBibleVersion()) {
  const normalizedVersion = normalizeBibleVersion(version);
  const baseDir = path.join(root, normalizedVersion);
  const directories = [baseDir];

  try {
    if (!fs.existsSync(baseDir)) return directories;

    fs.readdirSync(baseDir, { withFileTypes: true })
      .filter(entry => entry.isDirectory() && !entry.name.startsWith("."))
      .forEach(entry => {
        directories.push(path.join(baseDir, entry.name));
      });
  } catch {
    // Some packaged paths cannot be read directly on every platform.
  }

  return directories;
}

function getBibleSearchPaths(version = getBibleVersion()) {
  return Array.from(new Set([
    ...getBibleVersionDirectories(path.join(getLibraryRootDir(), "bibles"), version),
    ...getBibleSearchRoots()
      .filter(root => root !== path.join(getLibraryRootDir(), "bibles"))
      .flatMap(root => getBibleVersionDirectories(root, version)),
    version === "NBLA" ? legacyNblaDir : ""
  ].filter(Boolean)));
}

function getBibleFileCount(candidate, version = getBibleVersion()) {
  try {
    if (!candidate || !fs.existsSync(candidate)) return 0;
    const fileExtension = getBibleFileExtension(version);
    return fs.readdirSync(candidate).filter(fileName => fileName.toLowerCase().endsWith(fileExtension)).length;
  } catch {
    return 0;
  }
}

function getActiveBibleDir(version = getBibleVersion(), options = {}) {
  const userDir = getUserBibleDir(version);

  return getBibleSearchPaths(version)
    .filter(candidate => options.includeUser !== false || candidate !== userDir)
    .find(candidate => getBibleFileCount(candidate, version) > 0) || "";
}

function getAvailableBibleVersions() {
  const versions = new Set();

  getBibleSearchRoots().forEach(root => {
    try {
      if (!fs.existsSync(root)) return;

      fs.readdirSync(root, { withFileTypes: true })
        .filter(entry => entry.isDirectory())
        .forEach(entry => {
          const version = normalizeBibleVersion(entry.name);
          if (getBibleVersionDirectories(root, version)
            .some(candidate => getBibleFileCount(candidate, version) > 0)) {
            versions.add(version);
          }
        });
    } catch {
      // Some packaged paths cannot be read directly on every platform.
    }
  });

  if (getBibleFileCount(legacyNblaDir, "NBLA") > 0) versions.add("NBLA");

  return Array.from(versions).sort((a, b) => a.localeCompare(b));
}

function getBibleStatus() {
  const version = getBibleVersion();
  const activeDir = getActiveBibleDir(version);
  const installSourceDir = getActiveBibleDir(version, { includeUser: false });
  const userDir = getUserBibleDir(version);

  return {
    version,
    availableVersions: getAvailableBibleVersions(),
    loaded: bibleBookNames.length > 0,
    books: bibleBookNames.length,
    references: Object.keys(bibleReferences).length,
    sampleBooks: bibleBookNames.slice(0, 8),
    activeDir,
    userDir,
    canInstall: Boolean(installSourceDir),
    searchPaths: getBibleSearchPaths().map(candidate => ({
      path: candidate,
      exists: fs.existsSync(candidate),
      files: getBibleFileCount(candidate)
    }))
  };
}

function getReferenceVerses(book, chapter, startVerse, endVerse = startVerse) {
  const verses = [];
  const normalizedBook = normalizeReferenceText(book);

  for (let verse = startVerse; verse <= endVerse; verse++) {
    const reference = bibleReferences[`${normalizedBook}.${chapter}.${verse}`];
    if (reference) verses.push(reference);
  }

  return verses;
}

function getChapterVerseCount(book, chapter) {
  return bibleChapterVerseCounts[`${normalizeReferenceText(book)}.${chapter}`] || 0;
}

function getChapterVerses(book, chapter) {
  return getReferenceVerses(book, chapter, 1, getChapterVerseCount(book, chapter));
}

function getReferenceRangeVerses(book, startChapter, startVerse, endChapter, endVerse) {
  if (endChapter < startChapter) return [];

  const verses = [];

  for (let chapter = startChapter; chapter <= endChapter; chapter += 1) {
    const chapterVerseCount = getChapterVerseCount(book, chapter);
    if (!chapterVerseCount) continue;

    const firstVerse = chapter === startChapter ? startVerse : 1;
    const lastVerse = chapter === endChapter ? endVerse : chapterVerseCount;

    verses.push(...getReferenceVerses(book, chapter, firstVerse, lastVerse));
  }

  return verses;
}

function buildBibleReferenceMarkup(displayReference, book, chapter, startVerse, endVerse) {
  const verses = getReferenceVerses(book, chapter, startVerse, endVerse);
  if (!verses.length) return displayReference;

  return buildBibleReferencePopup(displayReference, verses);
}

function normalizeBibleReferenceKey(value) {
  return String(value || "")
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

function buildBibleReferencePopup(displayReference, verses) {
  const normalizedDisplay = escapeHtml(displayReference);
  const popupTitle = escapeHtml(normalizeBibleReferenceKey(displayReference));
  const verseCount = verses.length;
  const popupText = verses
    .map((reference, index) => {
      const verseReference = `${reference.book} ${reference.chapter}:${reference.verse}`;
      return `<span class="bible-popup-verse" data-verse-index="${index}"${index === 0 ? " data-active=\"true\"" : ""}><strong>${escapeHtml(verseReference)}</strong> ${escapeHtml(reference.text)}</span>`;
    })
    .join("");

  const nav = verseCount > 1
    ? `<span class="bible-popup-nav">
        <button type="button" class="bible-popup-nav-button" data-popup-verse="-1" aria-label="Previous verse">‹</button>
        <span class="bible-popup-position"><span data-popup-verse-current>1</span> / ${verseCount}</span>
        <button type="button" class="bible-popup-nav-button" data-popup-verse="1" aria-label="Next verse">›</button>
      </span>`
    : "";

  return `<span class="bible-ref" tabindex="0" role="button" data-reference="${popupTitle}" data-verse-count="${verseCount}">${normalizedDisplay}<span class="bible-popup">${popupText}${nav}</span></span>`;
}

function parseReferenceParts(book, referenceList) {
  const references = [];
  let currentChapter = null;

  referenceList.split(/\s*(?:,|\by\b)\s*/i).forEach(part => {
    const crossChapterRangeMatch = part.match(/^(\d{1,3}):(\d{1,3})(?:[-–](\d{1,3}):(\d{1,3}))$/);
    const chapterVerseMatch = part.match(/^(\d{1,3}):(\d{1,3})(?:[-–](\d{1,3}))?$/);
    const chapterRangeMatch = part.match(/^(\d{1,3})(?:[-–](\d{1,3}))$/);
    const verseOnlyMatch = part.match(/^(\d{1,3})(?:[-–](\d{1,3}))?$/);

    if (crossChapterRangeMatch) {
      currentChapter = Number(crossChapterRangeMatch[1]);
      references.push({
        type: "range",
        book,
        startChapter: currentChapter,
        startVerse: Number(crossChapterRangeMatch[2]),
        endChapter: Number(crossChapterRangeMatch[3]),
        endVerse: Number(crossChapterRangeMatch[4])
      });
      return;
    }

    if (chapterVerseMatch) {
      currentChapter = Number(chapterVerseMatch[1]);
      references.push({
        type: "verses",
        book,
        chapter: currentChapter,
        startVerse: Number(chapterVerseMatch[2]),
        endVerse: chapterVerseMatch[3]
          ? Number(chapterVerseMatch[3])
          : Number(chapterVerseMatch[2])
      });
      return;
    }

    if (chapterRangeMatch && currentChapter === null) {
      references.push({
        type: "chapter-range",
        book,
        startChapter: Number(chapterRangeMatch[1]),
        endChapter: Number(chapterRangeMatch[2])
      });
      return;
    }

    if (verseOnlyMatch && currentChapter !== null) {
      references.push({
        type: "verses",
        book,
        chapter: currentChapter,
        startVerse: Number(verseOnlyMatch[1]),
        endVerse: verseOnlyMatch[2]
          ? Number(verseOnlyMatch[2])
          : Number(verseOnlyMatch[1])
      });
      return;
    }

    if (verseOnlyMatch) {
      references.push({
        type: "chapter",
        book,
        chapter: Number(verseOnlyMatch[1])
      });
    }
  });

  return references;
}

function buildBibleReferenceListMarkup(displayReference, book, referenceList) {
  const verses = parseReferenceParts(book, referenceList).flatMap(reference => {
    if (reference.type === "chapter") {
      return getChapterVerses(reference.book, reference.chapter);
    }

    if (reference.type === "chapter-range") {
      return getReferenceRangeVerses(
        reference.book,
        reference.startChapter,
        1,
        reference.endChapter,
        getChapterVerseCount(reference.book, reference.endChapter)
      );
    }

    if (reference.type === "range") {
      return getReferenceRangeVerses(
        reference.book,
        reference.startChapter,
        reference.startVerse,
        reference.endChapter,
        reference.endVerse
      );
    }

    return getReferenceVerses(
      reference.book,
      reference.chapter,
      reference.startVerse,
      reference.endVerse
    );
  });

  if (!verses.length) return displayReference;
  return buildBibleReferencePopup(displayReference, verses);
}

function enrichBibleReferences(markdownLine) {
  if (!bibleBookPatterns.length) return markdownLine;

  const bookPattern = bibleBookPatterns.map(escapeRegExp).join("|");
  const referencePattern = new RegExp(
    `\\b(${bookPattern})\\s+((?:\\d{1,3}(?::\\d{1,3})?(?:[-–](?:(?:\\d{1,3}:)?\\d{1,3}))?)(?:\\s*(?:,|y)\\s*(?:(?:\\d{1,3}:)?\\d{1,3})(?:[-–](?:(?:\\d{1,3}:)?\\d{1,3}))?)*)`,
    "gi"
  );

  const enrichText = text => text.replace(referencePattern, (match, book, referenceList) =>
    buildBibleReferenceListMarkup(match, book, referenceList)
  );

  return String(markdownLine || "")
    .split(/(<[^>]+>)/g)
    .map(part => part.startsWith("<") && part.endsWith(">") ? part : enrichText(part))
    .join("");
}

function isFootnoteDefinitionLine(line) {
  return /^\s*\[\^[^\]]+\]:/.test(String(line || ""));
}

// Built-in pedagogical notes for common manual markers. Document `[^id]:`
// definitions always win; these fill gaps when an appendix is missing or not
// yet pasted into an imported draft.
const DEFAULT_FOOTNOTE_DEFINITIONS = new Map(Object.entries({
  kai: "**καί**. Une esta cláusula con la anterior. Solo suma: añade otra idea a la misma línea. No da razón ni contraste.",
  de: "**δέ**. Continúa el desarrollo. A veces solo avanza («y…»); a veces marca un leve contraste («pero…»). Sigue conectada a lo anterior.",
  gar: "**γάρ**. Introduce la razón — el «por qué» de lo que se acaba de decir. No es propósito («para que…»).",
  dioti: "**διότι**. Introduce la razón, como γάρ: el fundamento de la frase anterior.",
  alla: "**ἀλλά**. Introduce un contraste: lo que sigue se aparta de la dirección anterior («pero» / «sino»).",
  oun: "**οὖν**. Introduce la conclusión: «entonces» / «por eso» — el siguiente paso lógico.",
  e: "**ἤ**. Une alternativas («o»).",
  hina: "**ἵνα**. Introduce el propósito — el «para qué» de la acción gobernante.",
  ei: "**εἰ**. Introduce una condición: lo que sigue depende de que se cumpla esa condición.",
  hoti: "**ὅτι**. Puede introducir el contenido (lo que se dice, se sabe o se piensa) o la razón (el «por qué»), según el contexto.",
  hos: "**ὡς**. Marca el momento o la manera relacionada con la frase anterior — a menudo el «cuándo» o el «como».",
  hote: "**ὅτε**. Marca el momento — el «cuándo».",
  conn: "Conector relacional. Une esta cláusula con lo anterior.",
  part: "**Participio**. Forma verbal que no actúa como el verbo principal. Añade acción o detalle ligado a un nombre o a la afirmación cercana (a menudo se parece a «-ando / -iendo» o a un adjetivo hecho de un verbo).",
  inf: "**Infinitivo**. Nombra una acción sin ser el verbo principal. Completa el «qué» de un verbo cercano (debe, pide, quiere, puede…).",
  rel: "**Cláusula relativa**. No es el verbo principal de la sección; cuelga de un nombre (o persona o cosa) ya mencionado y añade detalle sobre ese anfitrión."
}));

// Manual shorthand → canonical grammar-note ids.
const FOOTNOTE_ID_ALIASES = {
  p: "part",
  i: "inf"
};

// Morphology / clause-form notes attached after a Greek paren should not steal
// the Greek click target: (ἀναγεννήσας)[^P] → usages + participle note.
const GRAMMAR_FORM_FOOTNOTE_IDS = new Set([
  "p", "part", "i", "inf", "rel", "conn"
]);

function resolveFootnoteId(id) {
  const lower = String(id || "").trim().toLowerCase();
  return FOOTNOTE_ID_ALIASES[lower] || lower;
}

function isGreekParentheticalLabel(value) {
  return /^[\p{Script=Greek}][\p{Script=Greek}\p{M}'ʼ’*·]*$/u.test(String(value || "").trim());
}

function isGrammarFormFootnoteId(id) {
  return GRAMMAR_FORM_FOOTNOTE_IDS.has(String(id || "").trim().toLowerCase());
}

function collectFootnoteDefinitions(body) {
  const map = new Map();

  String(body || "").split("\n").forEach(line => {
    const match = String(line).match(/^\s*\[\^([^\]]+)\]:\s*(.*)$/);
    if (!match) return;

    const id = match[1].trim();
    if (!id || map.has(id)) return;
    map.set(id, match[2].trim());
  });

  return map;
}

function getFootnoteDefinition(id) {
  const resolved = resolveFootnoteId(id);
  const candidates = [...new Set([String(id || "").trim(), resolved].filter(Boolean))];

  for (const candidate of candidates) {
    if (footnoteDefinitions.has(candidate)) return footnoteDefinitions.get(candidate);

    const lower = candidate.toLowerCase();
    for (const [key, value] of footnoteDefinitions.entries()) {
      if (String(key).toLowerCase() === lower) return value;
    }

    if (DEFAULT_FOOTNOTE_DEFINITIONS.has(lower)) {
      return DEFAULT_FOOTNOTE_DEFINITIONS.get(lower);
    }
  }

  return undefined;
}

function buildFootnoteMarkup(id, labelText, options = {}) {
  const { paren = false, rawLabelHtml = null } = options;
  const note = getFootnoteDefinition(id);
  const noteHtml = note !== undefined
    ? enrichBibleReferences(renderMarkdownInline(note).trim())
    : "<em>Nota no definida</em>";
  const referenceKey = escapeHtml(`footnote:${id}`);

  let labelHtml = "";
  if (rawLabelHtml) {
    labelHtml = rawLabelHtml;
  } else if (labelText != null && String(labelText).length) {
    labelHtml = paren ? `(${escapeHtml(labelText)})` : escapeHtml(labelText);
  } else {
    labelHtml = `<sup class="footnote-marker">${escapeHtml(id)}</sup>`;
  }

  return `<span class="bible-ref footnote-ref" tabindex="0" role="button" data-reference="${referenceKey}" data-footnote-id="${escapeHtml(id)}" data-verse-count="1">${labelHtml}<span class="bible-popup"><span class="bible-popup-verse" data-verse-index="0" data-active="true"><strong>${escapeHtml(id)}</strong> ${noteHtml}</span></span></span>`;
}

function enrichFootnotes(value) {
  let html = String(value || "");

  // *Infinitivo*[^inf] / <em>…</em>[^inf] → whole emphasized term is clickable
  html = html.replace(
    /<(em|strong|u|i|span)(\s[^>]*)?>([^<]+)<\/\1>\s*\[\^([^\]]+)\]/gi,
    (match, tag, attrs = "", label, id) => buildFootnoteMarkup(id, null, {
      rawLabelHtml: `<${tag}${attrs || ""}>${label}</${tag}>`
    })
  );

  // (καὶ)[^kai] → parenthetical label (connector pedagogy)
  // (ἀναγεννήσας)[^P] → keep Greek for usage popup; [^P] is grammar note only
  // Infinitivo[^inf] → preceding word/term is the clickable label
  // [^1] → superscript marker
  const pattern = /(?:\(([^)\n]+)\)|（([^）\n]+)）|([\p{L}\p{M}0-9]+(?:[-'ʼ’][\p{L}\p{M}0-9]+)*))?\[\^([^\]]+)\]/gu;

  const enrichText = text => text.replace(pattern, (match, labelWest, labelFull, labelWord, id) => {
    if (labelWest != null || labelFull != null) {
      const label = labelWest ?? labelFull;
      if (isGreekParentheticalLabel(label) && isGrammarFormFootnoteId(id)) {
        return `(${label})${buildFootnoteMarkup(id, null)}`;
      }
      return buildFootnoteMarkup(id, label, { paren: true });
    }
    if (labelWord != null) {
      return buildFootnoteMarkup(id, labelWord, { paren: false });
    }
    return buildFootnoteMarkup(id, null);
  });

  return html
    .split(/(<[^>]+>)/g)
    .map(part => part.startsWith("<") && part.endsWith(">") ? part : enrichText(part))
    .join("");
}

function lookupSpanishVerseForGreek(bookCode, chapter, verse) {
  for (const bookName of bibleBookCandidates(bookCode)) {
    const key = `${normalizeReferenceText(bookName)}.${chapter}.${verse}`;
    const hit = bibleReferences[key];
    if (hit?.text) return hit.text;
  }
  return "";
}

function buildGreekUsageMarkup(surface, options = {}) {
  const { paren = true } = options;
  const usage = lookupGreekUsage(surface, {
    presenterRootDir: __dirname,
    lookupVerseText: lookupSpanishVerseForGreek
  });
  if (!usage) return null;

  const referenceKey = escapeHtml(`greek:${usage.surface}`);
  const labelHtml = paren
    ? `(${escapeHtml(usage.surface)})`
    : escapeHtml(surface);
  const meta = [usage.lemma, usage.morphology].filter(Boolean).join(" · ");

  const popupText = usage.occurrences.map((occurrence, index) => {
    const spanish = occurrence.spanishHtml
      || (occurrence.spanish ? escapeHtml(occurrence.spanish) : `<em>${escapeHtml(occurrence.surfaceForm)}</em>`);
    const formNote = occurrence.surfaceForm && occurrence.surfaceForm !== usage.surface
      ? ` <span class="greek-usage-form">(${escapeHtml(occurrence.surfaceForm)})</span>`
      : "";
    return `<span class="bible-popup-verse" data-verse-index="${index}"${index === 0 ? " data-active=\"true\"" : ""}><strong>${escapeHtml(occurrence.reference)}</strong>${formNote} ${spanish}</span>`;
  }).join("");

  const nav = usage.occurrences.length > 1
    ? `<span class="bible-popup-nav">
        <button type="button" class="bible-popup-nav-button" data-popup-verse="-1" aria-label="Previous verse">‹</button>
        <span class="bible-popup-position"><span data-popup-verse-current>1</span> / ${usage.occurrences.length}</span>
        <button type="button" class="bible-popup-nav-button" data-popup-verse="1" aria-label="Next verse">›</button>
      </span>`
    : "";

  const spanishLabel = String(usage.spanishLabel || "").trim();
  const titleHtml = spanishLabel
    ? `<strong class="greek-usage-spanish">${escapeHtml(spanishLabel)}</strong> <span class="greek-usage-greek">${escapeHtml(usage.surface)}</span>`
    : `<strong>${escapeHtml(usage.surface)}</strong>`;
  const header = `<span class="greek-usage-header">${titleHtml} ${escapeHtml(meta)} · ${usage.count} uso${usage.count === 1 ? "" : "s"}</span>`;

  return `<span class="bible-ref greek-ref" tabindex="0" role="button" data-reference="${referenceKey}" data-verse-count="${usage.occurrences.length}">${labelHtml}<span class="bible-popup">${header}${popupText}${nav}</span></span>`;
}

function enrichGreekParentheticals(value) {
  const html = String(value || "");
  const pattern = /\(([\p{Script=Greek}][\p{Script=Greek}\p{M}'ʼ’*·]*)\)(?!\[\^)/gu;

  const enrichText = text => text.replace(pattern, (match, surface) => {
    const info = describeGreekForm(surface, __dirname);

    // Prefer pedagogical connector footnotes over MorphGNT usage dumps.
    if (info.footnoteId && getFootnoteDefinition(info.footnoteId) !== undefined) {
      return buildFootnoteMarkup(info.footnoteId, surface, { paren: true });
    }

    // Bare connectors without a note stay plain text (author should add [^kai], etc.).
    if (info.isConnector) {
      return match;
    }

    return buildGreekUsageMarkup(surface) || match;
  });

  // Do not re-process Greek already wrapped by footnote/usage anchors.
  let anchorDepth = 0;
  return html
    .split(/(<[^>]+>)/g)
    .map(part => {
      if (part.startsWith("<") && part.endsWith(">")) {
        if (/^<span\b/i.test(part) && anchorDepth > 0) anchorDepth += 1;
        else if (/^<span\b[^>]*\bbible-ref\b/i.test(part)) anchorDepth += 1;
        else if (/^<\/span>/i.test(part) && anchorDepth > 0) anchorDepth -= 1;
        return part;
      }
      return anchorDepth > 0 ? part : enrichText(part);
    })
    .join("");
}

function enrichBareGreekWords(value) {
  const html = String(value || "");
  if (!hasGreekScript(html)) return html;

  const pattern = /[\p{Script=Greek}][\p{Script=Greek}\p{M}'ʼ’·-]*/gu;

  const enrichText = text => text.replace(pattern, match => {
    const info = describeGreekForm(match, __dirname);
    if (info.isConnector) return match;
    return buildGreekUsageMarkup(match, { paren: false }) || match;
  });

  let anchorDepth = 0;
  return html
    .split(/(<[^>]+>)/g)
    .map(part => {
      if (part.startsWith("<") && part.endsWith(">")) {
        if (/^<span\b/i.test(part) && anchorDepth > 0) anchorDepth += 1;
        else if (/^<span\b[^>]*\bbible-ref\b/i.test(part)) anchorDepth += 1;
        else if (/^<\/span>/i.test(part) && anchorDepth > 0) anchorDepth -= 1;
        return part;
      }
      return anchorDepth > 0 ? part : enrichText(part);
    })
    .join("");
}

function enrichPresentationMarkup(value) {
  return enrichBibleReferences(
    enrichBareGreekWords(
      enrichGreekParentheticals(
        enrichFootnotes(String(value || ""))
      )
    )
  );
}

function getMarkdownHeadingLevel(line) {
  const match = String(line || "").match(/^(#{1,6})\s+/);
  return match ? match[1].length : 0;
}

function renderLine(line) {
  if (String(line || "").startsWith(sectionContextMarker)) {
    const context = JSON.parse(String(line).slice(sectionContextMarker.length));
    const contextText = String(context.text || "").trim();
    const level = Number(context.level) || 2;
    const bookMatch = level === 2 ? contextText.match(/^(?:[1-3]\s+)?[\p{L}]+/u) : null;
    const bookMark = bookMatch ? bookMatch[0].slice(0, 1).toUpperCase() : "";
    const bookHtml = bookMark
      ? `<span class="section-context-book" aria-hidden="true">${escapeHtml(bookMark)}</span>`
      : "";

    return `
      <div class="section-context level-${level}">
        ${bookHtml}
        <span class="section-context-text">${enrichPresentationMarkup(renderMarkdownInline(contextText).trim())}</span>
      </div>
    `.trim();
  }

  const manualTitle = parseManualTitleBlock(line);
  if (manualTitle) {
    return `
      <div class="manual-${manualTitle.type}">
        ${enrichPresentationMarkup(renderMarkdownInline(manualTitle.text).trim())}
      </div>
    `.trim();
  }

  const quizMarker = parseQuizMarker(line);
  if (quizMarker) {
    const quiz = findQuizByMarkerId(quizMarker.quizId);
    const title = getQuizMarkerTitle(quiz, quizMarker.quizId);
    const status = quiz ? serverText("quizReady") : serverText("quizNotFound");
    const button = quiz
      ? `<button type="button" onclick="launchQuiz('${escapeHtml(quizMarker.quizId)}')">${serverText("launchQuiz")}</button>`
      : `<button type="button" disabled>${serverText("missingQuizFile")}</button>`;
    const joinInfo = getJoinInfo();
    const joinCode = joinInfo.host && joinInfo.port
      ? `${joinInfo.host}:${joinInfo.port}`
      : joinInfo.url.replace(/^https?:\/\//, "").replace(/\/audience\.html$/, "");

    return {
      presenterHtml: `
        <aside class="quiz-cue">
          <div>
            <strong>${status}</strong>
            <span>${escapeHtml(title)}</span>
          </div>
          ${button}
        </aside>
      `.trim(),
      html: quiz
        ? `
        <aside class="quiz-cue projector-quiz-cue">
          <div>
            <strong>${serverText("quizReady")}</strong>
            <span>${escapeHtml(title)}</span>
            <small>${serverText("scanOrEnter")} <code>${escapeHtml(joinCode)}</code></small>
          </div>
          <img class="quiz-cue-qr" src="/quiz-join.svg" alt="${serverText("qrAlt")}">
        </aside>
      `.trim()
        : `
        <aside class="quiz-cue projector-quiz-cue missing">
          <div>
            <strong>${serverText("quizUnavailable")}</strong>
            <span>${escapeHtml(title)}</span>
            <small>${serverText("missingYaml")}</small>
          </div>
        </aside>
      `.trim()
    };
  }

  if (line.startsWith(synthesisMarker)) {
    const synthesis = JSON.parse(line.slice(synthesisMarker.length));
    const title = enrichPresentationMarkup(renderMarkdownInline(synthesis.title)).trim();
    const points = synthesis.points
      .map(point => `<li>${enrichPresentationMarkup(renderMarkdownInline(point)).trim()}</li>`)
      .join("");

    return {
      replaceGroup: synthesis.id,
      html: `
        <blockquote class="synthesis-box">
          <p>${title}</p>
          <ul>${points}</ul>
        </blockquote>
      `.trim()
    };
  }

  if (line.startsWith(animatedChainMarker)) {
    const chain = JSON.parse(line.slice(animatedChainMarker.length));

    return {
      replaceGroup: chain.id,
      html: renderAnimatedChain(chain)
    };
  }

  if (line.startsWith(h4IntroMarker)) {
    const intro = JSON.parse(line.slice(h4IntroMarker.length));

    return {
      h4Intro: true,
      html: enrichPresentationMarkup(renderMarkdown(intro.full)).trim(),
      h4OnlyHtml: enrichPresentationMarkup(renderMarkdown(intro.h4)).trim()
    };
  }

  if (line.startsWith(revealBatchMarker)) {
    const items = JSON.parse(line.slice(revealBatchMarker.length));
    return {
      batch: (Array.isArray(items) ? items : []).map(item => renderLine(item))
    };
  }

  if (line.startsWith(phraseUnitMarker)) {
    const unit = JSON.parse(line.slice(phraseUnitMarker.length));
    const cueType = unit.type === "dependent" ? "dependent" : "phrase";
    const phraseHtml = `
      <div class="marker-cue marker-${cueType} phrase-cue phrase-cue-${cueType === "dependent" ? "minus" : "plus"}">
        ${enrichPresentationMarkup(renderMarkdownInline(unit.text).trim())}
      </div>
    `.trim();
    const commentsHtml = (Array.isArray(unit.comments) ? unit.comments : [])
      .map(comment => enrichPresentationMarkup(renderMarkdown(comment)).trim())
      .join("");

    return {
      replaceGroup: unit.id,
      html: `${phraseHtml}${commentsHtml}`
    };
  }

  if (line.startsWith(phraseCueMarker)) {
    const cue = JSON.parse(line.slice(phraseCueMarker.length));
    const cueType = cue.type === "dependent" ? "dependent" : "phrase";

    return `
      <div class="marker-cue marker-${cueType} phrase-cue phrase-cue-${cueType === "dependent" ? "minus" : "plus"}">
        ${enrichPresentationMarkup(renderMarkdownInline(cue.text).trim())}
      </div>
    `.trim();
  }

  if (line.startsWith(crossReferenceMarker)) {
    const references = JSON.parse(line.slice(crossReferenceMarker.length));
    return renderCrossReferences(references);
  }

  if (isImageBlockquoteLine(line)) {
    return enrichPresentationMarkup(renderMarkdown(unwrapBlockquotePrefix(line))).trim();
  }

  if (isStandaloneScriptureLine(line)) {
    return `
      <p class="scripture-line">
        ${enrichPresentationMarkup(renderMarkdownInline(stripWrappingAsterisks(line)).trim())}
      </p>
    `.trim();
  }

  if (isGrammarNoteLine(line)) {
    return `
      <p class="marker-grammar grammar-note mechanical-point">
        ${enrichPresentationMarkup(renderMarkdownInline(normalizeCommentGlosses(line.replace(/^\*\s+/, ""))).trim())}
      </p>
    `.trim();
  }

  const definitionMatch = line.match(/^(.+?)\n:\s+(.+)$/s);

  if (definitionMatch) {
    return `
      <div class="definition">
        <div class="definition-term">${enrichPresentationMarkup(renderMarkdownInline(definitionMatch[1])).trim()}</div>
        <div class="definition-text">${enrichPresentationMarkup(renderMarkdownInline(definitionMatch[2])).trim()}</div>
      </div>
    `.trim();
  }

  const source = normalizeCommentGlosses(line);
  const headingLevel = getMarkdownHeadingLevel(line);
  const html = headingLevel > 0 && headingLevel <= 2
    ? renderMarkdown(source).trim()
    : enrichPresentationMarkup(renderMarkdown(source)).trim();

  if (line.startsWith("- ")) {
    return html.replace("<ul>", '<ul class="comment-bullets">');
  }

  return html;
}

function parseManualTitleBlock(line) {
  const match = String(line || "").match(/^:::(title|subtitle)\s*\n([\s\S]+?)\n:::$/i);
  if (!match) return null;

  return {
    type: match[1].toLowerCase(),
    text: match[2].trim()
  };
}

function parseQuizMarker(line) {
  const match = String(line || "").match(/^<!--\s*@quiz\s+#?([A-Za-z0-9_.:-]+)\s*-->$/);
  if (!match) return null;

  return {
    quizId: normalizeQuizId(match[1])
  };
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

function loadAppState() {
  if (!fs.existsSync(appStatePath)) return {};

  try {
    return JSON.parse(fs.readFileSync(appStatePath, "utf-8"));
  } catch (error) {
    console.warn(`Could not load app state: ${error.message}`);
    return {};
  }
}

function firstExistingDirectory(candidates) {
  return candidates.find(candidate => {
    try {
      return candidate && fs.existsSync(candidate) && fs.statSync(candidate).isDirectory();
    } catch {
      return false;
    }
  });
}

function copyDirectoryFiltered(sourceDir, destinationDir, options = {}) {
  if (!sourceDir || !fs.existsSync(sourceDir)) return false;

  const excludeDirs = new Set(options.excludeDirs || []);
  const excludeFiles = new Set(options.excludeFiles || []);
  const skipExisting = !!options.skipExisting;

  fs.mkdirSync(destinationDir, { recursive: true });

  fs.readdirSync(sourceDir, { withFileTypes: true }).forEach(entry => {
    if (entry.name.startsWith(".")) return;
    if (entry.isDirectory() && excludeDirs.has(entry.name)) return;
    if (entry.isFile() && excludeFiles.has(entry.name)) return;

    const sourcePath = path.join(sourceDir, entry.name);
    const destinationPath = path.join(destinationDir, entry.name);

    if (entry.isDirectory()) {
      copyDirectoryFiltered(sourcePath, destinationPath, options);
      return;
    }

    if (entry.isFile()) {
      if (skipExisting && fs.existsSync(destinationPath)) return;
      fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
      fs.copyFileSync(sourcePath, destinationPath);
    }
  });

  return true;
}

function getStarterSongFiles() {
  const sourceDir = firstExistingDirectory(bundledSongRoots);
  if (!sourceDir) return [];

  return fs.readdirSync(sourceDir)
    .filter(fileName => /\.(cho|chordpro|chopro|pro)$/i.test(fileName))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .slice(0, starterSongLimit)
    .map(fileName => ({
      sourceDir,
      fileName
    }));
}

function seedStarterSongs() {
  const songsDir = getSongsDir();
  const hasUserSongs = fs.existsSync(songsDir)
    && fs.readdirSync(songsDir).some(fileName => /\.(cho|chordpro|chopro|pro)$/i.test(fileName));

  if (hasUserSongs) return;

  const starterSongs = getStarterSongFiles();
  if (!starterSongs.length) return;

  fs.mkdirSync(songsDir, { recursive: true });
  starterSongs.forEach(song => {
    fs.copyFileSync(
      path.join(song.sourceDir, song.fileName),
      path.join(songsDir, song.fileName)
    );
  });
}

function seedStarterCourse() {
  const starterRomanosCourseDir = getStarterRomanosCourseDir();

  copyDirectoryFiltered(bundledDefaultCourseDir, starterRomanosCourseDir, {
    excludeDirs: new Set(["sessions"]),
    excludeFiles: new Set([".DS_Store"]),
    skipExisting: true
  });
}

function seedStarterBackgrounds() {
  const backgroundsDir = getBackgroundsDir();
  const sourceDir = firstExistingDirectory([
    process.resourcesPath ? path.join(process.resourcesPath, "backgrounds") : "",
    bundledBackgroundsDir
  ]);

  if (!sourceDir) return;

  const appState = loadAppState();
  const seededBackgrounds = new Set(Array.isArray(appState.seededBackgrounds) ? appState.seededBackgrounds : []);
  const bundledFiles = fs.readdirSync(sourceDir, { withFileTypes: true })
    .filter(entry => entry.isFile() && !entry.name.startsWith(".") && entry.name !== ".DS_Store")
    .map(entry => entry.name);

  if (!seededBackgrounds.size && bundledFiles.length) {
    const hasUserLibrary = fs.existsSync(backgroundsDir)
      && fs.readdirSync(backgroundsDir).some(fileName => !fileName.startsWith("."));

    if (hasUserLibrary) {
      bundledFiles.forEach(fileName => seededBackgrounds.add(fileName));
      saveAppState({ seededBackgrounds: [...seededBackgrounds] });
      return;
    }
  }

  let seededChanged = false;

  fs.mkdirSync(backgroundsDir, { recursive: true });

  bundledFiles.forEach(fileName => {
    if (seededBackgrounds.has(fileName)) return;

    const sourcePath = path.join(sourceDir, fileName);
    const destinationPath = path.join(backgroundsDir, fileName);

    if (!fs.existsSync(destinationPath)) {
      fs.copyFileSync(sourcePath, destinationPath);
    }

    seededBackgrounds.add(fileName);
    seededChanged = true;
  });

  if (seededChanged) {
    saveAppState({ seededBackgrounds: [...seededBackgrounds] });
  }
}

function seedStarterBible() {
  const version = getBibleVersion();
  const targetDir = getUserBibleDir(version);
  const fileExtension = getBibleFileExtension(version);
  const hasUserBible = fs.existsSync(targetDir)
    && fs.readdirSync(targetDir).some(fileName => fileName.toLowerCase().endsWith(fileExtension));

  if (hasUserBible) return;

  const sourceDir = getActiveBibleDir(version, { includeUser: false });

  if (!sourceDir) return;
  copyDirectoryFiltered(sourceDir, targetDir, {
    excludeFiles: new Set([".DS_Store"]),
    skipExisting: true
  });
}

function seedStarterContent() {
  const appState = loadAppState();

  try {
    const libraryRootDir = inferLibraryRootDir(appState);
    ensureLibraryFolders(libraryRootDir);
    seedStarterCourse();
    seedStarterSongs();
    seedStarterBackgrounds();
    seedStarterBible();

    const nextState = {
      starterContentVersion,
      libraryRootDir,
      courseLibraryDir: path.join(libraryRootDir, "courses")
    };

    const starterRomanosCourseDir = getStarterRomanosCourseDir();
    if (!isLoadableCourseDir(appState.lastCourseDir) && isLoadableCourseDir(starterRomanosCourseDir)) {
      nextState.lastCourseDir = starterRomanosCourseDir;
    }

    saveAppState(nextState);
  } catch (error) {
    console.warn(`Could not seed starter content: ${error.message}`);
  }
}

function saveAppState(nextState) {
  const appState = {
    ...loadAppState(),
    ...nextState
  };

  fs.mkdirSync(path.dirname(appStatePath), { recursive: true });
  fs.writeFileSync(appStatePath, `${JSON.stringify(appState, null, 2)}\n`);
}

function inferLibraryRootDir(state = loadAppState()) {
  if (typeof state.libraryRootDir === "string" && state.libraryRootDir.trim()) {
    return state.libraryRootDir;
  }

  if (typeof state.courseLibraryDir === "string" && state.courseLibraryDir.trim()) {
    return path.basename(state.courseLibraryDir) === "courses"
      ? path.dirname(state.courseLibraryDir)
      : state.courseLibraryDir;
  }

  if (defaultCourseLibraryDir) {
    return defaultCourseLibraryDir;
  }

  return runtimeDataDir;
}

function getLibraryRootDir() {
  return inferLibraryRootDir();
}

function getStarterRomanosCourseDir() {
  return path.join(getCourseLibraryDir(), "Romanos");
}

function getSongsDir() {
  return path.join(getLibraryRootDir(), "songs");
}

function getBackgroundsDir() {
  return path.join(getLibraryRootDir(), "backgrounds");
}

function getUserBibleDir(version = getBibleVersion()) {
  return path.join(getLibraryRootDir(), "bibles", normalizeBibleVersion(version));
}

function getCourseLibraryDir() {
  return path.join(getLibraryRootDir(), "courses");
}

function ensureLibraryFolders(libraryRootDir = getLibraryRootDir()) {
  [
    path.join(libraryRootDir, "courses"),
    path.join(libraryRootDir, "songs"),
    path.join(libraryRootDir, "backgrounds"),
    path.join(libraryRootDir, "bibles", getBibleVersion())
  ].forEach(folder => fs.mkdirSync(folder, { recursive: true }));
  writeLibraryMarker(libraryRootDir);
}

function writeLibraryMarker(libraryRootDir = getLibraryRootDir()) {
  if (!libraryRootDir) return;

  const markerPath = path.join(libraryRootDir, libraryMarkerFileName);
  if (fs.existsSync(markerPath)) return;

  fs.writeFileSync(markerPath, `${JSON.stringify({
    app: "CGV Presenter",
    version: 1,
    managedBy: "CGV Presenter",
    note: "User library folder. App updates must not delete or replace this folder.",
    createdAt: new Date().toISOString()
  }, null, 2)}\n`);
}

function setCourseLibraryDir(libraryRootDir) {
  if (!libraryRootDir || typeof libraryRootDir !== "string") return false;

  try {
    if (!fs.existsSync(libraryRootDir)) {
      fs.mkdirSync(libraryRootDir, { recursive: true });
    }

    if (!fs.statSync(libraryRootDir).isDirectory()) return false;
    ensureLibraryFolders(libraryRootDir);
    saveAppState({
      libraryRootDir,
      courseLibraryDir: path.join(libraryRootDir, "courses")
    });
    seedStarterCourse();
    seedStarterSongs();
    seedStarterBackgrounds();
    seedStarterBible();
    return true;
  } catch (error) {
    console.warn(`Could not save library folder: ${error.message}`);
    return false;
  }
}

function isLoadableCourseDir(courseDir) {
  try {
    if (!courseDir || typeof courseDir !== "string") return false;

    const manifestPath = path.join(courseDir, "manifest.json");
    if (!fs.existsSync(manifestPath)) return false;

    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    const entryPath = path.resolve(courseDir, manifest.entry || "slides/markdown.md");
    return fs.existsSync(entryPath);
  } catch (error) {
    console.warn(`Could not inspect course folder: ${error.message}`);
    return false;
  }
}

function getInstalledCourseDirs() {
  const courseLibraryDir = getCourseLibraryDir();
  if (!courseLibraryDir) return [];

  try {
    if (!fs.existsSync(courseLibraryDir)) return [];

    return fs.readdirSync(courseLibraryDir, { withFileTypes: true })
      .filter(entry => entry.isDirectory())
      .map(entry => path.join(courseLibraryDir, entry.name))
      .filter(isLoadableCourseDir)
      .sort((a, b) => {
        const aTime = fs.statSync(a).mtimeMs;
        const bTime = fs.statSync(b).mtimeMs;
        return bTime - aTime;
      });
  } catch (error) {
    console.warn(`Could not inspect course library folder: ${error.message}`);
    return [];
  }
}

function getStartupCourseDir() {
  const lastCourseDir = loadAppState().lastCourseDir;
  if (isLoadableCourseDir(lastCourseDir)) return lastCourseDir;

  return defaultCourseDir;
}

function isLoadableMarkdownFile(filePath) {
  try {
    if (!filePath || typeof filePath !== "string") return false;

    const resolvedPath = path.resolve(filePath);
    return fs.existsSync(resolvedPath)
      && fs.statSync(resolvedPath).isFile()
      && /\.(md|markdown)$/i.test(resolvedPath);
  } catch (error) {
    console.warn(`Could not inspect markdown file: ${error.message}`);
    return false;
  }
}

function resolveStartupCourse() {
  const appState = loadAppState();
  const lastTeachingMarkdown = appState.lastTeachingMarkdown;

  if (isLoadableMarkdownFile(lastTeachingMarkdown)) {
    return loadTeachingMarkdown(lastTeachingMarkdown);
  }

  return loadCourse(getStartupCourseDir());
}

function getCourseSessionsDir(course) {
  const courseId = safeDirectoryName(course?.id || path.basename(course?.rootDir || "legacy"));
  return path.join(runtimeDataDir, "sessions", courseId);
}

function loadTeachingMarkdown(markdownPath) {
  const entryPath = path.resolve(markdownPath);
  const rootDir = path.dirname(entryPath);
  const parsed = parseFrontMatter(fs.readFileSync(entryPath, "utf-8"));
  const baseName = path.basename(entryPath, path.extname(entryPath));
  const title = String(parsed.meta?.title || baseName).trim() || "Teaching";

  const course = {
    id: `teaching-${safeDirectoryName(baseName)}`,
    title,
    subtitle: String(parsed.meta?.subtitle || "").trim(),
    version: String(parsed.meta?.version || "").trim(),
    teachingImport: true,
    rootDir,
    entryPath
  };

  return {
    ...course,
    sessionsDir: getCourseSessionsDir(course)
  };
}

function loadCourse(courseDir) {
  const manifestPath = path.join(courseDir, "manifest.json");

  if (!fs.existsSync(manifestPath)) {
    const legacyCourse = {
      id: "legacy",
      title: "ROOTS",
      subtitle: "",
      version: "",
      rootDir: __dirname,
      entryPath: path.join(__dirname, "markdown.md")
    };

    return {
      ...legacyCourse,
      sessionsDir: getCourseSessionsDir(legacyCourse)
    };
  }

  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  const course = {
    ...manifest,
    rootDir: courseDir,
    entryPath: path.resolve(courseDir, manifest.entry || "slides/markdown.md")
  };

  return {
    ...course,
    sessionsDir: getCourseSessionsDir(course)
  };
}

function switchCourse(courseDir) {
  const nextCourse = loadCourse(courseDir);

  if (!fs.existsSync(nextCourse.entryPath)) {
    return false;
  }

  currentCourse = nextCourse;
  state.slide = 0;
  state.step = 0;
  resetQuiz();
  clearPopup();
  currentSession = createSession();
  loadSlides();
  saveSession();
  saveAppState({ lastCourseDir: currentCourse.rootDir, lastTeachingMarkdown: "" });
  serverEvents.dispatchEvent(new CustomEvent("course-loaded", {
    detail: {
      id: currentCourse.id,
      title: currentCourse.title,
      rootDir: currentCourse.rootDir
    }
  }));
  return true;
}

function switchTeachingMarkdown(markdownPath) {
  if (!isLoadableMarkdownFile(markdownPath)) return false;

  const nextCourse = loadTeachingMarkdown(markdownPath);
  currentCourse = nextCourse;
  state.slide = 0;
  state.step = 0;
  resetQuiz();
  clearPopup();
  currentSession = createSession();
  loadSlides();
  saveSession();
  saveAppState({ lastTeachingMarkdown: currentCourse.entryPath, lastCourseDir: "" });
  serverEvents.dispatchEvent(new CustomEvent("course-loaded", {
    detail: {
      id: currentCourse.id,
      title: currentCourse.title,
      rootDir: currentCourse.rootDir
    }
  }));
  return true;
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

function normalizeQuizId(value) {
  return unquote(value).trim().replace(/^#/, "");
}

function findQuizByMarkerId(quizId) {
  const normalizedQuizId = normalizeQuizId(quizId);
  if (!normalizedQuizId) return null;

  return quizBank.find(item =>
    item.id === normalizedQuizId || item.groupId === normalizedQuizId
  ) || null;
}

function getQuizMarkerTitle(quiz, fallbackId) {
  if (!quiz) return fallbackId;
  return String(quiz.title || fallbackId).replace(/\s+-\s+\d+$/, "").trim() || fallbackId;
}

function getQuizFiles(meta) {
  if (!meta.quizzes) return [];
  return Array.isArray(meta.quizzes) ? meta.quizzes : [meta.quizzes];
}

function getAutoQuizFiles() {
  const quizDir = path.resolve(path.dirname(currentCourse.entryPath), "..", "quizzes");
  if (!fs.existsSync(quizDir)) return [];

  return fs.readdirSync(quizDir)
    .filter(fileName => /\.(ya?ml)$/i.test(fileName))
    .sort((a, b) => a.localeCompare(b, "es", { numeric: true }))
    .map(fileName => path.join(quizDir, fileName));
}

function resolveCorrectIndex(quiz) {
  if (quiz.correctIndexRaw !== undefined) {
    const parsedIndex = Number(quiz.correctIndexRaw);
    return Number.isInteger(parsedIndex) && parsedIndex >= 0 && parsedIndex < quiz.choices.length
      ? parsedIndex
      : null;
  }

  if (quiz.correctRaw === undefined) return null;

  const correctValue = unquote(quiz.correctRaw).trim();
  const numericCorrect = Number(correctValue);

  if (Number.isInteger(numericCorrect)) {
    const oneBasedIndex = numericCorrect - 1;
    return oneBasedIndex >= 0 && oneBasedIndex < quiz.choices.length ? oneBasedIndex : null;
  }

  const normalizedCorrect = correctValue.toLowerCase();
  const matchingChoiceIndex = quiz.choices.findIndex(
    choice => String(choice).trim().toLowerCase() === normalizedCorrect
  );

  return matchingChoiceIndex >= 0 ? matchingChoiceIndex : null;
}

function parseQuizFile(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  if (/^questions:\s*$/m.test(content)) {
    return parseQuestionSetQuizFile(content, filePath);
  }

  const quizzes = [];
  let currentQuiz = null;
  let activeList = null;

  content.split("\n").forEach(rawLine => {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line === "quizzes:") return;

    const newQuizMatch = line.match(/^-\s+id:\s*(.+)$/);
    if (newQuizMatch) {
      currentQuiz = {
        id: normalizeQuizId(newQuizMatch[1]),
        groupId: null,
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
      return;
    }

    if (key === "correct") {
      currentQuiz.correctRaw = value;
      activeList = null;
      return;
    }

    if (key === "correctIndex") {
      currentQuiz.correctIndexRaw = value;
      activeList = null;
    }
  });

  return quizzes
    .filter(quiz => quiz.id && quiz.question && quiz.choices.length)
    .map(quiz => {
      const correctIndex = resolveCorrectIndex(quiz);
      const cleanedQuiz = {
        id: quiz.id,
        groupId: quiz.groupId || quiz.id,
        title: quiz.title,
        question: quiz.question,
        choices: quiz.choices
      };

      if (Number.isInteger(correctIndex)) {
        cleanedQuiz.correctIndex = correctIndex;
      }

      return cleanedQuiz;
    });
}

function parseQuestionSetQuizFile(content, filePath) {
  const lines = content.split("\n");
  const fileStem = normalizeQuizId(path.basename(filePath, path.extname(filePath)));
  const yamlId = normalizeQuizId(
    lines.find(line => line.trim().startsWith("id:"))?.split(/:\s*/).slice(1).join(":")
      || fileStem
  );
  const fileId = fileStem;
  const groupId = fileStem;
  if (yamlId !== fileStem) {
    console.warn(
      `Quiz id "${yamlId}" in ${path.basename(filePath)} does not match filename "${fileStem}"; using filename for slide markers.`
    );
  }
  const title = unquote(
    lines.find(line => line.trim().startsWith("title:"))?.split(/:\s*/).slice(1).join(":")
      || fileStem
  );
  const quizzes = [];
  let currentQuiz = null;
  let currentAnswer = null;

  lines.forEach(rawLine => {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) return;

    const questionMatch = line.match(/^-\s+question:\s*(.+)$/);
    if (questionMatch) {
      if (currentQuiz) quizzes.push(currentQuiz);
      currentQuiz = {
        id: quizzes.length === 0 ? fileId : `${fileId}-${quizzes.length + 1}`,
        groupId,
        title: `${title} - ${quizzes.length + 1}`,
        question: unquote(questionMatch[1]),
        choices: []
      };
      currentAnswer = null;
      return;
    }

    if (!currentQuiz) return;

    const answerTextMatch = line.match(/^-\s+text:\s*(.+)$/);
    if (answerTextMatch) {
      currentAnswer = {
        text: unquote(answerTextMatch[1]),
        index: currentQuiz.choices.length
      };
      currentQuiz.choices.push(currentAnswer.text);
      return;
    }

    const inlineAnswerMatch = line.match(/^-\s+(.+)$/);
    if (inlineAnswerMatch && line !== "answers:") {
      currentAnswer = {
        text: unquote(inlineAnswerMatch[1]),
        index: currentQuiz.choices.length
      };
      currentQuiz.choices.push(currentAnswer.text);
      return;
    }

    const correctMatch = line.match(/^correct:\s*(true|false)$/i);
    if (correctMatch && currentAnswer && correctMatch[1].toLowerCase() === "true") {
      currentQuiz.correctIndex = currentAnswer.index;
    }
  });

  if (currentQuiz) quizzes.push(currentQuiz);

  return quizzes.filter(quiz => quiz.id && quiz.question && quiz.choices.length);
}

function loadQuizBank(meta) {
  const quizPaths = new Set(
    getQuizFiles(meta).map(relativePath => path.resolve(path.dirname(currentCourse.entryPath), relativePath))
  );
  getAutoQuizFiles().forEach(filePath => quizPaths.add(filePath));

  const externalQuizzes = Array.from(quizPaths).flatMap(quizPath => {
    if (!fs.existsSync(quizPath)) {
      console.warn(`Quiz file not found: ${path.relative(path.dirname(currentCourse.entryPath), quizPath)}`);
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

  return { lines: groupRevealLines(displayLines), quiz };
}

function isPhraseCueLine(line) {
  // + phrases/words, - dependent clauses (italic-wrapped to avoid plain list bullets)
  return /^\+\s+\S/.test(String(line || "")) ||
    /^-\s+\*[^\s*][\s\S]*\*\s*$/.test(String(line || ""));
}

function isStandaloneScriptureLine(line) {
  // Tito verse lines are italic-wrapped with no space after the opening "*".
  // Grammar notes use "* " (markdown list markers) and must not match here.
  return /^\*[^\s*][\s\S]*\*\s*$/.test(String(line || ""));
}

function isGrammarNoteLine(line) {
  // * grammar, definitions, observations
  return /^\*\s+\S/.test(String(line || ""));
}

function stripMarkdownEmphasis(value) {
  return String(value || "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

// Actor / flow chains authored as normal markdown:
//   * *A* → *B* → *C*
//   - *A* ↓ *B* ↓ *C*
//   > Condición→Si...↓Resultado→Él...
function parseAnimatedChain(markdown) {
  const raw = String(markdown || "").trim();
  if (!raw) return null;

  const body = raw.replace(/^(?:[-*]|>)\s*/, "").trim();
  const hasDown = body.includes("↓");
  const hasRight = body.includes("→");
  if (!hasDown && !hasRight) return null;

  // v1: pure term chains only — skip grammar notes / descriptions.
  if (/[:：]/.test(body) || /\[\^[^\]]+\]/.test(body)) return null;

  const parts = body
    .split(/([→↓])/)
    .map(part => part.trim())
    .filter(Boolean);

  const items = [];
  const connectors = [];
  let expectItem = true;

  for (const part of parts) {
    if (part === "→" || part === "↓") {
      if (expectItem || connectors.length >= items.length) return null;
      connectors.push(part);
      expectItem = true;
      continue;
    }

    if (!expectItem) return null;
    items.push(stripMarkdownEmphasis(part));
    expectItem = false;
  }

  if (expectItem) return null;
  if (items.length < 2 || connectors.length !== items.length - 1) return null;
  // Reject unbalanced / leftover emphasis (e.g. arrow inside one *…* span).
  if (items.some(item => /[*_`]/.test(item))) return null;
  if (items.some(item => item.length > 80)) return null;

  const direction = hasDown && hasRight
    ? "mixed"
    : hasDown
      ? "vertical"
      : "horizontal";

  return { direction, items, connectors };
}

function buildAnimatedChainRevealsFromChain(chain) {
  const connectorKey = (chain.connectors || []).join("");
  const id = `chain-${normalizeReferenceText(chain.items.join("-"))}-${chain.direction}-${normalizeReferenceText(connectorKey)}`;

  return chain.items.map((_, index) =>
    `${animatedChainMarker}${JSON.stringify({
      id,
      direction: chain.direction,
      items: chain.items.slice(0, index + 1),
      connectors: (chain.connectors || []).slice(0, index)
    })}`
  );
}

function buildAnimatedChainReveals(line) {
  const chain = parseAnimatedChain(line);
  return chain ? buildAnimatedChainRevealsFromChain(chain) : null;
}

function parseMultilineAnimatedChain(lines, startIndex) {
  const first = parseAnimatedChain(lines[startIndex]);
  if (!first || first.direction !== "horizontal") return null;

  const items = [...first.items];
  const connectors = [...first.connectors];
  let index = startIndex + 1;
  let consumed = 1;
  let sawDown = false;
  let expectNextRow = false;

  while (index < lines.length) {
    const raw = String(lines[index] || "").trim();
    if (!raw) break;

    if (raw === "↓") {
      if (expectNextRow) return null;
      connectors.push("↓");
      sawDown = true;
      expectNextRow = true;
      index += 1;
      consumed += 1;
      continue;
    }

    if (expectNextRow) {
      const next = parseAnimatedChain(raw);
      if (next && next.direction === "horizontal") {
        items.push(...next.items);
        connectors.push(...next.connectors);
        expectNextRow = false;
        index += 1;
        consumed += 1;
        continue;
      }

      if (!/[→↓]/.test(raw) && !/^[-*#>]/.test(raw)) {
        items.push(stripMarkdownEmphasis(raw));
        expectNextRow = false;
        index += 1;
        consumed += 1;
        continue;
      }
    }

    break;
  }

  if (expectNextRow) return null;
  if (!sawDown || consumed < 3) return null;
  if (items.length < 3 || connectors.length !== items.length - 1) return null;
  if (items.some(item => !item || item.length > 80 || /[*_`]/.test(item))) return null;

  return {
    chain: {
      direction: "mixed",
      items,
      connectors
    },
    consumed
  };
}

function renderAnimatedChain(chain) {
  const direction = ["horizontal", "vertical", "mixed"].includes(chain.direction)
    ? chain.direction
    : "horizontal";
  const items = Array.isArray(chain.items) ? chain.items : [];
  const connectors = Array.isArray(chain.connectors) ? chain.connectors : [];
  const parts = [];
  const renderItem = (item, index) => {
    const classes = ["markdown-animation-item"];
    if (connectors[index] === "→") classes.push("markdown-animation-label");
    if (connectors[index - 1] === "→") classes.push("markdown-animation-value");
    if (connectors[index - 1] === "↓" && connectors[index] !== "→") {
      classes.push("markdown-animation-continuation");
    }
    return `<span class="${classes.join(" ")}">${escapeHtml(item)}</span>`;
  };

  if (direction === "mixed") {
    const rows = [];
    let row = items[0]
      ? [renderItem(items[0], 0)]
      : [];

    for (let index = 1; index < items.length; index++) {
      const arrow = connectors[index - 1] === "↓" ? "↓" : "→";
      if (arrow === "↓") {
        rows.push(row.join(""));
        rows.push(
          '<span class="markdown-animation-arrow markdown-animation-arrow-down" aria-hidden="true">↓</span>'
        );
        row = [];
      } else {
        row.push(
          '<span class="markdown-animation-arrow markdown-animation-arrow-right" aria-hidden="true">→</span>'
        );
      }

      row.push(renderItem(items[index], index));
    }

    if (row.length) rows.push(row.join(""));

    return `
      <div class="markdown-animation markdown-animation-${direction} markdown-animation-diagram" data-direction="${direction}" data-style="diagram">
        ${rows.map(rowHtml => (
          rowHtml.includes("markdown-animation-arrow-down")
            ? `<div class="markdown-animation-row markdown-animation-down-row">${rowHtml}</div>`
            : `<div class="markdown-animation-row">${rowHtml}</div>`
        )).join("")}
      </div>
    `.trim();
  }

  items.forEach((item, index) => {
    if (index > 0) {
      const arrow = connectors[index - 1] === "↓" ? "↓" : "→";
      parts.push(
        `<span class="markdown-animation-arrow markdown-animation-arrow-${arrow === "↓" ? "down" : "right"}" aria-hidden="true">${arrow}</span>`
      );
    }

    parts.push(
      `<span class="markdown-animation-item">${escapeHtml(item)}</span>`
    );
  });

  return `
    <div class="markdown-animation markdown-animation-${direction} markdown-animation-diagram" data-direction="${direction}" data-style="diagram">
      ${parts.join("")}
    </div>
  `.trim();
}

function parseCrossReferenceLine(line) {
  const match = String(line || "").match(
    /^\*\s+XRef\s*\(([^)]+)\)\s*:\s*[—-]\s*([^—]+?)\s*[—-]\s*(.+?)\s*$/i
  );

  if (!match) return null;

  return {
    term: match[1].trim(),
    reference: match[2].trim(),
    note: match[3].trim()
  };
}

function renderCrossReferences(references) {
  const items = Array.isArray(references) ? references : [];

  return `
    <p class="xref-note">
      ${items.map(reference => {
        const note = enrichPresentationMarkup(
          renderMarkdownInline(normalizeCommentGlosses(reference.note)).trim()
        );

        return `
          <span class="xref-reference" tabindex="0" role="button" aria-expanded="false" aria-label="XRef ${escapeHtml(reference.term)}: ${escapeHtml(reference.reference)}" data-xref-term="${escapeHtml(reference.term)}">
            ${escapeHtml(reference.reference)}
            <span class="xref-popup" role="note" hidden>${note}</span>
          </span>
        `.trim();
      }).join('<span class="xref-separator" aria-hidden="true"> · </span>')}
    </p>
  `.trim();
}

function normalizeCommentGlosses(text) {
  // Authors flag a defined term inside a comment with *"term" — an intentional
  // word-study marker that is often written with unbalanced emphasis. Convert it
  // into a lexeme span so the marker reads as a defined term instead of leaving a
  // stray asterisk in the rendered comment.
  return String(text || "").replace(/\*"([^"\n]+)"\*?/g, '<span class="lexeme">"$1"</span>');
}

function unwrapBlockquotePrefix(line) {
  return String(line || "").replace(/^(?:>\s?)+/, "").trim();
}

function isImageBlockquoteLine(line) {
  return /^>\s*!\[/.test(String(line || ""));
}

function stripWrappingAsterisks(line) {
  return String(line || "").replace(/^\*/, "").replace(/\*\s*$/, "").trim();
}

function buildPhraseCueLine(line) {
  const match = String(line || "").match(/^([+-])\s+([\s\S]+?)\s*$/);
  const type = match?.[1] === "-" ? "dependent" : "phrase";
  const text = match?.[2]?.trim() || "";

  return `${phraseCueMarker}${JSON.stringify({ type, text })}`;
}

function parsePhraseCueSource(line) {
  const match = String(line || "").match(/^([+-])\s+([\s\S]+?)\s*$/);
  if (!match) return null;
  return {
    type: match[1] === "-" ? "dependent" : "phrase",
    text: match[2].trim()
  };
}

function isTeachingCommentLine(line) {
  const value = String(line || "");
  if (!/^>\s?/.test(value)) return false;
  if (isImageBlockquoteLine(value)) return false;
  if (/^>\s*En S[ií]ntesis/i.test(value)) return false;
  return true;
}

function buildPhraseUnitLine(unit) {
  return `${phraseUnitMarker}${JSON.stringify(unit)}`;
}

function buildPhraseUnitReveals(unit, { clearPreviousUnit = null } = {}) {
  const comments = Array.isArray(unit.comments) ? unit.comments : [];
  let firstStep = buildPhraseUnitLine({ ...unit, comments: [] });

  // Same advance: drop the previous phrase's comment and introduce this phrase.
  if (clearPreviousUnit) {
    firstStep = `${revealBatchMarker}${JSON.stringify([
      buildPhraseUnitLine({ ...clearPreviousUnit, comments: [] }),
      firstStep
    ])}`;
  }

  const steps = [firstStep];

  for (let index = 0; index < comments.length; index++) {
    steps.push(buildPhraseUnitLine({
      ...unit,
      comments: comments.slice(0, index + 1)
    }));
  }

  return steps;
}

function getFirstPhraseCue(lines) {
  return lines.find(item => {
    const value = String(item || "");
    return value.startsWith(phraseCueMarker) || value.startsWith(phraseUnitMarker);
  }) || null;
}

function getPhraseCueType(line) {
  const value = String(line || "");

  if (value.startsWith(phraseUnitMarker)) {
    try {
      const unit = JSON.parse(value.slice(phraseUnitMarker.length));
      return unit.type === "dependent" ? "dependent" : "phrase";
    } catch {
      return null;
    }
  }

  if (!value.startsWith(phraseCueMarker)) return null;

  try {
    const cue = JSON.parse(value.slice(phraseCueMarker.length));
    return cue.type === "dependent" ? "dependent" : "phrase";
  } catch {
    return null;
  }
}

function getFirstCueOfType(lines, type) {
  return lines.find(item => getPhraseCueType(item) === type) || null;
}

function groupRevealLines(lines) {
  const revealLines = [];
  let phraseUnitCounter = 0;
  let previousPhraseUnit = null;

  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const manualTitleStart = line.match(/^:::(title|subtitle)\s*$/i);

    if (manualTitleStart) {
      const group = [line];

      while (lines[index + 1] && lines[index + 1] !== ":::") {
        group.push(lines[index + 1]);
        index++;
      }

      if (lines[index + 1] === ":::") {
        group.push(lines[index + 1]);
        index++;
      }

      revealLines.push(group.join("\n"));
      previousPhraseUnit = null;
      continue;
    }

    const multilineAnimatedChain = parseMultilineAnimatedChain(lines, index);
    if (multilineAnimatedChain) {
      revealLines.push(...buildAnimatedChainRevealsFromChain(multilineAnimatedChain.chain));
      index += multilineAnimatedChain.consumed - 1;
      previousPhraseUnit = null;
      continue;
    }

    const animatedChainReveals = buildAnimatedChainReveals(line);
    if (animatedChainReveals) {
      revealLines.push(...animatedChainReveals);
      previousPhraseUnit = null;
      continue;
    }

    if (isPhraseCueLine(line)) {
      const cue = parsePhraseCueSource(line);
      const comments = [];

      while (isTeachingCommentLine(lines[index + 1])) {
        index++;
        comments.push(lines[index]);
      }

      phraseUnitCounter += 1;
      const unit = {
        id: `phrase-unit-${phraseUnitCounter}`,
        type: cue?.type || "phrase",
        text: cue?.text || "",
        comments
      };
      const clearPreviousUnit = previousPhraseUnit && previousPhraseUnit.comments.length
        ? previousPhraseUnit
        : null;

      revealLines.push(...buildPhraseUnitReveals(unit, { clearPreviousUnit }));
      previousPhraseUnit = unit;
      continue;
    }

    if (String(line || "").trim()) {
      previousPhraseUnit = null;
    }

    const crossReference = parseCrossReferenceLine(line);
    if (crossReference) {
      const references = [crossReference];

      while (parseCrossReferenceLine(lines[index + 1])) {
        index++;
        references.push(parseCrossReferenceLine(lines[index]));
      }

      revealLines.push(`${crossReferenceMarker}${JSON.stringify(references)}`);
      continue;
    }

    if (line.match(/^>\s*En S[ií]ntesis/i)) {
      const group = [line];

      while (lines[index + 1]?.startsWith(">")) {
        group.push(lines[index + 1]);
        index++;
      }

      revealLines.push(...buildSynthesisReveals(group));
      continue;
    }

    if (lines[index + 1]?.startsWith(": ")) {
      revealLines.push(`${line}\n${lines[index + 1]}`);
      index++;
      continue;
    }

    if (line.startsWith("#### ")) {
      const group = [line];
      let cursor = index + 1;
      let firstH5Index = -1;

      while (lines[cursor] && !/^#{1,4}\s/.test(lines[cursor])) {
        if (firstH5Index === -1 && lines[cursor].startsWith("##### ")) {
          firstH5Index = cursor;
          break;
        }

        cursor++;
      }

      if (firstH5Index !== -1) {
        while (index + 1 <= firstH5Index) {
          index++;
          group.push(lines[index]);
        }

        revealLines.push(`${h4IntroMarker}${JSON.stringify({
          h4: line,
          full: group.join("\n")
        })}`);
        continue;
      }
    }

    if (!line.startsWith("### ")) {
      revealLines.push(line);
      continue;
    }

    const group = [line];

    while (lines[index + 1] && !/^#{1,6}\s/.test(lines[index + 1])) {
      group.push(lines[index + 1]);
      index++;
    }

    revealLines.push(group.join("\n"));
  }

  return revealLines;
}

function cleanBlockquoteLine(line) {
  return line.replace(/^>\s?/, "").trim();
}

function buildSynthesisReveals(lines) {
  const title = cleanBlockquoteLine(lines[0]);
  const points = lines
    .map(cleanBlockquoteLine)
    .filter(line => line.startsWith("- "))
    .map(line => line.slice(2).trim());

  return buildSynthesisRevealsFromParts(title, points);
}

function buildSynthesisRevealsFromParts(title, points) {
  const id = `synthesis-${normalizeReferenceText(title)}`;

  if (!points.length) {
    return [`${synthesisMarker}${JSON.stringify({ id, title, points: [] })}`];
  }

  return points.map((_, index) =>
    `${synthesisMarker}${JSON.stringify({
      id,
      title,
      points: points.slice(0, index + 1)
    })}`
  );
}

function isSynthesisHeadingBlock(block) {
  if (!Array.isArray(block) || block.length !== 1) return false;
  return /^#{1,6}\s+En S[ií]ntesis\s*$/i.test(block[0]);
}

function isMarkdownHeadingBlock(block) {
  return Array.isArray(block) && block.some(line => /^#{1,6}\s/.test(line));
}

function cleanSynthesisHeading(line) {
  return String(line || "").replace(/^#{1,6}\s+/, "").trim();
}

function getSynthesisPointFromBlock(block) {
  if (!Array.isArray(block) || !block.length) return "";

  return block
    .map((line, index) => {
      if (index === 0) return line.replace(/^\*\s+/, "").trim();
      return line.trim();
    })
    .filter(Boolean)
    .join(" ");
}

function normalizeSynthesisBlocks(blocks) {
  const normalized = [];

  for (let index = 0; index < blocks.length; index++) {
    const block = blocks[index];

    if (!isSynthesisHeadingBlock(block)) {
      normalized.push(block);
      continue;
    }

    const title = cleanSynthesisHeading(block[0]);
    const points = [];
    let cursor = index + 1;

    while (cursor < blocks.length && !isMarkdownHeadingBlock(blocks[cursor])) {
      const point = getSynthesisPointFromBlock(blocks[cursor]);
      if (point) points.push(point);
      cursor++;
    }

    normalized.push(buildSynthesisRevealsFromParts(title, points));
    index = cursor - 1;
  }

  return normalized;
}

function isIndependentClauseLine(line) {
  const value = String(line || "").trim();
  return value.startsWith("#### ") || value.startsWith(h4IntroMarker);
}

function splitBlocksAtAdditionalIndependentClauses(blocks) {
  return blocks.flatMap(block => {
    const splitBlocks = [];
    let current = [];
    let hasIndependentClause = false;

    for (const line of block) {
      if (isIndependentClauseLine(line) && hasIndependentClause && current.length) {
        splitBlocks.push(current);
        current = [];
        hasIndependentClause = false;
      }

      current.push(line);

      if (isIndependentClauseLine(line)) {
        hasIndependentClause = true;
      }
    }

    if (current.length) {
      splitBlocks.push(current);
    }

    return splitBlocks;
  });
}

function getFirstHeadingLevel(lines) {
  for (const line of lines) {
    const match = line.match(/^(#{1,6})\s/);
    if (match) return match[1].length;
  }

  return null;
}

function getFirstH4(lines) {
  const line = lines.find(item =>
    item.startsWith("#### ") ||
    item.startsWith(h4IntroMarker)
  );

  if (!line) return null;
  if (line.startsWith(h4IntroMarker)) {
    return JSON.parse(line.slice(h4IntroMarker.length)).h4 || null;
  }

  return line.split("\n")[0] || null;
}

function getFirstHeadingLine(lines, level) {
  const prefix = `${"#".repeat(level)} `;
  return lines.find(item => item.startsWith(prefix)) || null;
}

function hasSynthesisSlide(lines) {
  return lines.some(line => String(line || "").startsWith(synthesisMarker));
}

function isSynthesisHeadingLine(line) {
  return /^#{1,6}\s+En S[ií]ntesis\s*$/i.test(String(line || "").trim());
}

function buildSectionContextLine(line) {
  return `${sectionContextMarker}${JSON.stringify({
    level: getMarkdownHeadingLevel(line),
    text: line.replace(/^#{1,6}\s+/, "").trim()
  })}`;
}

function applyStickyHeadings(slidesToProcess) {
  let stickyH4 = null;
  let stickyH2 = null;
  let stickyH3 = null;
  let stickyDependent = null;
  let stickyPhrase = null;

  return slidesToProcess.map(slide => {
    const firstHeadingLevel = getFirstHeadingLevel(slide.lines);
    const slideH1 = getFirstHeadingLine(slide.lines, 1);
    const slideH2 = getFirstHeadingLine(slide.lines, 2);
    const slideH3Raw = getFirstHeadingLine(slide.lines, 3);
    const slideH3 = slideH3Raw && !isSynthesisHeadingLine(slideH3Raw) ? slideH3Raw : null;
    const slideH4 = getFirstH4(slide.lines);
    const slideDependent = getFirstCueOfType(slide.lines, "dependent");
    const slidePhrase = getFirstCueOfType(slide.lines, "phrase");
    const isSynthesisSlide = hasSynthesisSlide(slide.lines);
    const sticky = [];
    const canStickClauseContext =
      !isSynthesisSlide &&
      (!firstHeadingLevel || firstHeadingLevel > 4);

    // Editorial nav clears: En Síntesis, H1, H2 clear the stack below them.
    if (isSynthesisSlide || slideH1) {
      stickyH2 = null;
      stickyH3 = null;
      stickyH4 = null;
      stickyDependent = null;
      stickyPhrase = null;
    }

    // H2 stays in the top corner through H3/H4 content until H1 / H2 / En Síntesis.
    if (!isSynthesisSlide && stickyH2 && (!firstHeadingLevel || firstHeadingLevel > 2)) {
      sticky.push(stickyH2);
    }

    // H3 stays underneath H2 until next H3 / H2 / H1 / En Síntesis.
    if (!isSynthesisSlide && stickyH3 && (!firstHeadingLevel || firstHeadingLevel > 3)) {
      sticky.push(stickyH3);
    }

    // Keep only the most specific clause cue as context so teaching slides do not
    // look like they contain multiple active clauses at once.
    if (canStickClauseContext && !slideH4 && !slideDependent && !slidePhrase && stickyH4 && !stickyDependent && !stickyPhrase) {
      sticky.push(stickyH4);
    }

    if (canStickClauseContext && !slideDependent && !slidePhrase && stickyDependent && !stickyPhrase) {
      sticky.push(stickyDependent);
    }

    if (canStickClauseContext && !slidePhrase && stickyPhrase) {
      sticky.push(stickyPhrase);
    }

    if (slideH4) {
      stickyH4 = slideH4;
      stickyDependent = null;
      stickyPhrase = null;
    } else if (firstHeadingLevel && firstHeadingLevel < 4) {
      stickyH4 = null;
      stickyDependent = null;
      stickyPhrase = null;
    }

    if (slideDependent) {
      stickyDependent = slideDependent;
      stickyPhrase = null;
    }

    if (slidePhrase) {
      stickyPhrase = slidePhrase;
    }

    if (slideH2) {
      stickyH2 = buildSectionContextLine(slideH2);
      stickyH3 = null;
    } else if (slideH3) {
      stickyH3 = buildSectionContextLine(slideH3);
    }

    return {
      ...slide,
      stickyLines: sticky
    };
  });
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
    sequence: [],
    counts: {},
    countsByQuiz: {},
    answers: {},
    answersByQuiz: {}
  };
  quizError = null;
}

function clearPopup() {
  popupState = {
    reference: null,
    scrollRatio: 0,
    verseIndex: 0,
    verseCount: 0
  };
}

function findPopupVerseCount(reference) {
  const key = normalizeBibleReferenceKey(reference);
  if (!key) return 0;

  const escapedKey = escapeRegExp(key);

  for (let index = 0; index < slides.length; index += 1) {
    const rendered = renderSlideAt(index);
    const html = [
      ...(rendered.sticky || []),
      ...(rendered.lines || [])
    ].map(item => (typeof item === "string" ? item : item?.html || "")).join("\n");

    const match = html.match(
      new RegExp(
        `data-reference="${escapedKey}"[^>]*data-verse-count="(\\d+)"` +
          `|` +
          `data-verse-count="(\\d+)"[^>]*data-reference="${escapedKey}"`,
        "i"
      )
    );

    if (match) {
      return Number(match[1] || match[2]) || 0;
    }
  }

  return 0;
}

function emitPopupScroll() {
  io.emit("popup-scroll", {
    reference: popupState.reference,
    scrollRatio: popupState.scrollRatio,
    verseIndex: popupState.verseIndex,
    verseCount: popupState.verseCount
  });
}

function advanceOpenPopupVerse(direction) {
  if (!popupState.reference) return false;

  const total = Math.max(1, Number(popupState.verseCount) || findPopupVerseCount(popupState.reference) || 1);
  popupState.verseCount = total;
  const currentIndex = Number(popupState.verseIndex) || 0;

  if (direction > 0) {
    if (currentIndex < total - 1) {
      popupState.verseIndex = currentIndex + 1;
      popupState.scrollRatio = 0;
      emitPopupScroll();
      return true;
    }

    clearPopup();
    return true;
  }

  if (currentIndex > 0) {
    popupState.verseIndex = currentIndex - 1;
    popupState.scrollRatio = 0;
    emitPopupScroll();
    return true;
  }

  clearPopup();
  return true;
}

function startNewSession() {
  currentSession = createSession();
  state.slide = 0;
  state.step = 0;
  resetQuiz();
  clearPopup();
  saveSession();
}

function cleanHeadingText(line) {
  return String(line || "")
    .replace(/^#{1,6}\s+/, "")
    .replace(/<[^>]+>/g, "")
    .trim();
}

function getHeadingIndex(maxLevel = 2) {
  if (maxLevel === 2 && cachedHeadingIndex) {
    return cachedHeadingIndex;
  }

  const headings = slides.flatMap((slide, index) =>
    slide.lines
      .map(line => {
        const match = line.match(/^(#{1,6})\s+/);
        if (!match) return null;

        const level = match[1].length;
        if (level > maxLevel) return null;

        return {
          level,
          title: cleanHeadingText(line),
          slide: index
        };
      })
      .filter(Boolean)
  );

  if (maxLevel === 2) {
    cachedHeadingIndex = headings;
  }

  return headings;
}

function jumpToSlide(slideIndex) {
  const nextSlide = Number(slideIndex);
  if (!Number.isInteger(nextSlide) || nextSlide < 0 || nextSlide >= slides.length) {
    return false;
  }

  returnToTeachingMode();
  state.slide = nextSlide;
  state.step = 0;
  resetQuiz();
  clearPopup();
  notifyPresentationStepChanged();
  return true;
}

function goToNextSlideStep() {
  const returnedToTeaching = returnToTeachingMode();
  const current = slides[state.slide];
  if (!current) return returnedToTeaching;

  if (state.step < current.lines.length - 1) {
    state.step++;
  } else if (state.slide < slides.length - 1) {
    state.slide++;
    state.step = 0;
    resetQuiz();
  }

  clearPopup();
  notifyPresentationStepChanged();
  return true;
}

function goToPreviousSlideStep() {
  returnToTeachingMode();

  if (state.step > 0) {
    state.step--;
  } else if (state.slide > 0) {
    state.slide--;
    state.step = slides[state.slide].lines.length - 1;
    resetQuiz();
  }

  clearPopup();
  notifyPresentationStepChanged();
  return true;
}

function notifyPresentationStepChanged() {
  serverEvents.dispatchEvent(new CustomEvent("presentation-step-changed"));
}

function broadcastProjectorFrame(frame) {
  if (!frame?.dataUrl) return;

  io.emit("draw-point", {
    x: 0,
    y: 0,
    drawing: false,
    erase: false,
    meta: "projector-frame",
    frame: {
      width: frame.width,
      height: frame.height,
      dataUrl: frame.dataUrl
    }
  });
}

function getQuizIndex() {
  const groups = new Map();

  quizBank.forEach(quiz => {
    const groupId = quiz.groupId || quiz.id;
    if (groups.has(groupId)) return;

    groups.set(groupId, {
      id: groupId,
      title: quiz.title.replace(/\s+-\s+1$/, ""),
      question: quiz.question
    });
  });

  return Array.from(groups.values());
}

function publicQuiz(quiz, includeAnswer = false) {
  if (!quiz) return null;

  const publicData = {
    id: quiz.id,
    groupId: quiz.groupId || quiz.id,
    title: quiz.title,
    question: quiz.question,
    choices: quiz.choices
  };

  if (includeAnswer && Number.isInteger(quiz.correctIndex)) {
    publicData.correctIndex = quiz.correctIndex;
    publicData.correctAnswer = quiz.choices[quiz.correctIndex];
  }

  return publicData;
}

function getQuizReview() {
  if (quizState.active || !quizState.quiz) return [];

  const quizIds = quizState.sequence?.length ? quizState.sequence : [quizState.quiz.id];
  return quizIds
    .map(quizId => quizBank.find(item => item.id === quizId))
    .filter(Boolean)
    .map(quiz => publicQuiz(quiz, true));
}

function getParticipantQuizResult(participantId) {
  if (quizState.active || !quizState.quiz || !participantId) return null;

  const quizIds = quizState.sequence?.length ? quizState.sequence : [quizState.quiz.id];
  const items = quizIds
    .map(quizId => {
      const quiz = quizBank.find(item => item.id === quizId);
      if (!quiz) return null;

      const answers = quizState.answersByQuiz?.[quiz.id] || {};
      const answerIndex = answers[participantId];
      const hasAnswer = Number.isInteger(answerIndex);
      const correct = Number.isInteger(quiz.correctIndex) && hasAnswer
        ? answerIndex === quiz.correctIndex
        : false;

      return {
        quizId: quiz.id,
        question: quiz.question,
        answered: hasAnswer,
        answerIndex: hasAnswer ? answerIndex : null,
        answer: hasAnswer ? quiz.choices[answerIndex] : "",
        correctAnswerIndex: Number.isInteger(quiz.correctIndex) ? quiz.correctIndex : null,
        correctAnswer: Number.isInteger(quiz.correctIndex) ? quiz.choices[quiz.correctIndex] : "",
        correct
      };
    })
    .filter(Boolean);

  const answered = items.filter(item => item.answered).length;
  const correct = items.filter(item => item.correct).length;
  const total = items.length;

  return {
    total,
    answered,
    correct,
    percentage: total ? Math.round((correct / total) * 100) : 0,
    items
  };
}

function normalizeSongSections(value) {
  const text = String(value || "").replace(/\r\n/g, "\n").trim();
  if (!text) return [];

  const sections = [];
  let currentSection = [];

  text.split("\n").forEach(rawLine => {
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

function parseChordProSong(content, filePath, displayFile = path.basename(filePath)) {
  const lines = String(content || "").replace(/\r\n/g, "\n").split("\n");
  const metadata = {};
  const sections = [];
  let currentSection = null;

  function ensureSection(label = "") {
    if (!currentSection) {
      currentSection = {
        label,
        lines: [],
        chordLines: []
      };
      sections.push(currentSection);
    }
  }

  lines.forEach(rawLine => {
    const line = rawLine.trim();
    if (!line) {
      currentSection = null;
      return;
    }

    const directive = line.match(/^\{([^:}]+)(?::\s*([^}]+))?\}$/);
    if (directive) {
      const key = directive[1].trim().toLowerCase();
      const value = (directive[2] || "").trim();

      if (["title", "t"].includes(key)) metadata.title = value;
      else if (["subtitle", "st"].includes(key)) metadata.subtitle = value;
      else if (key === "key") metadata.key = value;
      else if (["background", "background_media", "background-media"].includes(key)) metadata.backgroundMedia = value;
      else if (["verse", "chorus", "bridge", "tag"].includes(key)) {
        currentSection = {
          label: value ? `${key} ${value}` : key,
          lines: [],
          chordLines: []
        };
        sections.push(currentSection);
      }
      return;
    }

    const bracketLabel = getBracketSectionLabel(line);
    if (bracketLabel) {
      currentSection = {
        label: bracketLabel,
        lines: [],
        chordLines: []
      };
      sections.push(currentSection);
      return;
    }

    const lyricLine = stripChordProChords(line);
    if (!lyricLine) return;

    ensureSection();
    currentSection.lines.push(lyricLine);
    currentSection.chordLines.push(line);
  });

  const title = metadata.title || path.basename(filePath, path.extname(filePath));
  const normalizedSections = sections
    .map(section => ({
      ...section,
      lines: section.lines.filter(Boolean),
      chordLines: section.chordLines.filter(Boolean)
    }))
    .filter(section => section.lines.length);

  return {
    id: displayFile.replace(/\.[^.]+$/, ""),
    title,
    subtitle: metadata.subtitle || "",
    key: metadata.key || "",
    backgroundMedia: metadata.backgroundMedia || "",
    file: displayFile,
    lyrics: normalizedSections.map(section => section.lines.join("\n")).join("\n\n"),
    chordLyrics: normalizedSections.map(section => {
      const label = section.label ? [`[${section.label}]`] : [];
      return [...label, ...section.chordLines].join("\n");
    }).join("\n\n"),
    sectionLabels: normalizedSections.map(section => section.label || ""),
    sections: normalizedSections.map(section => section.lines),
    chordSections: normalizedSections.map(section => section.chordLines)
  };
}

function listFilesRecursive(root, matcher) {
  if (!fs.existsSync(root)) return [];

  const files = [];
  const walk = directory => {
    fs.readdirSync(directory, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))
      .forEach(entry => {
        if (entry.name === ".DS_Store") return;

        const absolutePath = path.join(directory, entry.name);
        if (entry.isDirectory()) {
          walk(absolutePath);
          return;
        }

        if (entry.isFile() && matcher(entry.name)) {
          files.push({
            absolutePath,
            relativePath: path.relative(root, absolutePath).split(path.sep).join("/")
          });
        }
      });
  };

  walk(root);
  return files;
}

function loadSongLibrary() {
  // Key by relative file path so numbered/folder copies with the same title all remain searchable.
  const songsByFile = new Map();
  const songsDir = getSongsDir();

  [...bundledSongRoots, songsDir].forEach(root => {
    if (!fs.existsSync(root)) return;

    listFilesRecursive(root, fileName => /\.(cho|chordpro|chopro|pro)$/i.test(fileName))
      .slice(0, root === songsDir ? undefined : starterSongLimit)
      .forEach(file => {
        const song = parseChordProSong(
          fs.readFileSync(file.absolutePath, "utf-8"),
          file.absolutePath,
          file.relativePath
        );

        if (song.sections.length) {
          songsByFile.set(file.relativePath, song);
        }
      });
  });

  return [...songsByFile.values()]
    .sort((a, b) => a.file.localeCompare(b.file, undefined, { numeric: true }));
}

function loadBackgroundLibrary() {
  const sources = [
    {
      root: getBackgroundsDir(),
      urlPrefix: "/background-media"
    },
    {
      root: bundledBackgroundsDir,
      urlPrefix: "/bundled-background-media"
    },
    {
      root: assetBackgroundsDir,
      urlPrefix: "/assets/backgrounds"
    }
  ];

  const backgroundsByFile = new Map();

  sources.forEach(source => {
    if (!fs.existsSync(source.root)) return [];

    listFilesRecursive(source.root, fileName => /\.(apng|avif|gif|jpe?g|png|svg|webp|mp4|webm|ogg|mov)$/i.test(fileName))
      .forEach(file => {
        const key = file.relativePath.toLowerCase();
        if (backgroundsByFile.has(key)) return;

        const isVideo = /\.(mp4|webm|ogg|mov)$/i.test(file.relativePath);
        backgroundsByFile.set(key, {
          id: `${source.urlPrefix}/${file.relativePath}`,
          name: path.basename(file.relativePath, path.extname(file.relativePath)),
          file: file.relativePath,
          url: `${source.urlPrefix}/${file.relativePath.split("/").map(encodeURIComponent).join("/")}`,
          type: isVideo ? "video" : "image"
        });
      });
  });

  return [...backgroundsByFile.values()];
}

function safeBackgroundFileName(name, mimeType = "") {
  const extensionFromName = path.extname(String(name || "")).toLowerCase();
  const extensionFromMime = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogg",
    "video/quicktime": ".mov"
  }[mimeType] || "";
  const extension = extensionFromName || extensionFromMime || ".jpg";
  const base = path.basename(String(name || "background"), extensionFromName)
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 72) || "background";

  return `${base}${extension}`;
}

function importBackgroundFile(payload = {}) {
  const dataUrl = String(payload.dataUrl || "");
  const match = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!match) {
    throw new Error("Invalid background file.");
  }

  const mimeType = match[1];
  const allowed = /^(image\/(apng|avif|gif|jpeg|png|svg\+xml|webp)|video\/(mp4|webm|ogg|quicktime))$/i;
  if (!allowed.test(mimeType)) {
    throw new Error("Unsupported background file type.");
  }

  const backgroundsDir = getBackgroundsDir();
  fs.mkdirSync(backgroundsDir, { recursive: true });

  const originalName = safeBackgroundFileName(payload.name, mimeType);
  const extension = path.extname(originalName);
  const baseName = path.basename(originalName, extension);
  let fileName = originalName;
  let index = 2;

  while (fs.existsSync(path.join(backgroundsDir, fileName))) {
    fileName = `${baseName}-${index}${extension}`;
    index += 1;
  }

  fs.writeFileSync(path.join(backgroundsDir, fileName), Buffer.from(match[2], "base64"));

  return {
    id: `/background-media/${fileName}`,
    name: path.basename(fileName, extension),
    file: fileName,
    url: `/background-media/${encodeURIComponent(fileName)}`,
    type: mimeType.startsWith("video/") ? "video" : "image"
  };
}

function slugifySongTitle(title) {
  return String(title || "song")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64) || "song";
}

function getUniqueSongFileName(title) {
  const songsDir = getSongsDir();
  const baseSlug = slugifySongTitle(title);
  let fileName = `${baseSlug}.cho`;
  let index = 2;

  while (fs.existsSync(path.join(songsDir, fileName))) {
    fileName = `${baseSlug}-${index}.cho`;
    index += 1;
  }

  return fileName;
}

function safeSongRelativePath(value) {
  const relativePath = String(value || "")
    .replace(/\\/g, "/")
    .split("/")
    .filter(part => part && part !== "." && part !== "..")
    .join("/");

  return /\.(cho|chordpro|chopro|pro)$/i.test(relativePath) ? relativePath : "";
}

function buildChordProFile(title, chordLyrics, backgroundMedia = "") {
  const body = String(chordLyrics || "")
    .replace(/\r\n/g, "\n")
    .replace(/^\{title:[^\n]+\}\s*/i, "")
    .replace(/^\{background(?:[_-]media)?:[^\n]+\}\s*/gim, "")
    .trim();
  const background = cleanOptionalLongText(backgroundMedia, 1000);
  const header = [
    `{title: ${cleanLongText(title, "Untitled Song", 160)}}`,
    background ? `{background: ${background}}` : ""
  ].filter(Boolean).join("\n");

  return `${header}\n\n${body}\n`;
}

function saveSongFile(payload = {}) {
  const songsDir = getSongsDir();
  const title = cleanLongText(payload.title, "Untitled Song", 160);
  const chordLyrics = cleanLongText(payload.chordLyrics || payload.lyrics, "", 100000);
  if (!chordLyrics.trim()) {
    throw new Error("Song lyrics are required.");
  }

  fs.mkdirSync(songsDir, { recursive: true });

  const existingFile = safeSongRelativePath(payload.file);
  const fileName = existingFile || getUniqueSongFileName(title);
  const filePath = path.join(songsDir, fileName);
  const content = buildChordProFile(title, chordLyrics, payload.backgroundMedia);

  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf-8");
  return parseChordProSong(content, filePath, fileName);
}

function publicControllerState() {
  return {
    ...controllerState,
    step: Math.min(
      Math.max(0, Number(controllerState.step) || 0),
      Math.max(0, controllerState.sections.length - 1)
    )
  };
}

function setControllerSong(payload = {}) {
  const sections = Array.isArray(payload.sections)
    ? payload.sections
        .map(section => Array.isArray(section) ? section.map(line => String(line || "").trim()).filter(Boolean) : [])
        .filter(section => section.length)
    : normalizeSongSections(payload.lyrics);
  const chordSections = Array.isArray(payload.chordSections)
    ? payload.chordSections
        .map(section => Array.isArray(section) ? section.map(line => String(line || "").trim()).filter(Boolean) : [])
        .filter(section => section.length)
    : String(payload.chordLyrics || payload.lyrics || "").replace(/\r\n/g, "\n").trim()
      ? String(payload.chordLyrics || payload.lyrics || "")
          .replace(/\r\n/g, "\n")
          .trim()
          .split(/\n\s*\n/)
          .map(section => section.split("\n").map(line => line.trim()).filter(Boolean))
          .filter(section => section.length)
      : sections;
  const sectionLabels = Array.isArray(payload.sectionLabels)
    ? payload.sectionLabels.map(label => String(label || "").trim()).slice(0, sections.length)
    : [];

  controllerState = {
    active: sections.length > 0,
    blank: false,
    title: cleanText(payload.title, "Song"),
    sections,
    chordSections,
    sectionLabels,
    step: 0,
    background: cleanText(payload.background, controllerState.background || "#0f172a"),
    backgroundMedia: cleanOptionalLongText(payload.backgroundMedia),
    textColor: cleanText(payload.textColor, controllerState.textColor || "#ffffff"),
    accentColor: cleanText(payload.accentColor, controllerState.accentColor || "#38bdf8")
  };
}

function getSongListLines() {
  return loadSongLibrary().map((song, index) => {
    const number = song.file?.match(/(^|\/)[A-Za-z]*(\d+)/)?.[2] || String(index + 1).padStart(3, "0");
    return `${number}  ${song.title}`;
  });
}

function setControllerSongList(payload = {}) {
  const lines = getSongListLines();
  const sectionSize = 14;
  const sections = [];

  for (let index = 0; index < lines.length; index += sectionSize) {
    sections.push(lines.slice(index, index + sectionSize));
  }

  controllerState = {
    active: sections.length > 0,
    blank: false,
    title: cleanText(payload.title, "Song Requests"),
    sections,
    chordSections: sections,
    step: 0,
    background: cleanText(payload.background, controllerState.background || "#0f172a"),
    backgroundMedia: cleanOptionalLongText(payload.backgroundMedia),
    textColor: cleanText(payload.textColor, controllerState.textColor || "#ffffff"),
    accentColor: cleanText(payload.accentColor, controllerState.accentColor || "#38bdf8")
  };
}

function updateControllerStyle(payload = {}) {
  controllerState.background = cleanText(payload.background, controllerState.background || "#0f172a");
  controllerState.backgroundMedia = cleanOptionalLongText(payload.backgroundMedia);
  controllerState.textColor = cleanText(payload.textColor, controllerState.textColor || "#ffffff");
  controllerState.accentColor = cleanText(payload.accentColor, controllerState.accentColor || "#38bdf8");
}

function setControllerBlank(payload = {}) {
  const settings = loadStyleSettings();
  const useConfiguredBlankMedia = payload.useConfiguredBlankMedia !== false;
  controllerState = {
    active: true,
    blank: true,
    title: "Blank Screen",
    sections: [],
    chordSections: [],
    sectionLabels: [],
    step: 0,
    background: cleanText(payload.background, controllerState.background || "#0f172a"),
    backgroundMedia: cleanOptionalLongText(useConfiguredBlankMedia
      ? settings.blankBackgroundMedia || payload.backgroundMedia
      : payload.backgroundMedia),
    textColor: cleanText(payload.textColor, controllerState.textColor || "#ffffff"),
    accentColor: cleanText(payload.accentColor, controllerState.accentColor || "#38bdf8")
  };
}

function clearControllerOutput() {
  controllerState.active = false;
  controllerState.blank = false;
  controllerState.title = "";
  controllerState.sections = [];
  controllerState.chordSections = [];
  controllerState.sectionLabels = [];
  controllerState.step = 0;
}

function returnToTeachingMode() {
  const wasControllerActive = controllerState.active;
  if (wasControllerActive) clearControllerOutput();
  return wasControllerActive;
}

function nextControllerSection() {
  if (!controllerState.active) return false;
  const nextStep = Math.min(controllerState.sections.length - 1, controllerState.step + 1);
  if (nextStep === controllerState.step) return false;
  controllerState.step = nextStep;
  notifyPresentationStepChanged();
  return true;
}

function previousControllerSection() {
  if (!controllerState.active) return false;
  const previousStep = Math.max(0, controllerState.step - 1);
  if (previousStep === controllerState.step) return false;
  controllerState.step = previousStep;
  notifyPresentationStepChanged();
  return true;
}

function startQuizById(quizId) {
  const normalizedQuizId = normalizeQuizId(quizId);
  const foundIndex = normalizedQuizId
    ? quizBank.findIndex(item =>
        item.id === normalizedQuizId || item.groupId === normalizedQuizId
      )
    : 0;
  const startIndex = normalizedQuizId && foundIndex < 0 ? -1 : Math.max(0, foundIndex);
  const quiz = quizBank[startIndex] || quizBank[0];
  if (!quiz || startIndex < 0) {
    quizError = {
      message: normalizedQuizId
        ? `Quiz "${normalizedQuizId}" was not found. Check that the matching YAML file exists in the course quizzes folder.`
        : "No quiz is available for this course.",
      quizId: normalizedQuizId || ""
    };
    return false;
  }

  returnToTeachingMode();
  quizError = null;
  const activeGroupId = quiz.groupId || quiz.id;
  const sequence = quizBank
    .slice(startIndex)
    .filter(item => (item.groupId || item.id) === activeGroupId);

  quizState.active = true;
  quizState.quizId = quiz.id;
  quizState.quiz = quiz;
  quizState.launchedFromSlide = state.slide;
  quizState.sequence = sequence.map(item => item.id);
  quizState.counts = initQuizCounts(quiz);
  quizState.countsByQuiz = Object.fromEntries(
    sequence.map(item => [item.id, initQuizCounts(item)])
  );
  quizState.answers = {};
  quizState.answersByQuiz = Object.fromEntries(sequence.map(item => [item.id, {}]));
  return true;
}

function endActiveQuiz() {
  if (!quizState.active) return false;
  quizState.active = false;
  return true;
}

function clearActiveQuizAnswers() {
  if (!quizState.quiz) return false;

  quizState.counts = initQuizCounts(quizState.quiz);
  quizState.countsByQuiz = Object.fromEntries(
    (quizState.sequence || [quizState.quiz.id]).map(quizId => {
      const quiz = quizBank.find(item => item.id === quizId) || quizState.quiz;
      return [quizId, initQuizCounts(quiz)];
    })
  );
  quizState.answers = {};
  quizState.answersByQuiz = Object.fromEntries(
    (quizState.sequence || [quizState.quiz.id]).map(quizId => [quizId, {}])
  );
  clearResponsesForCurrentQuiz();
  return true;
}

function loadSlides() {
  const filePath = currentCourse.entryPath;
  const md = fs.readFileSync(filePath, "utf-8");
  const parsedDocument = parseFrontMatter(md);

  presentationMeta = parsedDocument.meta;
  footnoteDefinitions = collectFootnoteDefinitions(parsedDocument.body);

  const slideBlocks = parsedDocument.body
    .split(/\n\s*\n/)
    .map(block =>
      block
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean)
        // Keep appendix footnote definitions visible as definition cards;
        // popups still resolve from footnoteDefinitions collected above.
        .map(line => {
          const match = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/);
          if (!match) return line;
          const id = match[1].trim();
          const note = match[2].trim();
          return note ? `${id}\n: ${note}` : "";
        })
        .filter(Boolean)
    )
    .filter(slide => slide.length > 0);

  const parsedSlides = applyStickyHeadings(splitBlocksAtAdditionalIndependentClauses(
    normalizeSynthesisBlocks(slideBlocks)
  ).map(parseSlide));

  slides = [
    ...buildCoverSlides(presentationMeta),
    ...parsedSlides
  ];

  const inlineQuizzes = slides
    .filter(slide => slide.quiz)
    .map((slide, index) => ({
      id: `inline-slide-${index + 1}`,
      title: `Slide ${index + 1}`,
      question: slide.quiz.question,
      choices: slide.quiz.choices
    }));

  quizBank = [...loadQuizBank(presentationMeta), ...inlineQuizzes];
  invalidatePresentationCaches();
}

function buildCoverSlides(meta = {}) {
  const cover = String(meta.cover || "").trim();
  if (!cover) return [];

  return [parseSlide([`![${meta.title || "Course cover"}](${cover})`])];
}

const renderedSlideCache = new Map();
let cachedHeadingIndex = null;

function invalidatePresentationCaches() {
  renderedSlideCache.clear();
  cachedHeadingIndex = null;
}

function renderSlideAt(index) {
  const slide = slides[index];
  if (!slide) return { sticky: [], lines: [] };

  const cached = renderedSlideCache.get(index);
  if (cached) return cached;

  const rendered = {
    sticky: (slide.stickyLines || []).map(renderLine),
    lines: slide.lines.map(renderLine)
  };
  renderedSlideCache.set(index, rendered);
  return rendered;
}

function buildRenderedSlideWindow() {
  const currentSlide = Number(state.slide) || 0;

  return {
    slide: currentSlide,
    count: slides.length,
    current: renderSlideAt(currentSlide),
    next: renderSlideAt(currentSlide + 1),
    previous: currentSlide > 0 ? renderSlideAt(currentSlide - 1) : null
  };
}

function buildPayload(participantId = null) {
  return {
    course: {
      id: currentCourse.id,
      title: currentCourse.title,
      subtitle: currentCourse.subtitle,
      version: currentCourse.version
    },
    session: getSessionSummary(),
    connection: getJoinInfo(),
    presentation: presentationMeta,
    headings: getHeadingIndex(2),
    language: getAppLanguage(),
    bibleVersion: getBibleVersion(),
    quizzes: quizBank.map(quiz => publicQuiz(quiz)),
    slides: slides.map(slide => ({ quiz: slide.quiz })),
    slideCount: slides.length,
    renderedSlideWindow: buildRenderedSlideWindow(),
    slide: state.slide,
    step: state.step,
    quizState: {
      active: quizState.active,
      quizId: quizState.quizId,
      quiz: publicQuiz(quizState.quiz, !quizState.active),
      launchedFromSlide: quizState.launchedFromSlide,
      sequence: quizState.sequence,
      counts: quizState.counts,
      countsByQuiz: quizState.countsByQuiz,
      review: getQuizReview(),
      participantResult: getParticipantQuizResult(participantId),
      error: quizError
    },
    popupState: {
      reference: popupState.reference,
      scrollRatio: popupState.scrollRatio,
      verseIndex: popupState.verseIndex,
      verseCount: popupState.verseCount
    },
    audienceQrVisible,
    controllerState: publicControllerState()
  };
}

function sendState() {
  // Build one shared payload for projector/director/controller/etc.
  // Audience sockets with a participant id still get a personalized quiz result.
  let sharedPayload = null;

  for (const socket of io.sockets.sockets.values()) {
    if (socket.participantId) {
      socket.emit("state", buildPayload(socket.participantId));
      continue;
    }

    if (!sharedPayload) sharedPayload = buildPayload(null);
    socket.emit("state", sharedPayload);
  }
}

app.get("/session.csv", (req, res) => {
  const filename = `${currentSession.id}-responses.csv`;

  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
  res.send(buildSessionCsv());
});

app.post("/session/new", (req, res) => {
  startNewSession();
  sendState();
  res.json(getSessionSummary());
});

app.post("/course/load", (req, res) => {
  const courseDir = req.body?.courseDir;

  if (!courseDir || typeof courseDir !== "string" || !switchCourse(courseDir)) {
    res.status(400).json({ error: "Could not load course folder." });
    return;
  }

  sendState();
  res.json({
    id: currentCourse.id,
    title: currentCourse.title,
    rootDir: currentCourse.rootDir
  });
});

app.post("/course/load-markdown", (req, res) => {
  const markdownPath = req.body?.markdownPath;

  if (!markdownPath || typeof markdownPath !== "string" || !switchTeachingMarkdown(markdownPath)) {
    res.status(400).json({ error: "Could not load teaching markdown." });
    return;
  }

  sendState();
  res.json({
    id: currentCourse.id,
    title: currentCourse.title,
    rootDir: currentCourse.rootDir,
    entryPath: currentCourse.entryPath
  });
});

app.get("/course-library", (req, res) => {
  res.json({
    path: getLibraryRootDir(),
    coursesPath: getCourseLibraryDir(),
    suggestedPath: defaultCourseLibraryDir
  });
});

app.get("/library-paths", (req, res) => {
  const bibleStatus = getBibleStatus();
  const activeBiblePath = bibleStatus.searchPaths.find(candidate => candidate.exists && candidate.files > 0);

  res.json({
    libraryRoot: getLibraryRootDir(),
    runtimeDataDir,
    courses: getCourseLibraryDir(),
    songs: getSongsDir(),
    backgrounds: getBackgroundsDir(),
    bibles: getUserBibleDir(),
    bibleVersion: bibleStatus.version,
    activeBiblePath: activeBiblePath?.path || "",
    bibleSearchPaths: bibleStatus.searchPaths
  });
});

app.post("/course-library", (req, res) => {
  const courseLibraryDir = req.body?.courseLibraryDir;

  if (!setCourseLibraryDir(courseLibraryDir)) {
    res.status(400).json({ error: "Could not use that course library folder." });
    return;
  }

  res.json({
    path: getCourseLibraryDir(),
    suggestedPath: defaultCourseLibraryDir
  });
});

app.get("/courses/repository", (req, res) => {
  res.json(loadCourseRepositoryConfig());
});

app.get("/bible/status", (req, res) => {
  res.json(getBibleStatus());
});

app.get("/bible/versions", (req, res) => {
  res.json({
    selected: getBibleVersion(),
    versions: getAvailableBibleVersions()
  });
});

app.post("/bible/install", (req, res) => {
  const version = normalizeBibleVersion(req.body?.version || getBibleVersion());
  const sourceDir = getActiveBibleDir(version, { includeUser: false });
  const targetDir = getUserBibleDir(version);

  if (!sourceDir) {
    res.status(404).json({ error: `No ${version} Bible files were found to install.` });
    return;
  }

  try {
    copyDirectoryFiltered(sourceDir, targetDir, {
      excludeFiles: new Set([".DS_Store"]),
      skipExisting: false
    });

    saveStyleSettings({
      ...loadStyleSettings(),
      bibleVersion: version
    });
    loadBibleReferences();
    res.json(getBibleStatus());
  } catch (error) {
    res.status(500).json({ error: error.message || "Could not install Bible files." });
  }
});

app.get("/bible/test", (req, res) => {
  const text = typeof req.query.text === "string" && req.query.text.trim()
    ? req.query.text.trim()
    : "Hechos 8:3";

  res.json({
    text,
    html: enrichPresentationMarkup(text),
    status: getBibleStatus()
  });
});

app.get("/courses/catalog", async (req, res) => {
  try {
    res.json(await fetchCgvCourseCatalog());
  } catch (error) {
    res.status(500).json({ error: error.message || "Could not load course catalog." });
  }
});

app.post("/courses/install", async (req, res) => {
  const course = req.body?.course;

  if (!course || typeof course !== "object") {
    res.status(400).json({ error: "Select a course to install." });
    return;
  }

  try {
    const result = await downloadCourseFromCgv(course);
    res.json({
      courseDir: result.courseDir,
      title: result.manifest.title || course.title,
      fileCount: result.fileCount
    });
  } catch (error) {
    res.status(500).json({ error: error.message || "Could not install course." });
  }
});

app.get("/headings", (req, res) => {
  res.json(getHeadingIndex(2));
});

app.get("/headings/h1", (req, res) => {
  res.json(getHeadingIndex(1));
});

app.post("/jump/:slide", (req, res) => {
  if (!jumpToSlide(req.params.slide)) {
    res.status(400).json({ error: "Invalid slide." });
    return;
  }

  sendState();
  res.json({ slide: state.slide, step: state.step });
});

app.post("/control/next", (req, res) => {
  if (popupState.reference) {
    advanceOpenPopupVerse(1);
    sendState();
    res.json({
      slide: state.slide,
      step: state.step,
      popupState: {
        reference: popupState.reference,
        verseIndex: popupState.verseIndex,
        verseCount: popupState.verseCount
      }
    });
    return;
  }

  goToNextSlideStep();
  sendState();
  res.json({ slide: state.slide, step: state.step });
});

app.post("/control/prev", (req, res) => {
  if (popupState.reference) {
    advanceOpenPopupVerse(-1);
    sendState();
    res.json({
      slide: state.slide,
      step: state.step,
      popupState: {
        reference: popupState.reference,
        verseIndex: popupState.verseIndex,
        verseCount: popupState.verseCount
      }
    });
    return;
  }

  goToPreviousSlideStep();
  sendState();
  res.json({ slide: state.slide, step: state.step });
});

app.get("/quizzes", (req, res) => {
  res.json(getQuizIndex());
});

app.post("/quiz/start/:quizId", (req, res) => {
  if (!startQuizById(req.params.quizId)) {
    res.status(400).json({ error: quizError?.message || "No quiz available." });
    return;
  }

  sendState();
  res.json({ active: true, quizId: quizState.quizId });
});

app.post("/quiz/end", (req, res) => {
  endActiveQuiz();
  sendState();
  res.json({ active: quizState.active });
});

app.post("/quiz/clear", (req, res) => {
  clearActiveQuizAnswers();
  sendState();
  res.json({ cleared: true });
});

app.get("/state.json", (req, res) => {
  res.json(buildPayload());
});

app.get("/songs", (req, res) => {
  res.json(loadSongLibrary());
});

app.get("/songs/repository", (req, res) => {
  res.json({
    repository: `${defaultSongRepository.owner}/${defaultSongRepository.repo}`,
    url: `https://github.com/${defaultSongRepository.owner}/${defaultSongRepository.repo}/`,
    branch: defaultSongRepository.branch,
    songsPath: defaultSongRepository.songsPath
  });
});

app.post("/songs/sync", async (req, res) => {
  try {
    const result = await syncSongsFromGithub(req.body || {});
    res.json(result);
    io.emit("songs-updated", result);
  } catch (error) {
    res.status(500).json({ error: error.message || "Could not download songs." });
  }
});

app.get("/backgrounds", (req, res) => {
  res.json(loadBackgroundLibrary());
});

app.post("/backgrounds/import", (req, res) => {
  try {
    res.json(importBackgroundFile(req.body || {}));
  } catch (error) {
    res.status(400).json({
      error: error?.message || "The background could not be imported."
    });
  }
});

app.post("/songs/save", (req, res) => {
  try {
    res.json(saveSongFile(req.body || {}));
  } catch (error) {
    res.status(400).json({
      error: error?.message || "The song could not be saved."
    });
  }
});

app.post("/controller/song", (req, res) => {
  setControllerSong(req.body || {});
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/song-list", (req, res) => {
  setControllerSongList(req.body || {});
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/blank", (req, res) => {
  setControllerBlank(req.body || {});
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/style", (req, res) => {
  updateControllerStyle(req.body || {});
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/clear", (req, res) => {
  clearControllerOutput();
  notifyPresentationStepChanged();
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/next", (req, res) => {
  nextControllerSection();
  sendState();
  res.json(publicControllerState());
});

app.post("/controller/previous", (req, res) => {
  previousControllerSection();
  sendState();
  res.json(publicControllerState());
});

loadBibleReferences();
loadSlides();
if (currentCourse.teachingImport) {
  saveAppState({ lastTeachingMarkdown: currentCourse.entryPath, lastCourseDir: "" });
} else {
  saveAppState({ lastCourseDir: currentCourse.rootDir, lastTeachingMarkdown: "" });
}
saveSession();

io.on("connection", socket => {
  socket.emit("state", buildPayload(socket.participantId));

  socket.on("join-session", participant => {
    const registeredParticipant = registerParticipant(socket, participant);
    socket.emit("participant-ack", registeredParticipant);
    sendState();
  });

  socket.on("next", () => {
    if (goToNextSlideStep()) sendState();
  });

  socket.on("prev", () => {
    if (goToPreviousSlideStep()) sendState();
  });

  socket.on("reload-slides", () => {
    returnToTeachingMode();
    loadSlides();
    state.slide = 0;
    state.step = 0;
    resetQuiz();
    clearPopup();
    sendState();
  });

  socket.on("new-session", () => {
    startNewSession();
    sendState();
  });

  socket.on("set-popup-reference", reference => {
    returnToTeachingMode();
    popupState.reference = typeof reference === "string" && reference.trim()
      ? normalizeBibleReferenceKey(reference)
      : null;
    popupState.scrollRatio = 0;
    popupState.verseIndex = 0;
    popupState.verseCount = popupState.reference
      ? findPopupVerseCount(popupState.reference)
      : 0;
    sendState();
  });

  socket.on("set-popup-verse", verseIndex => {
    if (!popupState.reference) return;

    const parsedVerseIndex = Number(verseIndex);
    if (!Number.isInteger(parsedVerseIndex) || parsedVerseIndex < 0) return;

    if (!popupState.verseCount) {
      popupState.verseCount = findPopupVerseCount(popupState.reference);
    }

    const maxIndex = Math.max(0, (popupState.verseCount || 1) - 1);
    popupState.verseIndex = Math.min(maxIndex, parsedVerseIndex);
    popupState.scrollRatio = 0;
    emitPopupScroll();
  });

  socket.on("set-popup-scroll", scrollState => {
    if (!popupState.reference) return;

    const parsedVerseIndex = typeof scrollState === "object" && scrollState !== null
      ? Number(scrollState.verseIndex)
      : NaN;

    if (Number.isInteger(parsedVerseIndex) && parsedVerseIndex >= 0) {
      if (!popupState.verseCount) {
        popupState.verseCount = findPopupVerseCount(popupState.reference);
      }
      const maxIndex = Math.max(0, (popupState.verseCount || 1) - 1);
      popupState.verseIndex = Math.min(maxIndex, parsedVerseIndex);
      popupState.scrollRatio = 0;
    } else {
      const parsedRatio = typeof scrollState === "object" && scrollState !== null
        ? Number(scrollState.scrollRatio)
        : Number(scrollState);
      if (Number.isNaN(parsedRatio)) return;
      popupState.scrollRatio = Math.min(1, Math.max(0, parsedRatio));
    }

    emitPopupScroll();
  });

  socket.on("set-audience-qr-visible", visible => {
    audienceQrVisible = !!visible;
    sendState();
  });

  socket.on("draw-point", point => {
    if (!point || typeof point.x !== "number" || typeof point.y !== "number") return;
    socket.broadcast.emit("draw-point", point);
  });

  socket.on("draw-clear", () => {
    socket.broadcast.emit("draw-clear");
  });

  socket.on("start-quiz", quizId => {
    startQuizById(quizId);
    sendState();
  });

  socket.on("end-quiz", () => {
    if (endActiveQuiz()) sendState();
  });

  socket.on("clear-quiz", () => {
    if (clearActiveQuizAnswers()) sendState();
  });

  socket.on("controller-set-song", payload => {
    setControllerSong(payload || {});
    sendState();
  });

  socket.on("controller-song-list", payload => {
    setControllerSongList(payload || {});
    sendState();
  });

  socket.on("controller-blank", payload => {
    setControllerBlank(payload || {});
    sendState();
  });

  socket.on("controller-style", payload => {
    updateControllerStyle(payload || {});
    sendState();
  });

  socket.on("controller-clear", () => {
    clearControllerOutput();
    notifyPresentationStepChanged();
    sendState();
  });

  socket.on("controller-next", () => {
    if (nextControllerSection()) sendState();
  });

  socket.on("controller-previous", () => {
    if (previousControllerSection()) sendState();
  });

  socket.on("submit-answer", submission => {
    const submittedQuizId = typeof submission === "object" && submission !== null
      ? submission.quizId
      : quizState.quizId;
    const index = typeof submission === "object" && submission !== null
      ? submission.answerIndex
      : submission;
    const activeQuiz = quizBank.find(item => item.id === submittedQuizId);

    if (!quizState.active || !activeQuiz) {
      socket.emit("answer-ack", { accepted: false });
      return;
    }

    if (quizState.sequence?.length && !quizState.sequence.includes(activeQuiz.id)) {
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

    const submittedParticipant = typeof submission === "object" && submission !== null
      ? submission.participant
      : null;
    const participantId = cleanText(
      submittedParticipant?.id || socket.participantId,
      socket.id
    );

    if (!currentSession.participants[participantId]) {
      registerParticipant(socket, {
        id: participantId,
        name: submittedParticipant?.name || "Anonymous"
      });
    }

    if (!quizState.countsByQuiz[activeQuiz.id]) {
      quizState.countsByQuiz[activeQuiz.id] = initQuizCounts(activeQuiz);
    }

    if (!quizState.answersByQuiz[activeQuiz.id]) {
      quizState.answersByQuiz[activeQuiz.id] = {};
    }

    const quizAnswers = quizState.answersByQuiz[activeQuiz.id];
    const quizCounts = quizState.countsByQuiz[activeQuiz.id];

    if (quizAnswers[participantId] !== undefined) {
      const previous = quizAnswers[participantId];
      socket.emit("answer-ack", {
        accepted: true,
        answer: previous,
        quizId: activeQuiz.id,
        alreadyAnswered: true
      });
      return;
    }

    quizAnswers[participantId] = parsedIndex;
    quizCounts[parsedIndex] = (quizCounts[parsedIndex] || 0) + 1;

    if (activeQuiz.id === quizState.quizId) {
      quizState.answers[participantId] = parsedIndex;
      quizState.counts = quizCounts;
    }

    recordResponse(participantId, activeQuiz, parsedIndex);

    socket.emit("answer-ack", {
      accepted: true,
      answer: parsedIndex,
      quizId: activeQuiz.id
    });
    sendState();
  });
});

server.listen(serverPort, "0.0.0.0", () => {
  const joinInfo = getJoinInfo();
  console.log(`ROOTS Presenter running at http://localhost:${serverPort}`);
  console.log(`Audience pages available at ${joinInfo.url}`);
});

module.exports = {
  serverEvents,
  broadcastProjectorFrame,
  parseAnimatedChain,
  stripMarkdownEmphasis,
  buildAnimatedChainReveals
};
