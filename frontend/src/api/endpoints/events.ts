import { apiClient } from "../client";
import type { EventItem, EventListParams, PaginatedEvents } from "../types";

export const eventsApi = {
  list: async (params: EventListParams = {}): Promise<PaginatedEvents> =>
    (await apiClient.get<PaginatedEvents>("/events", { params })).data,
  get: async (id: number): Promise<EventItem> => (await apiClient.get<EventItem>(`/events/${id}`)).data,
  types: async (): Promise<string[]> => (await apiClient.get<{ types: string[] }>("/events/types")).data.types,
};
