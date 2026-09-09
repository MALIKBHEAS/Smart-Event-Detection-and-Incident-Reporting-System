import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridPaginationModel, GridSortModel } from "@mui/x-data-grid";
import { useReportsList } from "../reports/useReports";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";
import type { Report } from "../../api/types";

// Real backend values (app/schemas/report.py VALID_STATUSES /
// VALID_SEVERITIES) -- not an invented status system.
const STATUSES = ["open", "in_progress", "resolved", "closed"];
const SEVERITIES = ["low", "medium", "high", "critical"];

export function IncidentsPage() {
  const navigate = useNavigate();
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 10 });
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: "created_at", sort: "desc" }]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  const listParams = useMemo(
    () => ({
      page: paginationModel.page + 1,
      page_size: paginationModel.pageSize,
      search: search || undefined,
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
      sort_by: sortModel[0]?.field ?? "created_at",
      sort_dir: (sortModel[0]?.sort ?? "desc") as "asc" | "desc",
    }),
    [paginationModel, search, statusFilter, severityFilter, sortModel]
  );

  const { data, isLoading, error, refetch } = useReportsList(listParams);

  const columns: GridColDef<Report>[] = [
    { field: "id", headerName: "ID", width: 70 },
    { field: "title", headerName: "Title", flex: 1.3, minWidth: 200 },
    { field: "severity", headerName: "Severity", width: 120, renderCell: (p) => <StatusChip label={p.value} /> },
    {
      field: "status",
      headerName: "Status",
      width: 140,
      renderCell: (p) => <StatusChip label={String(p.value).replace("_", " ")} />,
    },
    {
      field: "camera_id",
      headerName: "Camera",
      width: 110,
      valueGetter: (_v, row) => (row.camera_id ? `Camera ${row.camera_id}` : "--"),
    },
    { field: "event_count", headerName: "Events", width: 90, sortable: false },
    {
      field: "created_at",
      headerName: "Created",
      width: 180,
      valueGetter: (_v, row) => (row.created_at ? new Date(row.created_at).toLocaleString() : "--"),
    },
  ];

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Incidents
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Incident response workflow over the same records shown in Report Center -- status transitions, notes, and
          linked events, backed by GET/PUT /reports.
        </Typography>
      </Box>

      <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          placeholder="Search title or summary..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 240 }}
        />
        <TextField
          size="small"
          select
          label="Status"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPaginationModel((m) => ({ ...m, page: 0 }));
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All statuses</MenuItem>
          {STATUSES.map((s) => (
            <MenuItem key={s} value={s} sx={{ textTransform: "capitalize" }}>
              {s.replace("_", " ")}
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
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All severities</MenuItem>
          {SEVERITIES.map((s) => (
            <MenuItem key={s} value={s} sx={{ textTransform: "capitalize" }}>
              {s}
            </MenuItem>
          ))}
        </TextField>
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
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
          onRowClick={(params) => navigate(`/incidents/${params.row.id}`)}
        />
      </Box>
    </Box>
  );
}
