import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import VideocamOutlinedIcon from "@mui/icons-material/VideocamOutlined";
import CameraAltOutlinedIcon from "@mui/icons-material/CameraAltOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import PsychologyOutlinedIcon from "@mui/icons-material/PsychologyOutlined";
import NotificationsOutlinedIcon from "@mui/icons-material/NotificationsOutlined";
import GroupOutlinedIcon from "@mui/icons-material/GroupOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import type { SvgIconComponent } from "@mui/icons-material";

export interface NavItem {
  label: string;
  path: string;
  icon: SvgIconComponent;
  /** False for sections with no supporting backend endpoint yet. */
  live: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: "/dashboard", icon: DashboardOutlinedIcon, live: true },
  { label: "Live Monitoring", path: "/live-monitoring", icon: VideocamOutlinedIcon, live: true },
  { label: "Cameras", path: "/cameras", icon: CameraAltOutlinedIcon, live: true },
  { label: "Incidents", path: "/incidents", icon: ReportProblemOutlinedIcon, live: true },
  { label: "Events", path: "/events", icon: BoltOutlinedIcon, live: true },
  { label: "Reports", path: "/reports", icon: DescriptionOutlinedIcon, live: true },
  { label: "Analytics", path: "/analytics", icon: InsightsOutlinedIcon, live: true },
  { label: "AI Intelligence", path: "/intelligence", icon: PsychologyOutlinedIcon, live: true },
  { label: "Notifications", path: "/notifications", icon: NotificationsOutlinedIcon, live: true },
  { label: "Users", path: "/users", icon: GroupOutlinedIcon, live: true },
  { label: "Settings", path: "/settings", icon: SettingsOutlinedIcon, live: true },
  { label: "System Health", path: "/health", icon: MonitorHeartOutlinedIcon, live: true },
];

export const PAGE_TITLES: Record<string, string> = Object.fromEntries(
  NAV_ITEMS.map((item) => [item.path, item.label])
);
