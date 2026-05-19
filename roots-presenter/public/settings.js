const viewScopes = [
  { key: "main", label: "Main View" },
  { key: "presenter", label: "Presenter View" },
  { key: "audience", label: "Audience View (Web)" }
];

const styleKeys = [
  { key: "h1", label: "H1 Main Titles", fields: ["size", "color"] },
  { key: "h2", label: "H2 Subtitles", fields: ["size", "color"] },
  { key: "h3", label: "H3 Bible Reference", fields: ["size", "color", "indent"] },
  { key: "scripture", label: "Scripture Under H3", fields: ["size", "color", "indent", "lineHeight"] },
  { key: "h4", label: "H4 Scripture Anchor", fields: ["size", "color", "indent"] },
  { key: "h5", label: "H5 First Comment", fields: ["size", "color", "indent"] },
  { key: "h6", label: "H6 Second Comment", fields: ["size", "color", "indent"] },
  { key: "bullet", label: "Bullet Comments", fields: ["size", "color", "indent"] },
  { key: "reference", label: "Bible Reference Links", fields: ["color"] }
];

const synthesisFields = [
  ["background", "Box Background"],
  ["color", "Text Color"],
  ["accent", "Accent Color"],
  ["titleColor", "Title Color"],
  ["textSize", "Text Size"]
];

const definitionFields = [
  ["background", "Background"],
  ["accent", "Accent Color"],
  ["termColor", "Term Color"],
  ["textColor", "Definition Text"]
];

const popupFields = [
  ["background", "Popup Background"],
  ["color", "Popup Text"],
  ["verseBackground", "Verse Background"],
  ["accent", "Accent Color"],
  ["referenceColor", "Reference Label"],
  ["textSize", "Text Size"]
];

const builtInThemes = window.CGV_STYLE_THEMES || [];

let settings = {
  language: "es",
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

function normalizeSettings(rawSettings) {
  const styles = rawSettings.styles || {};
  const customThemes = getCustomThemes(rawSettings);
  const language = ["es", "en"].includes(rawSettings.language) ? rawSettings.language : "es";

  if (styles.main || styles.presenter || styles.audience) {
    return {
      language,
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
  return field.charAt(0).toUpperCase() + field.slice(1);
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
  heading.textContent = section.label;

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

  synthesisFields.forEach(([field, label]) => {
    grid.appendChild(createInput(scope, "synthesis", field, label));
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
  heading.textContent = "Definitions";

  definitionFields.forEach(([field, label]) => {
    grid.appendChild(createInput(scope, "definition", field, label));
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
  heading.textContent = "Bible Popup";

  popupFields.forEach(([field, label]) => {
    grid.appendChild(createInput(scope, "popup", field, label));
  });

  wrapper.append(heading, grid);
  return wrapper;
}

function renderSettings() {
  const form = document.getElementById("settingsForm");
  form.innerHTML = "";
  renderLanguageSelect();
  renderThemeSelect();

  viewScopes.forEach(scope => {
    const group = document.createElement("section");
    const heading = document.createElement("h2");
    const backgroundSection = {
      key: "background",
      label: "View Background",
      fields: ["color"]
    };

    group.className = "view-group";
    heading.textContent = scope.label;
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
}

function renderLanguageSelect() {
  const select = document.getElementById("languageSelect");
  if (!select) return;

  select.value = settings.language || "es";
  document.documentElement.lang = settings.language || "es";
}

function renderThemeSelect() {
  const select = document.getElementById("themeSelect");
  if (!select) return;

  select.replaceChildren();
  getAvailableThemes().forEach(theme => {
    const option = document.createElement("option");
    option.value = theme.id;
    option.textContent = theme.builtIn ? theme.name : `${theme.name} (Custom)`;
    select.appendChild(option);
  });

  if (settings.theme && getAvailableThemes().some(theme => theme.id === settings.theme)) {
    select.value = settings.theme;
  }
}

function collectSettings() {
  const nextSettings = {
    language: document.getElementById("languageSelect")?.value || settings.language || "es",
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
    customThemes: currentCustomThemes
  });
  renderSettings();
  document.getElementById("statusText").textContent = `${theme.name} applied. Save to keep it.`;
}

function saveCurrentAsTheme() {
  const status = document.getElementById("statusText");
  const nameInput = document.getElementById("themeNameInput");
  const themeName = nameInput?.value.trim() || window.prompt("Theme name");
  if (!themeName) return;

  const id = safeThemeId(themeName);
  if (!id) {
    status.textContent = "Theme name needs at least one letter or number.";
    return;
  }

  if (builtInThemes.some(theme => theme.id === id)) {
    status.textContent = "That name is reserved by a built-in theme.";
    return;
  }

  const current = collectSettings();
  const customThemes = getCustomThemes()
    .filter(theme => theme.id !== id);
  const theme = {
    id,
    name: themeName.trim(),
    description: "Custom theme",
    settings: {
      language: current.language || "es",
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
  status.textContent = `${theme.name} saved as a custom theme. Save settings to keep it.`;
}

async function loadSettings() {
  const response = await fetch("/style-settings");
  settings = normalizeSettings(await response.json());
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
    status.textContent = "Could not save style settings.";
    return;
  }

  status.textContent = `Saved ${new Date().toLocaleTimeString()}`;
}

document.getElementById("saveButton").addEventListener("click", saveSettings);
document.getElementById("applyThemeButton").addEventListener("click", applySelectedTheme);
document.getElementById("saveThemeButton").addEventListener("click", saveCurrentAsTheme);
loadSettings();
