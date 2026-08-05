#!/usr/bin/env node
const http = require("http");
const { spawn } = require("child_process");
const path = require("path");

const port = 3491;
const root = path.join(__dirname, "..");
const child = spawn(process.execPath, ["server.js"], {
  cwd: root,
  env: { ...process.env, PORT: String(port) },
  stdio: ["ignore", "pipe", "pipe"]
});

function waitReady() {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), 25000);
    const onData = chunk => {
      if (/running at/i.test(String(chunk))) {
        clearTimeout(timer);
        resolve();
      }
    };
    child.stdout.on("data", onData);
    child.stderr.on("data", onData);
  });
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let body = "";
      res.on("data", chunk => { body += chunk; });
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    }).on("error", reject);
  });
}

(async () => {
  await waitReady();
  const text = "### 1 Juan 1:5:2 — Este es el mensaje: Dios es luz";
  const json = await getJson(`http://127.0.0.1:${port}/bible/test?text=${encodeURIComponent(text)}`);
  console.log(json.html);
  const checks = {
    hasMark: /bible-clause-hit/.test(json.html),
    hasStartWord: /data-start-word="2"/.test(json.html),
    fullId: /1 Juan 1:5:2/.test(json.html),
    orphaned: /1:5<\/span>:2|:2 —/.test(json.html),
    exactClause: /<mark class="bible-clause-hit">[^<]*mensaje[^<]*<\/mark>/i.test(json.html)
      && !/<mark class="bible-clause-hit">[^<]*que hemos/i.test(json.html)
  };
  console.log(checks);
  child.kill("SIGTERM");
  if (!checks.hasMark || !checks.hasStartWord || !checks.fullId || checks.orphaned || !checks.exactClause) {
    process.exit(1);
  }
})().catch(error => {
  console.error(error);
  child.kill("SIGTERM");
  process.exit(1);
});
