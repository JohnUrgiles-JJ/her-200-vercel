"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, clearToken, getJSON, getToken, type User } from "@/lib/api";

const SessionContext = createContext<{ user: User; logout: () => void } | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  const logout = useCallback(() => {
    clearToken();
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    if (!getToken()) return logout();
    getJSON<User>("/api/me/")
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) logout();
      });
  }, [logout]);

  if (!user) return <div className="flex min-h-screen items-center justify-center text-muted">Loading…</div>;
  return <SessionContext.Provider value={{ user, logout }}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}

/** Fetch a GET endpoint; pass null to skip. Call `reload` after mutations. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    getJSON<T>(path)
      .then((d) => !cancelled && (setData(d), setError("")))
      .catch((e) => !cancelled && setError((e as Error).message));
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  return { data, error, loading: !!path && data === null && !error, reload: () => setVersion((v) => v + 1) };
}

/** Questions (mentee) or inbox items (mentor) for the current user, refreshed together. */
export function useActivity() {
  const { user } = useSession();
  const questions = useApi<import("@/lib/api").Question[]>(user.role === "mentee" ? "/api/questions/mine/" : null);
  const inbox = useApi<import("@/lib/api").InboxItem[]>(user.role === "mentor" ? "/api/inbox/" : null);
  return { user, questions, inbox };
}

export function Status({ loading, error, empty, emptyText }: { loading?: boolean; error?: string; empty?: boolean; emptyText: string }) {
  if (loading) return <p className="py-8 text-muted">Loading…</p>;
  if (error) return <p className="py-8 text-danger">{error}</p>;
  if (empty) return <p className="py-8 text-muted">{emptyText}</p>;
  return null;
}
