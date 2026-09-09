/**
 * Mirrors backend/app/intelligence/schemas/analytics.py exactly.
 */

export interface CameraCount {
  camera_id: number | null;
  camera_name: string | null;
  count: number;
}

export interface BucketCount {
  bucket: string;
  count: number;
}

export interface OverviewResponse {
  total_detections: number;
  total_incidents: number;
  incidents_by_camera: CameraCount[];
  incidents_by_day: BucketCount[];
  incidents_by_week: BucketCount[];
  incidents_by_month: BucketCount[];
  incidents_by_category: BucketCount[];
  incidents_by_severity: BucketCount[];
}

export interface TrendPoint {
  label: string;
  current: number;
  previous: number;
  direction: "up" | "down" | "stable" | string;
  change_pct: number | null;
}

export interface TrendsResponse {
  trends: TrendPoint[];
}

export interface CameraRisk {
  camera_id: number;
  camera_name: string;
  risk_score: number;
  risk_level: string;
  incident_count: number;
}

export interface RiskResponse {
  overall_risk_score: number;
  overall_risk_level: string;
  by_camera: CameraRisk[];
}

export interface Recommendation {
  title: string;
  detail: string;
  priority: "low" | "medium" | "high" | string;
  related_camera_id: number | null;
}

export interface RecommendationsResponse {
  recommendations: Recommendation[];
}

export interface CameraHealthAnalytics {
  camera_id: number;
  camera_name: string;
  enabled: boolean;
  incidents_generated: number;
  average_confidence: number | null;
  last_incident_at: string | null;
  risk_score: number;
  risk_level: string;
  availability_pct: number | null;
  average_fps: number | null;
  dropped_frames: number | null;
}

export interface CamerasAnalyticsResponse {
  cameras: CameraHealthAnalytics[];
}

export interface IncidentCluster {
  report_id: number | null;
  incident_type: string | null;
  category: string;
  severity: string;
  camera_id: number | null;
  camera_name: string | null;
  occurrences: number;
  first_seen: string | null;
  last_seen: string | null;
  duration_seconds: number | null;
}

export interface Pattern {
  kind: string;
  description: string;
  strength: number;
}

export interface IncidentsResponse {
  clusters: IncidentCluster[];
  patterns: Pattern[];
}

export interface ExecutiveSummaryResponse {
  window_label: string;
  total_events: number;
  total_incidents: number;
  highest_risk_camera: string | null;
  most_frequent_event: string | null;
  peak_activity_window: string | null;
  overall_risk_level: string;
  recommended_action: string | null;
  narrative: string;
}

export interface Hotspot {
  kind: string;
  label: string;
  count: number;
  share_pct: number;
}

export interface HotspotsResponse {
  highest_risk_camera: Hotspot | null;
  busiest_hour: Hotspot | null;
  most_dangerous_day: Hotspot | null;
  hotspots: Hotspot[];
}

export interface Anomaly {
  kind: string;
  description: string;
  anomaly_score: number;
  context: Record<string, unknown>;
}

export interface AnomaliesResponse {
  anomalies: Anomaly[];
}
