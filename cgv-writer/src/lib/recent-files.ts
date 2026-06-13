const LAST_FILE_KEY = "cgv-writer-last-file";
const LAST_DIR_KEY = "cgv-writer-last-dir";

export function getLastOpenedPath(): string | null {
  try {
    return localStorage.getItem(LAST_FILE_KEY);
  } catch {
    return null;
  }
}

export function rememberOpenedPath(path: string): void {
  try {
    localStorage.setItem(LAST_FILE_KEY, path);
    const dir = path.replace(/[/\\][^/\\]+$/, "");
    if (dir) localStorage.setItem(LAST_DIR_KEY, dir);
  } catch {
    /* ignore */
  }
}

export function getLastOpenedDirectory(): string | undefined {
  try {
    return localStorage.getItem(LAST_DIR_KEY) || undefined;
  } catch {
    return undefined;
  }
}

export function clearLastOpenedPath(): void {
  try {
    localStorage.removeItem(LAST_FILE_KEY);
  } catch {
    /* ignore */
  }
}
