const { app, BrowserWindow, screen } = require("electron");

require("./server");

const APP_URL = "http://localhost:3000";

let presenterWindow;
let projectorWindow;

function getSecondaryDisplay() {
  const primaryDisplay = screen.getPrimaryDisplay();
  return screen
    .getAllDisplays()
    .find(display => display.id !== primaryDisplay.id);
}

function createPresenterWindow() {
  const { workArea } = screen.getPrimaryDisplay();

  presenterWindow = new BrowserWindow({
    x: workArea.x + 40,
    y: workArea.y + 40,
    width: Math.min(1200, workArea.width),
    height: Math.min(800, workArea.height),
    autoHideMenuBar: true
  });

  presenterWindow.loadURL(`${APP_URL}/presenter.html`);
}

function createProjectorWindow() {
  const secondaryDisplay = getSecondaryDisplay();
  const displayBounds = secondaryDisplay
    ? secondaryDisplay.bounds
    : screen.getPrimaryDisplay().bounds;

  projectorWindow = new BrowserWindow({
    x: displayBounds.x,
    y: displayBounds.y,
    width: displayBounds.width,
    height: displayBounds.height,
    backgroundColor: "#000000",
    autoHideMenuBar: true,
    frame: false,
    fullscreen: !!secondaryDisplay,
    show: false
  });

  projectorWindow.loadURL(`${APP_URL}/projector.html`);

  projectorWindow.once("ready-to-show", () => {
    projectorWindow.setBounds(displayBounds);

    if (secondaryDisplay) {
      projectorWindow.setFullScreen(true);
      projectorWindow.showInactive();
      presenterWindow.focus();
    } else {
      projectorWindow.show();
    }
  });
}

function createWindows() {
  createPresenterWindow();
  createProjectorWindow();
}

app.whenReady().then(createWindows);

app.on("window-all-closed", () => {
  app.quit();
});
