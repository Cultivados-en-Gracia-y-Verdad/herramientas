(function () {
  let projectorViewport = null;
  let projectorMode = "extended";

  function isTablet() {
    return document.body.classList.contains("tablet");
  }

  function hasProjectorViewport() {
    return !!(projectorViewport?.width > 0 && projectorViewport?.height > 0);
  }

  function setProjectorViewport(viewport) {
    if (!viewport) {
      projectorViewport = null;
      return;
    }

    const width = Math.round(Number(viewport.width));
    const height = Math.round(Number(viewport.height));
    if (width > 0 && height > 0) {
      projectorViewport = { width, height };
      return;
    }

    projectorViewport = null;
  }

  function setProjectorMode(mode) {
    if (mode === "mirrored" || mode === "extended") {
      projectorMode = mode;
    }
  }

  function getProjectorViewport() {
    if (!hasProjectorViewport()) return null;
    return { ...projectorViewport };
  }

  function getProjectorMode() {
    return projectorMode;
  }

  function getPreviewMetrics() {
    const vp = getProjectorViewport();
    if (!vp) {
      return { vp: null, scale: 1, left: 0, top: 0, width: 0, height: 0 };
    }

    const host = document.getElementById("tabletPreviewHost");
    const availableWidth = host?.clientWidth || window.innerWidth;
    const availableHeight = host?.clientHeight || window.innerHeight;
    const scale = Math.min(availableWidth / vp.width, availableHeight / vp.height);
    const width = vp.width * scale;
    const height = vp.height * scale;
    const left = (availableWidth - width) / 2;
    const top = (availableHeight - height) / 2;

    return { vp, scale, left, top, width, height };
  }

  function getPreviewFrame() {
    return document.getElementById("tabletPreviewFrame");
  }

  function applyTabletPreviewLayout() {
    const host = document.getElementById("tabletPreviewHost");
    const frame = getPreviewFrame();
    if (!host || !frame || !hasProjectorViewport()) return getPreviewMetrics();

    const metrics = getPreviewMetrics();
    frame.style.width = `${metrics.vp.width}px`;
    frame.style.height = `${metrics.vp.height}px`;
    frame.style.left = `${metrics.left}px`;
    frame.style.top = `${metrics.top}px`;
    frame.style.transform = `scale(${metrics.scale})`;
    frame.style.transformOrigin = "top left";
    return metrics;
  }

  function positionTabletDrawingCanvas(canvas) {
    const host = document.getElementById("tabletPreviewHost");
    if (!host || !canvas || !hasProjectorViewport()) return null;

    const metrics = applyTabletPreviewLayout();
    canvas.style.position = "absolute";
    canvas.style.left = `${metrics.left}px`;
    canvas.style.top = `${metrics.top}px`;
    canvas.style.width = `${metrics.width}px`;
    canvas.style.height = `${metrics.height}px`;
    canvas.style.zIndex = "30";
    return metrics;
  }

  function getDrawingTarget() {
    if (isTablet()) {
      return hasProjectorViewport() ? getPreviewFrame() : null;
    }

    return document.body;
  }

  function mapClientPoint(clientX, clientY, displayRect) {
    const vp = getProjectorViewport();
    if (!vp) return { x: 0, y: 0 };

    const rect = displayRect || (isTablet() ? null : { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight });
    if (!rect || rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 };

    return {
      x: ((clientX - rect.left) / rect.width) * vp.width,
      y: ((clientY - rect.top) / rect.height) * vp.height
    };
  }

  function positionElementOverTarget(element, target) {
    if (!element || !target) return null;

    if (!isTablet()) {
      const vp = getProjectorViewport();
      const width = vp?.width || Math.round(window.innerWidth);
      const height = vp?.height || Math.round(window.innerHeight);
      element.style.position = "fixed";
      element.style.left = "0";
      element.style.top = "0";
      element.style.width = `${width}px`;
      element.style.height = `${height}px`;
      element.style.objectFit = "fill";
      element.style.pointerEvents = element.tagName === "CANVAS" ? "" : "none";
      return { left: 0, top: 0, width, height };
    }

    const metrics = getPreviewMetrics();
    element.style.position = "absolute";
    element.style.left = `${metrics.left}px`;
    element.style.top = `${metrics.top}px`;
    element.style.width = `${metrics.width}px`;
    element.style.height = `${metrics.height}px`;
    element.style.objectFit = "fill";
    element.style.pointerEvents = element.tagName === "CANVAS" ? "" : "none";
    return metrics;
  }

  window.CGV_DRAWING_SYNC = {
    hasProjectorViewport,
    getProjectorViewport,
    getProjectorMode,
    setProjectorViewport,
    setProjectorMode,
    isTablet,
    getPreviewMetrics,
    applyTabletPreviewLayout,
    positionTabletDrawingCanvas,
    getDrawingTarget,
    mapClientPoint,
    positionElementOverTarget
  };
})();
