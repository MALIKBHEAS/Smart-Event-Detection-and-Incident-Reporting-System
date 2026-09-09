import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../api/endpoints/auth";
import { registerAuthFailureHandler } from "../api/client";
import { tokenStore } from "./tokenStore";
import type { CurrentUser } from "../api/types";

export interface AuthState {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  /** True only during the initial silent session-restore on page load. */
  isInitializing: boolean;
  loginError: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);

let initialRefreshStarted = false;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [loginError, setLoginError] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // On first load, try to silently restore a session from the persisted
  // refresh token (access tokens are memory-only and don't survive reload).
  useEffect(() => {
    const refreshToken = tokenStore.getRefreshToken();
    if (!refreshToken) {
      setIsInitializing(false);
      return;
    }
    if (initialRefreshStarted) return;
    initialRefreshStarted = true;
    
    authApi
      .refresh(refreshToken)
      .then(async (tokens) => {
        tokenStore.setAccessToken(tokens.access_token);
        tokenStore.setRefreshToken(tokens.refresh_token);
        const me = await authApi.me(tokens.access_token);
        setUser(me);
      })
      .catch(() => {
        tokenStore.clear();
      })
      .finally(() => setIsInitializing(false));
  }, []);

  // Wired up so api/client.ts can force a logout when a background token
  // refresh (triggered by a 401 on some other request) ultimately fails.
  useEffect(() => {
    registerAuthFailureHandler(clearSession);
  }, [clearSession]);

  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    setLoginError(null);
    try {
      const tokens = await authApi.login({ username, password });
      tokenStore.setAccessToken(tokens.access_token);
      tokenStore.setRefreshToken(tokens.refresh_token);
      const me = await authApi.me(tokens.access_token);
      setUser(me);
      return true;
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Login failed");
      return false;
    }
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string): Promise<boolean> => {
      setLoginError(null);
      try {
        await authApi.register({ username, email, password });
        return await login(username, password);
      } catch (err) {
        setLoginError(err instanceof Error ? err.message : "Registration failed");
        return false;
      }
    },
    [login]
  );

  const logout = useCallback(async () => {
    const refreshToken = tokenStore.getRefreshToken();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // Best-effort server-side revocation; clear the local session
        // either way so the user isn't stuck "logged in" on this device.
      }
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isInitializing,
      loginError,
      login,
      register,
      logout,
    }),
    [user, isInitializing, loginError, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
