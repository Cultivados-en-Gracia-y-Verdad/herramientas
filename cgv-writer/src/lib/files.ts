import { invoke } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";
import { getLastOpenedDirectory, rememberOpenedPath } from "./recent-files";

export async function readManualByPath(path: string): Promise<string> {
  return invoke<string>("read_manual", { path });
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

export async function loadStarterTemplate(): Promise<string> {
  const res = await fetch("/templates/manual-starter.md");
  return res.text();
}
