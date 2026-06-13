const STORAGE_KEY = "cgv-writer-writing-mode";

export function loadWritingModePreference(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function saveWritingModePreference(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    /* ignore quota / private mode */
  }
}
