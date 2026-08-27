const app = { course: "", data: null, steps: [], selected: 0, current: 0 };
const $ = selector => document.querySelector(selector);
const esc = (value = "") => String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
function notice(message, error = false) {
  const box = $("#notice");
  box.textContent = message;
  box.className = `notice${error ? " error" : ""}`;
  setTimeout(() => box.classList.add("hidden"), 6500);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "The Manager could not complete that action.");
  return body;
}

async function jsonAction(path, body, keepSelection = true) {
  const result = await api(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  notice(result.message);
  await refresh(keepSelection);
}

async function upload(path, input, extras = {}) {
  if (!input.files[0]) throw new Error("Choose a file first.");
  const form = new FormData();
  form.append("course", app.course);
  form.append("file", input.files[0]);
  Object.entries(extras).forEach(([key, value]) => form.append(key, value));
  const result = await api(path, {method: "POST", body: form});
  notice(result.message);
  await refresh(true);
}

async function uploadCompiler() {
  const skeleton = $("#skeleton-file");
  const observer = $("#observer-file");
  if (!observer.files[0]) throw new Error("Choose the Observer JSON.");
  if (!skeleton.files[0]) throw new Error("Choose the Compiler export.");
  const form = new FormData();
  form.append("course", app.course);
  form.append("skeleton", skeleton.files[0]);
  form.append("observer", observer.files[0]);
  form.append("compiler_version", "cgv-reader");
  const result = await api("/api/import-compiler", {method: "POST", body: form});
  notice(result.message);
  await refresh(false);
}

function currentIndex(steps) {
  const active = steps.findIndex(step => step.status === "active");
  if (active >= 0) return active;
  const unfinished = steps.findIndex(step => step.status !== "done");
  return unfinished >= 0 ? unfinished : steps.length - 1;
}

async function loadCourses() {
  const body = await api("/api/courses");
  $("#course").innerHTML = body.courses.map(c => `<option value="${esc(c.id)}">${esc(c.title)} — ${esc(c.folder)}</option>`).join("");
  const course = body.courses.find(c => c.id === "apocalipsis") || body.courses[0];
  if (!course) throw new Error("No course was found.");
  app.course = course.id;
  $("#course").value = app.course;
}

async function refresh(keepSelection = false) {
  const data = await api(`/api/dashboard?course=${encodeURIComponent(app.course)}`);
  app.data = data;

  const source = Object.fromEntries(data.steps.map(step => [String(step.number), step]));
  const imported = source["G1b"]?.status === "done";
  const checkRecorded = source["G2"]?.note?.startsWith("File check passed");
  const milestones = data.milestones || {};
  const step0Clear = milestones.step0Status === "clear";
  const step0NeedsCorrections = milestones.step0Status === "corrections";
  const blockProposalReady = Boolean(milestones.blockProposalFile);
  const blocksApproved = Boolean(milestones.blocksApproved);
  const structureProposalReady = Boolean(milestones.structureProposalFile);
  const structureApproved = Boolean(milestones.structureApproved);
  const contextQuotesBuilt = Boolean(milestones.contextQuotesBuilt);
  const contextQuoteCount = Number(milestones.contextQuoteCount || 0);

  app.steps = [
    {
      key: "G1b",
      title: "Import the two files",
      status: imported ? "done" : "active",
      detail: "Choose the Observer JSON and the file exported by Compiler. The Manager copies both into Apocalipsis.",
      note: imported ? "Both current files are in Apocalipsis." : "Both files are required.",
      action: ""
    },
    {
      key: "G2",
      title: "Check the current export",
      status: step0Clear ? "done" : (imported ? "active" : "waiting"),
      detail: step0NeedsCorrections
        ? "Step 0 found corrections. Open its report; do not repeat the file check."
        : "Check the imported file. When it passes, type /estructura in Cursor.",
      note: step0Clear
        ? "Step 0 passed."
        : step0NeedsCorrections
          ? "Step 0 completed and named the corrections."
          : checkRecorded
            ? "File check passed. Next: run /estructura."
            : "Ready to check.",
      action: step0NeedsCorrections ? "open-step0" : (imported && !checkRecorded ? "check-skeleton" : "")
    },
    {
      key: "blocks",
      title: "Approve the block inventory",
      status: blocksApproved ? "done" : (step0Clear ? "active" : "waiting"),
      detail: "Review Arquitecto’s proposed units, markers, counts, forms, summaries, and clause IDs. Approve them into blocks.md.",
      note: blocksApproved
        ? "blocks.md is approved."
        : blockProposalReady
          ? "The proposal is ready for your review."
          : "This begins after Step 0 passes.",
      action: blockProposalReady && !blocksApproved ? "open-block-proposal" : ""
    },
    {
      key: "structure",
      title: "Approve the structure",
      status: structureApproved ? "done" : (blocksApproved ? "active" : "waiting"),
      detail: "Review the proposed H1, H2, H3, telos, title, and subtitle. If they represent blocks.md, approve the structure.",
      note: structureApproved
        ? "Structure approved."
        : structureProposalReady
          ? "Open the proposal, review it, then approve it here."
          : "This follows the approved block inventory.",
      action: structureProposalReady && blocksApproved && !structureApproved ? "review-structure" : "",
      structureApproved
    },
    {
      key: "quotes",
      title: "Build context quotes",
      status: contextQuotesBuilt ? "done" : (structureApproved ? "active" : "waiting"),
      detail: "Build the Scripture context quotes now that the H2 spans are approved.",
      note: contextQuotesBuilt
        ? `${contextQuoteCount} context passages were built successfully.`
        : structureApproved
          ? "The approved structure is ready for context quotes."
          : "This follows the approved structure.",
      action: structureApproved && !contextQuotesBuilt ? "build-quotes" : ""
    },
    {
      key: "manual",
      title: "Write the manual",
      status: contextQuotesBuilt ? "active" : "waiting",
      detail: "In Cursor, type /manual. Escriba writes one H3 per pass, reading blocks.md.",
      note: contextQuotesBuilt
        ? `The ${contextQuoteCount} context passages are in place. Next: type /manual in Cursor.`
        : "The introduction must name the book’s series and their counts.",
      action: contextQuotesBuilt ? "open-manual" : ""
    },
    {
      key: "editorial",
      title: "Edit and correct",
      status: "waiting",
      detail: "Run @editor for mechanical work, then @corrector for prose.",
      note: "Editor first; Corrector second.",
      action: ""
    },
    {
      key: "release",
      title: "Final review and release",
      status: "waiting",
      detail: "Run the final checks, complete the human reading, approve the finished manual, and release it.",
      note: "Nothing releases automatically.",
      action: ""
    }
  ].map((step, index) => ({...step, number: String(index + 1)}));

  app.current = currentIndex(app.steps);
  if (!keepSelection || app.selected >= app.steps.length) app.selected = app.current;
  render();
}

function render() {
  const data = app.data;
  const completed = app.steps.filter(step => step.status === "done").length;
  $("#course-folder").textContent = data.course.folder;
  $("#course-title").textContent = data.course.title;
  $("#progress-label").textContent = `${completed} of ${app.steps.length} steps complete`;
  $("#progress-bar").style.width = `${completed / app.steps.length * 100}%`;

  $("#step-list").innerHTML = app.steps.map((step, index) => `
    <button class="nav-step ${step.status} ${index === app.selected ? "selected" : ""} ${index === app.current ? "current" : ""}" data-index="${index}">
      <span class="nav-icon">${step.status === "done" ? "✓" : esc(step.number)}</span>
      <span class="nav-title">${esc(step.title)}</span>
    </button>`).join("");

  const step = app.steps[app.selected];
  $("#step-number").textContent = step.number;
  $("#step-status").textContent = ({done: "DONE", active: "NOW", waiting: "LATER"})[step.status] || "LATER";
  $("#step-status").className = `status ${step.status}`;
  $("#now-label").textContent = app.selected === app.current ? "DO THIS NOW" : "WORKFLOW REFERENCE";
  $("#step-title").textContent = step.title;
  $("#step-detail").textContent = step.detail;
  $("#step-note").textContent = step.note;
  $("#return-current").classList.toggle("hidden", app.selected === app.current);
  $("#previous-step").disabled = app.selected === 0;
  $("#next-step").disabled = app.selected === app.steps.length - 1;
  renderControls(step);
  renderDecision(step);
  renderDetails(data);
}

function renderControls(step) {
  const box = $("#step-controls");
  const action = step.action;
  if (step.key === "G1b") {
    box.innerHTML = `
      <label class="field"><span>Observer JSON</span><input id="observer-file" type="file" accept=".json"></label>
      <label class="field"><span>Compiler export</span><input id="skeleton-file" type="file" accept=".md,.markdown,.txt"></label>
      <button class="primary-action" data-command="import-compiler">Import both files</button>`;
    return;
  }
  if (step.key === "structure" && step.action === "review-structure") {
    box.innerHTML = `
      <div class="actions">
        <button class="quiet" data-command="open-structure-proposal">Open proposal</button>
        <button class="primary-action" data-command="approve-structure">Approve this structure</button>
      </div>`;
    return;
  }
  const labels = {
    "confirm-cursor": "I confirmed @arquitecto",
    "prepare-course": "Create missing pipeline folders",
    "check-skeleton": "Check this file",
    "open-step0": "Open the Step 0 report",
    "open-block-proposal": "Open the block inventory proposal",
    "open-structure-proposal": "Open the structure proposal",
    "verify-blocks": "Verify blocks.md",
    "open-blocks": "Open blocks.md",
    "build-quotes": "Build context quotes",
    "open-manual": "Open the manual folder",
    "run-final-checks": "Run final automated evidence",
  };
  box.innerHTML = action && labels[action] ? `<button class="primary-action" data-command="${esc(action)}">${esc(labels[action])}</button>` : "";
}

function renderDecision() {
  $("#decision").classList.add("hidden");
  $("#gate-actions").innerHTML = "";
}

function renderDetails(data) {
  const blockers = [...data.validationErrors.map(error => ({reason: error})), ...data.blockers];
  $("#blockers").innerHTML = blockers.length ? blockers.map(item => `<p>${esc(item.reason)}</p>`).join("") : `<p>No formal blocker is recorded. The highlighted task is simply the first incomplete transition.</p>`;
  $("#provenance").innerHTML = data.provenance.length ? data.provenance.map(event => `<div class="gap"><strong>${esc(event.action)}</strong><p>${esc(event.notes || event.gate || "")}</p></div>`).join("") : `<p>No audit events have been recorded yet.</p>`;
}

async function handleCommand(command) {
  if (command === "refresh") return refresh(true);
  if (command === "import-compiler") return uploadCompiler();
  if (command === "import-observer") return upload("/api/import-observer", $("#observer-file"));
  if (command === "import-skeleton") return upload("/api/import-skeleton", $("#skeleton-file"), {compiler_version: $("#compiler-version").value});
  if (command === "record-skeleton") return jsonAction("/api/record-skeleton", {course: app.course, compilerVersion: $("#compiler-version").value});
  if (command === "confirm-cursor") return jsonAction("/api/confirm-cursor", {course: app.course});
  if (command === "prepare-course") return jsonAction("/api/prepare-course", {course: app.course});
  if (command === "check-skeleton") return jsonAction("/api/check-skeleton", {course: app.course});
  if (command === "open-step0") return jsonAction("/api/open", {course: app.course, target: "step0"});
  if (command === "open-block-proposal") return jsonAction("/api/open", {course: app.course, target: "block-proposal"});
  if (command === "open-structure-proposal") return jsonAction("/api/open", {course: app.course, target: "structure-proposal"});
  if (command === "approve-structure") return jsonAction("/api/approve-structure", {course: app.course}, false);
  if (command === "verify-blocks") return jsonAction("/api/verify-blocks", {course: app.course});
  if (command === "build-quotes") return jsonAction("/api/build-quotes", {course: app.course});
  if (command === "run-final-checks") return jsonAction("/api/run-final-checks", {course: app.course});
  if (command === "open-observation") return jsonAction("/api/open", {course: app.course, target: "observation"});
  if (command === "open-blocks") return jsonAction("/api/open", {course: app.course, target: "blocks"});
  if (command === "open-manual") return jsonAction("/api/open", {course: app.course, target: "manual"});
}

document.addEventListener("click", async event => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.classList.contains("nav-step")) { app.selected = Number(button.dataset.index); render(); return; }
  if (button.id === "previous-step") { app.selected -= 1; render(); return; }
  if (button.id === "next-step") { app.selected += 1; render(); return; }
  if (button.id === "return-current") { app.selected = app.current; render(); return; }
  button.disabled = true;
  try {
    if (button.id === "refresh") await refresh(true);
    else if (button.id === "open-course") await jsonAction("/api/open", {course: app.course, target: "course"});
    else if (button.dataset.command) await handleCommand(button.dataset.command);
    else if (button.dataset.gateStatus) await jsonAction("/api/transition", {course: app.course, status: button.dataset.gateStatus, notes: $("#gate-notes").value});
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
});

$("#course").addEventListener("change", async event => {
  app.course = event.target.value;
  try { await refresh(false); } catch (error) { notice(error.message, true); }
});

(async () => {
  try { await loadCourses(); await refresh(false); }
  catch (error) { notice(error.message, true); }
})();
