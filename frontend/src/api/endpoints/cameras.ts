import { apiClient } from "../client";
import type { Camera, CameraInput } from "../types";

export const camerasApi = {
  list: async (): Promise<Camera[]> => (await apiClient.get<Camera[]>("/cameras")).data,
  get: async (id: number): Promise<Camera> => (await apiClient.get<Camera>(`/cameras/${id}`)).data,
  create: async (input: CameraInput): Promise<Camera> => (await apiClient.post<Camera>("/cameras", input)).data,
  update: async (id: number, input: Partial<CameraInput>): Promise<Camera> =>
    (await apiClient.put<Camera>(`/cameras/${id}`, input)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/cameras/${id}`);
  },
};
