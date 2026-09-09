import axios from "axios";
import type { CurrentUser, LoginInput, TokenResponse } from "../types";

export interface RegisterInput {
  username: string;
  email: string;
  password: string;
  role?: string;
}

// A separate bare axios instance (not the shared apiClient) is used here on
// purpose: apiClient's interceptor attaches the access token and retries on
// 401 via these very endpoints, so routing auth calls through it risks a
// refresh-loop. Same base URL/proxy behavior, just no interceptor attached.
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";
const authClient = axios.create({ baseURL: API_BASE, headers: { "Content-Type": "application/json" } });

export const authApi = {
  login: async (input: LoginInput): Promise<TokenResponse> => (await authClient.post<TokenResponse>("/auth/login", input)).data,
  register: async (input: RegisterInput): Promise<CurrentUser> => (await authClient.post<CurrentUser>("/auth/register", input)).data,
  refresh: async (refreshToken: string): Promise<TokenResponse> =>
    (await authClient.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })).data,
  logout: async (refreshToken: string): Promise<void> => {
    await authClient.post("/auth/logout", { refresh_token: refreshToken });
  },
  me: async (accessToken: string): Promise<CurrentUser> =>
    (await authClient.get<CurrentUser>("/auth/me", { headers: { Authorization: `Bearer ${accessToken}` } })).data,
};
