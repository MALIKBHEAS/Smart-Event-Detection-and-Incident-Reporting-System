import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import StopOutlinedIcon from "@mui/icons-material/StopOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { useCameras, useWorkersHealth, useAnalyticsCameras } from "../../api/queries";
import { useAuth } from "../../auth/useAuth";
import { useCreateCamera, useUpdateCamera, useDeleteCamera, useStartWorker, useStopWorker } from "./useCameraMutations";
import { CameraFormDialog } from "./CameraFormDialog";
import { ConfirmDialog } from "../../components/common/ConfirmDialog";
import { ErrorState } from "../../components/common/ErrorState";
import { StatusChip } from "../../components/common/StatusChip";
import type { Camera } from "../../api/types";
import type { CameraFormValues } from "./cameraSchema";

interface Row extends Camera {
  workerConnected: boolean;
  riskLevel: string | null;
  riskScore: number | null;
}

export function CamerasPage() {
  const { user } = useAuth();
  const canWrite = user?.roles.some((role) => role === "Admin" || role === "Security Operator") ?? false;
  const { data: cameras, isLoading, error, refetch } = useCameras();
  const { data: workersHealth } = useWorkersHealth();
  const { data: cameraAnalytics } = useAnalyticsCameras(30);

  const createMutation = useCreateCamera();
  const updateMutation = useUpdateCamera();
  const deleteMutation = useDeleteCamera();
  const startMutation = useStartWorker();
  const stopMutation = useStopWorker();

  const [dialogCamera, setDialogCamera] = useState<Camera | null | undefined>(undefined);
  const [pendingDelete, setPendingDelete] = useState<Camera | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const rows: Row[] = useMemo(() => {
    const riskByCamera = new Map(cameraAnalytics?.cameras.map((c) => [c.camera_id, c]) ?? []);
    return (cameras ?? []).map((camera) => {
      const worker = workersHealth?.workers[String(camera.id)];
      const risk = riskByCamera.get(camera.id);
      return {
        ...camera,
        workerConnected: worker?.connected ?? false,
        riskLevel: risk?.risk_level ?? null,
        riskScore: risk?.risk_score ?? null,
      };
    });
  }, [cameras, workersHealth, cameraAnalytics]);

  async function handleCreate(values: CameraFormValues) {
    setFormError(null);
    try {
      await createMutation.mutateAsync({ ...values, location: values.location || null });
      setDialogCamera(undefined);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create camera");
    }
  }

  async function handleUpdate(id: number, values: CameraFormValues) {
    setFormError(null);
    try {
      await updateMutation.mutateAsync({ id, input: { ...values, location: values.location || null } });
      setDialogCamera(undefined);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to update camera");
    }
  }

  async function handleDelete() {
    if (!pendingDelete) return;
    await deleteMutation.mutateAsync(pendingDelete.id);
    setPendingDelete(null);
  }

  const columns: GridColDef<Row>[] = [
    { field: "name", headerName: "Camera", flex: 1, minWidth: 160 },
    {
      field: "enabled",
      headerName: "Status",
      width: 120,
      renderCell: (params) => <StatusChip label={params.value ? "enabled" : "disabled"} />,
    },
    { field: "location", headerName: "Location", flex: 1, minWidth: 140, valueGetter: (_v, row) => row.location ?? "--" },
    { field: "rtsp_url", headerName: "RTSP URL", flex: 1.4, minWidth: 200 },
    {
      field: "fps",
      headerName: "FPS",
      width: 90,
      sortable: false,
      renderCell: () => (
        <Tooltip title="Not exposed by the backend">
          <span>n/a</span>
        </Tooltip>
      ),
    },
    {
      field: "health",
      headerName: "Health",
      width: 110,
      renderCell: (params) => <StatusChip label={params.row.workerConnected ? "healthy" : "unknown"} />,
    },
    {
      field: "riskLevel",
      headerName: "Risk",
      width: 110,
      renderCell: (params) => (params.row.riskLevel ? <StatusChip label={params.row.riskLevel} /> : <span>--</span>),
    },
    {
      field: "worker",
      headerName: "Worker",
      width: 130,
      renderCell: (params) => <StatusChip label={params.row.workerConnected ? "running" : "stopped"} />,
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 210,
      sortable: false,
      filterable: false,
      renderCell: (params) =>
        !canWrite ? (
          <Typography variant="caption" color="text.secondary">
            View only
          </Typography>
        ) : (
        <Stack direction="row" spacing={0.25}>
          <Tooltip title="Start worker">
            <IconButton size="small" onClick={() => startMutation.mutate(params.row.id)}>
              <PlayArrowOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Stop / reconnect worker">
            <IconButton size="small" onClick={() => stopMutation.mutate(params.row.id)}>
              <StopOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reconnect (stop then start)">
            <IconButton
              size="small"
              onClick={async () => {
                await stopMutation.mutateAsync(params.row.id);
                startMutation.mutate(params.row.id);
              }}
            >
              <RefreshOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Edit">
            <IconButton size="small" onClick={() => setDialogCamera(params.row)}>
              <EditOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete">
            <IconButton size="small" color="error" onClick={() => setPendingDelete(params.row)}>
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
        )
    },
  ];

  return (
    <Box>
      <Stack direction="row" alignItems="flex-end" justifyContent="space-between" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Camera management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create, edit, and control camera workers. Backed by /cameras and /workers/start|stop.
          </Typography>
        </Box>
        {canWrite && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogCamera(null)}>
            Add camera
          </Button>
        )}
      </Stack>

      {error && <ErrorState message={error.message} onRetry={() => refetch()} />}

      <Box sx={{ height: 560, width: "100%" }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={isLoading}
          density="comfortable"
          disableRowSelectionOnClick
          slots={{ toolbar: GridToolbar }}
          slotProps={{ toolbar: { showQuickFilter: true } }}
          initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
          pageSizeOptions={[10, 25, 50]}
        />
      </Box>

      {dialogCamera !== undefined && (
        <CameraFormDialog
          open
          initial={dialogCamera}
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onCancel={() => {
            setDialogCamera(undefined);
            setFormError(null);
          }}
          onSubmit={(values) => (dialogCamera ? handleUpdate(dialogCamera.id, values) : handleCreate(values))}
        />
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete camera"
        description={`Delete "${pendingDelete?.name}"? This can't be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </Box>
  );
}
