const fs = require("fs/promises");
const http = require("http");
const path = require("path");
const { app, BrowserWindow, screen, Menu, dialog } = require("electron");

const APP_URL = "http://localhost:3000";
const DEFAULT_COURSE_LIBRARY_DIR = path.join(app.getPath("documents"), "CGV Presenter");
const LOGO_PATH = path.join(__dirname, "assets", "cgv-app-icon.png");

app.setName("CGV Presenter");
process.env.ROOTS_RUNTIME_DATA_DIR = app.getPath("userData");
process.env.ROOTS_DEFAULT_COURSE_LIBRARY_DIR = DEFAULT_COURSE_LIBRARY_DIR;

const { serverEvents } = require("./server");

let presenterWindow;
let projectorWindow;
let settingsWindow;
let courseDownloadWindow;
let presentationMode = "extended";
let switchingMode = false;
let headingMenuItems = [];
let quizMenuItems = [];
let menuRefreshTimer = null;
let loadedCourseTitle = "";

function shouldShowMenuBar() {
  return process.platform !== "darwin";
}

function scheduleCourseMenuRefresh() {
  clearTimeout(menuRefreshTimer);
  menuRefreshTimer = setTimeout(async () => {
    await refreshHeadingMenu();
    await refreshQuizMenu();
  }, 150);
}

serverEvents.addEventListener("course-loaded", scheduleCourseMenuRefresh);

function getLocal(pathname) {
  return new Promise((resolve, reject) => {
    const request = http.get(`${APP_URL}${pathname}`, response => {
      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`Request failed with status ${response.statusCode}`));
        return;
      }

      const chunks = [];
      response.on("data", chunk => chunks.push(chunk));
      response.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    });

    request.on("error", reject);
    request.setTimeout(5000, () => {
      request.destroy(new Error("Request timed out."));
    });
  });
}

function fetchCsvExport() {
  return getLocal("/session.csv");
}

async function getLocalJson(pathname) {
  return JSON.parse(await getLocal(pathname));
}

function postLocal(pathname) {
  return new Promise((resolve, reject) => {
    const request = http.request(`${APP_URL}${pathname}`, { method: "POST" }, response => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        response.resume();
        reject(new Error(`Request failed with status ${response.statusCode}`));
        return;
      }

      response.resume();
      response.on("end", resolve);
    });

    request.on("error", reject);
    request.setTimeout(5000, () => {
      request.destroy(new Error("Request timed out."));
    });
    request.end();
  });
}

function postJsonLocal(pathname, body) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body || {});
    const request = http.request(`${APP_URL}${pathname}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(payload)
      }
    }, response => {
      if (response.statusCode < 200 || response.statusCode >= 300) {
        response.resume();
        reject(new Error(`Request failed with status ${response.statusCode}`));
        return;
      }

      response.resume();
      response.on("end", resolve);
    });

    request.on("error", reject);
    request.setTimeout(5000, () => {
      request.destroy(new Error("Request timed out."));
    });
    request.end(payload);
  });
}

async function loadDownloadedCourse() {
  try {
    const library = await getCourseLibrary();

    const result = await dialog.showOpenDialog(presenterWindow || BrowserWindow.getFocusedWindow(), {
      title: "Load Downloaded Course",
      defaultPath: library.path || DEFAULT_COURSE_LIBRARY_DIR,
      properties: ["openDirectory"]
    });

    if (result.canceled || !result.filePaths.length) return;

    await postJsonLocal("/course/load", { courseDir: result.filePaths[0] });
    await refreshHeadingMenu();
    await refreshQuizMenu();
  } catch (error) {
    dialog.showErrorBox(
      "Load Downloaded Course",
      error?.message || "The selected course could not be loaded."
    );
  }
}

async function getCourseLibrary() {
  try {
    return await getLocalJson("/course-library");
  } catch {
    return {
      path: "",
      suggestedPath: DEFAULT_COURSE_LIBRARY_DIR
    };
  }
}

async function chooseCourseLibraryFolder() {
  try {
    const library = await getCourseLibrary();
    const result = await dialog.showOpenDialog(presenterWindow || BrowserWindow.getFocusedWindow(), {
      title: "Choose Course Library Folder",
      defaultPath: library.path || library.suggestedPath || DEFAULT_COURSE_LIBRARY_DIR,
      message: "Choose the folder where CGV Presenter should store downloaded courses.",
      properties: ["openDirectory", "createDirectory"]
    });

    if (result.canceled || !result.filePaths.length) return;

    await postJsonLocal("/course-library", { courseLibraryDir: result.filePaths[0] });
    await refreshHeadingMenu();
    await refreshQuizMenu();
  } catch (error) {
    dialog.showErrorBox(
      "Choose Course Library",
      error?.message || "The course library folder could not be saved."
    );
  }
}

async function refreshHeadingMenu() {
  try {
    const state = await getLocalJson("/state.json");
    headingMenuItems = await getLocalJson("/headings");
    loadedCourseTitle = state.course?.title || "";
  } catch (error) {
    headingMenuItems = [];
    loadedCourseTitle = "";
  }

  createMenu();
}

async function refreshQuizMenu() {
  try {
    quizMenuItems = await getLocalJson("/quizzes");
  } catch (error) {
    quizMenuItems = [];
  }

  createMenu();
}

async function jumpToSlide(slideIndex) {
  try {
    await postLocal(`/jump/${slideIndex}`);
  } catch (error) {
    dialog.showErrorBox(
      "Jump to Header",
      error?.message || "The presentation could not jump to that header."
    );
  }
}

async function goToNextSlideStep() {
  try {
    await postLocal("/control/next");
  } catch (error) {
    dialog.showErrorBox(
      "Next",
      error?.message || "The presentation could not advance."
    );
  }
}

async function goToPreviousSlideStep() {
  try {
    await postLocal("/control/prev");
  } catch (error) {
    dialog.showErrorBox(
      "Previous",
      error?.message || "The presentation could not go back."
    );
  }
}

async function startQuiz(quizId) {
  try {
    await postLocal(`/quiz/start/${encodeURIComponent(quizId)}`);
  } catch (error) {
    dialog.showErrorBox(
      "Launch Quiz",
      error?.message || "The quiz could not be launched."
    );
  }
}

async function endQuiz() {
  try {
    await postLocal("/quiz/end");
  } catch (error) {
    dialog.showErrorBox(
      "End Quiz",
      error?.message || "The quiz could not be ended."
    );
  }
}

async function clearQuizAnswers() {
  try {
    await postLocal("/quiz/clear");
  } catch (error) {
    dialog.showErrorBox(
      "Clear Quiz Answers",
      error?.message || "The quiz answers could not be cleared."
    );
  }
}

function buildHeadingSubmenu() {
  if (!headingMenuItems.length) {
    return [
      {
        label: loadedCourseTitle ? `Course: ${loadedCourseTitle}` : "No H1/H2 headers loaded",
        enabled: false
      }
    ];
  }

  const sections = [];
  let currentSection = null;

  headingMenuItems.forEach(heading => {
    if (heading.level === 1 || !currentSection) {
      currentSection = {
        ...heading,
        children: []
      };
      sections.push(currentSection);
      return;
    }

    currentSection.children.push(heading);
  });

  const menuItems = loadedCourseTitle
    ? [
        { label: `Course: ${loadedCourseTitle}`, enabled: false },
        { type: "separator" }
      ]
    : [];

  return [
    ...menuItems,
    ...sections.map(section => {
      const submenu = [
        {
          label: "Go to Section",
          click: () => jumpToSlide(section.slide)
        }
      ];

      if (section.children.length) {
        submenu.push({ type: "separator" });
        section.children.forEach(child => {
          submenu.push({
            label: child.title,
            click: () => jumpToSlide(child.slide)
          });
        });
      }

      return {
        label: section.title,
        submenu
      };
    })
  ];
}

function buildQuizSubmenu() {
  const launchItems = quizMenuItems.length
    ? quizMenuItems.map(quiz => ({
        label: quiz.title,
        click: () => startQuiz(quiz.id)
      }))
    : [{ label: "No quizzes loaded", enabled: false }];

  return [
    {
      label: "Launch Quiz",
      submenu: launchItems
    },
    { type: "separator" },
    {
      label: "End Quiz",
      accelerator: "CmdOrCtrl+Shift+Q",
      click: endQuiz
    },
    {
      label: "Clear Current Answers",
      click: clearQuizAnswers
    },
    { type: "separator" },
    {
      label: "Refresh Quiz List",
      click: refreshQuizMenu
    }
  ];
}

function buildExportFilename() {
  const timestamp = new Date()
    .toISOString()
    .replace(/[:.]/g, "-")
    .slice(0, 19);

  return `roots-quiz-results-${timestamp}.csv`;
}

async function exportQuizResults() {
  try {
    const parentWindow = presenterWindow || BrowserWindow.getFocusedWindow();
    const result = await dialog.showSaveDialog(parentWindow, {
      title: "Export Quiz Results",
      defaultPath: path.join(app.getPath("documents"), buildExportFilename()),
      filters: [{ name: "CSV", extensions: ["csv"] }]
    });

    if (result.canceled || !result.filePath) return;

    const csv = await fetchCsvExport();
    await fs.writeFile(result.filePath, csv, "utf8");
  } catch (error) {
    dialog.showErrorBox(
      "Export Quiz Results",
      error?.message || "The quiz results could not be exported."
    );
  }
}

async function startNewTeachingSession() {
  try {
    await postLocal("/session/new");
  } catch (error) {
    dialog.showErrorBox(
      "New Teaching Session",
      error?.message || "The session could not be created."
    );
  }
}

function openStyleSettings() {
  if (settingsWindow && !settingsWindow.isDestroyed()) {
    settingsWindow.focus();
    return;
  }

  settingsWindow = new BrowserWindow({
    width: 760,
    height: 820,
    title: "Style Settings",
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  settingsWindow.loadURL(`${APP_URL}/settings.html`);
  settingsWindow.on("closed", () => {
    settingsWindow = null;
  });
}

function openCourseDownload() {
  if (courseDownloadWindow && !courseDownloadWindow.isDestroyed()) {
    courseDownloadWindow.focus();
    return;
  }

  courseDownloadWindow = new BrowserWindow({
    width: 860,
    height: 760,
    title: "Download Courses",
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  courseDownloadWindow.loadURL(`${APP_URL}/courses.html`);
  courseDownloadWindow.on("closed", () => {
    courseDownloadWindow = null;
  });
}

function createMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        {
          label: "New Teaching Session",
          accelerator: "CmdOrCtrl+N",
          click: startNewTeachingSession
        },
        { type: "separator" },
        {
          label: "Export Quiz Results...",
          accelerator: "CmdOrCtrl+Shift+E",
          click: exportQuizResults
        },
        { type: "separator" },
        { role: "quit" }
      ]
    },
    {
      label: "Presentation",
      submenu: [
        {
          label: "Next",
          accelerator: "Right",
          click: goToNextSlideStep
        },
        {
          label: "Previous",
          accelerator: "Left",
          click: goToPreviousSlideStep
        },
        { type: "separator" },
        {
          label: "Extended Screen Mode",
          type: "radio",
          checked: presentationMode === "extended",
          click: () => switchPresentationMode("extended")
        },
        {
          label: "Mirrored Screen Mode",
          type: "radio",
          checked: presentationMode === "mirrored",
          click: () => switchPresentationMode("mirrored")
        },
        { type: "separator" },
        {
          label: "Exit Full Screen",
          accelerator: "Esc",
          click: exitFullScreen
        }
      ]
    },
    {
      label: "Course",
      submenu: [
        {
          label: "Download Courses...",
          click: openCourseDownload
        },
        {
          label: "Choose Course Library Folder...",
          click: chooseCourseLibraryFolder
        },
        {
          label: "Load Downloaded Course...",
          accelerator: "CmdOrCtrl+O",
          click: loadDownloadedCourse
        }
      ]
    },
    {
      label: "Quiz",
      submenu: buildQuizSubmenu()
    },
    {
      label: "Settings",
      submenu: [
        {
          label: "Style Settings...",
          accelerator: "CmdOrCtrl+,",
          click: openStyleSettings
        }
      ]
    },
    {
      label: "View",
      submenu: [
        {
          label: "Show H1/H2 Headers",
          submenu: buildHeadingSubmenu()
        },
        {
          label: "Refresh Headers",
          click: refreshHeadingMenu
        },
        { type: "separator" },
        { role: "reload" },
        { role: "togglefullscreen" },
        { role: "toggleDevTools" }
      ]
    },
    {
      label: "Window",
      submenu: [
        { role: "minimize" },
        { role: "close" }
      ]
    }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function exitFullScreen() {
  const focusedWindow = BrowserWindow.getFocusedWindow();
  const targetWindow = focusedWindow || projectorWindow || presenterWindow;

  if (targetWindow && !targetWindow.isDestroyed() && targetWindow.isFullScreen()) {
    targetWindow.setFullScreen(false);
  }
}

function attachPresentationShortcuts(window) {
  if (!window) return;

  window.webContents.on("before-input-event", (event, input) => {
    if (input.type !== "keyDown" || input.isAutoRepeat) return;

    const key = input.key;
    const isTextModifier = input.control || input.meta || input.alt;

    if (!isTextModifier && (key === "ArrowRight" || key === "PageDown" || key === " " || key === "Enter")) {
      event.preventDefault();
      goToNextSlideStep();
      return;
    }

    if (!isTextModifier && (key === "ArrowLeft" || key === "PageUp" || key === "Backspace")) {
      event.preventDefault();
      goToPreviousSlideStep();
      return;
    }

    if (key === "Escape") {
      exitFullScreen();
    }
  });
}

function closeWindow(window) {
  if (!window || window.isDestroyed()) return;
  window.close();
}

function clearWindowReferences() {
  if (presenterWindow?.isDestroyed()) presenterWindow = null;
  if (projectorWindow?.isDestroyed()) projectorWindow = null;
}

function switchPresentationMode(mode) {
  if (presentationMode === mode) return;

  presentationMode = mode;
  createMenu();
  recreatePresentationWindows();
}

function getSecondaryDisplay() {
  const primaryDisplay = screen.getPrimaryDisplay();
  return screen
    .getAllDisplays()
    .find(display => display.id !== primaryDisplay.id);
}

function createPresenterWindow(options = {}) {
  const { workArea } = screen.getPrimaryDisplay();
  const bounds = options.bounds || {
    x: workArea.x + 40,
    y: workArea.y + 40,
    width: Math.min(1200, workArea.width),
    height: Math.min(800, workArea.height)
  };

  presenterWindow = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  presenterWindow.loadURL(`${APP_URL}/presenter.html`);
  attachPresentationShortcuts(presenterWindow);

  presenterWindow.on("closed", () => {
    presenterWindow = null;
  });
}

function createProjectorWindow(options = {}) {
  const secondaryDisplay = getSecondaryDisplay();
  const useSecondaryDisplay = options.preferSecondary !== false && secondaryDisplay;
  const displayBounds = options.bounds || (useSecondaryDisplay
    ? secondaryDisplay.bounds
    : screen.getPrimaryDisplay().bounds);
  const fullscreen = options.fullscreen ?? !!useSecondaryDisplay;
  const frameless = options.frame === false;

  projectorWindow = new BrowserWindow({
    x: displayBounds.x,
    y: displayBounds.y,
    width: displayBounds.width,
    height: displayBounds.height,
    icon: LOGO_PATH,
    backgroundColor: "#000000",
    autoHideMenuBar: true,
    frame: !frameless,
    fullscreen,
    show: false
  });

  projectorWindow.loadURL(`${APP_URL}/projector.html?mode=${options.mode || presentationMode}`);
  attachPresentationShortcuts(projectorWindow);

  projectorWindow.once("ready-to-show", () => {
    projectorWindow.setBounds(displayBounds);

    if (fullscreen) {
      projectorWindow.setFullScreen(true);
    }

    if (options.showInactive) {
      projectorWindow.showInactive();
      presenterWindow?.focus();
    } else {
      projectorWindow.show();
      projectorWindow.focus();
    }
  });

  projectorWindow.on("closed", () => {
    projectorWindow = null;
  });
}

function createExtendedWindows() {
  const secondaryDisplay = getSecondaryDisplay();

  if (!secondaryDisplay) {
    const { workArea } = screen.getPrimaryDisplay();
    const gap = 18;
    const margin = 24;
    const availableWidth = workArea.width - (margin * 2) - gap;
    const presenterWidth = Math.max(720, Math.floor(availableWidth * 0.5));
    const projectorWidth = Math.max(520, availableWidth - presenterWidth);
    const windowHeight = Math.max(520, workArea.height - (margin * 2));

    createPresenterWindow({
      bounds: {
        x: workArea.x + margin,
        y: workArea.y + margin,
        width: presenterWidth,
        height: windowHeight
      }
    });

    createProjectorWindow({
      bounds: {
        x: workArea.x + margin + presenterWidth + gap,
        y: workArea.y + margin,
        width: projectorWidth,
        height: windowHeight
      },
      frame: true,
      fullscreen: false,
      mode: "extended",
      preferSecondary: false,
      showInactive: false
    });
    return;
  }

  createPresenterWindow();
  createProjectorWindow({
    frame: false,
    mode: "extended",
    preferSecondary: true,
    showInactive: true
  });
}

function createMirroredWindow() {
  createProjectorWindow({
    frame: false,
    fullscreen: true,
    mode: "mirrored",
    preferSecondary: false,
    showInactive: false
  });
}

function createPresentationWindows() {
  if (presentationMode === "mirrored") {
    createMirroredWindow();
    return;
  }

  createExtendedWindows();
}

function recreatePresentationWindows() {
  switchingMode = true;
  closeWindow(projectorWindow);
  closeWindow(presenterWindow);
  clearWindowReferences();

  setTimeout(() => {
    createPresentationWindows();
    switchingMode = false;
  }, 100);
}

function createWindows() {
  createMenu();
  createPresentationWindows();
  setTimeout(refreshHeadingMenu, 500);
  setTimeout(refreshQuizMenu, 600);
}

app.whenReady().then(createWindows);

app.on("window-all-closed", () => {
  if (switchingMode) return;
  app.quit();
});
