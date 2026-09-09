import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Table from "@mui/material/Table";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import TableBody from "@mui/material/TableBody";
import { useHealth, useWorkersHealth } from "../../api/queries";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";

function formatTimestamp(ts: number | null): string {
  if (ts == null) return "--";
  return new Date(ts * 1000).toLocaleString();
}

export function HealthPage() {
  const { data: health, error: healthError } = useHealth(5000);
  const { data: workersHealth } = useWorkersHealth(5000);

  const workerEntries = workersHealth ? Object.entries(workersHealth.workers) : [];

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        System health
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Live from /health and /health/workers, refreshed every 5s.
      </Typography>

      {healthError && <ErrorState message={healthError.message} />}

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Core services
            </Typography>
            {health ? (
              <Table size="small">
                <TableBody>
                  {Object.entries(health.services).map(([name, svc]) => (
                    <TableRow key={name}>
                      <TableCell sx={{ textTransform: "capitalize" }}>{name.replace("_", " ")}</TableCell>
                      <TableCell align="right">
                        <StatusChip label={svc.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell>Version</TableCell>
                    <TableCell align="right">{health.version}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Uptime</TableCell>
                    <TableCell align="right">{health.uptime ?? "--"}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            ) : (
              <Typography variant="body2" color="text.secondary">Loading&hellip;</Typography>
            )}
          </Paper>
        </Grid>


        <Grid size={12}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Worker streams
            </Typography>
            {workerEntries.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No workers currently running.</Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Camera ID</TableCell>
                    <TableCell>Camera</TableCell>
                    <TableCell>Connected</TableCell>
                    <TableCell>Last frame</TableCell>
                    <TableCell>Queue size</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {workerEntries.map(([id, worker]) => (
                    <TableRow key={id}>
                      <TableCell sx={{ fontFamily: "monospace" }}>{id}</TableCell>
                      <TableCell>{worker.camera_name}</TableCell>
                      <TableCell>
                        <StatusChip label={worker.connected ? "connected" : "disconnected"} />
                      </TableCell>
                      <TableCell>{formatTimestamp(worker.last_frame_timestamp)}</TableCell>
                      <TableCell>{worker.queue_size ?? "--"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
