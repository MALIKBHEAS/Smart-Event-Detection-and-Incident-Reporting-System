import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api/endpoints/notifications";

export function useNotificationsList(params: { page?: number; page_size?: number; unread_only?: boolean } = {}) {
  return useQuery({
    queryKey: ["notifications", params],
    queryFn: () => notificationsApi.list(params),
    refetchInterval: 30_000, // fallback if the WS connection drops
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}
