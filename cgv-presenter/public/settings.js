const viewScopes = [
  { key: "main", labelKey: "mainView" },
  { key: "presenter", labelKey: "presenterViewSettings" },
  { key: "audience", labelKey: "audienceViewWeb" }
];

const styleKeys = [
  { key: "h1", labelKey: "h1MainTitles", fields: ["size", "color"] },
  { key: "h2", labelKey: "h2Subtitles", fields: ["size", "color"] },
  { key: "h3", labelKey: "h3BibleReference", fields: ["size", "color", "indent"] },
  { key: "scripture", labelKey: "scriptureUnderH3", fields: ["size", "color", "indent", "lineHeight"] },
  { key: "h4", labelKey: "h4ScriptureAnchor", fields: ["size", "color", "indent"] },
  { key: "h5", labelKey: "h5FirstComment", fields: ["size", "color", "indent"] },
  { key: "h6", labelKey: "h6SecondComment", fields: ["size", "color", "indent"] },
  { key: "bullet", labelKey: "bulletComments", fields: ["size", "color", "indent"] },
  { key: "reference", labelKey: "bibleReferenceLinks", fields: ["color"] }
];

const synthesisFields = [
  ["background", "boxBackground"],
  ["color", "textColor"],
  ["accent", "accentColor"],
  ["titleColor", "titleColor"],
  ["textSize", "textSize"]
];

const definitionFields = [
  ["background", "background"],
  ["accent", "accentColor"],
  ["termColor", "termColor"],
  ["textColor", "definitionText"]
];

const popupFields = [
  ["background", "popupBackground"],
  ["color", "popupText"],
  ["verseBackground", "verseBackground"],
  ["accent", "accentColor"],
  ["referenceColor", "referenceLabel"],
  ["textSize", "textSize"]
];

const builtInThemes = window.CGV_STYLE_THEMES || [];
let availableBibleVersions = ["NBLA"];
let availableBackgrounds = [];
let bibleStatus = null;

let settings = {
  language: "es",
  bibleVersion: "NBLA",
  blankBackgroundMedia: "",
  theme: "",
  styles: { main: {}, presenter: {}, audience: {} },
  customThemes: []
};

function safeThemeId(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function getCustomThemes(rawSettings = settings) {
  return Array.isArray(rawSettings.customThemes) ? rawSettings.customThemes : [];
}

function getAvailableThemes() {
  return [
    ...builtInThemes.map(theme => ({ ...theme, builtIn: true })),
    ...getCustomThemes().map(theme => ({ ...theme, builtIn: false }))
  ];
}

function normalizeBibleVersion(value) {
  return String(value || "NBLA")
    .trim()
    .replace(/[^A-Za-z0-9_-]/g, "")
    .toUpperCase() || "NBLA";
}

function normalizeSettings(rawSettings) {
  const styles = rawSettings.styles || {};
  const customThemes = getCustomThemes(rawSettings);
  const language = ["es", "en"].includes(rawSettings.language) ? rawSettings.language : "es";
  const bibleVersion = normalizeBibleVersion(rawSettings.bibleVersion);
  const blankBackgroundMedia = String(rawSettings.blankBackgroundMedia || "");

  if (styles.main || styles.presenter || styles.audience) {
    return {
      language,
      bibleVersion,
      blankBackgroundMedia,
      theme: rawSettings.theme || "",
      customThemes,
      styles: {
        main: styles.main || {},
        presenter: styles.presenter || styles.main || {},
        audience: styles.audience || styles.main || {}
      }
    };
  }

  return {
    language,
    bibleVersion,
    blankBackgroundMedia,
    theme: rawSettings.theme || "",
    customThemes,
    styles: {
      main: styles,
      presenter: JSON.parse(JSON.stringify(styles)),
      audience: JSON.parse(JSON.stringify(styles))
    }
  };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function inputType(field) {
  return field.toLowerCase().includes("color") ||
    field === "background" ||
    field === "accent" ||
    field === "termColor" ||
    field === "textColor"
    ? "color"
    : "text";
}

function fieldLabel(field) {
  const labels = {
    size: "textSize",
    color: "textColor",
    indent: "indent",
    lineHeight: "lineHeight"
  };
  return labels[field] ? t(labels[field]) : field.charAt(0).toUpperCase() + field.slice(1);
}

function getValue(scope, sectionKey, field) {
  if (sectionKey === "background") {
    return settings.styles?.[scope]?.background || "";
  }

  return settings.styles?.[scope]?.[sectionKey]?.[field] || "";
}

function createInput(scope, sectionKey, field, labelText = fieldLabel(field)) {
  const value = getValue(scope, sectionKey, field);
  const label = document.createElement("label");
  const input = document.createElement("input");

  label.textContent = labelText;
  input.dataset.scope = scope;
  input.dataset.section = sectionKey;
  input.dataset.field = field;
  input.type = inputType(field);
  input.value = input.type === "color" && !value ? "#ffffff" : value;

  label.appendChild(input);
  return label;
}

function renderStyleSection(scope, section) {
  const wrapper = document.createElement("section");
  const grid = document.createElement("div");
  const heading = document.createElement("h3");

  wrapper.className = "settings-section nested";
  grid.className = "field-grid";
  heading.textContent = section.labelKey ? t(section.labelKey) : section.label;

  section.fields.forEach(field => {
    grid.appendChild(createInput(scope, section.key, field));
  });

  wrapper.append(heading, grid);
  return wrapper;
}

function renderSynthesisSection(scope) {
  const wrapper = document.createElement("section");
  const grid = document.createElement("div");
  const heading = document.createElement("h3");

  wrapper.className = "settings-section nested";
  grid.className = "field-grid";
  heading.textContent = "En Síntesis";

  synthesisFields.forEach(([field, labelKey]) => {
    grid.appendChild(createInput(scope, "synthesis", field, t(labelKey)));
  });

  wrapper.append(heading, grid);
  return wrapper;
}

function renderDefinitionSection(scope) {
  const wrapper = document.createElement("section");
  const grid = document.createElement("div");
  const heading = document.createElement("h3");

  wrapper.className = "settings-section nested";
  grid.className = "field-grid";
  heading.textContent = t("definitions");

  definitionFields.forEach(([field, labelKey]) => {
    grid.appendChild(createInput(scope, "definition", field, t(labelKey)));
  });

  wrapper.append(heading, grid);
  return wrapper;
}

function renderPopupSection(scope) {
  const wrapper = document.createElement("section");
  const grid = document.createElement("div");
  const heading = document.createElement("h3");

  wrapper.className = "settings-section nested";
  grid.className = "field-grid";
  heading.textContent = t("biblePopup");

  popupFields.forEach(([field, labelKey]) => {
    grid.appendChild(createInput(scope, "popup", field, t(labelKey)));
  });

  wrapper.append(heading, grid);
  return wrapper;
}

function renderSettings() {
  const form = document.getElementById("settingsForm");
  form.innerHTML = "";
  form.dataset.settingsSection = "style";
  renderLanguageSelect();
  renderBibleVersionSelect();
  renderBlankBackgroundSelect();
  renderThemeSelect();

  viewScopes.forEach(scope => {
    const group = document.createElement("section");
    const heading = document.createElement("h2");
    const backgroundSection = {
      key: "background",
      labelKey: "viewBackground",
      fields: ["color"]
    };

    group.className = "view-group";
    heading.textContent = t(scope.labelKey);
    group.appendChild(heading);
    group.appendChild(renderStyleSection(scope.key, backgroundSection));

    styleKeys.forEach(section => {
      group.appendChild(renderStyleSection(scope.key, section));
    });

    group.appendChild(renderSynthesisSection(scope.key));
    group.appendChild(renderDefinitionSection(scope.key));
    group.appendChild(renderPopupSection(scope.key));
    form.appendChild(group);
  });

  scrollToRequestedSection();
}

function scrollToRequestedSection() {
  const requested = window.location.hash.replace(/^#/, "") || "style";
  const target = requested === "language"
    ? document.getElementById("language-settings")
    : document.getElementById("style-settings");

  if (!target) return;

  requestAnimationFrame(() => {
    target.scrollIntoView({ block: "start" });
  });
}

function renderLanguageSelect() {
  const select = document.getElementById("languageSelect");
  if (!select) return;

  select.value = settings.language || "es";
  document.documentElement.lang = settings.language || "es";
}

function renderBibleVersionSelect() {
  const select = document.getElementById("bibleVersionSelect");
  if (!select) return;

  select.replaceChildren();
  const versions = Array.from(new Set([settings.bibleVersion || "NBLA", ...availableBibleVersions]))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));

  versions.forEach(version => {
    const option = document.createElement("option");
    option.value = version;
    option.textContent = version;
    select.appendChild(option);
  });

  select.value = settings.bibleVersion || "NBLA";
  renderBibleStatus();
}

function renderBibleStatus() {
  const status = document.getElementById("bibleStatusText");
  const button = document.getElementById("installBibleButton");
  if (!status || !button) return;

  if (!bibleStatus) {
    status.textContent = "";
    button.disabled = true;
    return;
  }

  const version = normalizeBibleVersion(document.getElementById("bibleVersionSelect")?.value || settings.bibleVersion);
  const isSelectedStatus = normalizeBibleVersion(bibleStatus.version) === version;

  if (isSelectedStatus && bibleStatus.loaded) {
    status.textContent = t("bibleInstalled", {
      version,
      books: bibleStatus.books,
      references: bibleStatus.references
    });
  } else if (availableBibleVersions.includes(version)) {
    status.textContent = t("bibleAvailableToInstall", { version });
  } else {
    status.textContent = t("bibleNotFound", { version });
  }

  button.disabled = !availableBibleVersions.includes(version);
}

function renderBlankBackgroundSelect() {
  const select = document.getElementById("blankBackgroundSelect");
  if (!select) return;

  const selected = settings.blankBackgroundMedia || "";
  select.replaceChildren();

  const noneOption = document.createElement("option");
  noneOption.value = "";
  noneOption.textContent = t("none");
  select.appendChild(noneOption);

  availableBackgrounds.forEach(background => {
    const option = document.createElement("option");
    option.value = background.url;
    option.textContent = background.name;
    select.appendChild(option);
  });

  select.value = selected;
}

function renderThemeSelect() {
  const select = document.getElementById("themeSelect");
  if (!select) return;

  select.replaceChildren();
  getAvailableThemes().forEach(theme => {
    const option = document.createElement("option");
    option.value = theme.id;
    option.textContent = theme.builtIn ? theme.name : `${theme.name} (${t("customTheme")})`;
    select.appendChild(option);
  });

  if (settings.theme && getAvailableThemes().some(theme => theme.id === settings.theme)) {
    select.value = settings.theme;
  }
}

function collectSettings() {
  const nextSettings = {
    language: document.getElementById("languageSelect")?.value || settings.language || "es",
    bibleVersion: document.getElementById("bibleVersionSelect")?.value || settings.bibleVersion || "NBLA",
    blankBackgroundMedia: document.getElementById("blankBackgroundSelect")?.value || "",
    theme: document.getElementById("themeSelect")?.value || settings.theme || "",
    customThemes: getCustomThemes(),
    styles: { main: {}, presenter: {}, audience: {} }
  };

  document.querySelectorAll("[data-scope][data-section][data-field]").forEach(input => {
    const scope = input.dataset.scope;
    const section = input.dataset.section;
    const field = input.dataset.field;
    const value = input.value.trim();

    if (section === "background") {
      if (value) nextSettings.styles[scope].background = value;
      return;
    }

    if (!nextSettings.styles[scope][section]) nextSettings.styles[scope][section] = {};
    if (value) nextSettings.styles[scope][section][field] = value;
  });

  return nextSettings;
}

function applySelectedTheme() {
  const select = document.getElementById("themeSelect");
  const theme = getAvailableThemes().find(item => item.id === select?.value);
  if (!theme) return;

  const currentCustomThemes = getCustomThemes();
  settings = normalizeSettings({
    ...clone(theme.settings),
    language: settings.language || "es",
    bibleVersion: settings.bibleVersion || "NBLA",
    blankBackgroundMedia: settings.blankBackgroundMedia || "",
    customThemes: currentCustomThemes
  });
  renderSettings();
  document.getElementById("statusText").textContent = t("themeApplied", { name: theme.name });
}

function saveCurrentAsTheme() {
  const status = document.getElementById("statusText");
  const nameInput = document.getElementById("themeNameInput");
  const themeName = nameInput?.value.trim() || window.prompt("Theme name");
  if (!themeName) return;

  const id = safeThemeId(themeName);
  if (!id) {
    status.textContent = t("themeNeedsName");
    return;
  }

  if (builtInThemes.some(theme => theme.id === id)) {
    status.textContent = t("reservedThemeName");
    return;
  }

  const current = collectSettings();
  const customThemes = getCustomThemes()
    .filter(theme => theme.id !== id);
  const theme = {
    id,
    name: themeName.trim(),
    description: t("customThemeDescription"),
    settings: {
      language: current.language || "es",
      bibleVersion: current.bibleVersion || "NBLA",
      blankBackgroundMedia: current.blankBackgroundMedia || "",
      theme: id,
      styles: clone(current.styles)
    }
  };

  settings = {
    ...current,
    theme: id,
    customThemes: [...customThemes, theme]
  };

  renderSettings();
  const nextNameInput = document.getElementById("themeNameInput");
  if (nextNameInput) nextNameInput.value = theme.name;
  status.textContent = t("themeSaved", { name: theme.name });
}

async function loadSettings() {
  const [settingsResponse, bibleVersionsResponse, backgroundsResponse, bibleStatusResponse] = await Promise.all([
    fetch("/style-settings"),
    fetch("/bible/versions").catch(() => null),
    fetch("/backgrounds").catch(() => null),
    fetch("/bible/status").catch(() => null)
  ]);

  if (bibleVersionsResponse?.ok) {
    const bibleVersions = await bibleVersionsResponse.json();
    availableBibleVersions = Array.isArray(bibleVersions.versions) && bibleVersions.versions.length
      ? bibleVersions.versions.map(normalizeBibleVersion)
      : ["NBLA"];
  }

  if (backgroundsResponse?.ok) {
    availableBackgrounds = await backgroundsResponse.json();
  }

  if (bibleStatusResponse?.ok) {
    bibleStatus = await bibleStatusResponse.json();
  }

  settings = normalizeSettings(await settingsResponse.json());
  window.CGVI18N.setLanguage(settings.language || "es");
  renderSettings();
}

async function saveSettings() {
  const status = document.getElementById("statusText");
  settings = collectSettings();

  const response = await fetch("/style-settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });

  if (!response.ok) {
    status.textContent = t("couldNotSaveSettings");
    return;
  }

  window.CGVI18N.setLanguage(settings.language || "es");
  status.textContent = `${t("saved")} ${new Date().toLocaleTimeString()}`;
}

async function installSelectedBible() {
  const status = document.getElementById("statusText");
  const version = normalizeBibleVersion(document.getElementById("bibleVersionSelect")?.value || settings.bibleVersion);

  status.textContent = t("installingBible", { version });
  const response = await fetch("/bible/install", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ version })
  });

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    status.textContent = result.error || t("couldNotInstallBible", { version });
    return;
  }

  bibleStatus = result;
  availableBibleVersions = Array.from(new Set([version, ...availableBibleVersions])).sort((a, b) => a.localeCompare(b));
  settings.bibleVersion = version;
  renderBibleVersionSelect();
  status.textContent = t("bibleInstallComplete", { version });
}

document.getElementById("saveButton").addEventListener("click", saveSettings);
document.getElementById("applyThemeButton").addEventListener("click", applySelectedTheme);
document.getElementById("saveThemeButton").addEventListener("click", saveCurrentAsTheme);
document.getElementById("installBibleButton").addEventListener("click", installSelectedBible);
document.getElementById("languageSelect").addEventListener("change", event => {
  settings = collectSettings();
  window.CGVI18N.setLanguage(event.target.value);
  renderSettings();
});
document.getElementById("bibleVersionSelect").addEventListener("change", () => {
  settings = collectSettings();
  renderBibleStatus();
});
window.addEventListener("hashchange", scrollToRequestedSection);
loadSettings();
