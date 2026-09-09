/**
 * Holds the access token in memory (not localStorage) so it's gone on tab
 * close/reload -- reduces the XSS blast radius. The refresh token is
 * persisted to localStorage (it's opaque/single-purpose and the backend
 * revokes it server-side on logout / rotates it on use, so a stale copy
 * left in storage isn't enough on its own without also getting a live
 * access token from it first).
 *
 * This is a plain module-level store (not React state) so the axios
 * interceptor in api/client.ts can read/write it synchronously without
 * needing to be inside a component or trigger re-renders on every token
 * refresh.
 */

const REFRESH_TOKEN_KEY = "sentry-deck.refresh-token";

let accessToken: string | null = null;

export const tokenStore = {
  getAccessToken(): string | null {
    return accessToken;
  },
  setAccessToken(token: string | null): void {
    accessToken = token;
  },
  getRefreshToken(): string | null {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setRefreshToken(token: string | null): void {
    if (token) {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } else {
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  },
  clear(): void {
    accessToken = null;
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
