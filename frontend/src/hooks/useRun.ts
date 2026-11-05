import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { Run } from "@/types/models";

const TERMINAL = ["completed", "failed", "degraded", "cancelled", "awaiting_review"];

/** Follows a background run via Server-Sent Events, falling back to polling if SSE is unavailable. */
export function useRun(runId: number | null) {
  const [sseRun, setSseRun] = useState<Run | null>(null);
  const [sseFailed, setSseFailed] = useState(false);
  useEffect(() => {
    setSseRun(null);
    setSseFailed(false);
    if (!runId || typeof EventSource === "undefined") { setSseFailed(true); return; }
    const es = new EventSource(`/api/v1/runs/${runId}/events`, { withCredentials: true });
    es.onmessage = (ev) => { try { setSseRun(JSON.parse(ev.data)); } catch { /* ignore malformed frame */ } };
    es.addEventListener("done", () => es.close());
    es.onerror = () => { es.close(); setSseFailed(true); };
    return () => es.close();
  }, [runId]);
  const poll = useQuery({
    queryKey: ["run", runId], enabled: !!runId && sseFailed, queryFn: () => api.get<Run>(`/runs/${runId}`),
    refetchInterval: (q) => (q.state.data && TERMINAL.includes(q.state.data.status) ? false : 1500),
  });
  const run = sseFailed ? poll.data ?? null : sseRun;
  return { run, done: !!run && TERMINAL.includes(run.status) };
}
