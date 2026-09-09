import { useEffect, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { keyframes } from "@mui/system";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";

const pulseHealthy = keyframes`
  0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
  70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 6px rgba(0, 255, 136, 0); }
  100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
`;

const pulseWarning = keyframes`
  0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255, 184, 0, 0.7); }
  70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 6px rgba(255, 184, 0, 0); }
  100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255, 184, 0, 0); }
`;

const pulseCritical = keyframes`
  0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255, 59, 59, 0.9); }
  50% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 8px rgba(255, 59, 59, 0); }
  100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(255, 59, 59, 0); }
`;

const flashUpdate = keyframes`
  0% { background-color: rgba(0, 217, 255, 0.2); }
  100% { background-color: #0d1117; }
`;

export type ComponentStatus = "healthy" | "warning" | "critical" | "offline";

interface DataPoint {
  time: number;
  value: number;
}

interface SocComponentCardProps {
  title: string;
  icon: ReactNode;
  status: ComponentStatus;
  mainValue: string | number;
  subtext?: string;
  data?: DataPoint[]; // For the sparkline
}

export function SocComponentCard({ title, icon, status, mainValue, subtext, data = [] }: SocComponentCardProps) {
  const [flash, setFlash] = useState(false);
  const [prevDataLength, setPrevDataLength] = useState(data.length);

  useEffect(() => {
    if (data.length > prevDataLength) {
      setFlash(true);
      const timer = setTimeout(() => setFlash(false), 250);
      setPrevDataLength(data.length);
      return () => clearTimeout(timer);
    } else {
      setPrevDataLength(data.length);
    }
  }, [data, prevDataLength]);

  let statusColor = "#6b7280"; // offline
  let pulseAnimation = "none";
  let glowColor = "transparent";
  
  if (status === "healthy") {
    statusColor = "#00ff88";
    pulseAnimation = `${pulseHealthy} 2s infinite`;
    glowColor = "rgba(0, 255, 136, 0.1)";
  } else if (status === "warning") {
    statusColor = "#ffb800";
    pulseAnimation = `${pulseWarning} 1.5s infinite`;
    glowColor = "rgba(255, 184, 0, 0.3)";
  } else if (status === "critical") {
    statusColor = "#ff3b3b";
    pulseAnimation = `${pulseCritical} 0.8s infinite`;
    glowColor = "rgba(255, 59, 59, 0.4)";
  }

  return (
    <Box
      sx={{
        bgcolor: "#0d1117",
        border: `1px solid ${status === "offline" ? "#30363d" : statusColor}`,
        borderRadius: 1,
        p: 2,
        position: "relative",
        boxShadow: `inset 0 0 20px ${glowColor}, 0 4px 12px rgba(0,0,0,0.5)`,
        transition: "all 0.2s ease-in-out",
        animation: flash ? `${flashUpdate} 0.25s ease-out` : "none",
        "&:hover": {
          boxShadow: `inset 0 0 30px ${glowColor}, 0 6px 16px rgba(0,0,0,0.7)`,
          transform: "translateY(-2px)",
        },
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: statusColor }}>
          {icon}
          <Typography variant="subtitle2" sx={{ color: "#e6edf3" }}>
            {title}
          </Typography>
        </Box>
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            bgcolor: statusColor,
            animation: pulseAnimation,
            mt: 0.5,
          }}
        />
      </Box>

      <Typography variant="h3" sx={{ color: statusColor, mb: 1 }}>
        {mainValue}
      </Typography>

      {subtext && (
        <Typography variant="body2" sx={{ color: "#8b949e", mb: 2, fontFamily: '"IBM Plex Mono", monospace' }}>
          {subtext}
        </Typography>
      )}

      {data.length > 0 && (
        <Box sx={{ height: 40, width: "100%", mt: "auto" }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <YAxis domain={["dataMin - 5", "dataMax + 5"]} hide />
              <Line
                type="monotone"
                dataKey="value"
                stroke={statusColor}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Box>
  );
}
