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

  const DEFAULT_DRAW_WIDTH = 1920;
  const DEFAULT_DRAW_HEIGHT = 1080;

  const ctx = tabletCanvas.getContext("2d");

  let drawing = false;
  let blankMode = false;
  let drawWidth = DEFAULT_DRAW_WIDTH;
  let drawHeight = DEFAULT_DRAW_HEIGHT;

  function resizeCanvas() {
    tabletCanvas.width = drawWidth;
    tabletCanvas.height = drawHeight;
    ctx.clearRect(0, 0, drawWidth, drawHeight);
  }

  function applyViewport(width, height) {
    if (!width || !height) return;

    drawWidth = Math.round(width);
    drawHeight = Math.round(height);

    resizeCanvas();

    if (!tabletSurface) return;

    const aspect = drawWidth / drawHeight;
    tabletSurface.style.aspectRatio = `${drawWidth} / ${drawHeight}`;

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
      x: ((event.clientX - rect.left) / rect.width) * drawWidth,
      y: ((event.clientY - rect.top) / rect.height) * drawHeight
    };
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

    emitPoint({
      ...getPoint(event),
      drawing: false
    });

    tabletCanvas.setPointerCapture?.(event.pointerId);
  });

  tabletCanvas.addEventListener("pointermove", event => {
    if (!drawing) return;

    event.preventDefault();

    emitPoint({
      ...getPoint(event),
      drawing: true
    });
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
      blankMode = !!point.active;

      if (blankSurface) {
        blankSurface.classList.toggle("active", blankMode);
      }
    }
  });

  drawingSocket.on("draw-clear", () => {
    ctx.clearRect(0, 0, drawWidth, drawHeight);
  });

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      ctx.clearRect(0, 0, drawWidth, drawHeight);
      drawingSocket.emit("draw-clear");
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => {
      drawingSocket.emit("next");
    });
  }

  if (prevButton) {
    prevButton.addEventListener("click", () => {
      drawingSocket.emit("prev");
    });
  }

  if (blankButton) {
    blankButton.addEventListener("click", () => {
      blankMode = !blankMode;

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
