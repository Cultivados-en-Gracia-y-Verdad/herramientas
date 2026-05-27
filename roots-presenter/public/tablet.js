const tabletCanvas = document.getElementById("tabletDrawingCanvas");
const projectorFeed = document.getElementById("tabletProjectorFeed");
const clearButton = document.getElementById("tabletClearButton");
const nextButton = document.getElementById("tabletNextButton");
const prevButton = document.getElementById("tabletPrevButton");
const blankButton = document.getElementById("tabletBlankButton");
const fullscreenButton = document.getElementById("tabletFullscreenButton");
const exitFullscreenButton = document.getElementById("tabletExitFullscreenButton");
const blankSurface = document.getElementById("tabletBlankSurface");
const tabletSurface = document.getElementById("tabletSurface");

if (fullscreenBlankButton && blankButton) {
  fullscreenBlankButton.addEventListener("click", () => {
    blankButton.click();
  });
}

if (tabletCanvas) {
  const drawingSocket = window.CGV_SOCKET || io();

  const DRAW_WIDTH = 1920;
  const DRAW_HEIGHT = 1080;
  const DRAW_COLOR = "#facc15";
  const PEN_WIDTH = 6;
  const ERASER_WIDTH = 42;
  const SWIPE_MIN_DISTANCE = 80;
  const SWIPE_MAX_VERTICAL_DRIFT = 90;

  const ctx = tabletCanvas.getContext("2d");

  let drawing = false;
  let blankMode = false;
  let blankInkImage = null;
  let lastViewport = { width: DRAW_WIDTH, height: DRAW_HEIGHT };
  let touchSwipe = null;

  function isFullscreenActive() {
    return !!(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.body.classList.contains("tablet-fullscreen")
    );
  }

  function setFullscreenClass(active) {
    document.body.classList.toggle("tablet-fullscreen", active);

    if (fullscreenButton) {
      fullscreenButton.textContent = active ? "Window" : "Fullscreen";
    }

    requestAnimationFrame(() => {
      applyViewport(lastViewport.width, lastViewport.height);
    });
  }

  async function enterFullscreen() {
    const target = document.documentElement;

    try {
      if (target.requestFullscreen) {
        await target.requestFullscreen();
      } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
      }
    } catch {
      // Some mobile browsers reject native fullscreen unless installed as PWA.
    }

    setFullscreenClass(true);
  }

  async function exitFullscreen() {
    try {
      if (document.exitFullscreen && document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (document.webkitExitFullscreen && document.webkitFullscreenElement) {
        document.webkitExitFullscreen();
      }
    } catch {
      // Keep fallback class behavior below.
    }

    setFullscreenClass(false);
  }

  async function toggleFullscreen() {
    if (isFullscreenActive()) {
      await exitFullscreen();
    } else {
      await enterFullscreen();
    }
  }

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

  function goNextFromSwipe() {
    if (blankMode) return;

    clearLocalInk();
    emitSlideChanged();
    drawingSocket.emit("next");
  }

  function goPrevFromSwipe() {
    if (blankMode) return;

    clearLocalInk();
    emitSlideChanged();
    drawingSocket.emit("prev");
  }

  function applyViewport(width, height) {
    if (!width || !height || !tabletSurface) return;

    lastViewport = { width, height };

    const aspect = width / height;
    tabletSurface.style.aspectRatio = `${width} / ${height}`;

    const availableWidth = window.innerWidth;
    const toolbarHeight = document.body.classList.contains("tablet-fullscreen") ? 0 : 64;
    const availableHeight = window.innerHeight - toolbarHeight;

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

  function isStylusEvent(event) {
    return event.pointerType === "pen" || event.pointerType === "mouse";
  }

  function isEraserEvent(event) {
    // Many stylus side buttons / erasers report button 5, buttons 32, or button/buttons 2.
    return event.pointerType === "pen" && (
      event.button === 5 ||
      event.buttons === 32 ||
      event.button === 2 ||
      event.buttons === 2
    );
  }

  function prepareContext(erase = false) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = erase ? ERASER_WIDTH : PEN_WIDTH;

    if (erase) {
      ctx.globalCompositeOperation = "destination-out";
      ctx.strokeStyle = "rgba(0,0,0,1)";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = DRAW_COLOR;
    }
  }

  function applyPoint(point) {
    if (!point) return;

    prepareContext(!!point.erase);

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
    drawingSocket.emit("draw-point", point);
  }

  function beginTouchSwipe(event) {
    touchSwipe = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastY: event.clientY
    };

    event.preventDefault();
    tabletCanvas.setPointerCapture?.(event.pointerId);
  }

  function updateTouchSwipe(event) {
    if (!touchSwipe || touchSwipe.pointerId !== event.pointerId) return;

    touchSwipe.lastX = event.clientX;
    touchSwipe.lastY = event.clientY;
    event.preventDefault();
  }

  function finishTouchSwipe(event) {
    if (!touchSwipe || touchSwipe.pointerId !== event.pointerId) return;

    const dx = touchSwipe.lastX - touchSwipe.startX;
    const dy = touchSwipe.lastY - touchSwipe.startY;

    touchSwipe = null;

    if (event?.pointerId !== undefined && tabletCanvas.hasPointerCapture?.(event.pointerId)) {
      tabletCanvas.releasePointerCapture(event.pointerId);
    }

    if (blankMode) return;
    if (Math.abs(dx) < SWIPE_MIN_DISTANCE) return;
    if (Math.abs(dy) > SWIPE_MAX_VERTICAL_DRIFT) return;

    if (dx < 0) {
      goNextFromSwipe();
    } else {
      goPrevFromSwipe();
    }
  }

  tabletCanvas.addEventListener("pointerdown", event => {
    if (event.pointerType === "touch") {
      beginTouchSwipe(event);
      return;
    }

    if (event.button !== 0 && !isEraserEvent(event)) return;
    if (!isStylusEvent(event)) return;

    event.preventDefault();
    drawing = true;

    const point = {
      ...getPoint(event),
      drawing: false,
      erase: isEraserEvent(event)
    };

    applyPoint(point);
    emitPoint(point);

    tabletCanvas.setPointerCapture?.(event.pointerId);
  });

  tabletCanvas.addEventListener("pointermove", event => {
    if (event.pointerType === "touch") {
      updateTouchSwipe(event);
      return;
    }

    if (!drawing) return;
    if (!isStylusEvent(event)) return;

    event.preventDefault();

    const point = {
      ...getPoint(event),
      drawing: true,
      erase: isEraserEvent(event)
    };

    applyPoint(point);
    emitPoint(point);
  });

  function stopDrawing(event) {
    if (event?.pointerType === "touch") {
      finishTouchSwipe(event);
      return;
    }

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

  document.addEventListener("fullscreenchange", () => {
    setFullscreenClass(!!document.fullscreenElement);
  });

  document.addEventListener("webkitfullscreenchange", () => {
    setFullscreenClass(!!document.webkitFullscreenElement);
  });

  window.addEventListener("resize", () => {
    applyViewport(lastViewport.width, lastViewport.height);
  });

  if (fullscreenButton) {
    fullscreenButton.addEventListener("click", toggleFullscreen);
  }

  if (exitFullscreenButton) {
    exitFullscreenButton.addEventListener("click", exitFullscreen);
  }

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
