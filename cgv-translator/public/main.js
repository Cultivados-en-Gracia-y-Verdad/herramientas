const tabs = [
  { id: "README", file: "README.md" },
  { id: "Observations", file: "observations.md" },
  { id: "Decision", file: "decision.md" },
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
  phraseIndex: 0,
  selectedGreekKey: "doulos",
  evidenceFile: null,
  decision: null,
  translationReturn: null,
  translationLoadedFromDisk: false,
  translationSaveTimer: null,
  translationSaving: false,
  dirty: false,
  saving: false
};

const translationView = document.querySelector("#translation-view");
const investigationView = document.querySelector("#investigation-view");
const sidebar = document.querySelector(".sidebar");
const phraseInterlinear = document.querySelector("#phrase-interlinear");
const decisionPanel = document.querySelector("#decision-panel");
const decisionPanelPolicy = document.querySelector("#decision-panel-policy");
const decisionPanelStatus = document.querySelector("#decision-panel-status");
const openInvestigationButton = document.querySelector("#open-investigation");
const investigationList = document.querySelector("#investigation-list");
const investigationToggle = document.querySelector("#investigation-toggle");
const title = document.querySelector("#investigation-title");
const metaPrimarySubject = document.querySelector("#meta-primary-subject");
const metaOriginReference = document.querySelector("#meta-origin-reference");
const metaCurrentStatus = document.querySelector("#meta-current-status");
const tabBar = document.querySelector("#tabs");
const editor = document.querySelector("#editor");
const evidenceViewer = document.querySelector("#evidence-viewer");
const decisionEditor = document.querySelector("#decision-editor");
const decisionStatus = document.querySelector("#decision-status");
const decisionVersion = document.querySelector("#decision-version");
const decisionEffectiveDate = document.querySelector("#decision-effective-date");
const decisionLemma = document.querySelector("#decision-lemma");
const decisionStrongs = document.querySelector("#decision-strongs");
const decisionRendering = document.querySelector("#decision-rendering");
const decisionConfidence = document.querySelector("#decision-confidence");
const decisionReason = document.querySelector("#decision-reason");
const approveDecision = document.querySelector("#approve-decision");
const translationEditor = document.querySelector("#translation-editor");
const translationReferenceTitle = document.querySelector("#translation-reference-title");
const translationReferenceMeta = document.querySelector("#translation-reference-meta");
const suggestionSourceLabel = document.querySelector("#suggestion-source-label");
const phraseSaveStatus = document.querySelector("#phrase-save-status");
const rv1909ReferenceText = document.querySelector("#rv1909-reference-text");
const bleReferenceText = document.querySelector("#ble-reference-text");
const versePreviewText = document.querySelector("#verse-preview-text");
const previousPhrase = document.querySelector("#previous-phrase");
const nextPhrase = document.querySelector("#next-phrase");
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
const replaceMessage = document.querySelector("#replace-message");
const replaceEvidence = document.querySelector("#replace-evidence");
const cancelReplace = document.querySelector("#cancel-replace");

let translationPhrases = [
  {
    reference: "Titus 1:1",
    greek: [
      { text: "Παῦλος" },
      { text: "δοῦλος", key: "doulos", strongs: "G1401", lemma: "δοῦλος" },
      { text: "θεοῦ" }
    ],
    prefix: "Pablo ",
    placeholder: "________",
    suffix: " de Dios",
    decisionStrong: "G1401",
    investigationId: "INV-0001",
    sourceTokenIds: ["n56001001001", "n56001001002", "n56001001003"],
    rv1909Text: "PABLO, siervo de Dios",
    bleText: "Pablo siervo de Dios",
    workingText: "PABLO, siervo de Dios",
    suggestionSource: "rv1909"
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "ἀπόστολος", key: "apostolos", strongs: "G652", lemma: "ἀπόστολος" },
      { text: "δὲ" },
      { text: "Ἰησοῦ" },
      { text: "Χριστοῦ" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: " de Jesucristo",
    decisionStrong: "G652",
    investigationId: "INV-0002",
    sourceTokenIds: ["n56001001004", "n56001001005", "n56001001006", "n56001001007"],
    rv1909Text: "y apóstol de Jesucristo",
    bleText: "apóstol de Jesucristo",
    workingText: "y apóstol de Jesucristo",
    suggestionSource: "rv1909",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "κατὰ" },
      { text: "πίστιν", key: "pistis", strongs: "G4102", lemma: "πίστις", rmac: "N-ASF" },
      { text: "ἐκλεκτῶν" },
      { text: "θεοῦ" }
    ],
    prefix: "según ",
    placeholder: "________",
    suffix: " elegidos de Dios",
    decisionStrong: "G4102",
    investigationId: "INV-0003",
    sourceTokenIds: ["n56001001008", "n56001001009", "n56001001010", "n56001001011"],
    rv1909Text: "según la fe de los escogidos de Dios",
    bleText: "según fe elegidos de Dios",
    workingText: "según la fe de los escogidos de Dios",
    suggestionSource: "rv1909",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "καὶ" },
      { text: "ἐπίγνωσιν" },
      { text: "ἀληθείας" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: ["n56001001012", "n56001001013", "n56001001014"],
    rv1909Text: "y el conocimiento de la verdad",
    bleText: "y conocimiento verdad",
    workingText: "y el conocimiento de la verdad",
    suggestionSource: "rv1909",
    provisional: true
  },
  {
    reference: "Titus 1:1",
    greek: [
      { text: "τῆς" },
      { text: "κατ’" },
      { text: "εὐσέβειαν" }
    ],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: ["n56001001015", "n56001001016", "n56001001017"],
    rv1909Text: "que es según la piedad",
    bleText: "de la según piedad",
    workingText: "que es según la piedad",
    suggestionSource: "rv1909",
    provisional: true
  }
];
const phraseSeparator = " ";
let translationUnits = [];
let translationUnitsLoaded = false;

const greekKeyByStrong = {
  G1401: "doulos",
  G652: "apostolos",
  G4102: "pistis"
};

const greekWordInfo = {
  doulos: {
    lemma: "δοῦλος",
    strongs: "G1401",
    investigationId: "INV-0001",
    approved: false,
    rendering: "siervo",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "δοῦλος"
  },
  apostolos: {
    lemma: "ἀπόστολος",
    strongs: "G652",
    investigationId: "INV-0002",
    approved: false,
    rendering: "apóstol",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "ἀπόστολος"
  },
  pistis: {
    lemma: "πίστις",
    strongs: "G4102",
    investigationId: "INV-0003",
    approved: false,
    rendering: "fe",
    source: "BLE",
    reference: "Titus 1:1",
    surface: "πίστιν",
    rmac: "N-ASF",
    construction: {
      prepositionSurface: "κατὰ",
      prepositionLemma: "κατά",
      caseCode: "A"
    }
  }
};

function selectedGreekInfo() {
  return greekWordInfo[state.selectedGreekKey]
    || Object.values(greekWordInfo).find(info => info.investigationId === state.investigation)
    || greekWordInfo.doulos;
}

function currentPhrase() {
  return translationPhrases[state.phraseIndex];
}

function defaultTranslationDocument() {
  return translationPhrases.map(phrase => phrase.savedText || "").filter(Boolean).join(phraseSeparator);
}

function phraseGreekText(phrase) {
  return phrase.greek.map(token => token.text).join(" ");
}

function setPhraseSaveStatus(text, stateName = "saved") {
  phraseSaveStatus.textContent = text;
  phraseSaveStatus.dataset.state = stateName;
}

function serializePhraseRecords() {
  return translationPhrases.map((phrase, index) => ({
    reference: phrase.reference,
    phraseIndex: index,
    greek: phraseGreekText(phrase),
    spanish: phrase.savedText || "",
    sourceTokenIds: phrase.sourceTokenIds || [],
    tokenRows: phrase.tokenRows || [],
    rv1909Text: phrase.rv1909Text || "",
    bleText: phrase.bleText || "",
    suggestionSource: phrase.suggestionSource || ""
  }));
}

function makePhraseFromRecord(record) {
  const rv1909Text = String(record.rv1909Text || "");
  const bleText = String(record.bleText || "");
  const savedText = String(record.spanish || "");
  return {
    reference: record.reference || "Titus 1:1",
    greek: [{ text: record.greek || record.reference || "" }],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: Array.isArray(record.sourceTokenIds) ? record.sourceTokenIds : [],
    tokenRows: Array.isArray(record.tokenRows) ? record.tokenRows : [],
    rv1909Text,
    bleText,
    savedText,
    workingText: savedText || rv1909Text || bleText,
    suggestionSource: savedText ? "saved" : (rv1909Text ? "rv1909" : (bleText ? "ble" : "blank")),
    provisional: true
  };
}

function suggestionTextForPhrase(phrase) {
  return phrase.rv1909Text || phrase.bleText || "";
}

function suggestionSourceForPhrase(phrase) {
  if (phrase.approvedDecision) return "Approved LBF decision";
  if (phrase.workingText && phrase.suggestionSource === "saved") return "Saved LBF phrase";
  if (phrase.suggestionSource === "ble") return "Fallback from BLE";
  if (phrase.suggestionSource === "blank") return "Blank";
  return phrase.rv1909Text ? "Draft from RV1909" : (phrase.bleText ? "Fallback from BLE" : "Blank");
}

async function loadContinuationUnits() {
  if (translationUnitsLoaded) return translationUnits;
  const { units } = await api("/api/translation/units").catch(() => ({ units: [] }));
  translationUnits = units.filter(unit => unit.reference !== "Titus 1:1");
  translationUnitsLoaded = true;
  return translationUnits;
}

function makePhraseFromUnit(unit) {
  const rv1909Text = unit.rv1909Text || "";
  const bleText = unit.bleText || "";
  return {
    reference: unit.reference,
    greek: [{ text: unit.greekText || unit.reference }],
    prefix: "",
    placeholder: "________",
    suffix: "",
    decisionStrong: "",
    investigationId: "",
    sourceTokenIds: unit.sourceTokenIds || [],
    tokenRows: unit.tokenRows || [],
    rv1909Text,
    bleText,
    savedText: "",
    workingText: rv1909Text || bleText || "",
    suggestionSource: rv1909Text ? "rv1909" : (bleText ? "ble" : "blank"),
    provisional: true
  };
}

function hasMoreTranslationUnits() {
  if (!translationUnitsLoaded) return true;
  const queuedReferences = new Set(translationPhrases.map(phrase => phrase.reference));
  return translationUnits.some(unit => !queuedReferences.has(unit.reference));
}

async function appendNextTranslationUnit() {
  const units = await loadContinuationUnits();
  const queuedReferences = new Set(translationPhrases.map(phrase => phrase.reference));
  const unit = units.find(item => !queuedReferences.has(item.reference));
  if (!unit) return false;

  const phrase = makePhraseFromUnit(unit);
  translationPhrases = [...translationPhrases, phrase];
  return true;
}

async function enrichPhraseReferencesFromUnits() {
  const units = await loadContinuationUnits();
  const unitsByReference = new Map(units.map(unit => [unit.reference, unit]));
  translationPhrases = translationPhrases.map(phrase => {
    const unit = unitsByReference.get(phrase.reference);
    if (!unit) return phrase;

    const rv1909Text = phrase.rv1909Text || unit.rv1909Text || "";
    const bleText = phrase.bleText || unit.bleText || "";
    return {
      ...phrase,
      sourceTokenIds: phrase.sourceTokenIds?.length ? phrase.sourceTokenIds : (unit.sourceTokenIds || []),
      tokenRows: phrase.tokenRows?.length
        ? phrase.tokenRows
        : (unit.tokenRows || []).filter(row => (phrase.sourceTokenIds || unit.sourceTokenIds || []).includes(row.sourceTokenId)),
      rv1909Text,
      bleText,
      workingText: phrase.workingText || rv1909Text || bleText || "",
      suggestionSource: phrase.workingText
        ? (phrase.suggestionSource || "saved")
        : (rv1909Text ? "rv1909" : (bleText ? "ble" : "blank"))
    };
  });
}

function buildTranslationLine(rendering = "") {
  const phrase = currentPhrase();
  const target = rendering || phrase.placeholder;
  return `${phrase.prefix}${target}${phrase.suffix}`;
}

function getTranslationTargetEnd(rendering = "") {
  const phrase = currentPhrase();
  return phrase.prefix.length + (rendering || phrase.workingText || phrase.placeholder).length;
}

function buildTranslationDocument() {
  return defaultTranslationDocument();
}

function getPhraseEnd(index = state.phraseIndex) {
  return translationPhrases[index].workingText.length;
}

function syncTranslationDocumentFromEditor() {
  currentPhrase().workingText = translationEditor.value;
}

function replacePhraseText(index, text) {
  translationPhrases[index].workingText = text;
  if (index === state.phraseIndex) {
    translationEditor.value = text;
  }
  renderVersePreview();
}

function scheduleTranslationSave() {
  window.clearTimeout(state.translationSaveTimer);
  setPhraseSaveStatus("Unsaved changes", "dirty");
  state.translationSaveTimer = window.setTimeout(() => {
    void saveTranslationDocument().catch(error => {
      setPhraseSaveStatus("Save error", "error");
      prototypeMessage.textContent = error.message || "Translation save error.";
    });
  }, 450);
}

async function saveTranslationDocument() {
  syncTranslationDocumentFromEditor();
  const phrase = currentPhrase();
  const previousSavedText = phrase.savedText || "";
  phrase.savedText = phrase.workingText;
  phrase.suggestionSource = "saved";
  setPhraseSaveStatus("Saving...", "saving");
  state.translationSaving = true;
  try {
    await api("/api/translation/current", {
      method: "PUT",
      body: JSON.stringify({
        content: buildTranslationDocument(),
        phrases: serializePhraseRecords()
      })
    });
    setPhraseSaveStatus("Saved", "saved");
    renderVersePreview();
  } catch (error) {
    phrase.savedText = previousSavedText;
    renderVersePreview();
    throw error;
  } finally {
    state.translationSaving = false;
  }
}

async function flushTranslationSave() {
  window.clearTimeout(state.translationSaveTimer);
  if (state.view === "translation") {
    await saveTranslationDocument();
  }
}

async function loadTranslationDocument() {
  const { content, phrases } = await api("/api/translation/current").catch(() => ({ content: "", phrases: [] }));
  if (Array.isArray(phrases) && phrases.length) {
    phrases
      .sort((a, b) => Number(a.phraseIndex || 0) - Number(b.phraseIndex || 0))
      .forEach(record => {
        const index = Number(record.phraseIndex);
        if (!Number.isInteger(index) || index < 0) return;
        if (!translationPhrases[index]) {
          translationPhrases[index] = makePhraseFromRecord(record);
        }
        const savedText = String(record.spanish || "");
        const rv1909Text = String(record.rv1909Text || translationPhrases[index].rv1909Text || "");
        const bleText = String(record.bleText || translationPhrases[index].bleText || "");
        translationPhrases[index] = {
          ...translationPhrases[index],
          sourceTokenIds: Array.isArray(record.sourceTokenIds) && record.sourceTokenIds.length
            ? record.sourceTokenIds
            : (translationPhrases[index].sourceTokenIds || []),
          tokenRows: Array.isArray(record.tokenRows) && record.tokenRows.length
            ? record.tokenRows
            : (translationPhrases[index].tokenRows || []),
          rv1909Text,
          bleText,
          savedText,
          workingText: savedText || rv1909Text || bleText || "",
          suggestionSource: savedText
            ? "saved"
            : (rv1909Text ? "rv1909" : (bleText ? "ble" : "blank"))
        };
      });
    state.translationLoadedFromDisk = true;
    return;
  }

  const saved = String(content || "").trim();
  if (!saved) return;
  translationPhrases[0].workingText = saved;
  translationPhrases[0].savedText = saved;
  translationPhrases[0].suggestionSource = "saved";
  state.translationLoadedFromDisk = true;
}

function renderPhraseInterlinear() {
  phraseInterlinear.replaceChildren();
  const rows = currentPhrase().tokenRows || [];
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.textContent = "—";
    phraseInterlinear.append(empty);
    return;
  }

  rows.forEach(token => {
    const item = document.createElement("div");
    item.className = "interlinear-token";

    const greekLine = document.createElement("div");
    greekLine.className = "interlinear-greek";
    const tokenInfo = Object.entries(greekWordInfo).find(([, info]) => info.surface === token.greek);
    if (tokenInfo) {
      const [key, info] = tokenInfo;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `greek-word-trigger ${info.approved ? "approved" : "provisional"}`;
      button.dataset.greekKey = key;
      button.textContent = token.greek;
      greekLine.append(button);
    } else {
      greekLine.textContent = token.greek || "—";
    }

    const bleLine = document.createElement("div");
    bleLine.className = "interlinear-ble";
    bleLine.textContent = token.ble || "—";

    const rmacLine = document.createElement("div");
    rmacLine.className = "interlinear-rmac";
    rmacLine.textContent = token.rmac || "—";

    item.append(greekLine, bleLine, rmacLine);
    phraseInterlinear.append(item);
  });
}

function saveCurrentPhraseText() {
  syncTranslationDocumentFromEditor();
  renderVersePreview();
}

function renderVersePreview() {
  const reference = currentPhrase().reference || "Titus 1:1";
  const parts = translationPhrases
    .filter(phrase => phrase.reference === reference)
    .map(phrase => {
      const saved = String(phrase.savedText || "").trim();
      return saved || "[incomplete]";
    });
  versePreviewText.textContent = parts.length ? parts.join(phraseSeparator) : "—";
}

function renderTranslationPhrase({ focus = false, cursorPosition = null } = {}) {
  renderPhraseInterlinear();
  const phrase = currentPhrase();
  const reference = phrase.reference || "Titus 1:1";
  const phraseNumber = translationPhrases
    .filter(item => item.reference === reference)
    .findIndex(item => item === phrase) + 1;
  translationReferenceTitle.textContent = `${reference} · Phrase ${phraseNumber || state.phraseIndex + 1}`;
  translationReferenceMeta.textContent = reference;
  suggestionSourceLabel.textContent = suggestionSourceForPhrase(phrase);
  rv1909ReferenceText.textContent = phrase.rv1909Text || "—";
  bleReferenceText.textContent = phrase.bleText || "—";
  if (translationEditor.value !== phrase.workingText) {
    translationEditor.value = phrase.workingText;
  }
  renderVersePreview();
  setPhraseSaveStatus(phrase.savedText ? "Saved" : "Unsaved changes", phrase.savedText ? "saved" : "dirty");
  previousPhrase.disabled = state.phraseIndex === 0;
  nextPhrase.disabled = state.phraseIndex === translationPhrases.length - 1 && !hasMoreTranslationUnits();
  nextPhrase.textContent = nextPhrase.disabled ? "End of Available Text" : "Next Phrase";
  decisionPanel.hidden = true;

  if (focus) {
    const position = cursorPosition ?? translationEditor.value.length;
    placeTranslationCursor(position);
  }
}

function captureTranslationReturnPoint() {
  state.translationReturn = {
    phraseIndex: state.phraseIndex,
    scrollTop: translationView.scrollTop,
    selectionStart: translationEditor.selectionStart ?? getTranslationTargetEnd(),
    selectionEnd: translationEditor.selectionEnd ?? getTranslationTargetEnd()
  };
}

function placeTranslationCursor(position) {
  translationEditor.focus();
  translationEditor.setSelectionRange(position, position);
}

function showTranslationView({ focusTranslation = false, cursorPosition = null } = {}) {
  state.view = "translation";
  translationView.hidden = false;
  investigationView.hidden = true;
  sidebar.hidden = true;
  setInvestigationListOpen(false);
  window.history.pushState(null, "", window.location.pathname);
  if (state.translationReturn?.phraseIndex != null) {
    state.phraseIndex = state.translationReturn.phraseIndex;
    renderTranslationPhrase();
  }
  translationView.scrollTop = state.translationReturn?.scrollTop || 0;
  if (focusTranslation) {
    placeTranslationCursor(cursorPosition ?? state.translationReturn?.selectionEnd ?? getTranslationTargetEnd());
    requestAnimationFrame(() => {
      translationView.scrollTop = state.translationReturn?.scrollTop || 0;
    });
  } else {
    translationEditor.focus();
  }
}

function showInvestigationView() {
  state.view = "investigation";
  translationView.hidden = true;
  investigationView.hidden = false;
  sidebar.hidden = false;
  window.location.hash = `investigation/${state.investigation}`;
}

function setStatus(text, stateName = "saved") {
  saveStatus.textContent = text;
  saveStatus.dataset.state = stateName;
}

function positionDecisionPanel(anchor) {
  const anchorRect = anchor.getBoundingClientRect();
  const panelRect = decisionPanel.getBoundingClientRect();
  const margin = 12;
  const viewportPadding = 12;
  let left = anchorRect.left + (anchorRect.width / 2) - (panelRect.width / 2);
  let top = anchorRect.bottom + margin;

  left = Math.max(viewportPadding, Math.min(left, window.innerWidth - panelRect.width - viewportPadding));

  if (top + panelRect.height + viewportPadding > window.innerHeight) {
    top = anchorRect.top - panelRect.height - margin;
  }

  top = Math.max(viewportPadding, top);
  decisionPanel.style.left = `${left}px`;
  decisionPanel.style.top = `${top}px`;
}

function hideGreekDecisionPanel() {
  decisionPanel.hidden = true;
}

function showGreekDecisionPanel(key, anchor) {
  const info = greekWordInfo[key];
  if (!info) return;

  state.selectedGreekKey = key;
  decisionPanel.hidden = false;
  decisionPanel.querySelector("dd").textContent = `${info.strongs} — ${info.lemma}`;
  decisionPanelPolicy.textContent = info.approved
    ? info.rendering
    : `${info.rendering || "—"} (${info.source || "unresolved"})`;
  decisionPanelStatus.textContent = info.approved ? "Approved decision" : "Provisional";
  openInvestigationButton.textContent = info.approved ? "View Decision" : "Open Investigation";
  positionDecisionPanel(anchor);
}

function applyDecisionToTranslation(decision) {
  if (decision?.status !== "Approved" || !decision.preferredRendering) return;

  const greekKey = greekKeyByStrong[decision.strongs];
  const alreadyApplied = greekKey
    && greekWordInfo[greekKey]?.approved
    && greekWordInfo[greekKey]?.source === `Decision ${decision.version}`;
  if (greekKey && greekWordInfo[greekKey]) {
    greekWordInfo[greekKey] = {
      ...greekWordInfo[greekKey],
      approved: true,
      rendering: decision.preferredRendering,
      source: `Decision ${decision.version}`
    };
  }

  const decisionPhrase = translationPhrases.find(phrase => phrase.decisionStrong === decision.strongs);
  if (decisionPhrase && !alreadyApplied) {
    const phraseIndex = translationPhrases.indexOf(decisionPhrase);
    decisionPhrase.approvedDecision = true;
    decisionPhrase.suggestionSource = "approved";
    replacePhraseText(phraseIndex, `${decisionPhrase.prefix}${decision.preferredRendering}${decisionPhrase.suffix}`);
  }
}

async function loadApprovedDecisions({ applyToText = !state.translationLoadedFromDisk } = {}) {
  const { investigations } = await api("/api/investigations");
  const decisions = [];

  for (const id of investigations) {
    const { decision } = await api(`/api/investigations/${id}/decision`).catch(() => ({ decision: null }));
    if (decision?.status === "Approved" && decision.preferredRendering) {
      decisions.push(decision);
      if (applyToText) {
        applyDecisionToTranslation(decision);
      } else {
        const greekKey = greekKeyByStrong[decision.strongs];
        if (greekKey && greekWordInfo[greekKey]) {
          greekWordInfo[greekKey] = {
            ...greekWordInfo[greekKey],
            approved: true,
            rendering: decision.preferredRendering,
            source: `Decision ${decision.version}`
          };
        }
      }
    }
  }

  if (!currentPhrase().workingText) {
    const suggestion = suggestionTextForPhrase(currentPhrase());
    currentPhrase().workingText = suggestion || buildTranslationLine();
    currentPhrase().suggestionSource = currentPhrase().rv1909Text
      ? "rv1909"
      : (currentPhrase().bleText ? "ble" : "blank");
  }
  renderTranslationPhrase();
  return decisions.find(decision => decision.strongs === currentPhrase().decisionStrong) || null;
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

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderInlineMarkdown(value) {
  const escaped = escapeHtml(value);
  return escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function appendMarkdownParagraph(parent, line) {
  const fieldMatch = line.match(/^([^:]+):\s*(.*)$/u);
  const paragraph = document.createElement("p");

  if (fieldMatch) {
    paragraph.className = "evidence-line";
    const label = document.createElement("strong");
    label.textContent = `${fieldMatch[1]}:`;
    paragraph.append(label, " ");
    const value = document.createElement("span");
    value.innerHTML = renderInlineMarkdown(fieldMatch[2]);
    paragraph.append(value);
  } else {
    paragraph.innerHTML = renderInlineMarkdown(line);
  }

  parent.append(paragraph);
}

function splitMarkdownTableRow(line) {
  const cells = line.trim().split("|");
  if (cells[0] === "") cells.shift();
  if (cells[cells.length - 1] === "") cells.pop();
  return cells.map(cell => cell.trim());
}

function isMarkdownTableSeparator(line) {
  return splitMarkdownTableRow(line).every(cell => /^:?-{3,}:?$/u.test(cell));
}

function appendMarkdownTable(parent, lines) {
  const [headerLine, , ...bodyLines] = lines;
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  const headerRow = document.createElement("tr");

  for (const cell of splitMarkdownTableRow(headerLine)) {
    const th = document.createElement("th");
    th.innerHTML = renderInlineMarkdown(cell);
    headerRow.append(th);
  }
  thead.append(headerRow);

  for (const line of bodyLines) {
    const row = document.createElement("tr");
    for (const cell of splitMarkdownTableRow(line)) {
      const td = document.createElement("td");
      td.innerHTML = renderInlineMarkdown(cell);
      row.append(td);
    }
    tbody.append(row);
  }

  table.append(thead, tbody);
  parent.append(table);
}

function renderEvidenceMarkdown(markdown) {
  const fragment = document.createDocumentFragment();
  const stack = [fragment];
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");

  const currentParent = () => stack[stack.length - 1];

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trim();
    if (!line) continue;

    if (
      line.startsWith("|")
      && lines[index + 1]?.trim().startsWith("|")
      && isMarkdownTableSeparator(lines[index + 1])
    ) {
      const tableLines = [line, lines[index + 1].trim()];
      index += 2;
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        tableLines.push(lines[index].trim());
        index += 1;
      }
      index -= 1;
      appendMarkdownTable(currentParent(), tableLines);
      continue;
    }

    if (line === "<details>") {
      const details = document.createElement("details");
      details.className = "usage-block";
      currentParent().append(details);
      stack.push(details);
      continue;
    }

    if (line === "</details>") {
      if (stack.length > 1) stack.pop();
      continue;
    }

    const summaryMatch = line.match(/^<summary>(.*)<\/summary>$/u);
    if (summaryMatch) {
      const summary = document.createElement("summary");
      summary.textContent = summaryMatch[1];
      currentParent().append(summary);
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/u);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length, 4);
      const heading = document.createElement(`h${level}`);
      heading.textContent = headingMatch[2];
      currentParent().append(heading);
      continue;
    }

    if (line === "---") {
      currentParent().append(document.createElement("hr"));
      continue;
    }

    appendMarkdownParagraph(currentParent(), line.replace(/\s{2}$/u, ""));
  }

  evidenceViewer.replaceChildren(fragment);
}

function showEditor() {
  editor.hidden = false;
  evidenceViewer.hidden = true;
  decisionEditor.hidden = true;
}

function showEvidenceViewer() {
  editor.hidden = true;
  evidenceViewer.hidden = false;
  decisionEditor.hidden = true;
}

function showDecisionEditor() {
  editor.hidden = true;
  evidenceViewer.hidden = true;
  decisionEditor.hidden = false;
}

function fillDecisionForm(decision) {
  state.decision = decision;
  decisionStatus.value = decision.status || "Draft";
  decisionVersion.value = decision.version || "1.0";
  decisionEffectiveDate.value = decision.effectiveDate || "";
  decisionLemma.value = decision.lemma || "δοῦλος";
  decisionStrongs.value = decision.strongs || "G1401";
  decisionRendering.value = decision.preferredRendering || "";
  decisionConfidence.value = decision.confidence || "Medium";
  decisionReason.value = decision.reason || "";
  approveDecision.disabled = decision.status === "Approved";
  decisionStatus.disabled = decision.status === "Approved" || decision.status === "Superseded";
}

function readDecisionForm() {
  return {
    status: decisionStatus.value,
    effectiveDate: decisionEffectiveDate.value,
    preferredRendering: decisionRendering.value,
    confidence: decisionConfidence.value,
    reason: decisionReason.value
  };
}

async function saveDecision(action = "save") {
  const { decision } = await api(`/api/investigations/${state.investigation}/decision`, {
    method: "PUT",
    body: JSON.stringify({ ...readDecisionForm(), action })
  });
  fillDecisionForm(decision);
  state.dirty = false;
  setStatus(action === "approve" ? "Approved" : "Saved", "saved");
  await loadInvestigationMeta();
  await loadApprovedDecisions({ applyToText: action === "approve" });
  scheduleTranslationSave();
}

async function returnToTranslation() {
  await saveCurrent();
  const decision = await loadApprovedDecisions({ applyToText: true });
  await saveTranslationDocument();
  const approvedRendering = decision?.status === "Approved" ? decision.preferredRendering : "";
  const cursorPosition = approvedRendering
    ? getTranslationTargetEnd(approvedRendering)
    : state.translationReturn?.selectionEnd ?? getTranslationTargetEnd();
  showTranslationView({ focusTranslation: true, cursorPosition });
}

async function movePhrase(direction) {
  try {
    await flushTranslationSave();
  } catch (error) {
    setPhraseSaveStatus("Save error", "error");
    prototypeMessage.textContent = error.message || "Translation save error.";
    return;
  }
  let nextIndex = state.phraseIndex + direction;
  if (direction > 0 && nextIndex >= translationPhrases.length) {
    const appended = await appendNextTranslationUnit();
    if (!appended) {
      renderTranslationPhrase();
      return;
    }
    nextIndex = state.phraseIndex + direction;
  }
  if (nextIndex < 0 || nextIndex >= translationPhrases.length) return;
  state.phraseIndex = nextIndex;
  state.translationReturn = {
    phraseIndex: state.phraseIndex,
    scrollTop: translationView.scrollTop,
    selectionStart: 0,
    selectionEnd: 0
  };
  renderTranslationPhrase();
  translationEditor.focus();
  placeTranslationCursor(getPhraseEnd());
}

async function saveCurrent() {
  if (state.evidenceFile || !state.dirty || state.saving) return;
  state.saving = true;
  saveButton.disabled = true;
  setStatus("Saving...", "saving");

  try {
    if (state.tab.file === "decision.md") {
      await saveDecision();
    } else {
      await api(`/api/investigations/${state.investigation}/files/${encodeURIComponent(state.tab.file)}`, {
        method: "PUT",
        body: JSON.stringify({ content: editor.value })
      });
      state.dirty = false;
      setStatus("Saved", "saved");
    }
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
  if (state.view === "translation") {
    saveCurrentPhraseText();
    captureTranslationReturnPoint();
    await flushTranslationSave();
  }
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
  if (state.tab.file === "decision.md") {
    showDecisionEditor();
    saveButton.disabled = false;
    setStatus("Loading...", "saving");
    prototypeMessage.textContent = "";
    const { decision } = await api(`/api/investigations/${state.investigation}/decision`);
    fillDecisionForm(decision);
    state.dirty = false;
    setStatus("Saved", "saved");
    decisionRendering.focus();
    await renderEvidenceFiles();
    return;
  }

  showEditor();
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
  renderEvidenceMarkdown(content);
  state.dirty = false;
  showEvidenceViewer();
  editor.disabled = false;
  evidenceViewer.focus();
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
  const activeInfo = Object.entries(greekWordInfo).find(([, info]) => info.investigationId === state.investigation);
  if (activeInfo) {
    state.selectedGreekKey = activeInfo[0];
  }
  const info = selectedGreekInfo();
  const constructionInput = document.querySelector("input[name='gather-type'][value='construction']");
  if (constructionInput) {
    constructionInput.disabled = !info.construction;
    if (constructionInput.disabled && constructionInput.checked) {
      document.querySelector("input[name='gather-type'][value='occurrences']").checked = true;
    }
  }
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

function buildGatherPayload(type, replace) {
  const info = selectedGreekInfo();
  return {
    type,
    replace,
    reference: info.reference || "Titus 1:1",
    surface: info.surface || "",
    lemma: info.lemma || "",
    strongs: info.strongs || "",
    rmac: info.rmac || "",
    prepositionSurface: info.construction?.prepositionSurface || "",
    prepositionLemma: info.construction?.prepositionLemma || "",
    caseCode: info.construction?.caseCode || ""
  };
}

function selectedGatherType() {
  return document.querySelector("input[name='gather-type']:checked")?.value || "occurrences";
}

async function runEvidenceGather({ replace = false } = {}) {
  const type = selectedGatherType();
  const labels = {
    occurrence: "occurrence",
    occurrences: "lemma",
    construction: "construction"
  };
  gatherMessage.textContent = replace
    ? `Replacing ${labels[type] || "evidence"} evidence...`
    : `Gathering ${labels[type] || "evidence"} evidence...`;
  runGather.disabled = true;
  replaceEvidence.disabled = true;

  try {
    await api(`/api/investigations/${state.investigation}/gather`, {
      method: "POST",
      body: JSON.stringify(buildGatherPayload(type, replace))
    });
    prototypeMessage.textContent = "Evidence gathered.";
    closeGatherModal();
    await renderEvidenceFiles();
    if (state.tab.file === "history.md") {
      await loadCurrentFile();
    }
  } catch (error) {
    if (error.code === "EVIDENCE_EXISTS") {
      gatherMessage.textContent = "";
      replaceMessage.textContent = `${error.fileName || "Evidence"} already exists.`;
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

translationEditor.addEventListener("input", () => {
  syncTranslationDocumentFromEditor();
  renderVersePreview();
  scheduleTranslationSave();
});

[
  decisionStatus,
  decisionEffectiveDate,
  decisionRendering,
  decisionConfidence,
  decisionReason
].forEach(control => {
  control.addEventListener("input", () => {
    state.dirty = true;
    setStatus("Unsaved changes", "dirty");
  });
});

saveButton.addEventListener("click", () => {
  void saveCurrent().catch(() => {});
});

approveDecision.addEventListener("click", () => {
  void (async () => {
    await saveDecision("approve");
    prototypeMessage.textContent = "Decision approved.";
  })().catch(error => {
    prototypeMessage.textContent = error.message || "Decision approval error.";
  });
});

phraseInterlinear.addEventListener("click", event => {
  if (event.target instanceof HTMLElement && event.target.dataset.greekKey) {
    event.stopPropagation();
    showGreekDecisionPanel(event.target.dataset.greekKey, event.target);
  }
});

openInvestigationButton.addEventListener("click", () => {
  const info = greekWordInfo[state.selectedGreekKey];
  if (info?.investigationId) {
    void openInvestigation(info.investigationId);
    return;
  }

  prototypeMessage.textContent = "No investigation has been created for this word yet.";
});

document.addEventListener("click", event => {
  if (decisionPanel.hidden) return;
  if (event.target instanceof Node && decisionPanel.contains(event.target)) return;
  hideGreekDecisionPanel();
});

translationView.addEventListener("scroll", hideGreekDecisionPanel);
window.addEventListener("resize", hideGreekDecisionPanel);

investigationToggle.addEventListener("click", () => {
  setInvestigationListOpen(!document.body.classList.contains("investigations-open"));
});

gatherEvidence.addEventListener("click", () => {
  openGatherModal();
});

backToTranslation.addEventListener("click", () => {
  void returnToTranslation().catch(error => {
    prototypeMessage.textContent = error.message || "Return error.";
  });
});

previousPhrase.addEventListener("click", () => {
  void movePhrase(-1);
});

nextPhrase.addEventListener("click", () => {
  void movePhrase(1);
});

runGather.addEventListener("click", () => {
  void runEvidenceGather().catch(() => {});
});

replaceEvidence.addEventListener("click", () => {
  void runEvidenceGather({ replace: true }).catch(() => {});
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
    if (state.view === "translation") {
      void flushTranslationSave();
    } else {
      void saveCurrent();
    }
  }
});

window.addEventListener("beforeunload", event => {
  if (state.view === "translation") {
    syncTranslationDocumentFromEditor();
    navigator.sendBeacon?.(
      "/api/translation/current",
      new Blob([JSON.stringify({
        content: buildTranslationDocument(),
        phrases: serializePhraseRecords()
      })], { type: "application/json" })
    );
  }

  if (!state.dirty) return;
  event.preventDefault();
});

async function openInitialRoute() {
  if (window.location.hash.startsWith("#investigation/")) {
    await openInvestigation(readInvestigationIdFromHash());
    return;
  }

  showTranslationView();
}

function readInvestigationIdFromHash() {
  const match = window.location.hash.match(/^#investigation\/(INV-\d{4})$/);
  return match?.[1] || "INV-0001";
}

window.addEventListener("hashchange", () => {
  if (window.location.hash.startsWith("#investigation/")) {
    void openInvestigation(readInvestigationIdFromHash()).catch(error => {
      prototypeMessage.textContent = error.message || "Investigation load error.";
    });
  }
});

await loadInvestigations();
renderTabs();
await loadTranslationDocument();
await enrichPhraseReferencesFromUnits();
renderTranslationPhrase();
await loadApprovedDecisions({ applyToText: !state.translationLoadedFromDisk });
await openInitialRoute();
