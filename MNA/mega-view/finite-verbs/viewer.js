const STORAGE_KEY = "mna-finite-verbs-assertions-v1";
const SESSION_STORAGE_KEY = "mna-finite-verbs-observation-session-v1";

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
const subjectsComplete = document.querySelector("#subjects-complete");
const objectsComplete = document.querySelector("#objects-complete");
const compressedObserved = document.querySelector("#compressed-observed");
const observationNotes = document.querySelector("#observation-notes");
const rmacPopover = document.querySelector("#rmac-popover");
const rmacPopoverCode = document.querySelector("#rmac-popover-code");
const rmacPopoverDetails = document.querySelector("#rmac-popover-details");
const rmacPopoverClose = document.querySelector("#rmac-popover-close");
const interlinearPopover = document.querySelector("#interlinear-popover");
const interlinearPopoverRef = document.querySelector("#interlinear-popover-ref");
const interlinearPopoverBody = document.querySelector("#interlinear-popover-body");
const interlinearPopoverClose = document.querySelector("#interlinear-popover-close");

let finiteVerbs = [];
let assertions = [];
let currentView = "verbs";
let assertionMode = "full";
let openOrder = null;
const ASSERTION_SCOPE = {
  chapter: 1,
  verseStart: 4,
  verseEnd: 14,
};

const RMAC_TENSE = {
  P: "Presente",
  I: "Imperfecto",
  F: "Futuro",
  A: "Aoristo",
  X: "Perfecto",
  Y: "Pluscuamperfecto",
};
const RMAC_VOICE = {
  A: "Activa",
  M: "Media",
  P: "Pasiva",
  E: "Media o pasiva",
};
const RMAC_MOOD = {
  I: "Indicativo",
  S: "Subjuntivo",
  O: "Optativo",
  M: "Imperativo",
  N: "Infinitivo",
  P: "Participio",
};
const RMAC_PERSON = { 1: "Primera", 2: "Segunda", 3: "Tercera" };
const RMAC_NUMBER = { S: "Singular", P: "Plural" };
const RMAC_PRONOUN = {
  "1S": "yo",
  "1P": "nosotros / nosotras",
  "2S": "tú / usted",
  "2P": "ustedes / vosotros / vosotras",
  "3S": "él / ella / ello",
  "3P": "ellos / ellas",
};

function decodeRmac(code) {
  const match = /^V-([PIFAXY])([AMPE])([ISOMNP])(?:-([123])([SP]))?$/.exec(code);
  if (!match) {
    return [{ label: "Código", value: "No hay explicación disponible" }];
  }
  const [, tense, voice, mood, person, number] = match;
  const details = [
    { label: "Parte de la oración", value: "Verbo" },
    { label: "Tiempo", value: RMAC_TENSE[tense] || tense },
    { label: "Voz", value: RMAC_VOICE[voice] || voice },
    { label: "Modo", value: RMAC_MOOD[mood] || mood },
  ];
  if (person) {
    details.push(
      { label: "Persona", value: RMAC_PERSON[person] || person },
      { label: "Número", value: RMAC_NUMBER[number] || number },
      {
        label: "Pronombre orientativo",
        value: RMAC_PRONOUN[`${person}${number}`] || "—",
      },
    );
  }
  return details;
}

function rmacSummary(code) {
  return decodeRmac(code)
    .filter((detail) => detail.label !== "Parte de la oración")
    .map((detail) => `${detail.label}: ${detail.value}`)
    .join("; ");
}

function closeRmacHelp() {
  rmacPopover.hidden = true;
}

function openRmacHelp(trigger, code) {
  rmacPopoverCode.textContent = code;
  rmacPopoverDetails.replaceChildren(
    ...decodeRmac(code).flatMap((detail) => {
      const term = document.createElement("dt");
      term.textContent = detail.label;
      const description = document.createElement("dd");
      description.textContent = detail.value;
      return [term, description];
    }),
  );

  const rect = trigger.getBoundingClientRect();
  rmacPopover.hidden = false;
  const popoverRect = rmacPopover.getBoundingClientRect();
  const left = Math.min(
    Math.max(12, rect.left),
    window.innerWidth - popoverRect.width - 12,
  );
  const preferredTop = rect.bottom + 8;
  const top =
    preferredTop + popoverRect.height <= window.innerHeight - 12
      ? preferredTop
      : Math.max(12, rect.top - popoverRect.height - 8);
  rmacPopover.style.left = `${left}px`;
  rmacPopover.style.top = `${top}px`;
}

function createRmacButton(code) {
  const button = document.createElement("button");
  button.className = "rmac-help";
  button.type = "button";
  button.textContent = code;
  button.title = rmacSummary(code);
  button.setAttribute("aria-label", `${code}. ${rmacSummary(code)}. Abrir ayuda RMAC`);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openRmacHelp(button, code);
  });
  return button;
}

function closeInterlinear() {
  interlinearPopover.hidden = true;
}

function openInterlinear(ref) {
  const tokens = window.EPHESIANS_INTERLINEAR?.[ref] || [];
  interlinearPopoverRef.textContent = ref;
  interlinearPopoverBody.replaceChildren(
    ...tokens.map((token) => {
      const word = document.createElement("span");
      word.className = "interlinear-word";

      const greek = document.createElement("span");
      greek.className = "interlinear-greek";
      greek.lang = "grc";
      greek.textContent = token.greek || "—";

      const spanish = document.createElement("span");
      spanish.className = "interlinear-spanish";
      spanish.lang = "es";
      spanish.textContent = token.es || "—";

      const details = document.createElement("span");
      details.className = "interlinear-details";

      const lemma = document.createElement("span");
      lemma.className = "interlinear-lemma";
      lemma.lang = "grc";
      lemma.textContent = token.lemma || "—";

      const strong = document.createElement("span");
      strong.className = "interlinear-code";
      strong.textContent = token.strong || "—";

      const rmac = document.createElement("span");
      rmac.className = "interlinear-code";
      rmac.textContent = token.rmac || "—";

      details.append(lemma, strong, rmac);
      word.append(greek, spanish, details);
      return word;
    }),
  );
  interlinearPopover.hidden = false;
}

function createReferenceButton(ref) {
  const button = document.createElement("button");
  button.className = "reference-link";
  button.type = "button";
  button.textContent = ref;
  button.title = `Abrir interlineal de ${ref}`;
  button.setAttribute("aria-label", `Abrir interlineal de ${ref}`);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openInterlinear(ref);
  });
  return button;
}

function loadObservationSession() {
  let session = {};
  try {
    session = JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) || "{}");
  } catch {
    session = {};
  }
  subjectsComplete.checked = session.subjects_complete === true;
  objectsComplete.checked = session.objects_complete === true;
  compressedObserved.checked = session.observed_compressed_view === true;
  observationNotes.value =
    typeof session.notes === "string" ? session.notes : "";
}

function persistObservationSession() {
  localStorage.setItem(
    SESSION_STORAGE_KEY,
    JSON.stringify(
      {
        subjects_complete: subjectsComplete.checked,
        objects_complete: objectsComplete.checked,
        observed_compressed_view: compressedObserved.checked,
        notes: observationNotes.value,
      },
      null,
      2,
    ),
  );
  saveStatus.textContent = "Saved locally";
}

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

  const row = document.createElement("div");
  row.className = "verb-button";

  const button = document.createElement("button");
  button.className = "verb-details-toggle";
  button.type = "button";
  button.setAttribute("aria-expanded", String(openOrder === verb.order));
  button.setAttribute("aria-controls", `morphology-${verb.order}`);

  const ref = document.createElement("span");
  ref.className = "ref";
  ref.append(createReferenceButton(verb.ref));

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

  button.append(surface, spanish, lemma);
  row.append(ref, button);

  const morphology = document.createElement("div");
  morphology.className = "morphology-row";
  morphology.id = `morphology-${verb.order}`;
  morphology.hidden = openOrder !== verb.order;
  morphology.append(
    (() => {
      const cell = document.createElement("div");
      cell.className = "morphology-cell";
      const label = document.createElement("span");
      label.className = "morphology-label";
      label.textContent = "RMAC";
      cell.append(label, createRmacButton(verb.rmac || verb.morph));
      return cell;
    })(),
    morphologyCell("Person", verb.person),
    morphologyCell("Tense", verb.tense),
    morphologyCell("Voice", verb.voice),
    morphologyCell("Mood", verb.mood),
    morphologyCell("Number", verb.number),
  );

  const toggleMorphology = () => {
    const isOpen = openOrder === verb.order;
    openOrder = isOpen ? null : verb.order;
    document.querySelectorAll(".morphology-row").forEach((row) => {
      row.hidden = row.id !== `morphology-${openOrder}`;
    });
    document.querySelectorAll(".verb-details-toggle").forEach((candidate) => {
      candidate.setAttribute(
        "aria-expanded",
        String(candidate.getAttribute("aria-controls") === `morphology-${openOrder}`),
      );
    });
  };

  button.addEventListener("click", toggleMorphology);
  card.append(row, morphology);
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
  const filtered = finiteVerbs.filter(
    (verb) =>
      (!chapter || String(verb.chapter) === chapter) &&
      (!mood || verb.mood === mood),
  );
  if (currentView !== "assertions") {
    return filtered;
  }
  return filtered.filter(
    (verb) =>
      verb.chapter === ASSERTION_SCOPE.chapter &&
      verb.verse >= ASSERTION_SCOPE.verseStart &&
      verb.verse <= ASSERTION_SCOPE.verseEnd,
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
  refCell.append(createReferenceButton(assertion.ref));

  const morphologyCellElement = document.createElement("td");
  morphologyCellElement.className = "assertion-morph";
  morphologyCellElement.append(createRmacButton(verb.rmac || verb.morph));

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
        refText.append(createReferenceButton(assertion.ref));
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
  if (showAssertions) {
    chapterFilter.value = "";
  }
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
    loadObservationSession();

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
    subjectsComplete.addEventListener("change", persistObservationSession);
    objectsComplete.addEventListener("change", persistObservationSession);
    compressedObserved.addEventListener("change", persistObservationSession);
    observationNotes.addEventListener("input", persistObservationSession);
    rmacPopoverClose.addEventListener("click", closeRmacHelp);
    interlinearPopoverClose.addEventListener("click", closeInterlinear);
    document.addEventListener("click", (event) => {
      if (
        !rmacPopover.hidden &&
        !rmacPopover.contains(event.target) &&
        !event.target.closest(".rmac-help")
      ) {
        closeRmacHelp();
      }
      if (
        !interlinearPopover.hidden &&
        !interlinearPopover.contains(event.target) &&
        !event.target.closest(".reference-link")
      ) {
        closeInterlinear();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeRmacHelp();
        closeInterlinear();
      }
    });

    render();
  } catch (error) {
    message.hidden = false;
    message.textContent = error.message;
  }
}

load();
