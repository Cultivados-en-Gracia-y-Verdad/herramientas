(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  let blankOverlay = null;
  let frameTimer = null;
  let captureInProgress = false;

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

  function collectStyles() {
    return [...document.styleSheets]
      .map(sheet => {
        try {
          return [...sheet.cssRules].map(rule => rule.cssText).join("\n");
        } catch {
          return "";
        }
      })
      .join("\n");
  }

  function cloneProjectorBody() {
    const clone = document.body.cloneNode(true);

    clone.querySelectorAll("script, #projectorCanvas, #projectorBlankOverlay").forEach(node => {
      node.remove();
    });

    clone.style.margin = "0";
    clone.style.width = `${window.innerWidth}px`;
    clone.style.height = `${window.innerHeight}px`;
    clone.style.overflow = "hidden";

    return clone;
  }

  async function captureProjectorFrame() {
    if (captureInProgress) return;

    captureInProgress = true;

    try {
      const width = Math.max(1, window.innerWidth);
      const height = Math.max(1, window.innerHeight);
      const clone = cloneProjectorBody();
      const styles = collectStyles();
      const serialized = new XMLSerializer().serializeToString(clone);
      const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
          <foreignObject width="100%" height="100%">
            <div xmlns="http://www.w3.org/1999/xhtml">
              <style>${styles}</style>
              ${serialized}
            </div>
          </foreignObject>
        </svg>
      `;
      const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const img = new Image();

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = url;
      });

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(url);

      emitMeta("projector-frame", {
        frame: {
          width,
          height,
          dataUrl: canvas.toDataURL("image/jpeg", 0.72)
        }
      });
    } catch (error) {
      console.warn("Projector frame capture failed:", error);
    } finally {
      captureInProgress = false;
    }
  }

  function startProjectorFeed() {
    if (frameTimer) return;

    captureProjectorFrame();
    frameTimer = setInterval(captureProjectorFrame, 400);
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
