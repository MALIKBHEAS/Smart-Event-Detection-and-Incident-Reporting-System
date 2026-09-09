import { apiClient } from "../client";
import type { WorkersHealthResponse } from "../types";

export const workersApi = {
  health: async (): Promise<WorkersHealthResponse> =>
    (await apiClient.get<WorkersHealthResponse>("/health/workers")).data,
  start: async (cameraId: number): Promise<unknown> =>
    (await apiClient.post(`/workers/start/${cameraId}`)).data,
  stop: async (cameraId: number): Promise<unknown> =>
    (await apiClient.post(`/workers/stop/${cameraId}`)).data,
};
