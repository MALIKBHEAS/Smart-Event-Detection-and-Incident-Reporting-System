import { apiClient } from "../client";
import type { PaginatedNotifications } from "../types";

export const notificationsApi = {
  list: async (params: { page?: number; page_size?: number; unread_only?: boolean } = {}): Promise<PaginatedNotifications> =>
    (await apiClient.get<PaginatedNotifications>("/notifications", { params })).data,
  markRead: async (id: number): Promise<void> => {
    await apiClient.put(`/notifications/${id}/read`);
  },
  markAllRead: async (): Promise<void> => {
    await apiClient.put("/notifications/read-all");
  },
};
