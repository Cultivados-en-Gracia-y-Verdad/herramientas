(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  let blankOverlay = null;
  let blankInkImage = null;

  function emitMeta(meta, extra = {}) {
    socket.emit("draw-point", {
      x: 0,
      y: 0,
      drawing: false,
      erase: false,
      meta,
      ...extra
    });
  }

  function sendProjectorViewport() {
    emitMeta("projector-viewport", {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    });
  }

  function ensureBlankOverlay() {
    if (blankOverlay) return blankOverlay;

    blankOverlay = document.createElement("div");
    blankOverlay.id = "projectorBlankOverlay";
    blankOverlay.style.position = "fixed";
    blankOverlay.style.inset = "0";
    blankOverlay.style.background = "#000";
    blankOverlay.style.opacity = "0";
    blankOverlay.style.pointerEvents = "none";
    blankOverlay.style.transition = "opacity 120ms ease";
    blankOverlay.style.zIndex = "99998";
    document.body.appendChild(blankOverlay);

    return blankOverlay;
  }

  function getProjectorCanvasContext() {
    const canvas = document.getElementById("projectorCanvas");
    const ctx = canvas?.getContext("2d");

    if (!canvas || !ctx) return null;

    return { canvas, ctx };
  }

  function clearProjectorDrawing() {
    const target = getProjectorCanvasContext();
    if (!target) return;

    target.ctx.clearRect(0, 0, target.canvas.width || 1920, target.canvas.height || 1080);
  }

  function saveBlankInk() {
    const target = getProjectorCanvasContext();
    if (!target) return;

    try {
      blankInkImage = target.ctx.getImageData(
        0,
        0,
        target.canvas.width || 1920,
        target.canvas.height || 1080
      );
    } catch {
      blankInkImage = null;
    }
  }

  function restoreBlankInk() {
    const target = getProjectorCanvasContext();
    if (!target) return;

    clearProjectorDrawing();

    if (blankInkImage) {
      target.ctx.putImageData(blankInkImage, 0, 0);
    }
  }

  function clearBlankInkMemory() {
    blankInkImage = null;
  }

  function setProjectorBlank(active) {
    const overlay = ensureBlankOverlay();

    if (active) {
      restoreBlankInk();
      overlay.style.opacity = "1";
      return;
    }

    saveBlankInk();
    clearProjectorDrawing();
    overlay.style.opacity = "0";
  }

  socket.on("draw-point", point => {
    if (point?.meta === "tablet-blank") {
      setProjectorBlank(!!point.active);
      return;
    }

    if (point?.meta === "slide-changed") {
      clearProjectorDrawing();
      return;
    }

    if (point?.meta === "blank-clear") {
      clearBlankInkMemory();
    }
  });

  socket.on("draw-clear", () => {
    clearBlankInkMemory();
  });

  window.addEventListener("resize", sendProjectorViewport);
  window.addEventListener("load", sendProjectorViewport);

  sendProjectorViewport();
})();
