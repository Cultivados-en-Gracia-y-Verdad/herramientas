(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  let blankOverlay = null;

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
    blankOverlay.style.zIndex = "100000";
    document.body.appendChild(blankOverlay);

    return blankOverlay;
  }

  function clearProjectorDrawing() {
    const canvas = document.getElementById("projectorCanvas");
    const ctx = canvas?.getContext("2d");

    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width || 1920, canvas.height || 1080);
    }
  }

  function setProjectorBlank(active) {
    if (active) {
      clearProjectorDrawing();
    }

    ensureBlankOverlay().style.opacity = active ? "1" : "0";
  }

  socket.on("draw-point", point => {
    if (point?.meta === "tablet-blank") {
      setProjectorBlank(!!point.active);
    }
  });

  window.addEventListener("resize", sendProjectorViewport);
  window.addEventListener("load", sendProjectorViewport);

  sendProjectorViewport();
})();
