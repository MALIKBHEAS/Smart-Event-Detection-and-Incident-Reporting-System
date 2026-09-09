import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridPaginationModel, GridSortModel } from "@mui/x-data-grid";
import { useEventsList, useEventTypes } from "./useEvents";
import { useCameras } from "../../api/queries";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";
import type { EventItem } from "../../api/types";

const SEVERITIES = ["low", "medium", "high", "critical"];

export function EventsPage() {
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: "timestamp", sort: "desc" }]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [cameraFilter, setCameraFilter] = useState<number | "">("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [detailEvent, setDetailEvent] = useState<EventItem | null>(null);

  const { data: eventTypes } = useEventTypes();
  const { data: cameras } = useCameras();

  const listParams = useMemo(
    () => ({
      page: paginationModel.page + 1,
      page_size: paginationModel.pageSize,
      search: search || undefined,
      event_type: typeFilter || undefined,
      severity: severityFilter || undefined,
      camera_id: cameraFilter === "" ? undefined : cameraFilter,
      start_time: startTime ? new Date(startTime).toISOString() : undefined,
      end_time: endTime ? new Date(endTime).toISOString() : undefined,
      sort_by: sortModel[0]?.field ?? "timestamp",
      sort_dir: (sortModel[0]?.sort ?? "desc") as "asc" | "desc",
    }),
    [paginationModel, search, typeFilter, severityFilter, cameraFilter, startTime, endTime, sortModel]
  );

  const { data, isLoading, error, refetch } = useEventsList(listParams);

  const columns: GridColDef<EventItem>[] = [
    { field: "id", headerName: "ID", width: 70 },
    {
      field: "type",
      headerName: "Event type",
      flex: 1,
      minWidth: 160,
      valueGetter: (_v, row) => row.type.replace(/_/g, " "),
      renderCell: (p) => <span style={{ textTransform: "capitalize" }}>{p.value}</span>,
    },
    { field: "severity", headerName: "Severity", width: 120, renderCell: (p) => <StatusChip label={p.value} /> },
    {
      field: "confidence",
      headerName: "Confidence",
      width: 110,
      sortable: false,
      valueGetter: (_v, row) => {
        const score = row.payload?.score;
        return typeof score === "number" ? `${Math.round(score * 100)}%` : "--";
      },
    },
    {
      field: "camera_id",
      headerName: "Camera",
      width: 110,
      valueGetter: (_v, row) => (row.camera_id ? `Camera ${row.camera_id}` : "--"),
    },
    {
      field: "linked",
      headerName: "Incident",
      width: 110,
      renderCell: (p) => (p.row.report_id ? <StatusChip label="linked" /> : <StatusChip label="unlinked" />),
    },
    {
      field: "timestamp",
      headerName: "Timestamp",
      width: 190,
      valueGetter: (_v, row) => (row.timestamp ? new Date(row.timestamp).toLocaleString() : "--"),
    },
    {
      field: "actions",
      headerName: "",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: (p) => (
        <Tooltip title="View detection detail">
          <IconButton size="small" onClick={() => setDetailEvent(p.row)}>
            <VisibilityOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ),
    },
  ];

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Events
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Raw detections from the pipeline, backed by GET /events. Supported types come from what the configured
          detectors actually produce.
        </Typography>
      </Box>

      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          placeholder="Search event type..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 200 }}
        />
        <TextField
          size="small"
          select
          label="Event type"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 170 }}
        >
          <MenuItem value="">All types</MenuItem>
          {(eventTypes ?? []).map((t) => (
            <MenuItem key={t} value={t} sx={{ textTransform: "capitalize" }}>
              {t.replace(/_/g, " ")}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          select
          label="Severity"
          value={severityFilter}
          onChange={(e) => {
            setSeverityFilter(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All severities</MenuItem>
          {SEVERITIES.map((s) => (
            <MenuItem key={s} value={s} sx={{ textTransform: "capitalize" }}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          select
          label="Camera"
          value={cameraFilter}
          onChange={(e) => {
            setCameraFilter(e.target.value === "" ? "" : Number(e.target.value));
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All cameras</MenuItem>
          {(cameras ?? []).map((c) => (
            <MenuItem key={c.id} value={c.id}>
              {c.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          size="small"
          type="datetime-local"
          label="From"
          value={startTime}
          onChange={(e) => {
            setStartTime(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          slotProps={{ inputLabel: { shrink: true } }}
        />
        <TextField
          size="small"
          type="datetime-local"
          label="To"
          value={endTime}
          onChange={(e) => {
            setEndTime(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>

      {error && <ErrorState message={error.message} onRetry={() => refetch()} />}

      <Box sx={{ height: 560, width: "100%" }}>
        <DataGrid
          rows={data?.items ?? []}
          columns={columns}
          loading={isLoading}
          rowCount={data?.total ?? 0}
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          sortModel={sortModel}
          onSortModelChange={setSortModel}
          pageSizeOptions={[25, 50, 100]}
          disableRowSelectionOnClick
        />
      </Box>

      <Dialog open={detailEvent !== null} onClose={() => setDetailEvent(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Detection detail</DialogTitle>
        <DialogContent>
          {detailEvent && (
            <Stack spacing={1.5} sx={{ py: 1 }}>
              <Row label="Event ID" value={String(detailEvent.id)} />
              <Row label="Type" value={detailEvent.type.replace(/_/g, " ")} />
              <Row label="Severity" value={detailEvent.severity} />
              <Row label="Camera" value={detailEvent.camera_id ? `Camera ${detailEvent.camera_id}` : "--"} />
              <Row label="Timestamp" value={detailEvent.timestamp ? new Date(detailEvent.timestamp).toLocaleString() : "--"} />
              <Row label="Linked incident" value={detailEvent.report_id ? `#${detailEvent.report_id}` : "Not linked"} />
              <Row
                label="Track ID"
                value={
                  detailEvent.payload?.track_id !== undefined && detailEvent.payload?.track_id !== null
                    ? String(detailEvent.payload.track_id)
                    : "--"
                }
              />
              <Row
                label="Confidence"
                value={typeof detailEvent.payload?.score === "number" ? `${Math.round((detailEvent.payload.score as number) * 100)}%` : "--"}
              />
              <Row
                label="Evidence"
                value={typeof detailEvent.payload?.screenshot_path === "string" ? String(detailEvent.payload.screenshot_path) : "No snapshot recorded"}
              />
            </Stack>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
      <Typography variant="body2" color="text.secondary" sx={{ textTransform: "capitalize" }}>
        {label}
      </Typography>
      <Typography variant="body2" fontWeight={600} sx={{ textTransform: "capitalize", maxWidth: 280, textAlign: "right" }}>
        {value}
      </Typography>
    </Box>
  );
}
