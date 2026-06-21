import { confirm } from "@tauri-apps/plugin-dialog";

export async function confirmAction(
  text: string,
  options: { title: string; okLabel?: string; cancelLabel?: string } = {
    title: "CGV Writer"
  }
): Promise<boolean> {
  try {
    return await confirm(text, {
      title: options.title,
      kind: "warning",
      okLabel: options.okLabel ?? "Continuar",
      cancelLabel: options.cancelLabel ?? "Cancelar"
    });
  } catch {
    return window.confirm(`${options.title}\n\n${text}`);
  }
}

/** Let a native message dialog fully dismiss before opening another native dialog. */
export function deferNativeDialog(): Promise<void> {
  return new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  });
}
