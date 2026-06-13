import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import { resolveBibleReference } from "cgv-bible";
import {
  getBibleLibraryStatus,
  invalidateBibleIndexCache,
  loadBibleIndex,
  type BibleIndex,
  type BibleStatus,
  type ResolveBibleReferenceResult
} from "./bible-client";
import {
  notifyBibleIndexUpdated,
  setSharedBibleIndex
} from "./bible-index-store";

interface BibleContextValue {
  status: BibleStatus | null;
  index: BibleIndex | null;
  loading: boolean;
  reload: () => Promise<void>;
  resolveReference: (reference: string) => Promise<ResolveBibleReferenceResult | null>;
}

const BibleContext = createContext<BibleContextValue | null>(null);

export function BibleProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<BibleStatus | null>(null);
  const [index, setIndex] = useState<BibleIndex | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    invalidateBibleIndexCache();

    const nextStatus = await getBibleLibraryStatus();
    setStatus(nextStatus);

    if (nextStatus.loaded) {
      const nextIndex = await loadBibleIndex(true);
      setIndex(nextIndex);
      setSharedBibleIndex(nextIndex);
    } else {
      setIndex(null);
      setSharedBibleIndex(null);
    }

    notifyBibleIndexUpdated();
    setLoading(false);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    const onLibraryChanged = () => {
      void reload();
    };

    window.addEventListener("cgv-bible-library-changed", onLibraryChanged);
    return () => window.removeEventListener("cgv-bible-library-changed", onLibraryChanged);
  }, [reload]);

  const resolveReference = useCallback(
    async (reference: string): Promise<ResolveBibleReferenceResult | null> => {
      const activeIndex = index ?? (await loadBibleIndex());
      if (!activeIndex) return null;
      if (!index) setIndex(activeIndex);
      return resolveBibleReference(reference, activeIndex);
    },
    [index]
  );

  const value = useMemo(
    () => ({ status, index, loading, reload, resolveReference }),
    [status, index, loading, reload, resolveReference]
  );

  return <BibleContext.Provider value={value}>{children}</BibleContext.Provider>;
}

export function useBible(): BibleContextValue {
  const context = useContext(BibleContext);
  if (!context) {
    throw new Error("useBible must be used within BibleProvider");
  }
  return context;
}
