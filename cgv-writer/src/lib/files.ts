import { invoke } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";
import { getLastOpenedDirectory, rememberOpenedPath } from "./recent-files";

export async function readManualByPath(path: string): Promise<string> {
  return invoke<string>("read_manual", { path });
}

export async function takeOpenedManualPaths(): Promise<string[]> {
  return invoke<string[]>("take_opened_manual_paths");
}

export async function openManualFile(): Promise<{ path: string; content: string } | null> {
  const path = await open({
    multiple: false,
    directory: false,
    defaultPath: getLastOpenedDirectory(),
    filters: [{ name: "Markdown", extensions: ["md"] }]
  });

  if (!path || typeof path !== "string") return null;

  const content = await readManualByPath(path);
  rememberOpenedPath(path);
  return { path, content };
}

export async function saveManualFile(
  path: string | null,
  content: string
): Promise<string | null> {
  let target = path;

  if (!target) {
    const picked = await save({
      filters: [{ name: "Markdown", extensions: ["md"] }],
      defaultPath: "manual.md"
    });
    if (!picked || typeof picked !== "string") return null;
    target = picked;
  }

  await invoke("write_manual", { path: target, content });
  rememberOpenedPath(target);
  return target;
}

function defaultDuplicatePath(path: string | null): string {
  if (!path) return "manual copia.md";

  const separatorIndex = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  const directory = separatorIndex >= 0 ? path.slice(0, separatorIndex + 1) : "";
  const fileName = separatorIndex >= 0 ? path.slice(separatorIndex + 1) : path;
  const dotIndex = fileName.lastIndexOf(".");
  const hasExtension = dotIndex > 0;
  const base = hasExtension ? fileName.slice(0, dotIndex) : fileName;
  const extension = hasExtension ? fileName.slice(dotIndex) : ".md";

  return `${directory}${base} copia${extension}`;
}

export async function duplicateManualFile(
  sourcePath: string | null,
  content: string
): Promise<string | null> {
  const picked = await save({
    filters: [{ name: "Markdown", extensions: ["md"] }],
    defaultPath: defaultDuplicatePath(sourcePath)
  });
  if (!picked || typeof picked !== "string") return null;

  if (sourcePath && picked === sourcePath) {
    throw new Error("Elija un nombre distinto para la copia.");
  }

  await invoke("write_manual", { path: picked, content });
  return picked;
}

export async function loadStarterTemplate(): Promise<string> {
  const res = await fetch("/templates/manual-starter.md");
  return res.text();
}
