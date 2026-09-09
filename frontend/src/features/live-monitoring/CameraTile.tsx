import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import { tokenStore } from "../../auth/tokenStore";
import { StatusChip } from "../../components/common/StatusChip";
import type { Camera, WorkerHealth } from "../../api/types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

interface CameraTileProps {
  camera: Camera;
  worker: WorkerHealth | undefined;
}

/**
 * Live tile backed by GET /cameras/{id}/stream (real MJPEG, multipart
 * multipart/x-mixed-replace) -- a plain <img> can render an MJPEG stream
 * directly, no video library needed. The access token goes as a query
 * param since <img> can't set an Authorization header (same pattern the
 * WebSocket connection uses).
 */
export function CameraTile({ camera, worker }: CameraTileProps) {
  const connected = worker?.connected ?? false;
  const token = tokenStore.getAccessToken();
  const streamUrl = connected && token ? `${API_BASE}/cameras/${camera.id}/stream?token=${encodeURIComponent(token)}` : null;

  return (
    <Box
      sx={{
        position: "relative",
        borderRadius: 2,
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "#000",
        aspectRatio: "16 / 9",
      }}
    >
      {streamUrl ? (
        <img
          src={streamUrl}
          alt={`Live view: ${camera.name}`}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <Box sx={{ display: "grid", placeItems: "center", height: "100%" }}>
          <Typography variant="caption" color="text.secondary">
            {connected ? "Waiting for stream..." : "Worker not running"}
          </Typography>
        </Box>
      )}

      <Box
        sx={{
          position: "absolute",
          top: 8,
          left: 8,
          right: 8,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <Chip
          label={camera.name}
          size="small"
          sx={{ bgcolor: "rgba(0,0,0,0.6)", color: "#fff", fontWeight: 600, backdropFilter: "blur(4px)" }}
        />
        <StatusChip label={connected ? "connected" : "offline"} />
      </Box>

      {worker?.queue_size != null && (
        <Box sx={{ position: "absolute", bottom: 8, left: 8 }}>
          <Chip
            label={`queue: ${worker.queue_size}`}
            size="small"
            variant="outlined"
            sx={{ bgcolor: "rgba(0,0,0,0.5)", color: "#fff", borderColor: "rgba(255,255,255,0.3)" }}
          />
        </Box>
      )}
    </Box>
  );
}
