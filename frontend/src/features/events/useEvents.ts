import { useQuery } from "@tanstack/react-query";
import { eventsApi } from "../../api/endpoints/events";
import type { EventListParams } from "../../api/types";

export function useEventsList(params: EventListParams) {
  return useQuery({
    queryKey: ["events", params],
    queryFn: () => eventsApi.list(params),
  });
}

export function useEvent(id: number | null) {
  return useQuery({
    queryKey: ["events", id],
    queryFn: () => eventsApi.get(id as number),
    enabled: id !== null,
  });
}

export function useEventTypes() {
  return useQuery({
    queryKey: ["events", "types"],
    queryFn: eventsApi.types,
  });
}
