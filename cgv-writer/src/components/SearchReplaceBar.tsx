import { useCallback, useEffect, useRef, useState } from "react";
import {
  dispatchSearch,
  dispatchSearchClose,
  type SearchReport
} from "../lib/search-bridge";
import "./SearchReplaceBar.css";

interface SearchReplaceBarProps {
  visible: boolean;
  showReplace: boolean;
  onShowReplaceChange: (show: boolean) => void;
  onClose: () => void;
}

function insertAtFindInput(input: HTMLInputElement, current: string, text: string): string {
  const start = input.selectionStart ?? current.length;
  const end = input.selectionEnd ?? current.length;
  const next = current.slice(0, start) + text + current.slice(end);
  const caret = start + text.length;
  requestAnimationFrame(() => {
    input.focus();
    input.setSelectionRange(caret, caret);
  });
  return next;
}

function isSearchBarField(target: EventTarget | null): target is HTMLInputElement | HTMLTextAreaElement {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement
  ) && target.closest(".search-replace-bar") != null;
}

export function SearchReplaceBar({
  visible,
  showReplace,
  onShowReplaceChange,
  onClose
}: SearchReplaceBarProps) {
  const [query, setQuery] = useState("");
  const [replace, setReplace] = useState("");
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [report, setReport] = useState<SearchReport>({ total: 0, current: 0 });
  const findRef = useRef<HTMLInputElement>(null);

  const focusFind = useCallback(() => {
    requestAnimationFrame(() => findRef.current?.focus());
  }, []);

  const pasteIntoFind = useCallback((text: string) => {
    const input = findRef.current;
    if (!input || !text) return;
    setQuery(current => insertAtFindInput(input, current, text));
  }, []);

  useEffect(() => {
    if (!visible) return;
    focusFind();
  }, [visible, showReplace, focusFind]);

  useEffect(() => {
    const onOpen = (event: Event) => {
      const detail = (event as CustomEvent<{ showReplace?: boolean; seed?: string }>).detail;
      if (detail?.showReplace) onShowReplaceChange(true);
      const seed = detail?.seed?.trim() ?? "";
      setQuery(seed);
      setReport({ total: 0, current: 0 });
      requestAnimationFrame(() => {
        findRef.current?.focus();
        if (seed) {
          findRef.current?.select();
        }
      });
    };
    const onReport = (event: Event) => {
      setReport((event as CustomEvent<SearchReport>).detail);
    };
    const onCloseEvent = () => onClose();

    window.addEventListener("cgv-search-open", onOpen);
    window.addEventListener("cgv-search-report", onReport);
    window.addEventListener("cgv-search-close", onCloseEvent);
    return () => {
      window.removeEventListener("cgv-search-open", onOpen);
      window.removeEventListener("cgv-search-report", onReport);
      window.removeEventListener("cgv-search-close", onCloseEvent);
    };
  }, [onClose, onShowReplaceChange]);

  useEffect(() => {
    if (visible) return;
    setQuery("");
    setReplace("");
    setCaseSensitive(false);
    setReport({ total: 0, current: 0 });
    dispatchSearch({ query: "", replace: "", caseSensitive: false, action: "clear" });
  }, [visible]);

  const run = useCallback(
    (action: "find" | "next" | "prev" | "replace" | "replaceAll", refocus = true) => {
      dispatchSearch({ query, replace, caseSensitive, action });
      if (refocus) focusFind();
    },
    [query, replace, caseSensitive, focusFind]
  );

  useEffect(() => {
    if (!visible || !query) return;
    const timer = window.setTimeout(() => {
      dispatchSearch({ query, replace, caseSensitive, action: "find" });
    }, 200);
    return () => window.clearTimeout(timer);
  }, [visible, query, caseSensitive, replace]);

  useEffect(() => {
    if (!visible) return;

    const onPaste = (event: ClipboardEvent) => {
      if (isSearchBarField(event.target)) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      const text = event.clipboardData?.getData("text/plain") ?? "";
      pasteIntoFind(text);
    };

    document.addEventListener("paste", onPaste, true);
    return () => document.removeEventListener("paste", onPaste, true);
  }, [visible, pasteIntoFind]);

  useEffect(() => {
    if (!visible) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (!isSearchBarField(event.target)) return;

      event.stopPropagation();

      const mod = event.metaKey || event.ctrlKey;
      if (mod && event.key.toLowerCase() === "g") {
        event.preventDefault();
        dispatchSearch({
          query,
          replace,
          caseSensitive,
          action: event.shiftKey ? "prev" : "next"
        });
        return;
      }

      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        dispatchSearch({ query, replace, caseSensitive, action: "next" });
        return;
      }

      if (event.key === "Enter" && event.shiftKey) {
        event.preventDefault();
        dispatchSearch({ query, replace, caseSensitive, action: "prev" });
      }
    };

    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [visible, query, replace, caseSensitive]);

  if (!visible) return null;

  const meta =
    report.total === 0
      ? query
        ? "Sin coincidencias"
        : ""
      : report.current
        ? `${report.current} / ${report.total}`
        : `${report.total}`;

  return (
    <form
      className="search-replace-bar"
      onSubmit={event => {
        event.preventDefault();
        run("next");
      }}
      onMouseDown={event => {
        if (!(event.target instanceof HTMLInputElement)) {
          event.preventDefault();
          focusFind();
        }
      }}
    >
      <label>
        Buscar
        <input
          ref={findRef}
          type="text"
          value={query}
          onChange={event => setQuery(event.target.value)}
          onPaste={event => event.stopPropagation()}
          onCopy={event => event.stopPropagation()}
          onCut={event => event.stopPropagation()}
          onKeyDown={event => {
            event.stopPropagation();
            if (event.key === "Escape") {
              event.preventDefault();
              onClose();
            }
          }}
          spellCheck={false}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
        />
      </label>

      {showReplace && (
        <label>
          Reemplazar
          <input
            type="text"
            value={replace}
            onChange={event => setReplace(event.target.value)}
            onPaste={event => event.stopPropagation()}
            onCopy={event => event.stopPropagation()}
            onCut={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
          />
        </label>
      )}

      <label className="search-case-toggle">
        <input
          type="checkbox"
          checked={caseSensitive}
          onChange={event => setCaseSensitive(event.target.checked)}
        />
        Aa
      </label>

      <div className="search-replace-actions">
        <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => run("prev")} title="Anterior (⇧Enter)">
          ↑
        </button>
        <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => run("next")} title="Siguiente (Enter)">
          ↓
        </button>
        {showReplace && (
          <>
            <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => run("replace")} title="Reemplazar">
              Reemplazar
            </button>
            <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => run("replaceAll")} title="Reemplazar todo">
              Todo
            </button>
          </>
        )}
        {!showReplace && (
          <button type="button" onMouseDown={event => event.preventDefault()} onClick={() => onShowReplaceChange(true)}>
            Reemplazar…
          </button>
        )}
        <button
          type="button"
          className="search-close"
          onMouseDown={event => event.preventDefault()}
          onClick={() => {
            dispatchSearchClose();
            onClose();
          }}
          title="Cerrar (Escape)"
        >
          ✕
        </button>
      </div>

      <span className="search-replace-meta" aria-live="polite">
        {meta}
      </span>
    </form>
  );
}
