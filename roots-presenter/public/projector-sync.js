(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  function sendProjectorViewport() {
    socket.emit("draw-point", {
      x: 0,
      y: 0,
      drawing: false,
      erase: false,
      meta: "projector-viewport",
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    });
  }

  window.addEventListener("resize", sendProjectorViewport);
  window.addEventListener("load", sendProjectorViewport);

  sendProjectorViewport();
})();
