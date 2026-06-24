import { useEffect, useRef, useState } from "react";
import "./FileMenu.css";

interface FileMenuProps {
  lastOpenedPath: string | null;
  onNew: () => void;
  onOpen: () => void;
  onSave: () => void;
  onDuplicate: () => void;
  onReopenLast: () => void;
  onTemplate: () => void;
  onQuit: () => void;
}

export function FileMenu({
  lastOpenedPath,
  onNew,
  onOpen,
  onSave,
  onDuplicate,
  onReopenLast,
  onTemplate,
  onQuit
}: FileMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const pick = (action: () => void) => {
    setOpen(false);
    action();
  };

  const lastName = lastOpenedPath?.split(/[/\\]/).pop();

  return (
    <div className="file-menu" ref={rootRef}>
      <button
        type="button"
        className={open ? "active" : undefined}
        onClick={() => setOpen(value => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        Archivo
      </button>
      {open && (
        <div className="file-menu-dropdown" role="menu">
          <button type="button" role="menuitem" onClick={() => pick(onNew)}>
            Nuevo
            <span>⌘N</span>
          </button>
          <button type="button" role="menuitem" onClick={() => pick(onOpen)}>
            Abrir…
            <span>⌘O</span>
          </button>
          {lastOpenedPath && (
            <button type="button" role="menuitem" onClick={() => pick(onReopenLast)} title={lastOpenedPath}>
              Reabrir {lastName}
            </button>
          )}
          <hr />
          <button type="button" role="menuitem" onClick={() => pick(onSave)}>
            Guardar
            <span>⌘S</span>
          </button>
          <button type="button" role="menuitem" onClick={() => pick(onDuplicate)}>
            Duplicar como…
          </button>
          <hr />
          <button type="button" role="menuitem" onClick={() => pick(onTemplate)}>
            Nueva plantilla
          </button>
          <hr />
          <button type="button" role="menuitem" onClick={() => pick(onQuit)}>
            Salir
            <span>⌘Q</span>
          </button>
        </div>
      )}
    </div>
  );
}
