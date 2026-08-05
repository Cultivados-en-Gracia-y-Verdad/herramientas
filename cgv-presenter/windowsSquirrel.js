const path = require("path");
const { spawn } = require("child_process");
const { ensureLanPortRule, removeLanPortRule } = require("./windowsFirewall");

function spawnUpdate(args, done) {
  const updateExe = path.resolve(path.dirname(process.execPath), "..", "Update.exe");
  try {
    spawn(updateExe, args, { detached: true }).on("close", () => done());
  } catch {
    done();
  }
}

function finish(app, delayMs = 1000) {
  setTimeout(() => app.quit(), delayMs);
}

/**
 * Handle Squirrel.Windows install lifecycle flags.
 * Must run before the Express server binds 0.0.0.0:3000.
 * Returns true when this process should quit immediately.
 */
function handleSquirrelEvent(app) {
  if (process.platform !== "win32") return false;

  const cmd = process.argv[1];
  if (!cmd || !String(cmd).startsWith("--squirrel")) return false;

  const target = path.basename(process.execPath);

  if (cmd === "--squirrel-install" || cmd === "--squirrel-updated") {
    // Port-based rule survives Squirrel version-folder moves (app-1.2.x/...).
    ensureLanPortRule({ elevateIfNeeded: true })
      .catch(() => {})
      .finally(() => {
        spawnUpdate([`--createShortcut=${target}`], () => finish(app));
      });
    return true;
  }

  if (cmd === "--squirrel-uninstall") {
    removeLanPortRule({ elevateIfNeeded: true })
      .catch(() => {})
      .finally(() => {
        spawnUpdate([`--removeShortcut=${target}`], () => finish(app));
      });
    return true;
  }

  if (cmd === "--squirrel-obsolete") {
    finish(app, 100);
    return true;
  }

  return false;
}

module.exports = {
  handleSquirrelEvent
};
