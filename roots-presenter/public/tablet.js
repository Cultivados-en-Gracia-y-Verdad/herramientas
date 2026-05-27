const tabletCanvas = document.getElementById("tabletDrawingCanvas");
const projectorImage = document.getElementById("tabletProjectorImage");
const clearButton = document.getElementById("tabletClearButton");

if (tabletCanvas) {
  const socket = io();

  const DRAW_WIDTH = 1920;
  const DRAW_HEIGHT = 1080;

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

    return {
      x: ((event.clientX - rect.left) / rect.width) * DRAW_WIDTH,
      y: ((event.clientY - rect.top) / rect.height) * DRAW_HEIGHT
    };
  }

  function drawLine(from, to) {
    if (!from || !to) return;

    ctx.strokeStyle = "#ffd400";
    ctx.lineWidth = 8;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  }

  tabletCanvas.addEventListener("pointerdown", event => {
    drawing = true;
    previousPoint = getPoint(event);
  });

  tabletCanvas.addEventListener("pointermove", event => {
    if (!drawing) return;

    const point = getPoint(event);

    drawLine(previousPoint, point);

    socket.emit("tablet-draw-line", {
      from: previousPoint,
      to: point
    });

    previousPoint = point;
  });

  function stopDrawing() {
    drawing = false;
    previousPoint = null;
  }

  tabletCanvas.addEventListener("pointerup", stopDrawing);
  tabletCanvas.addEventListener("pointercancel", stopDrawing);
  tabletCanvas.addEventListener("pointerleave", stopDrawing);

  socket.on("projector-snapshot", image => {
    if (projectorImage) {
      projectorImage.src = image;
    }
  });

  socket.on("tablet-clear-drawing", () => {
    ctx.clearRect(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
  });

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      ctx.clearRect(0, 0, DRAW_WIDTH, DRAW_HEIGHT);
      socket.emit("tablet-clear-drawing");
    });
  }
}
