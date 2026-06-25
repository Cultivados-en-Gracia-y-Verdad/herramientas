const STORAGE_KEY = "mna-finite-verbs-assertions-v1";

const chapterFilter = document.querySelector("#chapter-filter");
const moodFilter = document.querySelector("#mood-filter");
const verbPath = document.querySelector("#verb-path");
const count = document.querySelector("#count");
const message = document.querySelector("#message");
const saveStatus = document.querySelector("#save-status");
const verbsView = document.querySelector("#verbs-view");
const assertionsView = document.querySelector("#assertions-view");
const verbsViewButton = document.querySelector("#verbs-view-button");
const assertionsViewButton = document.querySelector("#assertions-view-button");
const assertionActions = document.querySelector("#assertion-actions");
const fullViewButton = document.querySelector("#full-view-button");
const compressedViewButton = document.querySelector("#compressed-view-button");
const assertionTableWrap = document.querySelector("#assertion-table-wrap");
const assertionTableBody = document.querySelector("#assertion-table-body");
const compressedAssertions = document.querySelector("#compressed-assertions");
const saveJsonButton = document.querySelector("#save-json-button");
const loadJsonInput = document.querySelector("#load-json-input");

let finiteVerbs = [];
let assertions = [];
let currentView = "verbs";
let assertionMode = "full";
let openOrder = null;

function uniqueSorted(values, numeric = false) {
  return [...new Set(values)].sort((a, b) =>
    numeric ? Number(a) - Number(b) : String(a).localeCompare(String(b)),
  );
}

function addOptions(select, values, format = String) {
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = format(value);
    select.append(option);
  }
}

function morphologyCell(label, value, className = "") {
  const cell = document.createElement("div");
  cell.className = "morphology-cell";

  const labelElement = document.createElement("span");
  labelElement.className = "morphology-label";
  labelElement.textContent = label;

  const valueElement = document.createElement("span");
  valueElement.className = `morphology-value ${className}`.trim();
  valueElement.textContent = value || "—";

  cell.append(labelElement, valueElement);
  return cell;
}

function createVerbItem(verb) {
  const item = document.createElement("li");
  item.className = "verb-item";

  const marker = document.createElement("span");
  marker.className = "path-marker";
  marker.setAttribute("aria-hidden", "true");

  const card = document.createElement("div");
  card.className = "verb-card";

  const button = document.createElement("button");
  button.className = "verb-button";
  button.type = "button";
  button.setAttribute("aria-expanded", String(openOrder === verb.order));
  button.setAttribute("aria-controls", `morphology-${verb.order}`);

  const ref = document.createElement("span");
  ref.className = "ref";
  ref.textContent = verb.ref;

  const surface = document.createElement("span");
  surface.className = "surface";
  surface.lang = "grc";
  surface.textContent = verb.surface;

  const spanish = document.createElement("span");
  spanish.className = "spanish";
  spanish.lang = "es";
  spanish.textContent = verb.es || "—";

  const lemma = document.createElement("span");
  lemma.className = "lemma";
  lemma.lang = "grc";
  lemma.textContent = verb.lemma;

  button.append(ref, surface, spanish, lemma);

  const morphology = document.createElement("div");
  morphology.className = "morphology-row";
  morphology.id = `morphology-${verb.order}`;
  morphology.hidden = openOrder !== verb.order;
  morphology.append(
    morphologyCell("Morph", verb.morph, "morph-code"),
    morphologyCell("Person", verb.person),
    morphologyCell("Tense", verb.tense),
    morphologyCell("Voice", verb.voice),
    morphologyCell("Mood", verb.mood),
    morphologyCell("Number", verb.number),
  );

  button.addEventListener("click", () => {
    const isOpen = openOrder === verb.order;
    openOrder = isOpen ? null : verb.order;
    document.querySelectorAll(".morphology-row").forEach((row) => {
      row.hidden = row.id !== `morphology-${openOrder}`;
    });
    document.querySelectorAll(".verb-button").forEach((candidate) => {
      candidate.setAttribute(
        "aria-expanded",
        String(candidate.getAttribute("aria-controls") === `morphology-${openOrder}`),
      );
    });
  });

  card.append(button, morphology);
  item.append(marker, card);
  return item;
}

function normalizeAssertion(row, verb) {
  return {
    order: verb.order,
    ref: verb.ref,
    subject: typeof row?.subject === "string" ? row.subject : "",
    verb_form: verb.surface,
    verb_lemma: verb.lemma,
    object: typeof row?.object === "string" ? row.object : "",
    notes: typeof row?.notes === "string" ? row.notes : "",
    confidence: typeof row?.confidence === "string" ? row.confidence : "",
  };
}

function loadAssertions() {
  let saved = [];
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    saved = [];
  }

  const initial = saved.length ? saved : window.ASSERTIONS || [];
  const byOrder = new Map(
    initial
      .filter((row) => row && Number.isInteger(Number(row.order)))
      .map((row) => [Number(row.order), row]),
  );
  assertions = finiteVerbs.map((verb) =>
    normalizeAssertion(byOrder.get(verb.order), verb),
  );
  persistAssertions();
}

function persistAssertions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(assertions, null, 2));
  saveStatus.textContent = "Saved locally";
}

function filteredVerbs() {
  const chapter = chapterFilter.value;
  const mood = moodFilter.value;
  return finiteVerbs.filter(
    (verb) =>
      (!chapter || String(verb.chapter) === chapter) &&
      (!mood || verb.mood === mood),
  );
}

function createTextField(value, placeholder, order, field, multiline = false) {
  const input = document.createElement(multiline ? "textarea" : "input");
  input.className = multiline ? "assertion-notes" : "assertion-input";
  if (!multiline) {
    input.type = "text";
  } else {
    input.rows = 1;
  }
  input.value = value;
  input.placeholder = placeholder;
  input.setAttribute("aria-label", `${placeholder} for assertion ${order}`);
  input.addEventListener("input", () => {
    const assertion = assertions.find((row) => row.order === order);
    if (!assertion) return;
    assertion[field] = input.value;
    persistAssertions();
  });
  return input;
}

function createAssertionRow(verb, assertion) {
  const row = document.createElement("tr");

  const subjectCell = document.createElement("td");
  subjectCell.append(
    createTextField(assertion.subject, "Subject", assertion.order, "subject"),
  );

  const verbCell = document.createElement("td");
  const verbForm = document.createElement("span");
  verbForm.className = "assertion-verb-form";
  verbForm.lang = "grc";
  verbForm.textContent = assertion.verb_form;
  const verbSpanish = document.createElement("span");
  verbSpanish.className = "assertion-verb-spanish";
  verbSpanish.lang = "es";
  verbSpanish.textContent = verb.es || "—";
  const verbLemma = document.createElement("span");
  verbLemma.className = "assertion-verb-lemma";
  verbLemma.lang = "grc";
  verbLemma.textContent = assertion.verb_lemma;
  verbCell.append(verbForm, verbSpanish, verbLemma);

  const objectCell = document.createElement("td");
  objectCell.append(
    createTextField(assertion.object, "Object", assertion.order, "object"),
    createTextField(assertion.notes, "Notes", assertion.order, "notes", true),
  );

  const refCell = document.createElement("td");
  refCell.className = "assertion-ref";
  refCell.textContent = assertion.ref;

  const morphologyCellElement = document.createElement("td");
  morphologyCellElement.className = "assertion-morph";
  morphologyCellElement.textContent = verb.morph;

  row.append(
    subjectCell,
    verbCell,
    objectCell,
    refCell,
    morphologyCellElement,
  );
  return row;
}

function renderAssertionTable(verbs) {
  const assertionsByOrder = new Map(assertions.map((row) => [row.order, row]));
  assertionTableBody.replaceChildren(
    ...verbs.map((verb) =>
      createAssertionRow(verb, assertionsByOrder.get(verb.order)),
    ),
  );
}

function groupConsecutiveAssertions(verbs) {
  const assertionsByOrder = new Map(assertions.map((row) => [row.order, row]));
  const groups = [];

  for (const verb of verbs) {
    const assertion = assertionsByOrder.get(verb.order);
    const subject = assertion.subject.trim();
    const last = groups[groups.length - 1];
    if (!last || last.subject !== subject) {
      groups.push({ subject, rows: [{ assertion, verb }] });
    } else {
      last.rows.push({ assertion, verb });
    }
  }
  return groups;
}

function renderCompressedAssertions(verbs) {
  const groups = groupConsecutiveAssertions(verbs);
  compressedAssertions.replaceChildren(
    ...groups.map((group) => {
      const block = document.createElement("div");
      block.className = "assertion-group";

      const subject = document.createElement("div");
      subject.className = "assertion-group-subject";
      subject.textContent = group.subject || "—";

      const list = document.createElement("ul");
      for (const { assertion, verb } of group.rows) {
        const item = document.createElement("li");
        const verbText = document.createElement("span");
        verbText.className = "compressed-verb";
        verbText.textContent = verb.es || assertion.verb_form;
        const objectText = document.createElement("span");
        objectText.className = "compressed-object";
        objectText.textContent = assertion.object
          ? ` ${assertion.object}`
          : "";
        const refText = document.createElement("span");
        refText.className = "compressed-ref";
        refText.textContent = assertion.ref;
        item.append(verbText, objectText, refText);
        list.append(item);
      }

      block.append(subject, list);
      return block;
    }),
  );
}

function render() {
  const verbs = filteredVerbs();

  if (!verbs.some((verb) => verb.order === openOrder)) {
    openOrder = null;
  }

  if (currentView === "verbs") {
    verbPath.replaceChildren(...verbs.map(createVerbItem));
  } else if (assertionMode === "full") {
    renderAssertionTable(verbs);
  } else {
    renderCompressedAssertions(verbs);
  }

  count.textContent = `${verbs.length} of ${finiteVerbs.length}`;
  message.hidden = verbs.length > 0;
  message.textContent = "No finite verbs match these filters.";
}

function setCurrentView(view) {
  currentView = view;
  const showAssertions = view === "assertions";
  verbsView.hidden = showAssertions;
  assertionsView.hidden = !showAssertions;
  assertionActions.hidden = !showAssertions;
  verbsViewButton.classList.toggle("active", !showAssertions);
  assertionsViewButton.classList.toggle("active", showAssertions);
  render();
}

function setAssertionMode(mode) {
  assertionMode = mode;
  const compressed = mode === "compressed";
  assertionTableWrap.hidden = compressed;
  compressedAssertions.hidden = !compressed;
  fullViewButton.classList.toggle("active", !compressed);
  compressedViewButton.classList.toggle("active", compressed);
  render();
}

async function saveAssertionsJson() {
  const contents = JSON.stringify(assertions, null, 2) + "\n";
  if ("showSaveFilePicker" in window) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: "assertions.json",
        types: [
          {
            description: "JSON",
            accept: { "application/json": [".json"] },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(contents);
      await writable.close();
      saveStatus.textContent = "assertions.json saved";
      return;
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }

  const blob = new Blob([contents], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "assertions.json";
  link.click();
  URL.revokeObjectURL(url);
  saveStatus.textContent = "assertions.json downloaded";
}

async function loadAssertionsJson(file) {
  try {
    const rows = JSON.parse(await file.text());
    if (!Array.isArray(rows)) {
      throw new Error("Assertions JSON must be an array.");
    }
    const byOrder = new Map(
      rows
        .filter((row) => row && Number.isInteger(Number(row.order)))
        .map((row) => [Number(row.order), row]),
    );
    assertions = finiteVerbs.map((verb) =>
      normalizeAssertion(byOrder.get(verb.order), verb),
    );
    persistAssertions();
    saveStatus.textContent = `${file.name} loaded`;
    render();
  } catch (error) {
    saveStatus.textContent = error.message;
  } finally {
    loadJsonInput.value = "";
  }
}

async function load() {
  try {
    if (Array.isArray(window.FINITE_VERBS)) {
      finiteVerbs = window.FINITE_VERBS;
    } else {
      const response = await fetch("output/finite_verbs.json");
      if (!response.ok) {
        throw new Error(`Unable to load finite verbs (${response.status})`);
      }
      finiteVerbs = await response.json();
    }

    finiteVerbs.sort((a, b) => a.order - b.order);
    loadAssertions();

    addOptions(
      chapterFilter,
      uniqueSorted(
        finiteVerbs.map((verb) => verb.chapter),
        true,
      ),
    );
    addOptions(
      moodFilter,
      uniqueSorted(finiteVerbs.map((verb) => verb.mood)),
      (mood) => mood[0].toUpperCase() + mood.slice(1),
    );

    chapterFilter.addEventListener("change", render);
    moodFilter.addEventListener("change", render);
    verbsViewButton.addEventListener("click", () => setCurrentView("verbs"));
    assertionsViewButton.addEventListener("click", () =>
      setCurrentView("assertions"),
    );
    fullViewButton.addEventListener("click", () => setAssertionMode("full"));
    compressedViewButton.addEventListener("click", () =>
      setAssertionMode("compressed"),
    );
    saveJsonButton.addEventListener("click", saveAssertionsJson);
    loadJsonInput.addEventListener("change", () => {
      if (loadJsonInput.files[0]) {
        loadAssertionsJson(loadJsonInput.files[0]);
      }
    });

    render();
  } catch (error) {
    message.hidden = false;
    message.textContent = error.message;
  }
}

load();
