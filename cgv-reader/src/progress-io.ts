// All working state for Titus currently lives scattered across localStorage
// keys — fast, but tied to one browser profile. A single cache clear (or the
// browser-pane-reset we just hit) can erase months of observation work with
// no way back. This module bundles everything into one portable JSON file
// the student can save, hand off, or commit to git for real version history.

export interface ProgressKeyInfo {
  key: string;
  label: string;
}

export const PROGRESS_KEYS: ProgressKeyInfo[] = [
  { key: "the-reader:titus:notes", label: "Notes" },
  { key: "o-prototype:titus:finite-verb-marks", label: "Finite verb marks (Brick 1)" },
  { key: "roots:titus:brick2:mood:imperativeCandidates", label: "Command mood marks" },
  { key: "roots:titus:brick2c:mood:statementCandidates", label: "Statement mood marks" },
  { key: "roots:titus:brick3:mood:subjunctiveCandidates", label: "Subjunctive mood marks" },
  { key: "roots:titus:brick3c:mood:optativeCandidates", label: "Optative mood marks" },
  { key: "roots:titus:brick2b:commandRecipients", label: "Command recipients" },
  { key: "roots:titus:brick3:dependentThoughtIntroducers", label: "Dependent introducer marks" },
  { key: "the-reader:spanish-clause-builder:titus:v3", label: "Clause spans" },
  { key: "the-reader:spanish-clause-builder:titus:statement-command-review:v1", label: "Clause observations" }
];

const KNOWN_KEYS = new Set(PROGRESS_KEYS.map(entry => entry.key));

export interface ProgressBundle {
  schema: 1;
  book: "titus";
  exportedAt: string;
  data: Record<string, unknown>;
}

export function buildProgressBundle(): ProgressBundle {
  const data: Record<string, unknown> = {};

  for (const { key } of PROGRESS_KEYS) {
    const raw = window.localStorage.getItem(key);
    if (raw === null) continue;
    try {
      data[key] = JSON.parse(raw);
    } catch {
      // Skip a corrupt entry rather than fail the whole export over one key.
    }
  }

  return { schema: 1, book: "titus", exportedAt: new Date().toISOString(), data };
}

// Browsers give JS no API to write to an arbitrary folder — the `download`
// attribute only accepts a path relative to the browser's configured
// Downloads directory (and only Chromium browsers honor the subfolder; others
// fall back to the flat filename). This is a stand-in until a real
// preferences menu lets the student point exports wherever they want.
const EXPORT_SUBFOLDER = "cgv-reader";

export function downloadProgressFile(): void {
  const bundle = buildProgressBundle();
  const json = JSON.stringify(bundle, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${EXPORT_SUBFOLDER}/titus-progress-${bundle.exportedAt.slice(0, 10)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function readProgressFile(file: File): Promise<unknown> {
  return file.text().then(text => JSON.parse(text));
}

export interface ImportSummary {
  restoredCount: number;
  unrecognizedKeys: string[];
}

export function applyProgressBundle(bundle: unknown): ImportSummary {
  if (!bundle || typeof bundle !== "object") {
    throw new Error("That file doesn't look like a Titus progress export.");
  }

  const record = bundle as Record<string, unknown>;
  if (record.book !== "titus" || !record.data || typeof record.data !== "object") {
    throw new Error("That file doesn't look like a Titus progress export.");
  }

  const data = record.data as Record<string, unknown>;
  const unrecognizedKeys: string[] = [];
  let restoredCount = 0;

  for (const [key, value] of Object.entries(data)) {
    window.localStorage.setItem(key, JSON.stringify(value));
    restoredCount += 1;
    if (!KNOWN_KEYS.has(key)) unrecognizedKeys.push(key);
  }

  return { restoredCount, unrecognizedKeys };
}
