const tabletSocket = window.CGV_SOCKET;
const sync = window.CGV_DRAWING_SYNC;
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
const previewHost = document.getElementById("tabletPreviewHost");
const waitingEl = document.getElementById("tabletWaiting");

let drawing = false;
let blankMode = false;
let lastPoint = null;
let sendTimer = null;
let lastScreenKey = "";
let slideDrawingDataUrl = "";
let blankDrawingDataUrl = "";
let canvasSyncFrame = null;

function getViewportSize() {
  const vp = sync.getProjectorViewport?.();
  if (!vp) return null;
  return { width: vp.width, height: vp.height };
}

function ensureViewportReady() {
  const size = getViewportSize();
  return !!(size && size.width > 0 && size.height > 0);
}

function clearCanvasOnly() {
  const size = getViewportSize();
  if (!size) return;
  const { width, height } = size;
  context.clearRect(0, 0, width, height);
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

  const size = getViewportSize();
  if (!size) return;
  const { width, height } = size;
  const image = new Image();
  image.onload = () => {
    clearCanvasOnly();
    context.drawImage(image, 0, 0, width, height);
    if (shouldBroadcast) sendDrawing();
  };
  image.src = dataUrl;
}

function updateTabletReadyState() {
  const ready = ensureViewportReady();
  waitingEl?.toggleAttribute("hidden", ready);
  previewHost?.toggleAttribute("hidden", !ready);
  return ready;
}

function positionDrawingCanvas() {
  if (!updateTabletReadyState()) return;
  sync.positionTabletDrawingCanvas(canvas);
}

function prepareDrawingCanvas() {
  const size = getViewportSize();
  if (!size) return;
  const { width, height } = size;
  if (canvas.width === width && canvas.height === height) return;

  canvas.width = width;
  canvas.height = height;
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.lineCap = "round";
  context.lineJoin = "round";
}

function resizeCanvas() {
  saveCurrentCanvas();
  positionDrawingCanvas();
  prepareDrawingCanvas();
  const snapshot = blankMode ? blankDrawingDataUrl : slideDrawingDataUrl;
  loadCanvasDataUrl(snapshot, !!snapshot);
}

function scheduleCanvasSync() {
  cancelAnimationFrame(canvasSyncFrame);
  canvasSyncFrame = requestAnimationFrame(() => {
    positionDrawingCanvas();
    window.CGV_TABLET_RENDER?.();
  });
}

function pointFromEvent(event) {
  return sync.mapClientPoint(event.clientX, event.clientY);
}

function penWidthForDisplay() {
  const size = getViewportSize();
  const metrics = sync.getPreviewMetrics?.();
  if (!size || !metrics?.width) return Number(penSize.value);
  return Number(penSize.value) * (size.width / metrics.width);
}

function shouldIgnorePointer(event) {
  return !!event.target.closest?.(".tablet-toolbar, .bible-ref, .bible-popup, button, input, select, textarea, a");
}

function startDrawing(event) {
  if (shouldIgnorePointer(event)) return;
  event.preventDefault();
  event.stopPropagation();
  if (!ensureViewportReady()) return;
  drawing = true;
  lastPoint = pointFromEvent(event);
  canvas.setPointerCapture?.(event.pointerId);
}

function draw(event) {
  if (!drawing || !lastPoint) return;
  event.preventDefault();
  event.stopPropagation();

  const point = pointFromEvent(event);
  context.strokeStyle = penColor.value;
  context.lineWidth = penWidthForDisplay();
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
  event.stopPropagation();
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
    dataUrl: getCanvasDataUrl()
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
    scheduleCanvasSync();
    loadCanvasDataUrl(blankDrawingDataUrl, true);
    return;
  }

  tabletSocket.emit("controller-clear");
  scheduleCanvasSync();
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
  if (data.projectorViewport) {
    sync.setProjectorViewport(data.projectorViewport);
  } else {
    sync.setProjectorViewport(null);
  }

  if (data.projectorMode) {
    sync.setProjectorMode(data.projectorMode);
    document.body.classList.remove("projector-extended", "projector-mirrored");
    document.body.classList.add(`projector-${data.projectorMode}`);
  }

  updateTabletReadyState();

  const controllerState = data.controllerState || {};
  const nextBlankMode = !!(controllerState.active && controllerState.blank);

  if (nextBlankMode !== blankMode) {
    saveCurrentCanvas();
    blankMode = nextBlankMode;
    document.body.classList.toggle("tablet-blank", blankMode);
    blankButton.classList.toggle("active", blankMode);
    scheduleCanvasSync();
    loadCanvasDataUrl(blankMode ? blankDrawingDataUrl : slideDrawingDataUrl, true);
  } else {
    document.body.classList.toggle("tablet-blank", blankMode);
    blankButton.classList.toggle("active", blankMode);
    scheduleCanvasSync();
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

function blockDefaultTouch(event) {
  if (shouldIgnorePointer(event)) return;
  event.preventDefault();
  event.stopPropagation();
}

toolbar?.addEventListener("pointerdown", event => event.stopPropagation());
toolbar?.addEventListener("click", event => event.stopPropagation());
window.addEventListener("resize", resizeCanvas);
canvas.addEventListener("pointerdown", startDrawing);
canvas.addEventListener("pointermove", draw);
canvas.addEventListener("pointerup", stopDrawing);
canvas.addEventListener("pointercancel", stopDrawing);
canvas.addEventListener("contextmenu", event => event.preventDefault());
["touchstart", "touchmove", "touchend", "gesturestart"].forEach(type => {
  previewHost?.addEventListener(type, blockDefaultTouch, { capture: true, passive: false });
  canvas?.addEventListener(type, blockDefaultTouch, { capture: true, passive: false });
});
document.addEventListener("gesturestart", event => event.preventDefault(), { passive: false });
previousButton.addEventListener("click", goPrevious);
nextButton.addEventListener("click", goNext);
clearButton.addEventListener("click", clearDrawing);
blankButton.addEventListener("click", () => setBlankMode(!blankMode));
fullscreenButton.addEventListener("click", toggleFullscreen);
tabletSocket.on("state", handleState);

function syncAfterRender() {
  saveCurrentCanvas();
  positionDrawingCanvas();
  prepareDrawingCanvas();
  loadCanvasDataUrl(blankMode ? blankDrawingDataUrl : slideDrawingDataUrl, false);
}

window.CGV_TABLET_RENDER = syncAfterRender;

resizeCanvas();
