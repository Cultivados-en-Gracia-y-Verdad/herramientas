(function () {
  let projectorViewport = null;

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

  function getProjectorViewport() {
    if (!hasProjectorViewport()) return null;
    return { ...projectorViewport };
  }

  function getToolbarInset() {
    // The toolbar is overlayed (fixed) and should not change the effective viewport
    // used to compute projector-matching preview scaling/coordinates.
    return 0;
  }

  function getPreviewMetrics() {
    const vp = getProjectorViewport();
    if (!vp) {
      return { vp: null, scale: 1, left: 0, top: 0, width: 0, height: 0 };
    }

    const availableWidth = window.innerWidth;
    const availableHeight = Math.max(120, window.innerHeight);
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

  function getDrawingTarget() {
    if (isTablet()) {
      return hasProjectorViewport() ? getPreviewFrame() : null;
    }

    return document.body;
  }

  function mapClientPoint(clientX, clientY, displayRect) {
    const vp = getProjectorViewport();
    const rect = displayRect || getDrawingTarget()?.getBoundingClientRect();
    if (!vp || !rect) return { x: 0, y: 0 };

    const w = Math.max(1, rect.width);
    const h = Math.max(1, rect.height);
    return {
      x: ((clientX - rect.left) / w) * vp.width,
      y: ((clientY - rect.top) / h) * vp.height
    };
  }

  function positionElementOverTarget(element, target) {
    if (!element || !target) return null;

    if (!isTablet()) {
      element.style.position = "fixed";
      element.style.left = "0";
      element.style.top = "0";
      element.style.width = `${window.innerWidth}px`;
      element.style.height = `${window.innerHeight}px`;
      element.style.objectFit = "fill";
      element.style.pointerEvents = element.tagName === "CANVAS" ? "" : "none";
      return { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
    }

    const rect = target.getBoundingClientRect();
    element.style.position = "fixed";
    element.style.left = `${rect.left}px`;
    element.style.top = `${rect.top}px`;
    element.style.width = `${rect.width}px`;
    element.style.height = `${rect.height}px`;
    element.style.objectFit = "fill";
    element.style.pointerEvents = element.tagName === "CANVAS" ? "" : "none";
    return rect;
  }

  window.CGV_DRAWING_SYNC = {
    hasProjectorViewport,
    getProjectorViewport,
    setProjectorViewport,
    isTablet,
    getPreviewMetrics,
    applyTabletPreviewLayout,
    getDrawingTarget,
    mapClientPoint,
    positionElementOverTarget
  };
})();
