const refreshCatalogButton = document.getElementById("refreshCatalogButton");
const repositoryStatus = document.getElementById("repositoryStatus");
const courseList = document.getElementById("courseList");

let catalogCourses = [];

async function readJson(response) {
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "Request failed.");
  }
  return result;
}

function setRepositoryStatus(message) {
  repositoryStatus.textContent = message;
}

function getRepositorySourceLabel(config, catalog) {
  return config.source || catalog?.source || config.url || catalog?.url || "cgv-data/courses";
}

function getInstallLocationLabel(config) {
  return config.downloadDir
    ? `${t("installedTo")}: ${config.downloadDir}`
    : t("chooseLibraryBeforeDownload");
}

function getCourseActionLabel(course) {
  if (!course.available && !course.installed) return t("comingSoon");
  if (course.updateAvailable) return t("updateAndLoad");
  if (course.installed) return t("load");
  return t("downloadAndLoad");
}

function renderCourses() {
  courseList.replaceChildren();

  if (!catalogCourses.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = t("noCoursesLoaded");
    courseList.append(empty);
    return;
  }

  catalogCourses.forEach(course => {
    const unavailable = !course.available && !course.installed;
    const item = document.createElement("article");
    item.className = "course-item";
    item.dataset.status = course.status || "not-downloaded";

    const title = document.createElement("h3");
    title.textContent = course.title;

    const titleRow = document.createElement("div");
    titleRow.className = "course-title-row";

    const badge = document.createElement("span");
    badge.className = `course-badge ${course.status || "not-downloaded"}`;
    badge.textContent = unavailable
      ? t("comingSoon")
      : course.updateAvailable
      ? t("updateAvailable")
      : course.installed
        ? t("downloaded")
        : t("notDownloaded");

    const meta = document.createElement("p");
    meta.className = "course-meta";
    meta.textContent = [
      course.version ? `${t("online")} ${course.version}` : "",
      course.localVersion ? `${t("local")} ${course.localVersion}` : "",
      course.path
    ]
      .filter(Boolean)
      .join(" · ");

    const description = document.createElement("p");
    description.textContent = course.description || t("courseFallbackDescription");

    const installButton = document.createElement("button");
    installButton.type = "button";
    installButton.textContent = getCourseActionLabel(course);
    installButton.disabled = unavailable;
    installButton.addEventListener("click", () => {
      if (unavailable) return;

      if (course.installed && !course.updateAvailable) {
        loadInstalledCourse(course, installButton);
        return;
      }

      installCourse(course, installButton);
    });

    titleRow.append(title, badge);
    item.append(titleRow, meta, description, installButton);
    courseList.append(item);
  });
}

async function loadRepositorySettings() {
  try {
    const config = await readJson(await fetch("/courses/repository"));
    setRepositoryStatus(`${t("source")}: ${getRepositorySourceLabel(config)}. ${getInstallLocationLabel(config)}`);
    await refreshCatalog();
  } catch (error) {
    setRepositoryStatus(error.message || t("couldNotLoadRepository"));
  }
}

async function refreshCatalog() {
  refreshCatalogButton.disabled = true;
  setRepositoryStatus(t("loadingCourses"));

  try {
    const catalog = await readJson(await fetch("/courses/catalog"));
    const config = await readJson(await fetch("/courses/repository"));
    catalogCourses = catalog.courses || [];
    renderCourses();
    const courseWord = catalogCourses.length === 1 ? t("courseSingular") : t("coursePlural");
    setRepositoryStatus(`${t("source")}: ${getRepositorySourceLabel(config, catalog)}. ${catalogCourses.length} ${courseWord} ${t("available")}. ${getInstallLocationLabel(config)}`);
  } catch (error) {
    catalogCourses = [];
    renderCourses();
    setRepositoryStatus(error.message || t("couldNotLoadCourses"));
  } finally {
    refreshCatalogButton.disabled = false;
  }
}

async function installCourse(course, button) {
  button.disabled = true;
  button.textContent = course.updateAvailable ? `${t("updating")}...` : `${t("downloading")}...`;
  setRepositoryStatus(`${course.updateAvailable ? t("updating") : t("downloading")} ${course.title} from CGV GitHub...`);

  try {
    const result = await readJson(await fetch("/courses/install", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ course })
    }));

    await readJson(await fetch("/course/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ courseDir: result.courseDir })
    }));

    setRepositoryStatus(`${result.title || course.title} ${course.updateAvailable ? t("updated") : t("downloadedLower")}, ${t("installedLoaded")}. ${result.fileCount || 0} ${t("filesSavedLocally")}.`);
    await refreshCatalog();
  } catch (error) {
    setRepositoryStatus(error.message || t("couldNotDownloadCourse"));
  } finally {
    button.disabled = false;
    button.textContent = getCourseActionLabel(course);
  }
}

async function loadInstalledCourse(course, button) {
  button.disabled = true;
  button.textContent = t("loading");
  setRepositoryStatus(`Loading ${course.title}...`);

  try {
    await readJson(await fetch("/course/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ courseDir: course.installedCourseDir })
    }));

    setRepositoryStatus(`${course.title} ${t("loaded")}`);
  } catch (error) {
    setRepositoryStatus(error.message || t("couldNotLoadCourse"));
  } finally {
    button.disabled = false;
    button.textContent = t("load");
  }
}

refreshCatalogButton.addEventListener("click", refreshCatalog);
window.CGVI18N.loadLanguage().then(loadRepositorySettings);
