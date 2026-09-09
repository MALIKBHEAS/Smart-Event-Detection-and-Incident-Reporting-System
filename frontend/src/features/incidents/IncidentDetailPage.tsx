import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import Divider from "@mui/material/Divider";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import { useReport, useUpdateReport } from "../reports/useReports";
import { useEventsList } from "../events/useEvents";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";
import { useAuth } from "../../auth/useAuth";

// Real backend values (app/schemas/report.py VALID_STATUSES) -- not an
// invented state machine. Any status can be set from any other; the
// backend doesn't enforce a strict transition graph, so neither does this UI.
const STATUSES = ["open", "in_progress", "resolved", "closed"];

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const incidentId = id ? Number(id) : null;
  const { data: incident, isLoading, error } = useReport(incidentId);
  const { data: relatedEvents } = useEventsList({ report_id: incidentId ?? undefined, page_size: 50 });
  const updateMutation = useUpdateReport();
  const { user } = useAuth();
  const canWrite = user?.roles.some((role) => role === "Admin" || role === "Security Operator") ?? false;

  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(false);

  useEffect(() => {
    setNotes(incident?.details ?? "");
  }, [incident?.details]);

  async function handleStatusChange(status: string) {
    if (!incidentId) return;
    await updateMutation.mutateAsync({ id: incidentId, input: { status } });
  }

  async function handleSaveNotes() {
    if (!incidentId) return;
    await updateMutation.mutateAsync({ id: incidentId, input: { details: notes } });
    setNotesSaved(true);
    setTimeout(() => setNotesSaved(false), 2000);
  }

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/incidents")} sx={{ mb: 2 }}>
        Back to incidents
      </Button>

      {error && <ErrorState message={error.message} />}

      {isLoading || !incident ? (
        <Skeleton variant="rounded" height={400} />
      ) : (
        <>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2} sx={{ mb: 2.5 }}>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                {incident.title}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <StatusChip label={incident.severity} />
                <StatusChip label={incident.status.replace("_", " ")} />
              </Stack>
            </Box>
          </Stack>

          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 8 }}>
              <Paper sx={{ p: 2.5, mb: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                  Description
                </Typography>
                <Typography variant="body2">{incident.summary}</Typography>
              </Paper>

              <Paper sx={{ p: 2.5, mb: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                  Operator notes
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  minRows={4}
                  placeholder={canWrite ? "Add investigation notes..." : "No notes yet."}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={!canWrite}
                  sx={{ mb: 1.5 }}
                />
                {canWrite && (
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<SaveOutlinedIcon />}
                      onClick={handleSaveNotes}
                      disabled={updateMutation.isPending}
                    >
                      Save notes
                    </Button>
                    {notesSaved && (
                      <Typography variant="caption" color="success.main">
                        Saved
                      </Typography>
                    )}
                  </Stack>
                )}
              </Paper>

              <Paper sx={{ p: 2.5, mb: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                  Related events ({relatedEvents?.total ?? 0})
                </Typography>
                {relatedEvents && relatedEvents.items.length > 0 ? (
                  <Stack spacing={1} divider={<Divider />}>
                    {relatedEvents.items.map((ev) => (
                      <Box key={ev.id} sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}>
                        <Box>
                          <Typography variant="body2" sx={{ textTransform: "capitalize" }}>
                            {ev.type.replace("_", " ")}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "--"}
                            {ev.camera_id ? ` \u00b7 Camera ${ev.camera_id}` : ""}
                          </Typography>
                        </Box>
                        <StatusChip label={ev.severity} />
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No events linked to this incident yet.
                  </Typography>
                )}
              </Paper>

              <Paper sx={{ p: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                  Evidence
                </Typography>
                {incident.attachments && incident.attachments.length > 0 ? (
                  <Stack spacing={1}>
                    {incident.attachments.map((att, i) => (
                      <Box key={i} sx={{ fontSize: 13, color: "text.secondary" }}>
                        &bull; {att.type ?? "attachment"}: {att.path ?? att.metadata_path ?? "--"}
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No evidence attachments recorded on this incident.
                  </Typography>
                )}
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <Paper sx={{ p: 2.5, mb: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                  Status
                </Typography>
                {canWrite ? (
                  <>
                    <ButtonGroup orientation="vertical" fullWidth size="small">
                      {STATUSES.map((s) => (
                        <Button
                          key={s}
                          variant={incident.status === s ? "contained" : "outlined"}
                          onClick={() => handleStatusChange(s)}
                          disabled={updateMutation.isPending || incident.status === s}
                          sx={{ textTransform: "capitalize", justifyContent: "flex-start" }}
                        >
                          {s.replace("_", " ")}
                        </Button>
                      ))}
                    </ButtonGroup>
                    {updateMutation.isError && (
                      <Alert severity="error" sx={{ mt: 1.5 }}>
                        Failed to update status.
                      </Alert>
                    )}
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Your role doesn&apos;t allow status changes.
                  </Typography>
                )}
              </Paper>

              <Paper sx={{ p: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                  Details
                </Typography>
                <Stack spacing={1.25}>
                  <DetailRow label="Incident ID" value={String(incident.id)} />
                  <DetailRow label="Camera" value={incident.camera_id ? `Camera ${incident.camera_id}` : "--"} />
                  <DetailRow label="Linked events" value={String(incident.event_count)} />
                  <DetailRow label="Occurred at" value={incident.occurred_at ? new Date(incident.occurred_at).toLocaleString() : "--"} />
                  <DetailRow label="Resolved at" value={incident.resolved_at ? new Date(incident.resolved_at).toLocaleString() : "--"} />
                  <DetailRow label="Created" value={incident.created_at ? new Date(incident.created_at).toLocaleString() : "--"} />
                  <DetailRow label="Updated" value={incident.updated_at ? new Date(incident.updated_at).toLocaleString() : "--"} />
                </Stack>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" fontWeight={600}>
        {value}
      </Typography>
    </Box>
  );
}
