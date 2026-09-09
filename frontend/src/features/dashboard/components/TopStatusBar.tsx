import { useState, useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import { keyframes } from "@mui/system";
import SecurityIcon from "@mui/icons-material/Security";

const pulse = keyframes`
  0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
  70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
  100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
`;

interface TopStatusBarProps {
  systemName?: string;
  isOnline?: boolean;
  activeAlerts?: number;
}

export function TopStatusBar({ systemName = "SENTRY TACTICAL SOC", isOnline = true, activeAlerts = 0 }: TopStatusBarProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const timeString = time.toLocaleTimeString("en-US", { hour12: false });
  const statusColor = isOnline ? "#00ff88" : "#ff3b3b";

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        py: 1.5,
        px: 3,
        mb: 3,
        bgcolor: "#0d1117",
        border: "1px solid #30363d",
        borderBottom: `2px solid ${isOnline ? "#00d9ff" : "#ff3b3b"}`,
        boxShadow: `0 4px 20px rgba(0,0,0,0.5), inset 0 -2px 10px ${isOnline ? "rgba(0,217,255,0.1)" : "rgba(255,59,59,0.1)"}`,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <SecurityIcon sx={{ color: "#00d9ff", fontSize: 28 }} />
        <Typography variant="h5" sx={{ m: 0, color: "#e6edf3" }}>
          {systemName}
        </Typography>
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 4 }}>
        <Typography variant="h3" sx={{ m: 0, color: "#00d9ff", fontSize: "1.75rem" }}>
          {timeString}
        </Typography>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, bgcolor: "#161b22", px: 2, py: 1, borderRadius: 1, border: "1px solid #30363d" }}>
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              bgcolor: statusColor,
              animation: isOnline ? `${pulse} 2s infinite` : "none",
            }}
          />
          <Typography variant="subtitle2" sx={{ color: statusColor }}>
            {isOnline ? "SYSTEM ONLINE" : "SYSTEM OFFLINE"}
          </Typography>
        </Box>

        <Chip
          label={`ACTIVE ALERTS: ${activeAlerts}`}
          sx={{
            borderRadius: 1,
            bgcolor: activeAlerts > 0 ? "rgba(255, 59, 59, 0.1)" : "rgba(0, 255, 136, 0.1)",
            color: activeAlerts > 0 ? "#ff3b3b" : "#00ff88",
            border: `1px solid ${activeAlerts > 0 ? "#ff3b3b" : "#00ff88"}`,
            fontWeight: "bold",
            fontFamily: '"IBM Plex Mono", monospace',
            height: 36,
          }}
        />
      </Box>
    </Box>
  );
}
