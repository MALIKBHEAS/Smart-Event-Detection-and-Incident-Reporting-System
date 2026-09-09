import { apiClient } from "../client";
import type {
  AnomaliesResponse,
  CamerasAnalyticsResponse,
  ExecutiveSummaryResponse,
  HotspotsResponse,
  IncidentsResponse,
  OverviewResponse,
  RecommendationsResponse,
  RiskResponse,
  TrendsResponse,
} from "../analyticsTypes";

export const analyticsApi = {
  overview: async (days = 30): Promise<OverviewResponse> =>
    (await apiClient.get<OverviewResponse>("/analytics/overview", { params: { days } })).data,
  trends: async (): Promise<TrendsResponse> =>
    (await apiClient.get<TrendsResponse>("/analytics/trends")).data,
  risk: async (days = 30): Promise<RiskResponse> =>
    (await apiClient.get<RiskResponse>("/analytics/risk", { params: { days } })).data,
  recommendations: async (days = 30): Promise<RecommendationsResponse> =>
    (await apiClient.get<RecommendationsResponse>("/analytics/recommendations", { params: { days } })).data,
  cameras: async (days = 30): Promise<CamerasAnalyticsResponse> =>
    (await apiClient.get<CamerasAnalyticsResponse>("/analytics/cameras", { params: { days } })).data,
  incidents: async (days = 30): Promise<IncidentsResponse> =>
    (await apiClient.get<IncidentsResponse>("/analytics/incidents", { params: { days } })).data,
  summary: async (hours = 24): Promise<ExecutiveSummaryResponse> =>
    (await apiClient.get<ExecutiveSummaryResponse>("/analytics/summary", { params: { hours } })).data,
  hotspots: async (days = 30): Promise<HotspotsResponse> =>
    (await apiClient.get<HotspotsResponse>("/analytics/hotspots", { params: { days } })).data,
  anomalies: async (): Promise<AnomaliesResponse> =>
    (await apiClient.get<AnomaliesResponse>("/analytics/anomalies")).data,
};
