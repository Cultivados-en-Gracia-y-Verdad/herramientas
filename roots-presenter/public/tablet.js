const tabletCanvas = document.getElementById("tabletDrawingCanvas");
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
  const DRAW_COLOR = "#facc15";
  const PEN_WIDTH = 6;

  const ctx = tabletCanvas.getContext("2d");

  let drawing = false;
  let blankMode = false;
  let drawWidth = DEFAULT_DRAW_WIDTH;
  let drawHeight = DEFAULT_DRAW_HEIGHT;

  function resizeCanvas() {
    const existingImage = ctx.getImageData(0, 0, tabletCanvas.width || 1, tabletCanvas.height || 1);

    tabletCanvas.width = drawWidth;
    tabletCanvas.height = drawHeight;

    if (existingImage.width && existingImage.height) {
      ctx.putImageData(existingImage, 0, 0);
    }
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

  window.addEventListener("resize", () => {
    resizeCanvas();
  });

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
    });
  }
}
