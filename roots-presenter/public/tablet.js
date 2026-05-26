const tabletSocket = window.CGV_SOCKET;
const stage = document.getElementById("tabletStage");
const canvas = document.getElementById("drawingCanvas");
const context = canvas.getContext("2d");
const penColor = document.getElementById("penColor");
const penSize = document.getElementById("penSize");
const previousButton = document.getElementById("previousButton");
const nextButton = document.getElementById("nextButton");
const clearButton = document.getElementById("clearButton");
const blankButton = document.getElementById("blankButton");
const fullscreenButton = document.getElementById("fullscreenButton");
const toolbar = document.querySelector(".tablet-toolbar");

let drawing = false;
let blankMode = false;
let lastPoint = null;
let sendTimer = null;
let lastScreenKey = "";
let slideDrawingDataUrl = "";
let blankDrawingDataUrl = "";

function resizeStage() {
  const availableWidth = Math.max(320, window.innerWidth - 16);
  const availableHeight = Math.max(180, window.innerHeight - 92);
  const width = Math.min(availableWidth, availableHeight * (16 / 9));
  const height = width * (9 / 16);

  stage.style.width = `${Math.round(width)}px`;
  stage.style.height = `${Math.round(height)}px`;
}

function clearCanvasOnly() {
  context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
}

function getCanvasDataUrl() {
  return canvas.width && canvas.height ? canvas.toDataURL("image/png") : "";
}

function saveCurrentCanvas() {
  if (blankMode) {
    blankDrawingDataUrl = getCanvasDataUrl();
    return;
  }

  slideDrawingDataUrl = getCanvasDataUrl();
}

function loadCanvasDataUrl(dataUrl = "", shouldBroadcast = true) {
  clearCanvasOnly();

  if (!dataUrl) {
    if (shouldBroadcast) tabletSocket.emit("tablet-drawing-clear");
    return;
  }

  const image = new Image();
  image.onload = () => {
    clearCanvasOnly();
    context.drawImage(image, 0, 0, canvas.clientWidth, canvas.clientHeight);
    if (shouldBroadcast) sendDrawing();
  };
  image.src = dataUrl;
}

function resizeCanvas() {
  saveCurrentCanvas();
  resizeStage();
  const snapshot = blankMode ? blankDrawingDataUrl : slideDrawingDataUrl;
  const ratio = window.devicePixelRatio || 1;
  const rect = stage.getBoundingClientRect();
  canvas.width = Math.round(rect.width * ratio);
  canvas.height = Math.round(rect.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.lineCap = "round";
  context.lineJoin = "round";

  loadCanvasDataUrl(snapshot, !!snapshot);
}

function pointFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  };
}

function shouldIgnorePointer(event) {
  return !!event.target.closest?.(".tablet-toolbar, .bible-ref, .bible-popup, button, input, select, textarea, a");
}

function startDrawing(event) {
  if (shouldIgnorePointer(event)) return;
  event.preventDefault();
  drawing = true;
  lastPoint = pointFromEvent(event);
  canvas.setPointerCapture?.(event.pointerId);
}

function draw(event) {
  if (!drawing || !lastPoint) return;
  event.preventDefault();

  const point = pointFromEvent(event);
  context.strokeStyle = penColor.value;
  context.lineWidth = Number(penSize.value);
  context.beginPath();
  context.moveTo(lastPoint.x, lastPoint.y);
  context.lineTo(point.x, point.y);
  context.stroke();
  lastPoint = point;
  scheduleSendDrawing();
}

function stopDrawing(event) {
  if (!drawing) return;
  event.preventDefault();
  drawing = false;
  lastPoint = null;
  canvas.releasePointerCapture?.(event.pointerId);
  sendDrawing();
}

function scheduleSendDrawing() {
  clearTimeout(sendTimer);
  sendTimer = setTimeout(sendDrawing, 220);
}

function sendDrawing() {
  clearTimeout(sendTimer);
  saveCurrentCanvas();
  tabletSocket.emit("tablet-drawing", {
    visible: true,
    dataUrl: canvas.toDataURL("image/png")
  });
}

function clearDrawing() {
  clearCanvasOnly();
  if (blankMode) {
    blankDrawingDataUrl = "";
  } else {
    slideDrawingDataUrl = "";
  }
  tabletSocket.emit("tablet-drawing-clear");
}

function setBlankMode(nextBlankMode) {
  if (blankMode === !!nextBlankMode) return;
  saveCurrentCanvas();
  blankMode = !!nextBlankMode;
  document.body.classList.toggle("tablet-blank", blankMode);
  blankButton.classList.toggle("active", blankMode);

  if (blankMode) {
    tabletSocket.emit("controller-blank", {
      background: "#000000",
      backgroundMedia: "",
      useConfiguredBlankMedia: false,
      textColor: "#ffffff",
      accentColor: "#38bdf8"
    });
    loadCanvasDataUrl(blankDrawingDataUrl, true);
    return;
  }

  tabletSocket.emit("controller-clear");
  loadCanvasDataUrl(slideDrawingDataUrl, true);
}

function goPrevious() {
  tabletSocket.emit("prev");
}

function goNext() {
  tabletSocket.emit("next");
}

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen?.();
    return;
  }

  document.documentElement.requestFullscreen?.();
}

function handleState(data = {}) {
  const controllerState = data.controllerState || {};
  const nextBlankMode = !!(controllerState.active && controllerState.blank);

  if (nextBlankMode !== blankMode) {
    saveCurrentCanvas();
    blankMode = nextBlankMode;
    document.body.classList.toggle("tablet-blank", blankMode);
    blankButton.classList.toggle("active", blankMode);
    loadCanvasDataUrl(blankMode ? blankDrawingDataUrl : slideDrawingDataUrl, true);
  } else {
    document.body.classList.toggle("tablet-blank", blankMode);
    blankButton.classList.toggle("active", blankMode);
  }

  const nextScreenKey = blankMode
    ? "blank"
    : `${data.slide || 0}:${data.step || 0}:${controllerState.active ? controllerState.title || "song" : "course"}`;

  if (lastScreenKey && nextScreenKey !== lastScreenKey && !blankMode) {
    slideDrawingDataUrl = "";
    clearCanvasOnly();
    tabletSocket.emit("tablet-drawing-clear");
  }

  lastScreenKey = nextScreenKey;
}

document.addEventListener("DOMContentLoaded", async () => {
  await window.CGVI18N.loadLanguage();
});

toolbar?.addEventListener("pointerdown", event => event.stopPropagation());
toolbar?.addEventListener("click", event => event.stopPropagation());
window.addEventListener("resize", resizeCanvas);
canvas.addEventListener("pointerdown", startDrawing);
canvas.addEventListener("pointermove", draw);
canvas.addEventListener("pointerup", stopDrawing);
canvas.addEventListener("pointercancel", stopDrawing);
previousButton.addEventListener("click", goPrevious);
nextButton.addEventListener("click", goNext);
clearButton.addEventListener("click", clearDrawing);
blankButton.addEventListener("click", () => setBlankMode(!blankMode));
fullscreenButton.addEventListener("click", toggleFullscreen);
tabletSocket.on("state", handleState);

resizeCanvas();
