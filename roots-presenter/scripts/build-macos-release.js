const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const { version } = require('../package.json');

const appBundle = path.join(root, 'out', 'CGV Presenter-darwin-arm64', 'CGV Presenter.app');
const installerScript = path.join(__dirname, 'Install CGV Presenter.applescript');
const installerApp = path.join(root, 'out', 'make', 'Install CGV Presenter.app');
const readmeSource = path.join(__dirname, 'macos-release-readme.txt');
const stagingDir = path.join(root, 'out', 'make', `CGV-Presenter-macOS-arm64-${version}`);
const releaseZip = path.join(root, 'out', 'make', `CGV-Presenter-macOS-arm64-${version}.zip`);

function run(command) {
  execSync(command, { stdio: 'inherit' });
}

function quote(value) {
  return JSON.stringify(value);
}

if (!fs.existsSync(appBundle)) {
  throw new Error(`Packaged app not found: ${appBundle}. Run npm run make:mac first.`);
}

fs.mkdirSync(path.dirname(releaseZip), { recursive: true });
fs.rmSync(installerApp, { recursive: true, force: true });
fs.rmSync(stagingDir, { recursive: true, force: true });
fs.mkdirSync(stagingDir, { recursive: true });

run(`osacompile -o ${quote(installerApp)} ${quote(installerScript)}`);
run(`codesign --force --deep --sign - ${quote(installerApp)}`);

run(`ditto ${quote(appBundle)} ${quote(path.join(stagingDir, 'CGV Presenter.app'))}`);
run(`ditto ${quote(installerApp)} ${quote(path.join(stagingDir, 'Install CGV Presenter.app'))}`);
fs.copyFileSync(readmeSource, path.join(stagingDir, 'README - Start Here.txt'));

fs.rmSync(releaseZip, { force: true });
run(`cd ${quote(stagingDir)} && zip -r -X ${quote(releaseZip)} .`);

console.log(`Created ${releaseZip}`);
