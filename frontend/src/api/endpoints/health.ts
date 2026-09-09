import { apiClient } from "../client";
import type { HealthResponse, SystemMetricsResponse } from "../types";

export const healthApi = {
  get: async (): Promise<HealthResponse> => (await apiClient.get<HealthResponse>("/health")).data,
  systemMetrics: async (): Promise<SystemMetricsResponse> => (await apiClient.get<SystemMetricsResponse>("/system/metrics")).data,
};
