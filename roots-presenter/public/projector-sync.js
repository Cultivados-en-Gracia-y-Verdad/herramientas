(() => {
  const params = new URLSearchParams(window.location.search);
  const isPreview = params.get("preview") === "1";
  const socket = window.CGV_SOCKET || (typeof io === "function" ? io() : null);

  if (!socket || isPreview) return;

  function sendProjectorViewport() {
    socket.emit("projector-viewport", {
      width: window.innerWidth,
      height: window.innerHeight
    });
  }

  window.addEventListener("resize", sendProjectorViewport);
  window.addEventListener("load", sendProjectorViewport);

  sendProjectorViewport();
})();
