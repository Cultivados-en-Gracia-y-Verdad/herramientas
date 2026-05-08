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

function renderCourses() {
  courseList.replaceChildren();

  if (!catalogCourses.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No courses loaded.";
    courseList.append(empty);
    return;
  }

  catalogCourses.forEach(course => {
    const item = document.createElement("article");
    item.className = "course-item";
    item.dataset.status = course.status || "not-downloaded";

    const title = document.createElement("h3");
    title.textContent = course.title;

    const titleRow = document.createElement("div");
    titleRow.className = "course-title-row";

    const badge = document.createElement("span");
    badge.className = `course-badge ${course.status || "not-downloaded"}`;
    badge.textContent = course.updateAvailable
      ? "Update available"
      : course.installed
        ? "Downloaded"
        : "Not downloaded";

    const meta = document.createElement("p");
    meta.className = "course-meta";
    meta.textContent = [
      course.version ? `Online ${course.version}` : "",
      course.localVersion ? `Local ${course.localVersion}` : "",
      course.path
    ]
      .filter(Boolean)
      .join(" · ");

    const description = document.createElement("p");
    description.textContent = course.description || "Cultivados en Gracia y Verdad course";

    const installButton = document.createElement("button");
    installButton.type = "button";
    installButton.textContent = course.updateAvailable
      ? "Update and Load"
      : course.installed
        ? "Load"
        : "Download and Load";
    installButton.addEventListener("click", () => {
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
    const library = config.downloadDir
      ? `Library: ${config.downloadDir}`
      : "Choose Course > Choose Course Library Folder... before downloading.";

    setRepositoryStatus(`Source: ${config.url}. ${library}`);
    await refreshCatalog();
  } catch (error) {
    setRepositoryStatus(error.message || "Could not load repository settings.");
  }
}

async function refreshCatalog() {
  refreshCatalogButton.disabled = true;
  setRepositoryStatus("Loading courses from CGV GitHub...");

  try {
    const catalog = await readJson(await fetch("/courses/catalog"));
    const config = await readJson(await fetch("/courses/repository"));
    catalogCourses = catalog.courses || [];
    renderCourses();
    setRepositoryStatus(`${catalog.name}: ${catalogCourses.length} course${catalogCourses.length === 1 ? "" : "s"} available. ${
      config.downloadDir ? `Library: ${config.downloadDir}` : "Choose a course library folder from the Course menu before downloading."
    }`);
  } catch (error) {
    catalogCourses = [];
    renderCourses();
    setRepositoryStatus(error.message || "Could not load CGV courses.");
  } finally {
    refreshCatalogButton.disabled = false;
  }
}

async function installCourse(course, button) {
  button.disabled = true;
  button.textContent = course.updateAvailable ? "Updating..." : "Downloading...";
  setRepositoryStatus(`${course.updateAvailable ? "Updating" : "Downloading"} ${course.title} from CGV GitHub...`);

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

    setRepositoryStatus(`${result.title || course.title} ${course.updateAvailable ? "updated" : "downloaded"}, installed, and loaded. ${result.fileCount || 0} files saved locally.`);
    await refreshCatalog();
  } catch (error) {
    setRepositoryStatus(error.message || "Could not download course.");
  } finally {
    button.disabled = false;
    button.textContent = course.updateAvailable
      ? "Update and Load"
      : course.installed
        ? "Load"
        : "Download and Load";
  }
}

async function loadInstalledCourse(course, button) {
  button.disabled = true;
  button.textContent = "Loading...";
  setRepositoryStatus(`Loading ${course.title}...`);

  try {
    await readJson(await fetch("/course/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ courseDir: course.installedCourseDir })
    }));

    setRepositoryStatus(`${course.title} loaded.`);
  } catch (error) {
    setRepositoryStatus(error.message || "Could not load course.");
  } finally {
    button.disabled = false;
    button.textContent = "Load";
  }
}

refreshCatalogButton.addEventListener("click", refreshCatalog);
loadRepositorySettings();
