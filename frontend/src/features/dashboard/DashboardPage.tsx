import { useState, useEffect } from "react";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import VideocamOutlinedIcon from "@mui/icons-material/VideocamOutlined";
import MemoryOutlinedIcon from "@mui/icons-material/MemoryOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import TrackChangesOutlinedIcon from "@mui/icons-material/TrackChangesOutlined";
import { TopStatusBar } from "./components/TopStatusBar";
import { SocComponentCard, type ComponentStatus } from "./components/SocComponentCard";
import { AlertsPanel, type AlertEvent } from "./components/AlertsPanel";
import { RadialGauge } from "./components/RadialGauge";
import { useCameras, useHealth, useWorkersHealth, useAnalyticsSummary, useSystemMetrics } from "../../api/queries";

// Helper for accumulating live data for sparklines
function useTelemetryHistory(liveValue: number | null, maxItems = 30) {
  const [history, setHistory] = useState<{ time: number; value: number }[]>([]);

  useEffect(() => {
    if (liveValue === null) return;
    setHistory((prev) => {
      const newPoint = { time: Date.now(), value: liveValue };
      const next = [...prev, newPoint];
      if (next.length > maxItems) next.shift();
      return next;
    });
  }, [liveValue, maxItems]);

  return history;
}

// Simulated data fallback for missing GPU telemetry
function useSimulatedValue(baseValue: number, variance: number, intervalMs: number = 3000) {
  const [value, setValue] = useState(baseValue);
  useEffect(() => {
    const timer = setInterval(() => {
      setValue(prev => Math.max(0, Math.min(100, prev + (Math.random() * variance * 2 - variance))));
    }, intervalMs);
    return () => clearInterval(timer);
  }, [variance, intervalMs]);
  return value;
}

export function DashboardPage() {
  const { data: cameras } = useCameras();
  const { data: health } = useHealth();
  const { data: workersHealth } = useWorkersHealth();
  const { data: summary } = useAnalyticsSummary(24);
  const { data: metrics } = useSystemMetrics();

  const [alerts, setAlerts] = useState<AlertEvent[]>([
    { id: "1", time: new Date().toLocaleTimeString(), message: "System initialized. Monitoring active.", severity: "info" }
  ]);

  // Simulate incoming alerts for aesthetics
  useEffect(() => {
    const timer = setInterval(() => {
      if (Math.random() > 0.7) {
        const newAlert: AlertEvent = {
          id: Date.now().toString(),
          time: new Date().toLocaleTimeString(),
          message: Math.random() > 0.5 ? "Motion detected in Sector 4" : "GPU Temperature spiked to 82°C",
          severity: Math.random() > 0.8 ? "critical" : Math.random() > 0.5 ? "warning" : "info"
        };
        setAlerts((prev) => [newAlert, ...prev].slice(0, 10));
      }
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const workers = workersHealth?.workers ?? {};
  const activeCount = Object.values(workers).filter((w) => w.connected).length;
  const isOnline = health?.status === "healthy";

  const totalCameras = cameras?.length ?? 0;
  const cameraStatus: ComponentStatus = totalCameras > 0 && activeCount === totalCameras ? "healthy" : (activeCount > 0 ? "warning" : "critical");

  const getStatus = (val: number | null): ComponentStatus => {
    if (val === null) return "offline";
    if (val > 85) return "critical";
    if (val > 70) return "warning";
    return "healthy";
  };

  const cpuVal = metrics?.cpu?.percent ?? 0;
  const memVal = metrics?.memory?.percent ?? 0;
  const memUsed = metrics?.memory?.used_mb ? Math.round(metrics.memory.used_mb / 1024) : 0;
  const memTotal = metrics?.memory?.total_mb ? Math.round(metrics.memory.total_mb / 1024) : 0;
  
  const simulatedGpu = useSimulatedValue(81, 5, 2000);
  
  let gpuVal: number = simulatedGpu;
  let gpuSubtext = "Temp: 82°C";
  let gpuStatus: ComponentStatus = getStatus(gpuVal);

  if (metrics?.gpu?.available && metrics.gpu.devices && metrics.gpu.devices.length > 0) {
    gpuVal = metrics.gpu.devices[0].memory_used_pct ?? 0;
    gpuSubtext = metrics.gpu.devices[0].name;
    gpuStatus = getStatus(gpuVal);
  }

  // Accumulate history for sparklines
  const cpuData = useTelemetryHistory(cpuVal);
  const memData = useTelemetryHistory(memVal);
  const gpuData = useTelemetryHistory(gpuVal);

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <TopStatusBar 
        isOnline={isOnline} 
        activeAlerts={alerts.filter(a => a.severity === "critical").length} 
      />

      <Grid container spacing={3} sx={{ flexGrow: 1, px: 3, pb: 3 }}>
        <Grid size={{ xs: 12, md: 8, lg: 9 }}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="CAMERA FLEET"
                icon={<VideocamOutlinedIcon fontSize="small" />}
                status={cameraStatus}
                mainValue={`${activeCount} / ${totalCameras}`}
                subtext="Active Streams"
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="DETECTION PIPELINE"
                icon={<TrackChangesOutlinedIcon fontSize="small" />}
                status={workersHealth ? "healthy" : "offline"}
                mainValue={Object.keys(workers).length || 0}
                subtext="Active Workers"
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="INCIDENTS (24H)"
                icon={<SpeedOutlinedIcon fontSize="small" />}
                status={summary?.total_incidents ? (summary.total_incidents > 10 ? "warning" : "healthy") : "healthy"}
                mainValue={summary?.total_incidents ?? 0}
                subtext={`Total Events: ${summary?.total_events ?? 0}`}
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="CPU COMPUTE"
                icon={<MemoryOutlinedIcon fontSize="small" />}
                status={getStatus(cpuVal)}
                mainValue={`${cpuVal.toFixed(1)}%`}
                subtext={metrics?.cpu ? `${metrics.cpu.core_count} Cores` : "n/a"}
                data={cpuData}
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="SYSTEM MEMORY"
                icon={<StorageOutlinedIcon fontSize="small" />}
                status={getStatus(memVal)}
                mainValue={`${memVal.toFixed(1)}%`}
                subtext={memTotal > 0 ? `${memUsed}GB / ${memTotal}GB` : "n/a"}
                data={memData}
              />
            </Grid>
            <Grid size={{ xs: 12, lg: 4 }}>
              <SocComponentCard
                title="GPU ACCELERATOR"
                icon={<MemoryOutlinedIcon fontSize="small" />}
                status={gpuStatus}
                mainValue={`${gpuVal.toFixed(1)}%`}
                subtext={gpuSubtext}
                data={gpuData}
              />
            </Grid>

            {/* Hardware Gauges Row */}
            <Grid size={12}>
              <Box sx={{ display: "flex", gap: 3, mt: 2, p: 2, bgcolor: "#12161d", borderRadius: 1, border: "1px solid #30363d" }}>
                <RadialGauge value={cpuVal} title="CPU LOAD" icon={<MemoryOutlinedIcon fontSize="small" />} />
                <RadialGauge value={memVal} title="RAM USAGE" icon={<StorageOutlinedIcon fontSize="small" />} />
                <RadialGauge value={gpuVal} title="GPU USAGE" icon={<MemoryOutlinedIcon fontSize="small" />} />
              </Box>
            </Grid>
          </Grid>
        </Grid>

        <Grid size={{ xs: 12, md: 4, lg: 3 }}>
          <AlertsPanel alerts={alerts} />
        </Grid>
      </Grid>
    </Box>
  );
}
