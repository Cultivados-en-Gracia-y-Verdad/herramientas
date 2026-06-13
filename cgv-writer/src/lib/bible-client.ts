import { invoke } from "@tauri-apps/api/core";
import {
  buildBibleIndex,
  isEmptyBibleIndex,
  resolveBibleReference,
  type BibleFile,
  type BibleIndex,
  type ResolveBibleReferenceResult
} from "cgv-bible";

export interface WriterSettings {
  libraryRootDir?: string | null;
  bibleVersion?: string | null;
}

export interface BibleStatus {
  configured: boolean;
  libraryRootDir?: string | null;
  version: string;
  loaded: boolean;
  books: number;
  references: number;
  bibleDir?: string | null;
  availableVersions: string[];
  error?: string | null;
}

export type { BibleIndex, ResolveBibleReferenceResult };
export { formatBiblePopupText, formatScriptureLine } from "cgv-bible";

export async function readWriterSettings(): Promise<WriterSettings> {
  try {
    return await invoke<WriterSettings>("read_writer_settings");
  } catch {
    return {};
  }
}

export async function saveWriterSettings(settings: WriterSettings): Promise<void> {
  await invoke("save_writer_settings", { settings });
}

export async function getBibleLibraryStatus(): Promise<BibleStatus> {
  try {
    return await invoke<BibleStatus>("get_bible_library_status");
  } catch (error) {
    return {
      configured: false,
      version: "NBLA",
      loaded: false,
      books: 0,
      references: 0,
      availableVersions: [],
      error: String(error)
    };
  }
}

async function readBibleFilesFromDisk(): Promise<BibleFile[]> {
  return invoke<BibleFile[]>("read_bible_files_command");
}

let cachedIndex: BibleIndex | null = null;
let loadPromise: Promise<BibleIndex | null> | null = null;

export function invalidateBibleIndexCache(): void {
  cachedIndex = null;
  loadPromise = null;
}

export async function loadBibleIndex(force = false): Promise<BibleIndex | null> {
  if (!force && cachedIndex && !isEmptyBibleIndex(cachedIndex)) {
    return cachedIndex;
  }

  if (!force && loadPromise) {
    return loadPromise;
  }

  loadPromise = (async () => {
    try {
      const settings = await readWriterSettings();
      if (!settings.libraryRootDir?.trim()) {
        cachedIndex = null;
        return null;
      }

      const files = await readBibleFilesFromDisk();
      if (!files.length) {
        cachedIndex = null;
        return null;
      }

      cachedIndex = buildBibleIndex(files, settings.bibleVersion ?? "NBLA");
      return cachedIndex;
    } catch {
      cachedIndex = null;
      return null;
    } finally {
      loadPromise = null;
    }
  })();

  return loadPromise;
}

export async function resolveReferenceFromLibrary(
  reference: string
): Promise<ResolveBibleReferenceResult | null> {
  const index = await loadBibleIndex();
  if (!index) return null;
  return resolveBibleReference(reference, index);
}
