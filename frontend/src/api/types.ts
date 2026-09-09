/**
 * Types mirror the backend's actual response shapes -- nothing invented.
 * See backend/app/schemas/camera.py, backend/app/main.py,
 * backend/app/services/health_service.py, backend/app/workers/worker.py.
 */

export interface Camera {
  id: number;
  name: string;
  rtsp_url: string;
  location: string | null;
  enabled: boolean;
  detector_config: Record<string, unknown> | null;
  tracker_config: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CameraInput {
  name: string;
  rtsp_url: string;
  location?: string | null;
  enabled?: boolean;
  detector_config?: Record<string, unknown> | null;
  tracker_config?: Record<string, unknown> | null;
}

export interface ServiceStatus {
  status: string;
  latency_ms?: number | null;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | string;
  version: string;
  uptime: string | null;
  services: {
    database: ServiceStatus;
    worker_manager: ServiceStatus;
    event_fusion: ServiceStatus;
  };
  workers: { active: number };
}

export interface SystemMetricsResponse {
  cpu: { percent: number; core_count: number };
  memory: { percent: number; used_mb: number; total_mb: number };
  disk: { percent: number; used_gb: number; total_gb: number };
  gpu: { available: boolean; reason?: string; devices?: { name: string; memory_used_pct: number | null }[] };
  python_version: string;
  platform: string;
  process_uptime_seconds: number;
  workers: { total: number; connected: number };
  queue_sizes: number[];
  processing_fps: number | null;
  detection_latency_ms: number | null;
}

export interface WorkerHealth {
  camera_name: string;
  connected: boolean;
  last_frame_timestamp: number | null;
  queue_size: number | null;
}

export interface WorkersHealthResponse {
  workers: Record<string, WorkerHealth>;
}

// --- Auth --------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  roles: string[];
}

export interface LoginInput {
  username: string;
  password: string;
}

// --- Reports -------------------------------------------------------------

export interface Attachment {
  type?: string;
  path?: string | null;
  metadata_path?: string | null;
  [key: string]: unknown;
}

export interface Report {
  id: number;
  title: string;
  summary: string;
  details: string | null;
  incident_type: string | null;
  severity: string;
  status: string;
  camera_id: number | null;
  occurred_at: string | null;
  resolved_at: string | null;
  attachments: Attachment[] | null;
  tags: string[] | null;
  created_at: string | null;
  updated_at: string | null;
  event_count: number;
}

export interface ReportInput {
  title: string;
  summary: string;
  details?: string | null;
  incident_type?: string | null;
  severity?: string;
  status?: string;
  camera_id?: number | null;
  occurred_at?: string | null;
  attachments?: Attachment[] | null;
  tags?: string[] | null;
}

export interface PaginatedReports {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReportListParams {
  page?: number;
  page_size?: number;
  status?: string;
  severity?: string;
  camera_id?: number;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

// --- Events ----------------------------------------------------------------

export interface EventItem {
  id: number;
  camera_id: number | null;
  report_id: number | null;
  type: string;
  severity: string;
  timestamp: string | null;
  payload: Record<string, unknown> | null;
  linked: boolean;
}

export interface PaginatedEvents {
  items: EventItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EventListParams {
  page?: number;
  page_size?: number;
  camera_id?: number;
  event_type?: string;
  severity?: string;
  start_time?: string;
  end_time?: string;
  search?: string;
  linked_only?: boolean;
  report_id?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

// --- Users management --------------------------------------------------

export interface ManagedUser {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  roles: string[];
}

// --- Notifications -------------------------------------------------------

export interface AppNotification {
  id: number;
  type: string;
  message: string;
  severity: string;
  related_type: string | null;
  related_id: number | null;
  read: boolean;
  created_at: string | null;
}

export interface PaginatedNotifications {
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

// --- Notifications -------------------------------------------------------

export interface AppNotification {
  id: number;
  type: string;
  message: string;
  severity: string;
  related_type: string | null;
  related_id: number | null;
  read: boolean;
  created_at: string | null;
}

export interface PaginatedNotifications {
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

// --- Settings --------------------------------------------------------------

export interface AppSettingsData {
  detection_confidence_threshold: number;
  evidence_retention_days: number;
  notify_on_new_event: boolean;
  notify_on_new_incident: boolean;
  updated_at: string | null;
}

export interface AppSettingsUpdate {
  detection_confidence_threshold?: number;
  evidence_retention_days?: number;
  notify_on_new_event?: boolean;
  notify_on_new_incident?: boolean;
}
