import { useParams, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import Skeleton from "@mui/material/Skeleton";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import { useReport } from "./useReports";
import { reportsApi, triggerBlobDownload } from "../../api/endpoints/reports";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";

export function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const reportId = id ? Number(id) : null;
  const { data: report, isLoading, error } = useReport(reportId);

  async function handleDownload(kind: "pdf" | "csv") {
    if (!reportId) return;
    const blob = kind === "pdf" ? await reportsApi.downloadPdf(reportId) : await reportsApi.downloadCsv(reportId);
    triggerBlobDownload(blob, `report-${reportId}.${kind}`);
  }

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/reports")} sx={{ mb: 2 }}>
        Back to reports
      </Button>

      {error && <ErrorState message={error.message} />}

      {isLoading || !report ? (
        <Skeleton variant="rounded" height={400} />
      ) : (
        <>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2} sx={{ mb: 2.5 }}>
            <Box>
              <Typography variant="h5" fontWeight={700}>
                {report.title}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <StatusChip label={report.severity} />
                <StatusChip label={report.status.replace("_", " ")} />
                {report.incident_type && <Chip size="small" variant="outlined" label={report.incident_type} />}
              </Stack>
            </Box>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" startIcon={<PictureAsPdfOutlinedIcon />} onClick={() => handleDownload("pdf")}>
                PDF
              </Button>
              <Button variant="outlined" startIcon={<TableChartOutlinedIcon />} onClick={() => handleDownload("csv")}>
                CSV
              </Button>
            </Stack>
          </Stack>

          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 8 }}>
              <Paper sx={{ p: 2.5, mb: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                  Summary
                </Typography>
                <Typography variant="body2">{report.summary}</Typography>
                {report.details && (
                  <>
                    <Divider sx={{ my: 1.5 }} />
                    <Typography variant="body2" color="text.secondary">
                      {report.details}
                    </Typography>
                  </>
                )}
              </Paper>

              <Paper sx={{ p: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                  Evidence
                </Typography>
                {report.attachments && report.attachments.length > 0 ? (
                  <Stack spacing={1}>
                    {report.attachments.map((att, i) => (
                      <Box key={i} sx={{ fontSize: 13, color: "text.secondary" }}>
                        &bull; {att.type ?? "attachment"}: {att.path ?? att.metadata_path ?? "--"}
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No evidence attachments recorded on this report.
                  </Typography>
                )}
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, md: 4 }}>
              <Paper sx={{ p: 2.5 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                  Details
                </Typography>
                <Stack spacing={1.25}>
                  <DetailRow label="Report ID" value={String(report.id)} />
                  <DetailRow label="Linked events" value={String(report.event_count)} />
                  <DetailRow label="Camera" value={report.camera_id ? `Camera ${report.camera_id}` : "--"} />
                  <DetailRow label="Occurred at" value={report.occurred_at ? new Date(report.occurred_at).toLocaleString() : "--"} />
                  <DetailRow label="Resolved at" value={report.resolved_at ? new Date(report.resolved_at).toLocaleString() : "--"} />
                  <DetailRow label="Created" value={report.created_at ? new Date(report.created_at).toLocaleString() : "--"} />
                  <DetailRow label="Updated" value={report.updated_at ? new Date(report.updated_at).toLocaleString() : "--"} />
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
