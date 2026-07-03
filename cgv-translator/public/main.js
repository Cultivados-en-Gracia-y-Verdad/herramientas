const tabs = [
  { id: "README", file: "README.md" },
  { id: "Observations", file: "observations.md" },
  { id: "Questions", file: "questions.md" },
  { id: "Evidence", file: "evidence.md" },
  { id: "Research", file: "research.md" },
  { id: "Policy", file: "policy.md" },
  { id: "History", file: "history.md" }
];

const state = {
  view: "translation",
  investigation: "INV-0001",
  tab: tabs[0],
  evidenceFile: null,
  dirty: false,
  saving: false
};

const translationView = document.querySelector("#translation-view");
const investigationView = document.querySelector("#investigation-view");
const sidebar = document.querySelector(".sidebar");
const doulosTrigger = document.querySelector("#doulos-trigger");
const decisionPanel = document.querySelector("#decision-panel");
const openInvestigationButton = document.querySelector("#open-investigation");
const investigationList = document.querySelector("#investigation-list");
const investigationToggle = document.querySelector("#investigation-toggle");
const title = document.querySelector("#investigation-title");
const metaPrimarySubject = document.querySelector("#meta-primary-subject");
const metaOriginReference = document.querySelector("#meta-origin-reference");
const metaCurrentStatus = document.querySelector("#meta-current-status");
const tabBar = document.querySelector("#tabs");
const editor = document.querySelector("#editor");
const saveStatus = document.querySelector("#save-status");
const saveButton = document.querySelector("#save-button");
const gatherEvidence = document.querySelector("#gather-evidence");
const backToTranslation = document.querySelector("#back-to-translation");
const prototypeMessage = document.querySelector("#prototype-message");
const evidenceFiles = document.querySelector("#evidence-files");
const gatherModal = document.querySelector("#gather-modal");
const gatherMessage = document.querySelector("#gather-message");
const runGather = document.querySelector("#run-gather");
const cancelGather = document.querySelector("#cancel-gather");
const replaceActions = document.querySelector("#replace-actions");
const replaceEvidence = document.querySelector("#replace-evidence");
const cancelReplace = document.querySelector("#cancel-replace");

function showTranslationView() {
  state.view = "translation";
  translationView.hidden = false;
  investigationView.hidden = true;
  sidebar.hidden = true;
  setInvestigationListOpen(false);
  window.history.pushState(null, "", window.location.pathname);
  doulosTrigger.focus();
}

function showInvestigationView() {
  state.view = "investigation";
  translationView.hidden = true;
  investigationView.hidden = false;
  sidebar.hidden = false;
  window.location.hash = "investigation/INV-0001";
}

function setStatus(text, stateName = "saved") {
  saveStatus.textContent = text;
  saveStatus.dataset.state = stateName;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error || `Request failed: ${response.status}`);
    error.code = body.code;
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function fetchText(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.text();
}

async function loadInvestigations() {
  const { investigations } = await api("/api/investigations");
  investigationList.innerHTML = "";

  for (const id of investigations) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `investigation-item${id === state.investigation ? " active" : ""}`;
    button.textContent = id;
    button.addEventListener("click", () => openInvestigation(id));
    investigationList.append(button);
  }
}

function setInvestigationListOpen(open) {
  document.body.classList.toggle("investigations-open", open);
  investigationToggle.setAttribute("aria-expanded", String(open));
}

function renderTabs() {
  tabBar.innerHTML = "";
  for (const tab of tabs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab${tab.file === state.tab.file ? " active" : ""}`;
    button.textContent = tab.id;
    button.addEventListener("click", () => openTab(tab));
    tabBar.append(button);
  }
}

async function saveCurrent() {
  if (state.evidenceFile || !state.dirty || state.saving) return;
  state.saving = true;
  saveButton.disabled = true;
  setStatus("Saving...", "saving");

  try {
    await api(`/api/investigations/${state.investigation}/files/${encodeURIComponent(state.tab.file)}`, {
      method: "PUT",
      body: JSON.stringify({ content: editor.value })
    });
    state.dirty = false;
    setStatus("Saved", "saved");
  } catch (error) {
    setStatus("Save error", "error");
    throw error;
  } finally {
    state.saving = false;
    saveButton.disabled = false;
  }
}

async function loadInvestigationMeta() {
  const { meta } = await api(`/api/investigations/${state.investigation}`);
  metaPrimarySubject.textContent = meta.primarySubject || "-";
  metaOriginReference.textContent = meta.originReference || "-";
  metaCurrentStatus.textContent = meta.currentStatus || "-";
}

async function openInvestigation(id) {
  await saveCurrent();
  state.investigation = id;
  state.tab = tabs[0];
  state.evidenceFile = null;
  showInvestigationView();
  title.textContent = id;
  await loadInvestigations();
  setInvestigationListOpen(false);
  await loadInvestigationMeta();
  renderTabs();
  await loadCurrentFile();
}

async function openTab(tab) {
  if (!state.evidenceFile && tab.file === state.tab.file) return;
  await saveCurrent();
  state.tab = tab;
  state.evidenceFile = null;
  renderTabs();
  await loadCurrentFile();
}

async function loadCurrentFile() {
  editor.disabled = true;
  editor.readOnly = false;
  saveButton.disabled = false;
  setStatus("Loading...", "saving");
  prototypeMessage.textContent = "";
  const { content } = await api(
    `/api/investigations/${state.investigation}/files/${encodeURIComponent(state.tab.file)}`
  );
  editor.value = content;
  state.dirty = false;
  editor.disabled = false;
  editor.focus();
  setStatus("Saved", "saved");
  await renderEvidenceFiles();
}

async function openEvidenceFile(fileName) {
  await saveCurrent();
  editor.disabled = true;
  editor.readOnly = true;
  saveButton.disabled = true;
  setStatus("Evidence file", "saved");
  prototypeMessage.textContent = "";

  const content = await fetchText(
    `/api/investigations/${state.investigation}/evidence/${encodeURIComponent(fileName)}`
  );
  state.evidenceFile = fileName;
  editor.value = content;
  state.dirty = false;
  editor.disabled = false;
  editor.focus();
  prototypeMessage.textContent = `Viewing ${fileName}.`;
}

async function renderEvidenceFiles() {
  if (state.tab.file !== "evidence.md") {
    evidenceFiles.hidden = true;
    evidenceFiles.innerHTML = "";
    return;
  }

  const { files } = await api(`/api/investigations/${state.investigation}/evidence`);
  evidenceFiles.innerHTML = "";

  if (!files.length) {
    evidenceFiles.hidden = true;
    return;
  }

  const heading = document.createElement("p");
  heading.className = "evidence-files-label";
  heading.textContent = "Available evidence";
  evidenceFiles.append(heading);

  const list = document.createElement("div");
  list.className = "evidence-file-list";

  for (const file of files) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "evidence-file-card";
    button.textContent = file.name;
    button.addEventListener("click", () => {
      void openEvidenceFile(file.name).catch(error => {
        prototypeMessage.textContent = error.message || "Evidence file error.";
      });
    });
    list.append(button);
  }

  evidenceFiles.append(list);
  evidenceFiles.hidden = false;
}

function openGatherModal() {
  gatherMessage.textContent = "";
  replaceActions.hidden = true;
  runGather.disabled = false;
  gatherModal.hidden = false;
  runGather.focus();
}

function closeGatherModal() {
  gatherModal.hidden = true;
  gatherMessage.textContent = "";
  replaceActions.hidden = true;
}

async function runOccurrenceGather({ replace = false } = {}) {
  gatherMessage.textContent = replace ? "Replacing occurrences..." : "Gathering occurrences...";
  runGather.disabled = true;
  replaceEvidence.disabled = true;

  try {
    await api(`/api/investigations/${state.investigation}/gather`, {
      method: "POST",
      body: JSON.stringify({ type: "occurrences", replace })
    });
    prototypeMessage.textContent = "Occurrence evidence gathered.";
    closeGatherModal();
    await renderEvidenceFiles();
    if (state.tab.file === "history.md") {
      await loadCurrentFile();
    }
  } catch (error) {
    if (error.code === "EVIDENCE_EXISTS") {
      gatherMessage.textContent = "";
      replaceActions.hidden = false;
      replaceEvidence.disabled = false;
      replaceEvidence.focus();
      return;
    }
    gatherMessage.textContent = error.message || "Gather error.";
  } finally {
    runGather.disabled = false;
    replaceEvidence.disabled = false;
  }
}

editor.addEventListener("input", () => {
  if (state.evidenceFile) return;
  state.dirty = true;
  setStatus("Unsaved changes", "dirty");
});

saveButton.addEventListener("click", () => {
  void saveCurrent().catch(() => {});
});

doulosTrigger.addEventListener("click", () => {
  decisionPanel.hidden = !decisionPanel.hidden;
});

openInvestigationButton.addEventListener("click", () => {
  void openInvestigation("INV-0001");
});

investigationToggle.addEventListener("click", () => {
  setInvestigationListOpen(!document.body.classList.contains("investigations-open"));
});

gatherEvidence.addEventListener("click", () => {
  openGatherModal();
});

backToTranslation.addEventListener("click", () => {
  showTranslationView();
});

runGather.addEventListener("click", () => {
  const selected = document.querySelector("input[name='gather-type']:checked")?.value;
  if (selected !== "occurrences") {
    gatherMessage.textContent = "Only occurrences are implemented.";
    return;
  }
  void runOccurrenceGather().catch(() => {});
});

replaceEvidence.addEventListener("click", () => {
  void runOccurrenceGather({ replace: true }).catch(() => {});
});

cancelGather.addEventListener("click", () => {
  closeGatherModal();
});

cancelReplace.addEventListener("click", () => {
  closeGatherModal();
});

gatherModal.addEventListener("click", event => {
  if (event.target === gatherModal) {
    closeGatherModal();
  }
});

window.addEventListener("keydown", event => {
  if (event.key === "Escape" && !gatherModal.hidden) {
    closeGatherModal();
    return;
  }

  const mod = event.metaKey || event.ctrlKey;
  if (mod && event.key.toLowerCase() === "s") {
    event.preventDefault();
    void saveCurrent();
  }
});

window.addEventListener("beforeunload", event => {
  if (!state.dirty) return;
  event.preventDefault();
});

await loadInvestigations();
renderTabs();
if (window.location.hash === "#investigation/INV-0001") {
  await openInvestigation("INV-0001");
} else {
  showTranslationView();
}
