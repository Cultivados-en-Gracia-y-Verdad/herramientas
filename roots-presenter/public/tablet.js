const tabletCanvas = document.getElementById("tabletDrawingCanvas");
const projectorImage = document.getElementById("tabletProjectorImage");
const clearButton = document.getElementById("tabletClearButton");

if (tabletCanvas) {
  const drawingSocket = window.CGV_SOCKET || io();

  const DRAW_WIDTH = 1920;
  const DRAW_HEIGHT = 1080;
  const DRAW_COLOR = "#facc15";
  const PEN_WIDTH = 6;

  const ctx = tabletCanvas.getContext("2d");

  let drawing = false;
  let previousPoint = null;

  function resizeCanvas() {
    tabletCanvas.width = DRAW_WIDTH;
    tabletCanvas.height = DRAW_HEIGHT;
  }

  resizeCanvas();

  window.addEventListener("resize", resizeCanvas);

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

    previousPoint = point;
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

    previousPoint = point;
    applyPoint(point);
    emitPoint(point);
  });

  function stopDrawing(event) {
    drawing = false;
    previousPoint = null;

    if (event?.pointerId !== undefined && tabletCanvas.hasPointerCapture?.(event.pointerId)) {
      tabletCanvas.releasePointerCapture(event.pointerId);
    }
  }

  tabletCanvas.addEventListener("pointerup", stopDrawing);
  tabletCanvas.addEventListener("pointercancel", stopDrawing);
  tabletCanvas.addEventListener("pointerleave", stopDrawing);

  drawingSocket.on("projector-snapshot", image => {
    if (projectorImage) {
      projectorImage.src = image;
    }
  });

  drawingSocket.on("draw-clear", () => {
    ctx.clearRect(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
  });

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      ctx.clearRect(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
      drawingSocket.emit("draw-clear");
    });
  }
}
