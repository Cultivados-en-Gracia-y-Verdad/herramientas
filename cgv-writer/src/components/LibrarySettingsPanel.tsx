import { open } from "@tauri-apps/plugin-dialog";
import { useCallback, useEffect, useState } from "react";
import {
  getBibleLibraryStatus,
  readWriterSettings,
  saveWriterSettings,
  type BibleStatus
} from "../lib/bible-client";
import { isTauriRuntime } from "../lib/tauri-env";
import "./LibrarySettingsPanel.css";

function shortenPath(path: string, max = 42): string {
  if (path.length <= max) return path;
  const parts = path.split(/[/\\]/);
  const file = parts.pop() ?? path;
  if (parts.length === 0) return file;
  return `…/${parts.slice(-2).join("/")}/${file}`;
}

export function LibrarySettingsPanel() {
  const [libraryRootDir, setLibraryRootDir] = useState<string | null>(null);
  const [bibleVersion, setBibleVersion] = useState("NBLA");
  const [status, setStatus] = useState<BibleStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    const next = await getBibleLibraryStatus();
    setStatus(next);
    return next;
  }, []);

  useEffect(() => {
    void (async () => {
      const settings = await readWriterSettings();
      setLibraryRootDir(settings.libraryRootDir ?? null);
      setBibleVersion(settings.bibleVersion ?? "NBLA");
      await refreshStatus();
    })();
  }, [refreshStatus]);

  const chooseLibraryFolder = useCallback(async () => {
    setBusy(true);
    setMessage(null);

    try {
      const picked = await open({
        directory: true,
        multiple: false,
        title: "Elegir carpeta de biblioteca CGV"
      });

      if (!picked || typeof picked !== "string") {
        return;
      }

      const settings = await readWriterSettings();
      const nextSettings = {
        ...settings,
        libraryRootDir: picked,
        bibleVersion: settings.bibleVersion ?? "NBLA"
      };

      await saveWriterSettings(nextSettings);
      setLibraryRootDir(picked);
      window.dispatchEvent(new CustomEvent("cgv-bible-library-changed"));

      const nextStatus = await refreshStatus();
      if (nextStatus.loaded) {
        setMessage(
          `Biblioteca conectada: ${nextStatus.books} libros, ${nextStatus.references.toLocaleString()} versículos (${nextStatus.version}).`
        );
      } else {
        setMessage(nextStatus.error ?? "No se encontraron biblias en esa carpeta.");
      }
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  }, [refreshStatus]);

  const handleVersionChange = useCallback(
    async (version: string) => {
      if (!libraryRootDir) return;

      setBusy(true);
      setMessage(null);

      try {
        const settings = await readWriterSettings();
        await saveWriterSettings({
          ...settings,
          libraryRootDir,
          bibleVersion: version
        });
        setBibleVersion(version);
        window.dispatchEvent(new CustomEvent("cgv-bible-library-changed"));
        await refreshStatus();
      } catch (error) {
        setMessage(String(error));
      } finally {
        setBusy(false);
      }
    },
    [libraryRootDir, refreshStatus]
  );

  const versions =
    status?.availableVersions?.length ? status.availableVersions : bibleVersion ? [bibleVersion] : ["NBLA"];

  return (
    <section className="panel panel-library">
      <h2>Biblioteca CGV</h2>
      <p className="panel-meta library-help">
        Use la misma carpeta raíz que CGV Presenter — la que contiene{" "}
        <code>bibles/</code>, <code>courses/</code>, etc. (no elija solo <code>bibles/NBLA</code>).
      </p>

      {!isTauriRuntime() && (
        <p className="library-warning">
          Abra CGV Writer con <code>npm run tauri:dev</code>. En el navegador solo no puede leer la biblioteca.
        </p>
      )}

      <div className="library-path">
        {libraryRootDir ? shortenPath(libraryRootDir) : "Sin configurar"}
      </div>

      <button
        type="button"
        className="library-choose"
        onClick={() => void chooseLibraryFolder()}
        disabled={busy}
      >
        Elegir carpeta…
      </button>

      {libraryRootDir && versions.length > 1 && (
        <label className="library-version">
          <span>Versión</span>
          <select
            value={bibleVersion}
            onChange={event => void handleVersionChange(event.target.value)}
            disabled={busy}
          >
            {versions.map(version => (
              <option key={version} value={version}>
                {version}
              </option>
            ))}
          </select>
        </label>
      )}

      <ul className="library-status-list">
        <li className={status?.loaded ? "ok" : status?.configured ? "warn" : undefined}>
          {status?.loaded
            ? `${status.version}: ${status.books} libros, ${status.references.toLocaleString()} versículos — clic en referencias H3`
            : status?.configured
              ? status.error ?? "Biblias no encontradas"
              : "Seleccione la carpeta de biblioteca"}
        </li>
        {status?.bibleDir && (
          <li className="library-dir" title={status.bibleDir}>
            {shortenPath(status.bibleDir, 48)}
          </li>
        )}
      </ul>

      {message && <p className="library-message">{message}</p>}
    </section>
  );
}
