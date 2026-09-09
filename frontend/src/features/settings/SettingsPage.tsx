import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Switch from "@mui/material/Switch";
import FormControlLabel from "@mui/material/FormControlLabel";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Skeleton from "@mui/material/Skeleton";
import { settingsApi } from "../../api/endpoints/settings";
import { useAuth } from "../../auth/useAuth";
import { ErrorState } from "../../components/common/ErrorState";
import type { AppSettingsUpdate } from "../../api/types";

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.roles.includes("Admin") ?? false;
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get });
  const updateMutation = useMutation({
    mutationFn: (input: AppSettingsUpdate) => settingsApi.update(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  const [threshold, setThreshold] = useState(0.5);
  const [retentionDays, setRetentionDays] = useState(30);
  const [notifyEvent, setNotifyEvent] = useState(true);
  const [notifyIncident, setNotifyIncident] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!data) return;
    setThreshold(data.detection_confidence_threshold);
    setRetentionDays(data.evidence_retention_days);
    setNotifyEvent(data.notify_on_new_event);
    setNotifyIncident(data.notify_on_new_incident);
  }, [data]);

  async function handleSave() {
    await updateMutation.mutateAsync({
      detection_confidence_threshold: threshold,
      evidence_retention_days: retentionDays,
      notify_on_new_event: notifyEvent,
      notify_on_new_incident: notifyIncident,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Only settings actually persisted and applied by the backend are shown here -- nothing here is decorative.
      </Typography>

      {error && <ErrorState message={error.message} />}
      {!isAdmin && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You can view settings, but only an Admin can change them.
        </Alert>
      )}

      {isLoading || !data ? (
        <Skeleton variant="rounded" height={320} />
      ) : (
        <Paper sx={{ p: 3, maxWidth: 560 }}>
          <Stack spacing={4}>
            <Box>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>
                Detection confidence threshold: {threshold.toFixed(2)}
              </Typography>
              <Slider
                value={threshold}
                onChange={(_e, v) => setThreshold(v as number)}
                min={0}
                max={1}
                step={0.01}
                disabled={!isAdmin}
              />
            </Box>

            <TextField
              label="Evidence retention (days)"
              type="number"
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
              disabled={!isAdmin}
              slotProps={{ htmlInput: { min: 1, max: 3650 } }}
              fullWidth
            />

            <Stack spacing={1}>
              <FormControlLabel
                control={<Switch checked={notifyEvent} onChange={(e) => setNotifyEvent(e.target.checked)} disabled={!isAdmin} />}
                label="Notify on new event"
              />
              <FormControlLabel
                control={<Switch checked={notifyIncident} onChange={(e) => setNotifyIncident(e.target.checked)} disabled={!isAdmin} />}
                label="Notify on new incident"
              />
            </Stack>

            {isAdmin && (
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Button variant="contained" onClick={handleSave} disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Saving..." : "Save settings"}
                </Button>
                {saved && (
                  <Typography variant="caption" color="success.main">
                    Saved
                  </Typography>
                )}
              </Stack>
            )}

            <Typography variant="caption" color="text.secondary">
              Last updated: {data.updated_at ? new Date(data.updated_at).toLocaleString() : "never"}
            </Typography>
          </Stack>
        </Paper>
      )}
    </Box>
  );
}
