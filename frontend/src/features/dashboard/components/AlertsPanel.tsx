
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { motion, AnimatePresence } from "framer-motion";

export type AlertSeverity = "info" | "warning" | "critical";

export interface AlertEvent {
  id: string;
  time: string;
  message: string;
  severity: AlertSeverity;
}

interface AlertsPanelProps {
  alerts: AlertEvent[];
}

const severityConfig = {
  info: { color: "#00d9ff", icon: <InfoOutlinedIcon fontSize="small" /> },
  warning: { color: "#ffb800", icon: <WarningAmberOutlinedIcon fontSize="small" /> },
  critical: { color: "#ff3b3b", icon: <ErrorOutlineIcon fontSize="small" /> },
};

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <Box
      sx={{
        bgcolor: "#0d1117",
        border: "1px solid #30363d",
        borderRadius: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Box sx={{ p: 2, borderBottom: "1px solid #30363d", bgcolor: "#161b22" }}>
        <Typography variant="subtitle1" sx={{ color: "#e6edf3" }}>
          SYSTEM EVENTS LOG
        </Typography>
      </Box>

      <Box sx={{ p: 2, flexGrow: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 1 }}>
        <AnimatePresence initial={false}>
          {alerts.map((alert) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -20, height: 0 }}
              animate={{ opacity: 1, x: 0, height: "auto" }}
              exit={{ opacity: 0, scale: 0.9, height: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1.5,
                  p: 1.5,
                  bgcolor: "rgba(22, 27, 34, 0.5)",
                  borderLeft: `3px solid ${severityConfig[alert.severity].color}`,
                  borderRadius: "0 4px 4px 0",
                }}
              >
                <Box sx={{ color: severityConfig[alert.severity].color, mt: 0.2 }}>
                  {severityConfig[alert.severity].icon}
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: "#8b949e", fontFamily: '"IBM Plex Mono", monospace' }}>
                    {alert.time}
                  </Typography>
                  <Typography variant="body2" sx={{ color: "#e6edf3", mt: 0.5 }}>
                    {alert.message}
                  </Typography>
                </Box>
              </Box>
            </motion.div>
          ))}
          {alerts.length === 0 && (
            <Typography variant="body2" sx={{ color: "#8b949e", textAlign: "center", mt: 4 }}>
              No recent events.
            </Typography>
          )}
        </AnimatePresence>
      </Box>
    </Box>
  );
}
