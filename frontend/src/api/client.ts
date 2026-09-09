import axios from "axios";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";
import { authApi } from "./endpoints/auth";
import { tokenStore } from "../auth/tokenStore";

// Defaults to `/api`, which vite.config.ts's dev proxy rewrites to the
// FastAPI backend (the backend sends no CORS headers, so this proxy is
// required in dev; see vite.config.ts and README for the prod equivalent).
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 60_000,
});

/**
 * Called by AuthContext so this module can force a logout (clear tokens,
 * redirect to /login) when a refresh attempt fails -- without api/client.ts
 * importing AuthContext directly (that would be a circular import, since
 * AuthContext itself uses apiClient-backed endpoints indirectly).
 */
let onAuthFailure: (() => void) | null = null;
export function registerAuthFailureHandler(handler: () => void): void {
  onAuthFailure = handler;
}

apiClient.interceptors.request.use((config) => {
  const token = tokenStore.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Queues concurrent 401s behind a single in-flight refresh call instead of
// firing one refresh request per failed request.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return null;
  try {
    const tokens = await authApi.refresh(refreshToken);
    tokenStore.setAccessToken(tokens.access_token);
    tokenStore.setRefreshToken(tokens.refresh_token);
    return tokens.access_token;
  } catch {
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;

    if (error.response?.status === 401 && originalRequest && !originalRequest._retried && !originalRequest.url?.includes("/auth/")) {
      originalRequest._retried = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const newAccessToken = await refreshPromise;
      if (newAccessToken) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      }
      // Refresh failed -- session is genuinely gone.
      tokenStore.clear();
      onAuthFailure?.();
      return Promise.reject(new Error("انتهت الجلسة (Session Expired). يرجى تسجيل الدخول مجدداً."));
    }

    let detail = "Request failed";
    if (error.response?.data && (error.response.data as any).detail) {
      const d = (error.response.data as any).detail;
      if (Array.isArray(d)) {
        // Validation error (HTTP 422)
        detail = d.map((e) => `${e.loc?.join(".")}: ${e.msg}`).join(", ");
      } else if (typeof d === "string") {
        detail = d;
      }
    } else if (error.response?.status === 401) {
      detail = "Unauthorized access";
    } else if (error.message) {
      detail = error.message;
    }
    return Promise.reject(new Error(detail));
  }
);
