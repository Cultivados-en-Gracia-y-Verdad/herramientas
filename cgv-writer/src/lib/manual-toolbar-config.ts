/** Toolbar actions that can be hidden in the Manual tab (use Presentación tab instead). */
export type ManualToolbarCommandId = "slideBreak" | "quiz";

/** Hidden by default in Manual view — add IDs here as more move to Presentación. */
export const MANUAL_HIDDEN_COMMANDS: ManualToolbarCommandId[] = ["quiz"];

export function isManualCommandVisible(id: ManualToolbarCommandId): boolean {
  return !MANUAL_HIDDEN_COMMANDS.includes(id);
}
