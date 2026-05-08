const viewScopes = [
  { key: "main", label: "Main View" },
  { key: "presenter", label: "Presenter View" },
  { key: "audience", label: "Audience View (Web)" }
];

const styleKeys = [
  { key: "h1", label: "H1 Main Titles", fields: ["size", "color"] },
  { key: "h2", label: "H2 Subtitles", fields: ["size", "color"] },
  { key: "h3", label: "H3 Bible Reference", fields: ["size", "color", "indent"] },
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

let settings = { styles: { main: {}, presenter: {}, audience: {} } };

function normalizeSettings(rawSettings) {
  const styles = rawSettings.styles || {};

  if (styles.main || styles.presenter || styles.audience) {
    return {
      styles: {
        main: styles.main || {},
        presenter: styles.presenter || styles.main || {},
        audience: styles.audience || styles.main || {}
      }
    };
  }

  return {
    styles: {
      main: styles,
      presenter: JSON.parse(JSON.stringify(styles)),
      audience: JSON.parse(JSON.stringify(styles))
    }
  };
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

function collectSettings() {
  const nextSettings = { styles: { main: {}, presenter: {}, audience: {} } };

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
loadSettings();
