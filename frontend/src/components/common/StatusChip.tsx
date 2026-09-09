import Chip from "@mui/material/Chip";
import { alpha } from "@mui/material/styles";
import { severityColor } from "../../app/theme";

const OK_STATUSES = new Set(["healthy", "running", "connected", "resolved", "low"]);
const WARN_STATUSES = new Set(["degraded", "medium", "warning", "open"]);
const BAD_STATUSES = new Set(["unavailable", "critical", "high", "disconnected", "stopped"]);

function colorFor(status: string): string {
  const lower = status.toLowerCase();
  if (["low", "medium", "high", "critical"].includes(lower)) return severityColor(lower);
  if (OK_STATUSES.has(lower)) return "#2fb787";
  if (WARN_STATUSES.has(lower)) return "#e6a13c";
  if (BAD_STATUSES.has(lower)) return "#e5484d";
  return "#5b6576";
}

export function StatusChip({ label, dot = true }: { label: string; dot?: boolean }) {
  const color = colorFor(label);
  return (
    <Chip
      size="small"
      icon={
        dot ? (
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: color,
              display: "inline-block",
              marginLeft: 8,
            }}
          />
        ) : undefined
      }
      label={label}
      sx={{
        bgcolor: alpha(color, 0.14),
        color,
        border: `1px solid ${alpha(color, 0.35)}`,
        textTransform: "capitalize",
        "& .MuiChip-icon": { order: 1 },
      }}
    />
  );
}
