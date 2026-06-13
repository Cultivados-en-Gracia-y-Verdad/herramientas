import { message } from "@tauri-apps/plugin-dialog";

export async function confirmAction(
  text: string,
  options: { title: string; okLabel?: string; cancelLabel?: string } = {
    title: "CGV Writer"
  }
): Promise<boolean> {
  const okLabel = options.okLabel ?? "Continuar";
  try {
    const result = await message(text, {
      title: options.title,
      kind: "warning",
      buttons: { ok: okLabel, cancel: options.cancelLabel ?? "Cancelar" }
    });
    // macOS may return "Ok" instead of the custom label for the primary button.
    return result === okLabel || result === "Ok";
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
