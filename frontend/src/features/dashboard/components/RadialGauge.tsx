import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { type ReactNode } from "react";

export function RadialGauge({ value, title, icon }: { value: number; title: string; icon: ReactNode }) {
  const radius = 30;
  const stroke = 6;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  let color = "#00ff88";
  if (value > 85) color = "#ff3b3b";
  else if (value > 70) color = "#ffb800";

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2, minWidth: 160 }}>
      <Box sx={{ position: "relative", width: radius * 2, height: radius * 2 }}>
        <svg height={radius * 2} width={radius * 2}>
          <circle
            stroke="#1f242d"
            fill="transparent"
            strokeWidth={stroke}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
          />
          <circle
            stroke={color}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={circumference + " " + circumference}
            style={{ strokeDashoffset, transition: "stroke-dashoffset 0.5s ease-in-out" }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            transform={`rotate(-90 ${radius} ${radius})`}
          />
        </svg>
        <Box sx={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", alignItems: "center", justifyContent: "center", color }}>
          {icon}
        </Box>
      </Box>
      <Box>
        <Typography variant="caption" sx={{ color: "#8b949e", display: "block" }}>{title}</Typography>
        <Typography variant="h6" sx={{ color: "#e6edf3", lineHeight: 1 }}>{value.toFixed(1)}%</Typography>
      </Box>
    </Box>
  );
}
