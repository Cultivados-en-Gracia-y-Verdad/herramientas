import { useRef, useState, type ChangeEvent } from "react";
import { applyProgressBundle, downloadProgressFile, readProgressFile } from "./progress-io";

export default function ProgressControls() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const handleLoadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setBusy(true);
    try {
      const bundle = await readProgressFile(file);
      const confirmed = window.confirm(
        "This replaces your current Titus progress (marked verbs, clauses, moods, observations, notes) with what's in this file. Your current state isn't kept — this can't be undone. Continue?"
      );
      if (!confirmed) return;

      const summary = applyProgressBundle(bundle);
      window.alert(`Loaded ${summary.restoredCount} saved item(s). Reloading to pick up the change…`);
      window.location.reload();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Couldn't read that file.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="progress-controls" aria-label="Save or load Titus progress">
      <button type="button" className="progress-btn" onClick={downloadProgressFile} disabled={busy}>
        Save progress
      </button>
      <button type="button" className="progress-btn" onClick={handleLoadClick} disabled={busy}>
        Load progress
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        className="progress-file-input"
        onChange={handleFileChange}
      />
    </div>
  );
}
