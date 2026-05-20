const fs = require("fs/promises");
const http = require("http");
const path = require("path");
const { app, BrowserWindow, screen, Menu, dialog, shell } = require("electron");

const APP_URL = "http://localhost:3000";
const DEFAULT_COURSE_LIBRARY_DIR = path.join(app.getPath("documents"), "CGV Presenter");
const LOGO_PATH = path.join(__dirname, "assets", "cgv-app-icon.png");
const APP_STATE_PATH = path.join(app.getPath("userData"), "app-state.json");

app.setName("CGV Presenter");
process.env.ROOTS_RUNTIME_DATA_DIR = app.getPath("userData");
process.env.ROOTS_DEFAULT_COURSE_LIBRARY_DIR = DEFAULT_COURSE_LIBRARY_DIR;

const { serverEvents } = require("./server");

let presenterWindow;
let projectorWindow;
let controllerWindow;
let stageWindow;
let directorWindow;
let settingsWindow;
let courseDownloadWindow;
let presentationMode = "extended";
let switchingMode = false;
let headingMenuItems = [];
let quizMenuItems = [];
let menuRefreshTimer = null;
let loadedCourseTitle = "";
let appLanguage = "es";

const MAIN_TRANSLATIONS = {
  es: {
    loadDownloadedCourse: "Cargar curso descargado",
    selectedCourseCouldNotLoad: "No se pudo cargar el curso seleccionado.",
    welcomeTitle: "Bienvenido a CGV Presenter",
    welcomeMessage: "CGV Presenter está listo para usarse.",
    starterDetail: "El contenido inicial se instaló automáticamente:\n\n• Curso Romanos\n• Referencias bíblicas NBLA\n• 5 canciones iniciales\n\nPuedes comenzar ahora o escoger una carpeta de biblioteca fácil de encontrar, como Documents/CGV Presenter.",
    useStarterLibrary: "Usar biblioteca inicial",
    chooseLibraryFolder: "Escoger carpeta de biblioteca...",
    chooseCourseLibraryFolder: "Escoger carpeta de biblioteca de cursos",
    chooseCourseLibraryMessage: "Escoge la carpeta donde CGV Presenter debe guardar los cursos descargados.",
    chooseCourseLibrary: "Escoger biblioteca de cursos",
    courseLibraryCouldNotSave: "No se pudo guardar la carpeta de biblioteca de cursos.",
    folderUnavailable: "Esa carpeta no está disponible todavía.",
    openCourseLibrary: "Abrir biblioteca de cursos",
    openSongsFolder: "Abrir carpeta de canciones",
    openBibleFolder: "Abrir carpeta de Biblias",
    noBibleFolder: "No se encontró una carpeta bíblica activa. Abre Estado de Biblia para ver todas las rutas de búsqueda.",
    bibleStatus: "Estado de Biblia",
    nblaBibleStatus: "Estado de Biblia NBLA",
    loaded: "Cargado",
    yes: "Sí",
    no: "No",
    books: "Libros",
    references: "Referencias",
    activeFolder: "Carpeta activa",
    noneFound: "Ninguna encontrada",
    searchPaths: "Rutas de búsqueda",
    bibleStatusCouldNotLoad: "No se pudo cargar el estado de la Biblia.",
    jumpToHeader: "Ir al encabezado",
    couldNotJump: "La presentación no pudo ir a ese encabezado.",
    next: "Siguiente",
    previous: "Anterior",
    couldNotAdvance: "La presentación no pudo avanzar.",
    couldNotGoBack: "La presentación no pudo retroceder.",
    launchQuiz: "Iniciar quiz",
    quizCouldNotLaunch: "No se pudo iniciar el quiz.",
    endQuiz: "Terminar quiz",
    quizCouldNotEnd: "No se pudo terminar el quiz.",
    clearQuizAnswers: "Borrar respuestas del quiz",
    quizCouldNotClear: "No se pudieron borrar las respuestas del quiz.",
    noHeadersLoaded: "No hay encabezados H1/H2 cargados",
    course: "Curso",
    goToSection: "Ir a la sección",
    noQuizzesLoaded: "No hay quizzes cargados",
    clearCurrentAnswers: "Borrar respuestas actuales",
    refreshQuizList: "Actualizar lista de quizzes",
    exportQuizResults: "Exportar resultados del quiz",
    quizCouldNotExport: "No se pudieron exportar los resultados del quiz.",
    newTeachingSession: "Nueva sesión de enseñanza",
    sessionCouldNotCreate: "No se pudo crear la sesión.",
    styleSettings: "Configuración de estilo",
    downloadCourses: "Descargar cursos",
    controller: "Control",
    stageView: "Vista de escenario",
    director: "Director",
    file: "Archivo",
    edit: "Editar",
    presentation: "Presentación",
    extendedScreenMode: "Modo pantalla extendida",
    mirroredScreenMode: "Modo pantalla duplicada",
    exitFullScreen: "Salir de pantalla completa",
    library: "Biblioteca",
    openCourseLibraryFolder: "Abrir carpeta de biblioteca de cursos",
    bibleStatusMenu: "Estado de Biblia...",
    quiz: "Quiz",
    settings: "Configuración",
    view: "Vista",
    openController: "Abrir control",
    openStageView: "Abrir vista de escenario",
    openDirector: "Abrir director",
    showHeaders: "Mostrar encabezados H1/H2",
    refreshHeaders: "Actualizar encabezados",
    window: "Ventana"
  },
  en: {}
};

MAIN_TRANSLATIONS.en = {
  ...MAIN_TRANSLATIONS.es,
  loadDownloadedCourse: "Load Downloaded Course",
  selectedCourseCouldNotLoad: "The selected course could not be loaded.",
  welcomeTitle: "Welcome to CGV Presenter",
  welcomeMessage: "CGV Presenter is ready to use.",
  starterDetail: "Starter content has been installed automatically:\n\n• Romanos course\n• NBLA Bible references\n• 5 starter songs\n\nYou can begin now, or choose an easy-to-access library folder such as Documents/CGV Presenter.",
  useStarterLibrary: "Use Starter Library",
  chooseLibraryFolder: "Choose Library Folder...",
  chooseCourseLibraryFolder: "Choose Course Library Folder",
  chooseCourseLibraryMessage: "Choose the folder where CGV Presenter should store downloaded courses.",
  chooseCourseLibrary: "Choose Course Library",
  courseLibraryCouldNotSave: "The course library folder could not be saved.",
  folderUnavailable: "That folder is not available yet.",
  openCourseLibrary: "Open Course Library",
  openSongsFolder: "Open Songs Folder",
  openBibleFolder: "Open Bible Folder",
  noBibleFolder: "No active Bible folder was found. Open Bible Status to see all search paths.",
  bibleStatus: "Bible Status",
  nblaBibleStatus: "NBLA Bible Status",
  loaded: "Loaded",
  yes: "Yes",
  no: "No",
  books: "Books",
  references: "References",
  activeFolder: "Active folder",
  noneFound: "None found",
  searchPaths: "Search paths",
  bibleStatusCouldNotLoad: "Bible status could not be loaded.",
  jumpToHeader: "Jump to Header",
  couldNotJump: "The presentation could not jump to that header.",
  next: "Next",
  previous: "Previous",
  couldNotAdvance: "The presentation could not advance.",
  couldNotGoBack: "The presentation could not go back.",
  launchQuiz: "Launch Quiz",
  quizCouldNotLaunch: "The quiz could not be launched.",
  endQuiz: "End Quiz",
  quizCouldNotEnd: "The quiz could not be ended.",
  clearQuizAnswers: "Clear Quiz Answers",
  quizCouldNotClear: "The quiz answers could not be cleared.",
  noHeadersLoaded: "No H1/H2 headers loaded",
  course: "Course",
  goToSection: "Go to Section",
  noQuizzesLoaded: "No quizzes loaded",
  clearCurrentAnswers: "Clear Current Answers",
  refreshQuizList: "Refresh Quiz List",
  exportQuizResults: "Export Quiz Results",
  quizCouldNotExport: "The quiz results could not be exported.",
  newTeachingSession: "New Teaching Session",
  sessionCouldNotCreate: "The session could not be created.",
  styleSettings: "Style Settings",
  downloadCourses: "Download Courses",
  controller: "Controller",
  stageView: "Stage View",
  director: "Director",
  file: "File",
  edit: "Edit",
  presentation: "Presentation",
  extendedScreenMode: "Extended Screen Mode",
  mirroredScreenMode: "Mirrored Screen Mode",
  exitFullScreen: "Exit Full Screen",
  library: "Library",
  openCourseLibraryFolder: "Open Course Library Folder",
  bibleStatusMenu: "Bible Status...",
  quiz: "Quiz",
  settings: "Settings",
  view: "View",
  openController: "Open Controller",
  openStageView: "Open Stage View",
  openDirector: "Open Director",
  showHeaders: "Show H1/H2 Headers",
  refreshHeaders: "Refresh Headers",
  window: "Window"
};

function mt(key) {
  return MAIN_TRANSLATIONS[appLanguage]?.[key] || MAIN_TRANSLATIONS.es[key] || key;
}

async function refreshAppLanguage() {
  try {
    const settings = await getLocalJson("/style-settings");
    appLanguage = ["es", "en"].includes(settings.language) ? settings.language : "es";
  } catch {
    appLanguage = "es";
  }
}

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
      title: mt("loadDownloadedCourse"),
      defaultPath: library.path || DEFAULT_COURSE_LIBRARY_DIR,
      properties: ["openDirectory"]
    });

    if (result.canceled || !result.filePaths.length) return;

    await postJsonLocal("/course/load", { courseDir: result.filePaths[0] });
    await refreshHeadingMenu();
    await refreshQuizMenu();
  } catch (error) {
    dialog.showErrorBox(
      mt("loadDownloadedCourse"),
      error?.message || mt("selectedCourseCouldNotLoad")
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

async function loadLocalAppState() {
  try {
    return JSON.parse(await fs.readFile(APP_STATE_PATH, "utf8"));
  } catch {
    return {};
  }
}

async function saveLocalAppState(nextState) {
  const appState = {
    ...await loadLocalAppState(),
    ...nextState
  };

  await fs.mkdir(path.dirname(APP_STATE_PATH), { recursive: true });
  await fs.writeFile(APP_STATE_PATH, `${JSON.stringify(appState, null, 2)}\n`, "utf8");
}

async function showFirstRunSetup() {
  const appState = await loadLocalAppState();
  if (appState.setupCompleted) return;

  const result = await dialog.showMessageBox(presenterWindow || BrowserWindow.getFocusedWindow(), {
    type: "info",
    title: mt("welcomeTitle"),
    message: mt("welcomeMessage"),
    detail: mt("starterDetail"),
    buttons: [mt("useStarterLibrary"), mt("chooseLibraryFolder")],
    defaultId: 0,
    cancelId: 0
  });

  if (result.response === 1) {
    await chooseCourseLibraryFolder();
  }

  await saveLocalAppState({ setupCompleted: true });
}

async function chooseCourseLibraryFolder() {
  try {
    const library = await getCourseLibrary();
    const result = await dialog.showOpenDialog(presenterWindow || BrowserWindow.getFocusedWindow(), {
      title: mt("chooseCourseLibraryFolder"),
      defaultPath: library.path || library.suggestedPath || DEFAULT_COURSE_LIBRARY_DIR,
      message: mt("chooseCourseLibraryMessage"),
      properties: ["openDirectory", "createDirectory"]
    });

    if (result.canceled || !result.filePaths.length) return;

    await postJsonLocal("/course-library", { courseLibraryDir: result.filePaths[0] });
    await refreshHeadingMenu();
    await refreshQuizMenu();
  } catch (error) {
    dialog.showErrorBox(
      mt("chooseCourseLibrary"),
      error?.message || mt("courseLibraryCouldNotSave")
    );
  }
}

async function openFolderPath(folderPath, title) {
  if (!folderPath || typeof folderPath !== "string") {
    dialog.showErrorBox(title, mt("folderUnavailable"));
    return;
  }

  try {
    await fs.mkdir(folderPath, { recursive: true });
    const error = await shell.openPath(folderPath);

    if (error) {
      dialog.showErrorBox(title, error);
    }
  } catch (error) {
    dialog.showErrorBox(
      title,
      error?.message || mt("folderUnavailable")
    );
  }
}

async function getLibraryPaths() {
  try {
    return await getLocalJson("/library-paths");
  } catch {
    return {};
  }
}

async function openCourseLibraryFolder() {
  const paths = await getLibraryPaths();
  await openFolderPath(paths.courses, mt("openCourseLibrary"));
}

async function openSongsFolder() {
  const paths = await getLibraryPaths();
  await openFolderPath(paths.songs, mt("openSongsFolder"));
}

async function openBibleFolder() {
  const paths = await getLibraryPaths();

  if (paths.bibles) {
    await openFolderPath(paths.bibles, mt("openBibleFolder"));
    return;
  }

  dialog.showErrorBox(
    mt("openBibleFolder"),
    mt("noBibleFolder")
  );
}

async function showBibleStatus() {
  try {
    const status = await getLocalJson("/bible/status");
    const active = status.searchPaths.find(candidate => candidate.exists && candidate.files > 0);
    const details = [
      `${mt("loaded")}: ${status.loaded ? mt("yes") : mt("no")}`,
      `${mt("books")}: ${status.books}`,
      `${mt("references")}: ${status.references}`,
      "",
      active
        ? `${mt("activeFolder")}:\n${active.path}`
        : `${mt("activeFolder")}:\n${mt("noneFound")}`,
      "",
      `${mt("searchPaths")}:`,
      ...status.searchPaths.map(candidate => (
        `${candidate.exists ? "✓" : "•"} ${candidate.path} (${candidate.files} files)`
      ))
    ].join("\n");

    dialog.showMessageBox(presenterWindow || BrowserWindow.getFocusedWindow(), {
      type: status.loaded ? "info" : "warning",
      title: mt("bibleStatus"),
      message: mt("nblaBibleStatus"),
      detail: details
    });
  } catch (error) {
    dialog.showErrorBox(
      mt("bibleStatus"),
      error?.message || mt("bibleStatusCouldNotLoad")
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
      mt("jumpToHeader"),
      error?.message || mt("couldNotJump")
    );
  }
}

async function goToNextSlideStep() {
  try {
    await postLocal("/control/next");
  } catch (error) {
    dialog.showErrorBox(
      mt("next"),
      error?.message || mt("couldNotAdvance")
    );
  }
}

async function goToPreviousSlideStep() {
  try {
    await postLocal("/control/prev");
  } catch (error) {
    dialog.showErrorBox(
      mt("previous"),
      error?.message || mt("couldNotGoBack")
    );
  }
}

async function startQuiz(quizId) {
  try {
    await postLocal(`/quiz/start/${encodeURIComponent(quizId)}`);
  } catch (error) {
    dialog.showErrorBox(
      mt("launchQuiz"),
      error?.message || mt("quizCouldNotLaunch")
    );
  }
}

async function endQuiz() {
  try {
    await postLocal("/quiz/end");
  } catch (error) {
    dialog.showErrorBox(
      mt("endQuiz"),
      error?.message || mt("quizCouldNotEnd")
    );
  }
}

async function clearQuizAnswers() {
  try {
    await postLocal("/quiz/clear");
  } catch (error) {
    dialog.showErrorBox(
      mt("clearQuizAnswers"),
      error?.message || mt("quizCouldNotClear")
    );
  }
}

function buildHeadingSubmenu() {
  if (!headingMenuItems.length) {
    return [
      {
        label: loadedCourseTitle ? `${mt("course")}: ${loadedCourseTitle}` : mt("noHeadersLoaded"),
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
        { label: `${mt("course")}: ${loadedCourseTitle}`, enabled: false },
        { type: "separator" }
      ]
    : [];

  return [
    ...menuItems,
    ...sections.map(section => {
      const submenu = [
        {
          label: mt("goToSection"),
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
    : [{ label: mt("noQuizzesLoaded"), enabled: false }];

  return [
    {
      label: mt("launchQuiz"),
      submenu: launchItems
    },
    { type: "separator" },
    {
      label: mt("endQuiz"),
      accelerator: "CmdOrCtrl+Shift+Q",
      click: endQuiz
    },
    {
      label: mt("clearCurrentAnswers"),
      click: clearQuizAnswers
    },
    { type: "separator" },
    {
      label: mt("refreshQuizList"),
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
      title: mt("exportQuizResults"),
      defaultPath: path.join(app.getPath("documents"), buildExportFilename()),
      filters: [{ name: "CSV", extensions: ["csv"] }]
    });

    if (result.canceled || !result.filePath) return;

    const csv = await fetchCsvExport();
    await fs.writeFile(result.filePath, csv, "utf8");
  } catch (error) {
    dialog.showErrorBox(
      mt("exportQuizResults"),
      error?.message || mt("quizCouldNotExport")
    );
  }
}

async function startNewTeachingSession() {
  try {
    await postLocal("/session/new");
  } catch (error) {
    dialog.showErrorBox(
      mt("newTeachingSession"),
      error?.message || mt("sessionCouldNotCreate")
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
    title: mt("styleSettings"),
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  settingsWindow.loadURL(`${APP_URL}/settings.html`);
  settingsWindow.on("closed", async () => {
    settingsWindow = null;
    await refreshAppLanguage();
    createMenu();
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
    title: mt("downloadCourses"),
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  courseDownloadWindow.loadURL(`${APP_URL}/courses.html`);
  courseDownloadWindow.on("closed", () => {
    courseDownloadWindow = null;
  });
}

function openControllerWindow() {
  if (controllerWindow && !controllerWindow.isDestroyed()) {
    controllerWindow.focus();
    return;
  }

  controllerWindow = new BrowserWindow({
    width: 1120,
    height: 820,
    title: mt("controller"),
    icon: LOGO_PATH,
    autoHideMenuBar: !shouldShowMenuBar()
  });

  controllerWindow.loadURL(`${APP_URL}/controller.html`);
  controllerWindow.on("closed", () => {
    controllerWindow = null;
  });
}

function openStageWindow() {
  if (stageWindow && !stageWindow.isDestroyed()) {
    stageWindow.focus();
    return;
  }

  stageWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    title: mt("stageView"),
    icon: LOGO_PATH,
    backgroundColor: "#05070c",
    autoHideMenuBar: !shouldShowMenuBar()
  });

  stageWindow.loadURL(`${APP_URL}/stage.html`);
  stageWindow.on("closed", () => {
    stageWindow = null;
  });
}

function openDirectorWindow() {
  if (directorWindow && !directorWindow.isDestroyed()) {
    directorWindow.focus();
    return;
  }

  directorWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    title: mt("director"),
    icon: LOGO_PATH,
    backgroundColor: "#08111f",
    autoHideMenuBar: !shouldShowMenuBar()
  });

  directorWindow.loadURL(`${APP_URL}/director.html`);
  directorWindow.on("closed", () => {
    directorWindow = null;
  });
}

function createMenu() {
  const template = [
    {
      label: mt("file"),
      submenu: [
        {
          label: mt("newTeachingSession"),
          accelerator: "CmdOrCtrl+N",
          click: startNewTeachingSession
        },
        { type: "separator" },
        {
          label: `${mt("exportQuizResults")}...`,
          accelerator: "CmdOrCtrl+Shift+E",
          click: exportQuizResults
        },
        { type: "separator" },
        { role: "quit" }
      ]
    },
    {
      label: mt("edit"),
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "pasteAndMatchStyle" },
        { role: "delete" },
        { type: "separator" },
        { role: "selectAll" }
      ]
    },
    {
      label: mt("presentation"),
      submenu: [
        {
          label: mt("next"),
          accelerator: "Right",
          click: goToNextSlideStep
        },
        {
          label: mt("previous"),
          accelerator: "Left",
          click: goToPreviousSlideStep
        },
        { type: "separator" },
        {
          label: mt("extendedScreenMode"),
          type: "radio",
          checked: presentationMode === "extended",
          click: () => switchPresentationMode("extended")
        },
        {
          label: mt("mirroredScreenMode"),
          type: "radio",
          checked: presentationMode === "mirrored",
          click: () => switchPresentationMode("mirrored")
        },
        { type: "separator" },
        {
          label: mt("exitFullScreen"),
          accelerator: "Esc",
          click: exitFullScreen
        }
      ]
    },
    {
      label: mt("library"),
      submenu: [
        {
          label: `${mt("downloadCourses")}...`,
          click: openCourseDownload
        },
        {
          label: `${mt("chooseCourseLibraryFolder")}...`,
          click: chooseCourseLibraryFolder
        },
        {
          label: `${mt("loadDownloadedCourse")}...`,
          accelerator: "CmdOrCtrl+O",
          click: loadDownloadedCourse
        },
        { type: "separator" },
        {
          label: mt("openCourseLibraryFolder"),
          click: openCourseLibraryFolder
        },
        { type: "separator" },
        {
          label: mt("openSongsFolder"),
          click: openSongsFolder
        },
        { type: "separator" },
        {
          label: mt("openBibleFolder"),
          click: openBibleFolder
        },
        {
          label: mt("bibleStatusMenu"),
          click: showBibleStatus
        }
      ]
    },
    {
      label: mt("quiz"),
      submenu: buildQuizSubmenu()
    },
    {
      label: mt("settings"),
      submenu: [
        {
          label: `${mt("styleSettings")}...`,
          accelerator: "CmdOrCtrl+,",
          click: openStyleSettings
        }
      ]
    },
    {
      label: mt("view"),
      submenu: [
        {
          label: mt("openController"),
          accelerator: "CmdOrCtrl+Shift+C",
          click: openControllerWindow
        },
        {
          label: mt("openStageView"),
          accelerator: "CmdOrCtrl+Shift+S",
          click: openStageWindow
        },
        {
          label: mt("openDirector"),
          accelerator: "CmdOrCtrl+Shift+D",
          click: openDirectorWindow
        },
        { type: "separator" },
        {
          label: mt("showHeaders"),
          submenu: buildHeadingSubmenu()
        },
        {
          label: mt("refreshHeaders"),
          click: refreshHeadingMenu
        },
        { type: "separator" },
        { role: "reload" },
        { role: "togglefullscreen" },
        { role: "toggleDevTools" }
      ]
    },
    {
      label: mt("window"),
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

function installTextEditingContextMenu() {
  app.on("web-contents-created", (_event, contents) => {
    contents.on("context-menu", (_menuEvent, params) => {
      if (!params.isEditable) return;

      Menu.buildFromTemplate([
        { role: "undo", enabled: params.editFlags.canUndo },
        { role: "redo", enabled: params.editFlags.canRedo },
        { type: "separator" },
        { role: "cut", enabled: params.editFlags.canCut },
        { role: "copy", enabled: params.editFlags.canCopy },
        { role: "paste", enabled: params.editFlags.canPaste },
        { role: "delete", enabled: params.editFlags.canDelete },
        { type: "separator" },
        { role: "selectAll", enabled: params.editFlags.canSelectAll }
      ]).popup({ window: BrowserWindow.fromWebContents(contents) });
    });
  });
}

function closeWindow(window) {
  if (!window || window.isDestroyed()) return;
  window.close();
}

function clearWindowReferences() {
  if (presenterWindow?.isDestroyed()) presenterWindow = null;
  if (projectorWindow?.isDestroyed()) projectorWindow = null;
  if (controllerWindow?.isDestroyed()) controllerWindow = null;
  if (stageWindow?.isDestroyed()) stageWindow = null;
  if (directorWindow?.isDestroyed()) directorWindow = null;
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

async function createWindows() {
  await refreshAppLanguage();
  createMenu();
  createPresentationWindows();
  setTimeout(refreshHeadingMenu, 500);
  setTimeout(refreshQuizMenu, 600);
  setTimeout(showFirstRunSetup, 900);
}

app.whenReady().then(() => {
  installTextEditingContextMenu();
  createWindows();
});

app.on("window-all-closed", () => {
  if (switchingMode) return;
  app.quit();
});
