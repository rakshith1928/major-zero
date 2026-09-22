import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type MeResponse } from "./api";
import { ApiError } from "./errors";

interface AuthValue {
  user: MeResponse | null;
  loading: boolean;
  register: (payload: Record<string, unknown>) => Promise<void>;
  login: (payload: Record<string, unknown>) => Promise<void>;
  logout: () => void;
  setUser: (user: MeResponse | null) => void;
}

const AuthCtx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem("zb_token")) {
      setLoading(false);
      return;
    }
    // A dead backend (cold start, offline) must not nuke a good token:
    // only 401/403 means the token itself is bad.
    api.me().then(setUser).catch((err: unknown) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        localStorage.removeItem("zb_token");
      }
    }).finally(() => setLoading(false));
  }, []);

  const value: AuthValue = {
    user,
    loading,
    async register(payload: Record<string, unknown>) {
      const body = await api.register(payload);
      localStorage.setItem("zb_token", body.access_token);
      setUser(await api.me());
    },
    async login(payload: Record<string, unknown>) {
      const body = await api.login(payload);
      localStorage.setItem("zb_token", body.access_token);
      setUser(await api.me());
    },
    logout() {
      localStorage.removeItem("zb_token");
      // Drop per-account chat sessions too (current and legacy keys) so the
      // next login starts clean instead of reading another account's thread.
      try {
        Object.keys(localStorage)
          .filter((k) => k.startsWith("zb-chat-") || k === "zb-chat-session")
          .forEach((k) => localStorage.removeItem(k));
      } catch { /* storage unavailable: nothing to clear */ }
      setUser(null);
    },
    setUser,
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
