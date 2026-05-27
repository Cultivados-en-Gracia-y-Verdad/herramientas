const tabletCanvas = document.getElementById("tabletDrawingCanvas");
const projectorFeed = document.getElementById("tabletProjectorFeed");
const clearButton = document.getElementById("tabletClearButton");
const nextButton = document.getElementById("tabletNextButton");
const prevButton = document.getElementById("tabletPrevButton");
const blankButton = document.getElementById("tabletBlankButton");
const blankSurface = document.getElementById("tabletBlankSurface");
const tabletSurface = document.getElementById("tabletSurface");

if (tabletCanvas) {
  const drawingSocket = window.CGV_SOCKET || io();

  const DRAW_WIDTH = 1920;
  const DRAW_HEIGHT = 1080;
  const DRAW_COLOR = "#facc15";
  const PEN_WIDTH = 6;

  const ctx = tabletCanvas.getContext("2d");

  let drawing = false;
  let blankMode = false;
  let blankInkImage = null;

  function setNavigationDisabled(disabled) {
    if (nextButton) {
      nextButton.disabled = disabled;
      nextButton.style.opacity = disabled ? "0.4" : "1";
    }

    if (prevButton) {
      prevButton.disabled = disabled;
      prevButton.style.opacity = disabled ? "0.4" : "1";
    }
  }

  function resizeCanvas() {
    if (tabletCanvas.width === DRAW_WIDTH && tabletCanvas.height === DRAW_HEIGHT) {
      return;
    }

    tabletCanvas.width = DRAW_WIDTH;
    tabletCanvas.height = DRAW_HEIGHT;
  }

  function clearLocalInk() {
    ctx.clearRect(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
  }

  function saveBlankInk() {
    try {
      blankInkImage = ctx.getImageData(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
    } catch {
      blankInkImage = null;
    }
  }

  function restoreBlankInk() {
    clearLocalInk();

    if (blankInkImage) {
      ctx.putImageData(blankInkImage, 0, 0);
    }
  }

  function clearBlankInkMemory() {
    blankInkImage = null;
  }

  function clearSyncedInk() {
    clearLocalInk();
    clearBlankInkMemory();
    drawingSocket.emit("draw-clear");
  }

  function emitSlideChanged() {
    drawingSocket.emit("draw-point", {
      x: 0,
      y: 0,
      drawing: false,
      erase: false,
      meta: "slide-changed"
    });
  }

  function applyViewport(width, height) {
    if (!width || !height || !tabletSurface) return;

    const aspect = width / height;
    tabletSurface.style.aspectRatio = `${width} / ${height}`;

    const availableWidth = window.innerWidth;
    const availableHeight = window.innerHeight - 64;

    let surfaceWidth = availableWidth;
    let surfaceHeight = surfaceWidth / aspect;

    if (surfaceHeight > availableHeight) {
      surfaceHeight = availableHeight;
      surfaceWidth = surfaceHeight * aspect;
    }

    tabletSurface.style.width = `${surfaceWidth}px`;
    tabletSurface.style.height = `${surfaceHeight}px`;
  }

  resizeCanvas();

  function getPoint(event) {
    const rect = tabletCanvas.getBoundingClientRect();

    if (!rect.width || !rect.height) {
      return { x: 0, y: 0 };
    }

    return {
      x: ((event.clientX - rect.left) / rect.width) * DRAW_WIDTH,
      y: ((event.clientY - rect.top) / rect.height) * DRAW_HEIGHT
    };
  }

  function prepareContext() {
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = DRAW_COLOR;
    ctx.lineWidth = PEN_WIDTH;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }

  function applyPoint(point) {
    if (!point) return;

    prepareContext();

    if (!point.drawing) {
      ctx.beginPath();
      ctx.moveTo(point.x, point.y);
      return;
    }

    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
  }

  function emitPoint(point) {
    drawingSocket.emit("draw-point", {
      ...point,
      erase: false
    });
  }

  tabletCanvas.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;

    event.preventDefault();
    drawing = true;

    const point = {
      ...getPoint(event),
      drawing: false
    };

    applyPoint(point);
    emitPoint(point);

    tabletCanvas.setPointerCapture?.(event.pointerId);
  });

  tabletCanvas.addEventListener("pointermove", event => {
    if (!drawing) return;

    event.preventDefault();

    const point = {
      ...getPoint(event),
      drawing: true
    };

    applyPoint(point);
    emitPoint(point);
  });

  function stopDrawing(event) {
    drawing = false;

    if (event?.pointerId !== undefined && tabletCanvas.hasPointerCapture?.(event.pointerId)) {
      tabletCanvas.releasePointerCapture(event.pointerId);
    }
  }

  tabletCanvas.addEventListener("pointerup", stopDrawing);
  tabletCanvas.addEventListener("pointercancel", stopDrawing);
  tabletCanvas.addEventListener("pointerleave", stopDrawing);

  drawingSocket.on("draw-point", point => {
    if (point?.meta === "projector-viewport" && point.viewport) {
      applyViewport(point.viewport.width, point.viewport.height);
      return;
    }

    if (point?.meta === "projector-frame" && point.frame) {
      applyViewport(point.frame.width, point.frame.height);

      if (projectorFeed) {
        projectorFeed.src = point.frame.dataUrl;
      }
      return;
    }

    if (point?.meta === "tablet-blank") {
      const nextBlankMode = !!point.active;

      if (nextBlankMode) {
        restoreBlankInk();
      } else if (blankMode) {
        saveBlankInk();
        clearLocalInk();
      }

      blankMode = nextBlankMode;
      setNavigationDisabled(blankMode);

      if (blankSurface) {
        blankSurface.classList.toggle("active", blankMode);
      }

      return;
    }

    if (point?.meta === "slide-changed") {
      if (!blankMode) {
        clearLocalInk();
      }
      return;
    }

    applyPoint(point);
  });

  drawingSocket.on("draw-clear", () => {
    clearLocalInk();
    clearBlankInkMemory();
  });

  if (clearButton) {
    clearButton.addEventListener("click", clearSyncedInk);
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => {
      if (blankMode) return;

      clearLocalInk();
      emitSlideChanged();

      drawingSocket.emit("next");
    });
  }

  if (prevButton) {
    prevButton.addEventListener("click", () => {
      if (blankMode) return;

      clearLocalInk();
      emitSlideChanged();

      drawingSocket.emit("prev");
    });
  }

  if (blankButton) {
    blankButton.addEventListener("click", () => {
      const nextBlankMode = !blankMode;

      if (nextBlankMode) {
        restoreBlankInk();
      } else {
        saveBlankInk();
        clearLocalInk();
      }

      blankMode = nextBlankMode;
      setNavigationDisabled(blankMode);

      if (blankSurface) {
        blankSurface.classList.toggle("active", blankMode);
      }

      drawingSocket.emit("draw-point", {
        x: 0,
        y: 0,
        drawing: false,
        erase: false,
        meta: "tablet-blank",
        active: blankMode
      });
    });
  }
}
