import { useQuery } from "@tanstack/react-query";
import { camerasApi } from "./endpoints/cameras";
import { healthApi } from "./endpoints/health";
import { workersApi } from "./endpoints/workers";
import { analyticsApi } from "./endpoints/analytics";

// Centralized query-key + read-hook registry (feature-based mutation hooks
// live alongside their feature, e.g. src/features/cameras/useCameraMutations.ts).

export const qk = {
  cameras: ["cameras"] as const,
  health: ["health"] as const,
  systemMetrics: ["system-metrics"] as const,
  workersHealth: ["workers-health"] as const,
  analyticsOverview: (days: number) => ["analytics", "overview", days] as const,
  analyticsTrends: ["analytics", "trends"] as const,
  analyticsRisk: (days: number) => ["analytics", "risk", days] as const,
  analyticsRecommendations: (days: number) => ["analytics", "recommendations", days] as const,
  analyticsCameras: (days: number) => ["analytics", "cameras", days] as const,
  analyticsIncidents: (days: number) => ["analytics", "incidents", days] as const,
  analyticsSummary: (hours: number) => ["analytics", "summary", hours] as const,
  analyticsHotspots: (days: number) => ["analytics", "hotspots", days] as const,
  analyticsAnomalies: ["analytics", "anomalies"] as const,
};

export function useCameras() {
  return useQuery({ queryKey: qk.cameras, queryFn: camerasApi.list });
}

export function useHealth(refetchMs = 15_000) {
  return useQuery({ queryKey: qk.health, queryFn: healthApi.get, refetchInterval: refetchMs });
}

export function useSystemMetrics(refetchMs = 5_000) {
  return useQuery({ queryKey: qk.systemMetrics, queryFn: healthApi.systemMetrics, refetchInterval: refetchMs });
}

export function useWorkersHealth(refetchMs = 5_000) {
  return useQuery({ queryKey: qk.workersHealth, queryFn: workersApi.health, refetchInterval: refetchMs });
}

export function useAnalyticsOverview(days = 30) {
  return useQuery({ queryKey: qk.analyticsOverview(days), queryFn: () => analyticsApi.overview(days) });
}

export function useAnalyticsTrends() {
  return useQuery({ queryKey: qk.analyticsTrends, queryFn: analyticsApi.trends });
}

export function useAnalyticsRisk(days = 30) {
  return useQuery({ queryKey: qk.analyticsRisk(days), queryFn: () => analyticsApi.risk(days) });
}

export function useAnalyticsRecommendations(days = 30) {
  return useQuery({ queryKey: qk.analyticsRecommendations(days), queryFn: () => analyticsApi.recommendations(days) });
}

export function useAnalyticsCameras(days = 30) {
  return useQuery({ queryKey: qk.analyticsCameras(days), queryFn: () => analyticsApi.cameras(days) });
}

export function useAnalyticsIncidents(days = 30) {
  return useQuery({ queryKey: qk.analyticsIncidents(days), queryFn: () => analyticsApi.incidents(days) });
}

export function useAnalyticsSummary(hours = 24) {
  return useQuery({ queryKey: qk.analyticsSummary(hours), queryFn: () => analyticsApi.summary(hours) });
}

export function useAnalyticsHotspots(days = 30) {
  return useQuery({ queryKey: qk.analyticsHotspots(days), queryFn: () => analyticsApi.hotspots(days) });
}

export function useAnalyticsAnomalies(refetchMs = 30_000) {
  return useQuery({ queryKey: qk.analyticsAnomalies, queryFn: analyticsApi.anomalies, refetchInterval: refetchMs });
}
