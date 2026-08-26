const state = { course: "", dashboard: null };

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));

function notice(message, error = false) {
  const box = $("#notice");
  box.textContent = message;
  box.className = `notice${error ? " error" : ""}`;
  window.setTimeout(() => box.classList.add("hidden"), 7000);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The Manager could not complete that action.");
  return body;
}

async function loadCourses() {
  const body = await api("/api/courses");
  const select = $("#course");
  select.innerHTML = body.courses.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.folder)} — ${escapeHtml(c.title)}</option>`).join("");
  const preferred = body.courses.find(c => c.id === "apocalipsis") || body.courses[0];
  if (!preferred) throw new Error("No course with state.yaml was found.");
  state.course = preferred.id;
  select.value = state.course;
}

async function refresh() {
  if (!state.course) return;
  const data = await api(`/api/dashboard?course=${encodeURIComponent(state.course)}`);
  state.dashboard = data;
  render(data);
}

function render(data) {
  $("#course-folder").textContent = data.course.folder;
  $("#course-title").textContent = data.course.title;
  $("#next-action").textContent = data.nextAction;
  $("#project-status").textContent = data.projectStatus;
  $("#release-status").textContent = `Release: ${data.releaseStatus}`;
  $("#current-gate").textContent = data.currentGate;
  $("#current-gate-label").textContent = data.currentGateLabel;
  $("#artifact-status").textContent = data.artifactCurrent ? "Current" : "Not recorded";
  $("#artifact-path").textContent = data.artifactPath;
  $("#blocker-count").textContent = String(data.blockers.length);
  $("#blocker-text").textContent = data.blockers.length ? data.blockers.map(b => b.reason).join(" · ") : "No formal blockers recorded";
  $(".warning-card").classList.toggle("has-warning", data.blockers.length > 0 || data.validationErrors.length > 0);

  $("#steps").innerHTML = data.steps.map(step => `
    <article class="step ${step.status}">
      <div class="step-number">${step.status === "done" ? "✓" : step.number}</div>
      <div>
        <h3>${escapeHtml(step.title)}</h3>
        <p>${escapeHtml(step.detail)}</p>
        <p class="step-note">${escapeHtml(step.note)}</p>
      </div>
      <span class="step-state">${escapeHtml(step.status)}</span>
      ${step.action ? `<button class="step-action secondary" data-step-action="${escapeHtml(step.action)}">${stepButtonLabel(step.action)}</button>` : ""}
    </article>`).join("");

  $("#gates").innerHTML = data.gates.map(gate => `
    <div class="gate">
      <span class="gate-dot ${gate.status.toLowerCase()}"></span>
      <span class="gate-label">${escapeHtml(gate.label)}</span>
      <span class="gate-status">${escapeHtml(gate.status)}</span>
    </div>`).join("");

  const gatePanel = $("#gate-action-panel");
  gatePanel.classList.toggle("hidden", data.gateActions.length === 0);
  $("#gate-actions").innerHTML = data.gateActions.map(action => `<button class="${action.status === "BLOCKED" ? "danger" : ""}" data-gate-status="${action.status}">${escapeHtml(action.label)}</button>`).join("");

  $("#provenance").innerHTML = data.provenance.length ? data.provenance.map(event => `
    <div class="event">
      <p><strong>${escapeHtml(event.action)}</strong></p>
      <p>${escapeHtml(event.notes || event.gate || "")}</p>
      <p class="event-meta">${escapeHtml(event.actor)} · ${escapeHtml(event.timestamp || "")}</p>
    </div>`).join("") : '<p class="muted">No events recorded yet.</p>';

  $("#known-gaps").innerHTML = data.knownGaps.map(item => `
    <div class="known-gap">
      <p><strong>${escapeHtml(item.gap)}</strong></p>
      <p>${escapeHtml(item.effect)}</p>
    </div>`).join("");
}

function stepButtonLabel(action) {
  return {
    "confirm-cursor": "I confirmed @arquitecto",
    "prepare-course": "Create missing pipeline folders",
    "open-observation": "Open observation folder",
    "import-skeleton": "Choose skeleton above",
    "record-skeleton": "Record staged skeleton",
    "check-skeleton": "Run both skeleton checks",
    "verify-blocks": "Run block verifier",
    "open-blocks": "Open blocks.md",
    "build-quotes": "Build context quotes",
    "open-manual": "Open manual folder",
    "run-final-checks": "Run final automated evidence",
  }[action] || "Open";
}

async function jsonAction(path, body) {
  const result = await api(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  notice(result.message);
  await refresh();
}

async function upload(path, input, extras = {}) {
  if (!input.files[0]) throw new Error("Choose a file first.");
  const form = new FormData();
  form.append("course", state.course);
  form.append("file", input.files[0]);
  Object.entries(extras).forEach(([key, value]) => form.append(key, value));
  const result = await api(path, {method: "POST", body: form});
  input.value = "";
  notice(result.message);
  await refresh();
}

document.addEventListener("click", async event => {
  const button = event.target.closest("button");
  if (!button) return;
  button.disabled = true;
  try {
    if (button.id === "refresh") await refresh();
    else if (button.id === "accept-attestation") await upload("/api/accept-gate0", $("#attestation-file"));
    else if (button.id === "import-observer") await upload("/api/import-observer", $("#observer-file"));
    else if (button.id === "import-skeleton") await upload("/api/import-skeleton", $("#skeleton-file"), {compiler_version: $("#compiler-version").value});
    else if (button.dataset.action === "open-course") await jsonAction("/api/open", {course: state.course, target: "course"});
    else if (button.dataset.gateStatus) await jsonAction("/api/transition", {course: state.course, status: button.dataset.gateStatus, notes: $("#gate-notes").value});
    else if (button.dataset.stepAction) {
      const action = button.dataset.stepAction;
      if (action === "confirm-cursor") await jsonAction("/api/confirm-cursor", {course: state.course});
      else if (action === "prepare-course") await jsonAction("/api/prepare-course", {course: state.course});
      else if (action === "record-skeleton") await jsonAction("/api/record-skeleton", {course: state.course, compilerVersion: $("#compiler-version").value});
      else if (action === "check-skeleton") await jsonAction("/api/check-skeleton", {course: state.course});
      else if (action === "verify-blocks") await jsonAction("/api/verify-blocks", {course: state.course});
      else if (action === "build-quotes") await jsonAction("/api/build-quotes", {course: state.course});
      else if (action === "run-final-checks") await jsonAction("/api/run-final-checks", {course: state.course});
      else if (action === "import-skeleton") $("#skeleton-file").click();
      else if (action === "open-observation") await jsonAction("/api/open", {course: state.course, target: "observation"});
      else if (action === "open-blocks") await jsonAction("/api/open", {course: state.course, target: "blocks"});
      else if (action === "open-manual") await jsonAction("/api/open", {course: state.course, target: "manual"});
    }
  } catch (error) {
    notice(error.message, true);
  } finally {
    button.disabled = false;
  }
});

$("#course").addEventListener("change", async event => {
  state.course = event.target.value;
  try { await refresh(); } catch (error) { notice(error.message, true); }
});

(async () => {
  try {
    await loadCourses();
    await refresh();
  } catch (error) {
    notice(error.message, true);
  }
})();
