import { CheckCircle2, XCircle } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { ApiError } from "@/services/api";

type T = { id: number; kind: "ok" | "error"; text: string; trace?: string | null };
const Ctx = createContext<{ ok: (t: string) => void; error: (e: unknown) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const push = useCallback((t: Omit<T, "id">) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { ...t, id }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), t.kind === "error" ? 8000 : 4000);
  }, []);
  const ok = useCallback((text: string) => push({ kind: "ok", text }), [push]);
  const error = useCallback((e: unknown) => push({ kind: "error", text: e instanceof Error ? e.message : String(e),
    trace: e instanceof ApiError ? e.traceId : null }), [push]);
  return (
    <Ctx.Provider value={{ ok, error }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className="flex items-start gap-2 rounded-md border border-slate-200 bg-white px-3 py-2.5 text-sm shadow-lg">
            {t.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" /> : <XCircle className="mt-0.5 h-4 w-4 text-red-600" />}
            <div className="min-w-0"><p className="text-ink">{t.text}</p>
              {t.trace && <p className="font-mono text-2xs text-slate-500">Trace ID {t.trace}</p>}</div>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useToast outside ToastProvider");
  return c;
}
