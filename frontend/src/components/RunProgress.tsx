import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { useEffect, useRef } from "react";
import { Badge, Notice } from "@/components/ui";
import { useRun } from "@/hooks/useRun";
import { label } from "@/utils/format";

export function RunProgress({ runId, onDone }: { runId: number; onDone?: (status: string) => void }) {
  const { run, done } = useRun(runId);
  const fired = useRef(false);
  const status = run?.status;
  useEffect(() => {
    if (done && status && onDone && !fired.current) { fired.current = true; onDone(status); }
  }, [done, status, onDone]);
  if (!run) return <p className="flex items-center gap-2 text-sm text-slate-600"><Loader2 className="h-4 w-4 animate-spin" />Starting…</p>;
  const errs: string[] = [...(run.result?.provider_errors ?? []), ...((run.result?.invalid_items ?? []) as any[]).map((i) => i.error)];
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="flex items-center gap-2">
        <Badge value={run.status} />
        <div className="h-1.5 flex-1 overflow-hidden rounded bg-slate-100">
          <div className="h-full bg-accent transition-all" style={{ width: `${Math.round((run.progress ?? 0) * 100)}%` }} />
        </div>
        <span className="text-xs tabular-nums text-slate-600">{Math.round((run.progress ?? 0) * 100)}%</span>
      </div>
      <ol className="space-y-1 text-sm">
        {(run.steps ?? []).map((s, i) => (
          <li key={i} className="flex items-center gap-2">
            {s.status === "completed" || s.status === "passed" || s.status === "reused" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> :
              s.status === "failed" || s.status === "error" ? <XCircle className="h-4 w-4 text-red-600" /> :
                <CircleDashed className="h-4 w-4 text-amber-600" />}
            <span className="text-ink">{label(s.name)}</span><span className="text-xs text-slate-500">{label(s.status)}</span>
          </li>
        ))}
      </ol>
      {run.status === "degraded" && <Notice tone="warn">The workflow finished in a degraded state. Deterministic results were kept;
        AI output that failed validation was not saved and needs manual authoring.</Notice>}
      {run.status === "failed" && <Notice tone="danger">{run.error}</Notice>}
      {errs.length > 0 && <ul className="list-disc space-y-0.5 pl-5 text-xs text-amber-900">{errs.slice(0, 6).map((e, i) => <li key={i}>{e}</li>)}</ul>}
      {run.status === "awaiting_review" && <Notice>Generated items are waiting for human review. The workflow resumes
        automatically once each item has a decision.</Notice>}
    </div>
  );
}
