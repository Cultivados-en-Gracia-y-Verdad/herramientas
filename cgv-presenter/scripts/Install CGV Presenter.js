ObjC.import('Cocoa');

const fileManager = $.NSFileManager.defaultManager;
const appName = 'CGV Presenter.app';
const setupTitle = 'CGV Presenter Setup';

function ns(value) {
  return $(String(value));
}

function alert(message, buttons) {
  const dialog = $.NSAlert.alloc.init;
  dialog.messageText = setupTitle;
  dialog.informativeText = message;
  buttons.forEach((button) => dialog.addButtonWithTitle(button));
  return dialog.runModal();
}

function runTask(path, args) {
  const task = $.NSTask.alloc.init;
  task.launchPath = path;
  task.arguments = args.map(String);
  task.launch;
  task.waitUntilExit;
  return task.terminationStatus;
}

function fail(message) {
  alert(`Installation could not be completed.\n\n${message}`, ['OK']);
}

function main() {
  try {
    const installerPath = ObjC.unwrap($.NSBundle.mainBundle.bundlePath);
    const sourceFolder = ObjC.unwrap(ns(installerPath).stringByDeletingLastPathComponent);
    const sourcePath = `${sourceFolder}/${appName}`;
    const targetPath = `/Applications/${appName}`;

    if (!fileManager.fileExistsAtPath(sourcePath)) {
      alert(
        'Could not find CGV Presenter in the same folder as this installer.\n\nPlease unzip the full download, then double-click Install CGV Presenter again.',
        ['OK']
      );
      return;
    }

    const installChoice = alert(
      'This will install CGV Presenter in your Applications folder.\n\nBecause CGV Presenter is distributed directly by Cultivados en Gracia y Verdad (not through the Mac App Store), macOS requires a one-time local setup step.\n\nClick Install to continue.',
      ['Install', 'Cancel']
    );

    if (installChoice !== $.NSAlertFirstButtonReturn) {
      return;
    }

    if (fileManager.fileExistsAtPath(targetPath)) {
      if (!fileManager.removeItemAtPathError(targetPath, null)) {
        throw new Error(`Could not replace the existing app at ${targetPath}`);
      }
    }

    if (!fileManager.copyItemAtPathToPathError(sourcePath, targetPath, null)) {
      throw new Error(`Could not copy CGV Presenter to ${targetPath}`);
    }

    if (runTask('/usr/bin/xattr', ['-cr', targetPath]) !== 0) {
      throw new Error('Could not clear the macOS quarantine flag.');
    }

    const launchChoice = alert(
      'CGV Presenter was installed successfully.\n\nYou can open it from Applications like any other app.',
      ['Open CGV Presenter', 'Done']
    );

    if (launchChoice === $.NSAlertFirstButtonReturn) {
      runTask('/usr/bin/open', [targetPath]);
    }
  } catch (error) {
    fail(error.message || String(error));
  }
}

main();
