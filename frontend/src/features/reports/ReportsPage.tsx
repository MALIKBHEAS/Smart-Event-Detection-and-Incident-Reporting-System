import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef, GridPaginationModel, GridSortModel } from "@mui/x-data-grid";
import { useReportsList, useCreateReport, useDeleteReport } from "./useReports";
import { reportsApi, triggerBlobDownload } from "../../api/endpoints/reports";
import { ReportFormDialog } from "./ReportFormDialog";
import type { ReportFormValues } from "./ReportFormDialog";
import { ConfirmDialog } from "../../components/common/ConfirmDialog";
import { ErrorState } from "../../components/common/ErrorState";
import { StatusChip } from "../../components/common/StatusChip";
import { useAuth } from "../../auth/useAuth";
import type { Report } from "../../api/types";

export function ReportsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = user?.roles.some((role) => role === "Admin" || role === "Security Operator") ?? false;

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 10 });
  const [sortModel, setSortModel] = useState<GridSortModel>([{ field: "created_at", sort: "desc" }]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Report | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

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
  const createMutation = useCreateReport();
  const deleteMutation = useDeleteReport();

  async function handleCreate(values: ReportFormValues) {
    setFormError(null);
    try {
      await createMutation.mutateAsync(values);
      setDialogOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create report");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    await deleteMutation.mutateAsync(pendingDelete.id);
    setPendingDelete(null);
  }

  async function handleDownload(report: Report, kind: "pdf" | "csv") {
    setDownloadingId(report.id);
    try {
      const blob = kind === "pdf" ? await reportsApi.downloadPdf(report.id) : await reportsApi.downloadCsv(report.id);
      triggerBlobDownload(blob, `report-${report.id}.${kind}`);
    } finally {
      setDownloadingId(null);
    }
  }

  const columns: GridColDef<Report>[] = [
    { field: "id", headerName: "ID", width: 70 },
    { field: "title", headerName: "Title", flex: 1.4, minWidth: 200 },
    {
      field: "severity",
      headerName: "Severity",
      width: 120,
      sortable: true,
      renderCell: (params) => <StatusChip label={params.value} />,
    },
    {
      field: "status",
      headerName: "Status",
      width: 130,
      sortable: true,
      renderCell: (params) => <StatusChip label={String(params.value).replace("_", " ")} />,
    },
    { field: "event_count", headerName: "Events", width: 90, sortable: false },
    {
      field: "created_at",
      headerName: "Created",
      width: 170,
      sortable: true,
      valueGetter: (_v, row) => (row.created_at ? new Date(row.created_at).toLocaleString() : "--"),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 190,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={0.25}>
          <Tooltip title="View">
            <IconButton size="small" onClick={() => navigate(`/reports/${params.row.id}`)}>
              <VisibilityOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Download PDF">
            <IconButton size="small" disabled={downloadingId === params.row.id} onClick={() => handleDownload(params.row, "pdf")}>
              <PictureAsPdfOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Download CSV">
            <IconButton size="small" disabled={downloadingId === params.row.id} onClick={() => handleDownload(params.row, "csv")}>
              <TableChartOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          {canWrite && (
            <Tooltip title="Delete">
              <IconButton size="small" color="error" onClick={() => setPendingDelete(params.row)}>
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ),
    },
  ];

  return (
    <Box>
      <Stack direction="row" alignItems="flex-end" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" gap={1.5}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Report center
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Incident reports with PDF/CSV export, linked events, evidence, and analytics summaries.
          </Typography>
        </Box>
        {canWrite && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            New report
          </Button>
        )}
      </Stack>

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
          {["open", "in_progress", "resolved", "closed"].map((s) => (
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
          {["low", "medium", "high", "critical"].map((s) => (
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
          onRowClick={(params) => navigate(`/reports/${params.row.id}`)}
        />
      </Box>

      <ReportFormDialog
        open={dialogOpen}
        initial={null}
        submitting={createMutation.isPending}
        errorMessage={formError}
        onCancel={() => {
          setDialogOpen(false);
          setFormError(null);
        }}
        onSubmit={handleCreate}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete report"
        description={`Delete "${pendingDelete?.title}"? This can't be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </Box>
  );
}
