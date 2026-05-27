(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  let blankOverlay = null;
  let frameTimer = null;

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

  function setProjectorBlank(active) {
    ensureBlankOverlay().style.opacity = active ? "1" : "0";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getSlideText() {
    const slide = document.getElementById("projectorSlide");
    return slide ? slide.innerText || slide.textContent || "" : "";
  }

  function captureProjectorFrame() {
    const width = Math.max(1, window.innerWidth);
    const height = Math.max(1, window.innerHeight);
    const slideText = escapeHtml(getSlideText());
    const fontSize = Math.max(24, Math.round(Math.min(width, height) * 0.05));
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <rect width="100%" height="100%" fill="#071633"/>
        <foreignObject x="0" y="0" width="${width}" height="${height}">
          <div xmlns="http://www.w3.org/1999/xhtml" style="box-sizing:border-box;width:${width}px;height:${height}px;display:flex;align-items:center;justify-content:center;padding:${Math.round(width * 0.06)}px;color:white;font-family:Arial,sans-serif;font-weight:700;text-align:left;font-size:${fontSize}px;line-height:1.25;white-space:pre-wrap;">
            ${slideText}
          </div>
        </foreignObject>
      </svg>
    `;
    const dataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;

    emitMeta("projector-frame", {
      frame: {
        width,
        height,
        dataUrl
      }
    });
  }

  function startProjectorFeed() {
    if (frameTimer) return;

    captureProjectorFrame();
    frameTimer = setInterval(captureProjectorFrame, 500);
  }

  socket.on("draw-point", point => {
    if (point?.meta === "tablet-blank") {
      setProjectorBlank(!!point.active);
    }
  });

  window.addEventListener("resize", () => {
    sendProjectorViewport();
    captureProjectorFrame();
  });

  window.addEventListener("load", () => {
    sendProjectorViewport();
    startProjectorFeed();
  });

  sendProjectorViewport();
  startProjectorFeed();
})();
