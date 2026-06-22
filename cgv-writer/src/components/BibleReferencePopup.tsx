import { formatBibleVerseLabel } from "cgv-bible";
import type { ResolveBibleReferenceResult } from "cgv-bible";
import "./BibleReferencePopup.css";

interface BibleReferencePopupProps {
  open: boolean;
  reference: string;
  version: string;
  loading: boolean;
  error: string | null;
  result: ResolveBibleReferenceResult | null;
  showUseText?: boolean;
  onClose: () => void;
  onUseText: () => void;
}

export function BibleReferencePopup({
  open,
  reference,
  version,
  loading,
  error,
  result,
  showUseText = true,
  onClose,
  onUseText
}: BibleReferencePopupProps) {
  if (!open) return null;

  return (
    <div className="bible-popup-overlay" onClick={onClose}>
      <div
        className="bible-popup-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bible-popup-title"
        onClick={event => event.stopPropagation()}
      >
        <header className="bible-popup-header">
          <div>
            <p className="bible-popup-version">{version}</p>
            <h3 id="bible-popup-title">{reference}</h3>
          </div>
          <button type="button" className="bible-popup-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>

        <div className="bible-popup-body">
          {loading && <p className="bible-popup-status">Buscando versículo…</p>}
          {!loading && error && <p className="bible-popup-error">{error}</p>}
          {!loading && !error && result?.verses.map(verse => (
            <p key={`${verse.book}-${verse.chapter}-${verse.verse}`} className="bible-popup-verse">
              <strong>{formatBibleVerseLabel(verse)}</strong> {verse.text}
            </p>
          ))}
        </div>

        <footer className="bible-popup-footer">
          {!loading && showUseText && result?.verses.length ? (
            <button type="button" className="primary" onClick={onUseText}>
              Agregar texto NBLA
            </button>
          ) : null}
          <button type="button" onClick={onClose}>
            Cerrar
          </button>
        </footer>
      </div>
    </div>
  );
}
