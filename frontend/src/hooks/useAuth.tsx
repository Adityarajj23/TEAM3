import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { api, ApiError } from "@/services/api";
import type { Me } from "@/types/models";

interface AuthCtx { me: Me | null; loading: boolean; can: (perm: string) => boolean; refresh: () => void; signOut: () => Promise<void> }
const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["me"], retry: false, staleTime: 60_000,
    queryFn: async () => {
      try { return await api.get<Me>("/auth/me"); } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
  });
  const me = q.data ?? null;
  const can = (perm: string) => !!me && (me.permissions.includes("*") || me.permissions.includes(perm));
  const signOut = async () => { await api.post("/auth/logout"); qc.clear(); qc.setQueryData(["me"], null); };
  return <Ctx.Provider value={{ me, loading: q.isLoading, can, refresh: () => q.refetch(), signOut }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
