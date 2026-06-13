import "./EmptyWelcome.css";

interface EmptyWelcomeProps {
  lastOpenedPath: string | null;
  onOpen: () => void;
  onNew: () => void;
  onReopenLast: () => void;
  onTemplate: () => void;
}

export function EmptyWelcome({
  lastOpenedPath,
  onOpen,
  onNew,
  onReopenLast,
  onTemplate
}: EmptyWelcomeProps) {
  const lastName = lastOpenedPath?.split(/[/\\]/).pop();

  return (
    <div className="empty-welcome">
      <div className="empty-welcome-card">
        <h2>CGV Writer</h2>
        <p>Escriba un manual para Presenter, o abra un archivo <code>.md</code> existente.</p>
        <div className="empty-welcome-actions">
          <button type="button" className="primary" onClick={onOpen}>
            Abrir archivo…
            <span className="empty-welcome-shortcut">⌘O</span>
          </button>
          <button type="button" onClick={onNew}>
            Nuevo documento
            <span className="empty-welcome-shortcut">⌘N</span>
          </button>
          {lastOpenedPath && (
            <button type="button" onClick={onReopenLast} title={lastOpenedPath}>
              Reabrir {lastName}
            </button>
          )}
          <button type="button" className="subtle" onClick={onTemplate}>
            Empezar desde plantilla
          </button>
        </div>
      </div>
    </div>
  );
}
