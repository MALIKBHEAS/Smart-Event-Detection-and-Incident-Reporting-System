import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import ToggleButton from "@mui/material/ToggleButton";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Skeleton from "@mui/material/Skeleton";
import { useCameras, useWorkersHealth } from "../../api/queries";
import { ErrorState } from "../../components/common/ErrorState";
import { CameraTile } from "./CameraTile";
import type { Camera } from "../../api/types";

const LAYOUTS = [1, 4, 9, 16] as const;

export function LiveMonitoringPage() {
  const { data: cameras, isLoading, error, refetch } = useCameras();
  const { data: workersHealth } = useWorkersHealth(5000);
  const [layout, setLayout] = useState<(typeof LAYOUTS)[number]>(4);
  const [selected, setSelected] = useState<Camera[]>([]);

  const tiles = useMemo(() => {
    if (selected.length > 0) return selected.slice(0, layout);
    return (cameras ?? []).slice(0, layout);
  }, [selected, cameras, layout]);

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Live monitoring
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Real MJPEG stream from GET /cameras/{"{id}"}/stream -- only cameras with a running worker show video; others
          show an offline state. Start/stop workers from Camera Management.
        </Typography>
      </Box>

      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <ToggleButtonGroup
          size="small"
          value={layout}
          exclusive
          onChange={(_e, value) => value && setLayout(value)}
        >
          {LAYOUTS.map((n) => (
            <ToggleButton key={n} value={n}>
              {n === 1 ? "1" : `${Math.sqrt(n)}x${Math.sqrt(n)}`}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Autocomplete
          multiple
          size="small"
          options={cameras ?? []}
          value={selected}
          onChange={(_e, value) => setSelected(value)}
          getOptionLabel={(c) => c.name}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          sx={{ minWidth: 280, flex: 1 }}
          renderInput={(params) => <TextField {...params} placeholder="Choose cameras (default: first ones)" />}
        />
      </Stack>

      {error && <ErrorState message={error.message} onRetry={() => refetch()} />}

      {isLoading ? (
        <Box sx={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(Math.sqrt(layout), 4)}, 1fr)`, gap: 1.5 }}>
          {Array.from({ length: layout }).map((_, i) => (
            <Skeleton key={i} variant="rounded" sx={{ aspectRatio: "16 / 9" }} />
          ))}
        </Box>
      ) : tiles.length === 0 ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <Typography variant="body2" color="text.secondary">
            No cameras configured yet. Add one in Camera Management.
          </Typography>
        </Box>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(Math.round(Math.sqrt(layout)), 4)}, 1fr)`,
            gap: 1.5,
          }}
        >
          {tiles.map((camera) => (
            <CameraTile key={camera.id} camera={camera} worker={workersHealth?.workers[String(camera.id)]} />
          ))}
        </Box>
      )}
    </Box>
  );
}
