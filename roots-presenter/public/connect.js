const views = {
  controller: {
    path: "/controller.html",
    titleKey: "controllerView",
    helpKey: "scanControllerQr"
  },
  audience: {
    path: "/audience.html",
    titleKey: "audience",
    helpKey: "scanAudienceQr"
  },
  director: {
    path: "/director.html",
    titleKey: "director",
    helpKey: "scanDirectorQr"
  },
  stage: {
    path: "/stage.html",
    titleKey: "stageView",
    helpKey: "scanStageQr"
  },
};

let connectionInfo = {};
let activeView = "controller";

const byId = id => document.getElementById(id);

function renderView(viewKey) {
  const view = views[viewKey] || views.controller;
  activeView = views[viewKey] ? viewKey : "controller";
  const info = connectionInfo[activeView] || {};
  const url = info.url || `${window.location.origin}${view.path}`;

  document.querySelectorAll(".view-tabs button").forEach(button => {
    button.classList.toggle("active", button.dataset.view === activeView);
  });

  byId("qrImage").src = `/connection-qr.svg?path=${encodeURIComponent(view.path)}&t=${Date.now()}`;
  byId("viewTitle").textContent = t(view.titleKey);
  byId("viewHelp").textContent = t(view.helpKey);
  byId("urlInput").value = url;
}

async function loadConnectionInfo() {
  try {
    const response = await fetch("/connection-info");
    connectionInfo = response.ok ? await response.json() : {};
  } catch {
    connectionInfo = {};
  }

  renderView(activeView);
}

async function copyActiveUrl() {
  const input = byId("urlInput");
  input.select();
  input.setSelectionRange(0, input.value.length);

  try {
    await navigator.clipboard.writeText(input.value);
    byId("statusText").textContent = t("linkCopied");
  } catch {
    document.execCommand("copy");
    byId("statusText").textContent = t("linkCopied");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await window.CGVI18N.loadLanguage();
  await loadConnectionInfo();

  document.querySelectorAll(".view-tabs button").forEach(button => {
    button.addEventListener("click", () => renderView(button.dataset.view));
  });

  byId("copyButton").addEventListener("click", copyActiveUrl);
});
