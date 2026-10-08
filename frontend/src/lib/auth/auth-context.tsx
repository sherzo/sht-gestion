"use client";

// Sesión de la app (research R4, R12): el token de acceso vive solo en memoria; la
// cookie HttpOnly lo renueva. La renovación se serializa entre pestañas con Web Locks.
import { createContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch, connectSession } from "@/lib/api/client";
import type { Schemas } from "@/lib/api/client";

export type SessionUser = Schemas["SessionUser"];
type SessionResponse = Schemas["SessionResponse"];

export type AuthStatus = "loading" | "setup_required" | "anonymous" | "authenticated";

export type AuthState = {
  status: AuthStatus;
  user: SessionUser | null;
  sessionExpiresAt: string | null;
};

export type AuthContextValue = AuthState & {
  login: (username: string, password: string) => Promise<SessionUser>;
  logout: () => Promise<void>;
  /** Cierra la sesión solo en este equipo, sin llamar a la API (la sesión ya terminó). */
  endLocalSession: () => void;
  setSession: (session: SessionResponse) => void;
  reloadUser: () => Promise<void>;
  /** Registra quién resuelve una sesión terminada (diálogo de reingreso). */
  setSessionEndedHandler: (handler: (() => Promise<boolean>) | null) => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

// Se renueva un minuto antes de que venza el token de acceso.
const REFRESH_MARGIN_SECONDS = 60;

async function requestRefresh(): Promise<SessionResponse | null> {
  const run = async () => {
    try {
      return await apiFetch<SessionResponse>("/auth/refresh", { method: "POST", authenticated: false });
    } catch {
      return null;
    }
  };
  if (typeof navigator !== "undefined" && "locks" in navigator) {
    return navigator.locks.request("sht-refresh", run);
  }
  return run();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null, sessionExpiresAt: null });
  const tokenRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const endedHandlerRef = useRef<(() => Promise<boolean>) | null>(null);
  const refreshRef = useRef<() => Promise<string | null>>(async () => null);

  const clearSession = useCallback((status: AuthStatus = "anonymous") => {
    tokenRef.current = null;
    if (timerRef.current) clearTimeout(timerRef.current);
    setState({ status, user: null, sessionExpiresAt: null });
  }, []);

  const setSession = useCallback((session: SessionResponse) => {
    tokenRef.current = session.access_token;
    if (timerRef.current) clearTimeout(timerRef.current);
    const delay = Math.max(session.expires_in - REFRESH_MARGIN_SECONDS, 30) * 1000;
    timerRef.current = setTimeout(() => void refreshRef.current(), delay);
    setState({ status: "authenticated", user: session.user, sessionExpiresAt: session.session_expires_at });
  }, []);

  const refresh = useCallback(async (): Promise<string | null> => {
    const session = await requestRefresh();
    if (!session) return null;
    setSession(session);
    return session.access_token;
  }, [setSession]);
  refreshRef.current = refresh;

  useEffect(() => {
    connectSession({
      getAccessToken: () => tokenRef.current,
      refresh,
      onSessionEnded: async () => {
        if (endedHandlerRef.current) return endedHandlerRef.current();
        clearSession();
        return false;
      },
    });
    return () => connectSession(null);
  }, [refresh, clearSession]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await apiFetch<Schemas["SetupStatus"]>("/setup/status", { authenticated: false });
        if (cancelled) return;
        if (status.setup_required) {
          clearSession("setup_required");
          return;
        }
      } catch {
        // Sin conexión: se intenta igual la renovación, que también fallará y pedirá ingresar.
      }
      const token = await refresh();
      if (!cancelled && !token) clearSession();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh, clearSession]);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const session = await apiFetch<SessionResponse>("/auth/login", {
        method: "POST",
        body: { username, password },
        authenticated: false,
      });
      setSession(session);
      return session.user;
    },
    [setSession],
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST", skipReauth: true });
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const reloadUser = useCallback(async () => {
    const me = await apiFetch<Schemas["MeResponse"]>("/auth/me");
    setState((current) => ({ ...current, user: me.user, sessionExpiresAt: me.session_expires_at }));
  }, []);

  const endLocalSession = useCallback(() => clearSession(), [clearSession]);

  const setSessionEndedHandler = useCallback((handler: (() => Promise<boolean>) | null) => {
    endedHandlerRef.current = handler;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, logout, endLocalSession, setSession, reloadUser, setSessionEndedHandler }),
    [state, login, logout, endLocalSession, setSession, reloadUser, setSessionEndedHandler],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
