const { execFile, spawn } = require("child_process");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);

const FIREWALL_RULE_NAME = "CGV Presenter LAN";

function isWindows() {
  return process.platform === "win32";
}

function lanPort() {
  const port = Number(process.env.PORT || 3000);
  return Number.isFinite(port) && port > 0 ? port : 3000;
}

function quotePowerShell(value) {
  return `'${String(value || "").replace(/'/g, "''")}'`;
}

function buildNetshAddArgs(port = lanPort()) {
  return [
    "advfirewall",
    "firewall",
    "add",
    "rule",
    `name=${FIREWALL_RULE_NAME}`,
    "dir=in",
    "action=allow",
    "protocol=TCP",
    `localport=${port}`,
    "profile=private,domain,public",
    "enable=yes"
  ];
}

function buildNetshDeleteArgs() {
  return [
    "advfirewall",
    "firewall",
    "delete",
    "rule",
    `name=${FIREWALL_RULE_NAME}`
  ];
}

function runNetsh(args) {
  return execFileAsync("netsh", args, {
    windowsHide: true,
    encoding: "utf8"
  });
}

async function firewallRuleExists() {
  if (!isWindows()) return false;
  try {
    const { stdout } = await runNetsh([
      "advfirewall",
      "firewall",
      "show",
      "rule",
      `name=${FIREWALL_RULE_NAME}`
    ]);
    return /Rule Name:/i.test(String(stdout || ""))
      && !/No rules match/i.test(String(stdout || ""));
  } catch {
    return false;
  }
}

function runElevatedNetsh(args) {
  return new Promise((resolve, reject) => {
    const argumentList = args.map(quotePowerShell).join(",");
    const script = [
      `$p = Start-Process -FilePath netsh -ArgumentList @(${argumentList}) -Verb RunAs -Wait -PassThru -WindowStyle Hidden;`,
      "if ($null -eq $p) { exit 1 }",
      "exit $p.ExitCode"
    ].join(" ");

    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
      {
        windowsHide: true,
        stdio: "ignore"
      }
    );

    child.on("error", reject);
    child.on("exit", code => {
      if (code === 0) resolve();
      else reject(new Error(`Elevated netsh exited with code ${code}`));
    });
  });
}

async function ensureLanPortRule(options = {}) {
  const { elevateIfNeeded = true } = options;
  if (!isWindows()) {
    return { ok: true, skipped: true };
  }

  const port = lanPort();
  if (await firewallRuleExists()) {
    return { ok: true, alreadyPresent: true, port };
  }

  try {
    await runNetsh(buildNetshDeleteArgs()).catch(() => {});
    await runNetsh(buildNetshAddArgs(port));
    return { ok: true, added: true, elevated: false, port };
  } catch (error) {
    if (!elevateIfNeeded) {
      return { ok: false, error, port };
    }
  }

  try {
    await runElevatedNetsh(buildNetshDeleteArgs()).catch(() => {});
    await runElevatedNetsh(buildNetshAddArgs(port));
    return { ok: true, added: true, elevated: true, port };
  } catch (error) {
    return { ok: false, error, port };
  }
}

async function removeLanPortRule(options = {}) {
  const { elevateIfNeeded = true } = options;
  if (!isWindows()) {
    return { ok: true, skipped: true };
  }

  if (!(await firewallRuleExists())) {
    return { ok: true, alreadyAbsent: true };
  }

  try {
    await runNetsh(buildNetshDeleteArgs());
    return { ok: true, removed: true, elevated: false };
  } catch (error) {
    if (!elevateIfNeeded) {
      return { ok: false, error };
    }
  }

  try {
    await runElevatedNetsh(buildNetshDeleteArgs());
    return { ok: true, removed: true, elevated: true };
  } catch (error) {
    return { ok: false, error };
  }
}

module.exports = {
  FIREWALL_RULE_NAME,
  lanPort,
  firewallRuleExists,
  ensureLanPortRule,
  removeLanPortRule
};
