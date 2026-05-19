const express = require("express");
const http = require("http");
const https = require("https");
const os = require("os");
const { Server } = require("socket.io");
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const QRCode = require("qrcode");

const app = express();
const server = http.createServer(app);
const io = new Server(server);
const serverPort = Number(process.env.PORT || 3000);
const serverEvents = new EventTarget();
const resourceBibleDir = process.resourcesPath
  ? path.join(process.resourcesPath, "bibles", "NBLA")
  : "";
const unpackedResourceBibleDir = process.resourcesPath
  ? path.join(process.resourcesPath, "app.asar.unpacked", "bibles", "NBLA")
  : "";
const executableResourceBibleDir = process.execPath
  ? path.join(path.dirname(process.execPath), "resources", "bibles", "NBLA")
  : "";
const cwdBibleDir = path.join(process.cwd(), "bibles", "NBLA");
const bundledBibleDir = path.join(__dirname, "bibles", "NBLA");
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
const backgroundsDir = path.join(__dirname, "backgrounds");
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

  return path.join(appData, "ROOTS Presenter", "data");
}

const runtimeDataDir = getRuntimeDataDir();
const defaultCourseLibraryDir = process.env.ROOTS_DEFAULT_COURSE_LIBRARY_DIR || "";
const styleSettingsPath = path.join(runtimeDataDir, "style-settings.json");
const bundledStyleSettingsPath = path.join(bundledDataDir, "style-settings.json");
const appStatePath = path.join(runtimeDataDir, "app-state.json");
const starterCourseLibraryDir = path.join(runtimeDataDir, "courses");
const starterRomanosCourseDir = path.join(starterCourseLibraryDir, "Romanos");
const songsDir = path.join(runtimeDataDir, "songs");
seedStarterContent();
const defaultCourseDir = isLoadableCourseDir(starterRomanosCourseDir)
  ? starterRomanosCourseDir
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
const synthesisMarker = "::roots-synthesis::";
const h4IntroMarker = "::roots-h4-intro::";

app.use(express.json({ limit: "250kb" }));
app.use(
  "/fonts/ibm-plex-sans",
  express.static(path.join(__dirname, "node_modules", "@fontsource", "ibm-plex-sans", "files"))
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
  saveStyleSettings(settings);
  io.emit("style-settings-updated", { updatedAt: Date.now() });
  res.json(settings);
});
app.get("/join-info", (req, res) => {
  res.json(getJoinInfo());
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
app.use("/background-media", express.static(backgroundsDir));
app.use(express.static(path.join(__dirname, "public")));
app.use("/course-assets", (req, res, next) => {
  express.static(currentCourse?.rootDir || defaultCourseDir)(req, res, next);
});

let slides = [];
let presentationMeta = {};
let quizBank = [];
let currentCourse = loadCourse(getStartupCourseDir());
let bibleReferences = {};
let bibleChapterVerseCounts = {};
let bibleBookNames = [];
let bibleBookPatterns = [];
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
  verseIndex: 0
};

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

function getLocalIpAddress() {
  const interfaces = os.networkInterfaces();

  for (const addresses of Object.values(interfaces)) {
    for (const address of addresses || []) {
      if (address.family === "IPv4" && !address.internal) {
        return address.address;
      }
    }
  }

  return "localhost";
}

function getJoinInfo() {
  const host = getLocalIpAddress();

  return {
    host,
    port: serverPort,
    path: "/audience.html",
    url: `http://${host}:${serverPort}/audience.html`
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

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function cssValue(value, fallback) {
  return /^[#(),.%\w\s-]+$/.test(String(value || "")) ? value : fallback;
}

function safeDirectoryName(value, fallback = "course") {
  return path.basename(String(value || fallback)).replace(/[^\w.\- ]/g, "_") || fallback;
}

function downloadFile(url, destinationPath) {
  return new Promise((resolve, reject) => {
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
    request.setTimeout(30000, () => {
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

function rawCgvCourseUrl(relativePath) {
  return `${cgvRawBaseUrl}/${String(relativePath).split("/").map(encodeURIComponent).join("/")}`;
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

function readInstalledCourseManifest(coursePath) {
  const courseLibraryDir = getCourseLibraryDir();
  if (!courseLibraryDir || !isSafeCgvCoursePath(coursePath)) return null;

  const manifestPath = path.join(courseLibraryDir, safeDirectoryName(coursePath), "manifest.json");
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
  const courseLibraryDir = getCourseLibraryDir();
  const remoteManifest = await fetchCgvCourseManifest(item.name);
  const installedManifest = readInstalledCourseManifest(item.name);
  const installedCourseDir = courseLibraryDir
    ? path.join(courseLibraryDir, safeDirectoryName(item.name))
    : "";
  const remoteVersion = String(remoteManifest?.version || "").trim();
  const localVersion = String(installedManifest?.version || "").trim();
  const installed = Boolean(installedManifest);
  const updateAvailable = installed && remoteVersion && compareVersions(remoteVersion, localVersion) > 0;

  return {
    id: safeDirectoryName(item.name),
    title: remoteManifest?.title || cleanCourseTitle(item.name),
    description: remoteManifest?.description || "Cultivados en Gracia y Verdad course",
    version: remoteVersion,
    localVersion,
    installed,
    installedCourseDir: installed ? installedCourseDir : "",
    updateAvailable,
    status: updateAvailable ? "update-available" : installed ? "downloaded" : "not-downloaded",
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

async function downloadCourseFromCgv(course) {
  const courseLibraryDir = getCourseLibraryDir();

  if (!courseLibraryDir) {
    throw new Error("Choose a course library folder before downloading courses.");
  }

  const coursePath = course?.path || course?.id;

  if (!isSafeCgvCoursePath(coursePath)) {
    throw new Error("The selected course path is not valid.");
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
    id: courseId,
    title: course?.title || cleanCourseTitle(coursePath),
    subtitle: course?.subtitle || "",
    version: course?.version || "",
    entry: entryPath,
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

function loadStyleSettings() {
  const settingsPath = fs.existsSync(styleSettingsPath)
    ? styleSettingsPath
    : bundledStyleSettingsPath;

  if (!fs.existsSync(settingsPath)) return {};

  try {
    return JSON.parse(fs.readFileSync(settingsPath, "utf-8"));
  } catch (error) {
    console.warn(`Could not load style settings: ${error.message}`);
    return {};
  }
}

function saveStyleSettings(settings) {
  fs.mkdirSync(path.dirname(styleSettingsPath), { recursive: true });
  fs.writeFileSync(styleSettingsPath, `${JSON.stringify(settings, null, 2)}\n`);
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
  const bibleDir = getBibleSearchPaths()
    .filter(Boolean)
    .find(candidate => getBibleFileCount(candidate) > 0);

  if (!bibleDir) {
    console.warn("No NBLA Bible data found. Bible reference popups will be disabled.");
    return;
  }

  bibleReferences = {};
  bibleChapterVerseCounts = {};

  fs.readdirSync(bibleDir)
    .filter(fileName => fileName.endsWith(".nbla.md"))
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

  console.log(`Loaded ${bibleBookNames.length} NBLA Bible books from ${bibleDir}`);
}

function getBibleSearchPaths() {
  const appData =
    process.env.APPDATA ||
    process.env.LOCALAPPDATA ||
    process.env.HOME ||
    "";

  return Array.from(new Set([
    resourceBibleDir,
    unpackedResourceBibleDir,
    executableResourceBibleDir,

    process.resourcesPath
      ? path.join(process.resourcesPath, "app", "bibles", "NBLA")
      : "",

    process.resourcesPath
      ? path.join(process.resourcesPath, "app.asar", "bibles", "NBLA")
      : "",

    appData
      ? path.join(appData, "ROOTS Presenter", "bibles", "NBLA")
      : "",

    bundledBibleDir,
    cwdBibleDir,
    legacyNblaDir
  ].filter(Boolean)));
}

function getBibleFileCount(candidate) {
  try {
    if (!candidate || !fs.existsSync(candidate)) return 0;
    return fs.readdirSync(candidate).filter(fileName => fileName.endsWith(".nbla.md")).length;
  } catch {
    return 0;
  }
}

function getBibleStatus() {
  return {
    loaded: bibleBookNames.length > 0,
    books: bibleBookNames.length,
    references: Object.keys(bibleReferences).length,
    sampleBooks: bibleBookNames.slice(0, 8),
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

function buildBibleReferencePopup(displayReference, verses) {
  const normalizedDisplay = escapeHtml(displayReference);
  const popupTitle = escapeHtml(displayReference);
  const popupText = verses
    .map(reference => {
      const verseReference = `${reference.book} ${reference.chapter}:${reference.verse}`;
      return `<div><strong>${escapeHtml(verseReference)}</strong> ${escapeHtml(reference.text)}</div>`;
    })
    .join("");

  return `<span class="bible-ref" tabindex="0" role="button" data-reference="${popupTitle}">${normalizedDisplay}<span class="bible-popup">${popupText}</span></span>`;
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

  return markdownLine.replace(referencePattern, (match, book, referenceList) =>
    buildBibleReferenceListMarkup(match, book, referenceList)
  );
}

function renderLine(line) {
  const manualTitle = parseManualTitleBlock(line);
  if (manualTitle) {
    return `
      <div class="manual-${manualTitle.type}">
        ${enrichBibleReferences(marked.parseInline(manualTitle.text).trim())}
      </div>
    `.trim();
  }

  const quizMarker = parseQuizMarker(line);
  if (quizMarker) {
    const quiz = quizBank.find(item => item.id === quizMarker.quizId);
    const title = quiz?.title || quizMarker.quizId;
    const status = quiz ? "Quiz ready" : "Quiz not found";
    const button = quiz
      ? `<button type="button" onclick="launchQuiz('${escapeHtml(quizMarker.quizId)}')">Launch quiz</button>`
      : `<button type="button" disabled>Missing quiz file</button>`;
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
            <strong>Quiz listo</strong>
            <span>${escapeHtml(title)}</span>
            <small>Escanee el código o entre a <code>${escapeHtml(joinCode)}</code></small>
          </div>
          <img class="quiz-cue-qr" src="/quiz-join.svg" alt="Código QR para entrar al quiz">
        </aside>
      `.trim()
        : `
        <aside class="quiz-cue projector-quiz-cue missing">
          <div>
            <strong>Quiz no disponible</strong>
            <span>${escapeHtml(title)}</span>
            <small>Falta el archivo YAML correspondiente.</small>
          </div>
        </aside>
      `.trim()
    };
  }

  if (line.startsWith(synthesisMarker)) {
    const synthesis = JSON.parse(line.slice(synthesisMarker.length));
    const title = enrichBibleReferences(marked.parseInline(synthesis.title)).trim();
    const points = synthesis.points
      .map(point => `<li>${enrichBibleReferences(marked.parseInline(point)).trim()}</li>`)
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

  if (line.startsWith(h4IntroMarker)) {
    const intro = JSON.parse(line.slice(h4IntroMarker.length));

    return {
      h4Intro: true,
      html: marked.parse(enrichBibleReferences(intro.full)).trim(),
      h4OnlyHtml: marked.parse(enrichBibleReferences(intro.h4)).trim()
    };
  }

  const definitionMatch = line.match(/^(.+?)\n:\s+(.+)$/s);

  if (definitionMatch) {
    return `
      <div class="definition">
        <div class="definition-term">${enrichBibleReferences(marked.parseInline(definitionMatch[1])).trim()}</div>
        <div class="definition-text">${enrichBibleReferences(marked.parseInline(definitionMatch[2])).trim()}</div>
      </div>
    `.trim();
  }

  const html = enrichBibleReferences(marked.parse(line)).trim();

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
  if (isLoadableCourseDir(starterRomanosCourseDir)) return;

  copyDirectoryFiltered(bundledDefaultCourseDir, starterRomanosCourseDir, {
    excludeDirs: new Set(["sessions"]),
    excludeFiles: new Set([".DS_Store"])
  });
}

function seedStarterContent() {
  const appState = loadAppState();

  try {
    seedStarterCourse();
    seedStarterSongs();

    const nextState = {
      starterContentVersion
    };

    if (!isLoadableCourseDir(appState.lastCourseDir) && isLoadableCourseDir(starterRomanosCourseDir)) {
      nextState.lastCourseDir = starterRomanosCourseDir;
    }

    if (!appState.courseLibraryDir && fs.existsSync(starterCourseLibraryDir)) {
      nextState.courseLibraryDir = starterCourseLibraryDir;
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

function getCourseLibraryDir() {
  const configuredDir = loadAppState().courseLibraryDir;
  return typeof configuredDir === "string" ? configuredDir : "";
}

function setCourseLibraryDir(courseLibraryDir) {
  if (!courseLibraryDir || typeof courseLibraryDir !== "string") return false;

  try {
    if (!fs.existsSync(courseLibraryDir)) {
      fs.mkdirSync(courseLibraryDir, { recursive: true });
    }

    if (!fs.statSync(courseLibraryDir).isDirectory()) return false;
    saveAppState({ courseLibraryDir });
    return true;
  } catch (error) {
    console.warn(`Could not save course library folder: ${error.message}`);
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

function getCourseSessionsDir(course) {
  const courseId = safeDirectoryName(course?.id || path.basename(course?.rootDir || "legacy"));
  return path.join(runtimeDataDir, "sessions", courseId);
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
  saveAppState({ lastCourseDir: currentCourse.rootDir });
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
  const fileId = normalizeQuizId(
    lines.find(line => line.trim().startsWith("id:"))?.split(/:\s*/).slice(1).join(":")
      || path.basename(filePath, path.extname(filePath))
  );
  const title = unquote(
    lines.find(line => line.trim().startsWith("title:"))?.split(/:\s*/).slice(1).join(":")
      || fileId
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
        groupId: fileId,
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

function groupRevealLines(lines) {
  const revealLines = [];

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

function applyStickyH4(slidesToProcess) {
  let stickyH4 = null;

  return slidesToProcess.map(slide => {
    const firstHeadingLevel = getFirstHeadingLevel(slide.lines);
    const slideH4 = getFirstH4(slide.lines);
    const sticky = firstHeadingLevel && firstHeadingLevel > 4 ? stickyH4 : null;

    if (slideH4) {
      stickyH4 = slideH4;
    } else if (firstHeadingLevel && firstHeadingLevel < 4) {
      stickyH4 = null;
    }

    return {
      ...slide,
      stickyLines: sticky ? [sticky] : []
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
    verseIndex: 0
  };
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
  return slides.flatMap((slide, index) =>
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
  return true;
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

function parseChordProSong(content, filePath) {
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
    id: path.basename(filePath, path.extname(filePath)),
    title,
    subtitle: metadata.subtitle || "",
    key: metadata.key || "",
    file: path.basename(filePath),
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

function loadSongLibrary() {
  const songFiles = new Map();

  [...bundledSongRoots, songsDir].forEach(root => {
    if (!fs.existsSync(root)) return;

    fs.readdirSync(root)
      .filter(fileName => /\.(cho|chordpro|chopro|pro)$/i.test(fileName))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .slice(0, root === songsDir ? undefined : starterSongLimit)
      .forEach(fileName => {
        songFiles.set(fileName, path.join(root, fileName));
      });
  });

  return [...songFiles.entries()]
    .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
    .map(([, filePath]) => parseChordProSong(fs.readFileSync(filePath, "utf-8"), filePath))
    .filter(song => song.sections.length);
}

function loadBackgroundLibrary() {
  const sources = [
    {
      root: backgroundsDir,
      urlPrefix: "/background-media"
    },
    {
      root: assetBackgroundsDir,
      urlPrefix: "/assets/backgrounds"
    }
  ];

  return sources.flatMap(source => {
    if (!fs.existsSync(source.root)) return [];

    return fs.readdirSync(source.root)
      .filter(fileName => /\.(apng|avif|gif|jpe?g|png|svg|webp|mp4|webm|ogg|mov)$/i.test(fileName))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
      .map(fileName => {
        const isVideo = /\.(mp4|webm|ogg|mov)$/i.test(fileName);
        return {
          id: `${source.urlPrefix}/${fileName}`,
          name: path.basename(fileName, path.extname(fileName)),
          file: fileName,
          url: `${source.urlPrefix}/${encodeURIComponent(fileName)}`,
          type: isVideo ? "video" : "image"
        };
      });
  });
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
  const baseSlug = slugifySongTitle(title);
  let fileName = `${baseSlug}.cho`;
  let index = 2;

  while (fs.existsSync(path.join(songsDir, fileName))) {
    fileName = `${baseSlug}-${index}.cho`;
    index += 1;
  }

  return fileName;
}

function buildChordProFile(title, chordLyrics) {
  const body = String(chordLyrics || "")
    .replace(/\r\n/g, "\n")
    .replace(/^\{title:[^\n]+\}\s*/i, "")
    .trim();

  return `{title: ${cleanLongText(title, "Untitled Song", 160)}}\n\n${body}\n`;
}

function saveSongFile(payload = {}) {
  const title = cleanLongText(payload.title, "Untitled Song", 160);
  const chordLyrics = cleanLongText(payload.chordLyrics || payload.lyrics, "", 100000);
  if (!chordLyrics.trim()) {
    throw new Error("Song lyrics are required.");
  }

  fs.mkdirSync(songsDir, { recursive: true });

  const existingFile = payload.file ? path.basename(String(payload.file)) : "";
  const fileName = existingFile || getUniqueSongFileName(title);
  const filePath = path.join(songsDir, fileName);
  const content = buildChordProFile(title, chordLyrics);

  fs.writeFileSync(filePath, content, "utf-8");
  return parseChordProSong(content, filePath);
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
    const number = song.file?.match(/^(\d+)/)?.[1] || String(index + 1).padStart(3, "0");
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
  controllerState = {
    active: true,
    blank: true,
    title: "Blank Screen",
    sections: [],
    chordSections: [],
    sectionLabels: [],
    step: 0,
    background: cleanText(payload.background, controllerState.background || "#0f172a"),
    backgroundMedia: cleanOptionalLongText(payload.backgroundMedia),
    textColor: cleanText(payload.textColor, controllerState.textColor || "#ffffff"),
    accentColor: cleanText(payload.accentColor, controllerState.accentColor || "#38bdf8")
  };
}

function clearControllerOutput() {
  controllerState.active = false;
  controllerState.blank = false;
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
  return true;
}

function previousControllerSection() {
  if (!controllerState.active) return false;
  const previousStep = Math.max(0, controllerState.step - 1);
  if (previousStep === controllerState.step) return false;
  controllerState.step = previousStep;
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

  slides = applyStickyH4(parsedDocument.body
    .split(/\n\s*\n/)
    .map(block =>
      block
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean)
    )
    .filter(slide => slide.length > 0)
    .map(parseSlide));

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
    quizzes: quizBank.map(quiz => publicQuiz(quiz)),
    slides: slides.map(slide => ({ quiz: slide.quiz })),
    renderedSlides: slides.map(slide => ({
      sticky: (slide.stickyLines || []).map(renderLine),
      lines: slide.lines.map(renderLine)
    })),
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
      verseIndex: popupState.verseIndex
    },
    controllerState: publicControllerState()
  };
}

function sendState() {
  for (const socket of io.sockets.sockets.values()) {
    socket.emit("state", buildPayload(socket.participantId));
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

app.get("/course-library", (req, res) => {
  res.json({
    path: getCourseLibraryDir(),
    suggestedPath: defaultCourseLibraryDir
  });
});

app.get("/library-paths", (req, res) => {
  const bibleStatus = getBibleStatus();
  const activeBiblePath = bibleStatus.searchPaths.find(candidate => candidate.exists && candidate.files > 0);

  res.json({
    runtimeDataDir,
    courses: getCourseLibraryDir() || starterCourseLibraryDir,
    songs: songsDir,
    bibles: activeBiblePath?.path || "",
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

app.get("/bible/test", (req, res) => {
  const text = typeof req.query.text === "string" && req.query.text.trim()
    ? req.query.text.trim()
    : "Hechos 8:3";

  res.json({
    text,
    html: enrichBibleReferences(text),
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
  goToNextSlideStep();
  sendState();
  res.json({ slide: state.slide, step: state.step });
});

app.post("/control/prev", (req, res) => {
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

app.get("/backgrounds", (req, res) => {
  res.json(loadBackgroundLibrary());
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
saveAppState({ lastCourseDir: currentCourse.rootDir });
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
      ? reference.trim()
      : null;
    popupState.scrollRatio = 0;
    popupState.verseIndex = 0;
    sendState();
  });

  socket.on("set-popup-scroll", scrollState => {
    if (!popupState.reference) return;

    const parsedRatio = typeof scrollState === "object" && scrollState !== null
      ? Number(scrollState.scrollRatio)
      : Number(scrollState);
    if (Number.isNaN(parsedRatio)) return;

    popupState.scrollRatio = Math.min(1, Math.max(0, parsedRatio));
    const parsedVerseIndex = typeof scrollState === "object" && scrollState !== null
      ? Number(scrollState.verseIndex)
      : NaN;

    if (Number.isInteger(parsedVerseIndex) && parsedVerseIndex >= 0) {
      popupState.verseIndex = parsedVerseIndex;
    }
    sendState();
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
  serverEvents
};
