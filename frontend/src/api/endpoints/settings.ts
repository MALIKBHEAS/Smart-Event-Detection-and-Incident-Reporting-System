import { apiClient } from "../client";
import type { AppSettingsData, AppSettingsUpdate } from "../types";

export const settingsApi = {
  get: async (): Promise<AppSettingsData> => (await apiClient.get<AppSettingsData>("/settings")).data,
  update: async (input: AppSettingsUpdate): Promise<AppSettingsData> =>
    (await apiClient.put<AppSettingsData>("/settings", input)).data,
};
