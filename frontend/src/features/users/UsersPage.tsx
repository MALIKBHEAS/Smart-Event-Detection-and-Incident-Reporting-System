import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import MenuItem from "@mui/material/MenuItem";
import Alert from "@mui/material/Alert";
import AddIcon from "@mui/icons-material/Add";
import BlockOutlinedIcon from "@mui/icons-material/BlockOutlined";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import { DataGrid } from "@mui/x-data-grid";
import type { GridColDef } from "@mui/x-data-grid";
import { useUsersList, useSetUserActive, useSetUserRoles, useCreateUser } from "./useUsers";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";
import { ConfirmDialog } from "../../components/common/ConfirmDialog";
import { useAuth } from "../../auth/useAuth";
import type { ManagedUser } from "../../api/types";

const ROLES = ["Admin", "Security Operator", "Viewer"];

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const { data: users, isLoading, error, refetch } = useUsersList();
  const setActiveMutation = useSetUserActive();
  const setRolesMutation = useSetUserRoles();
  const createMutation = useCreateUser();

  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDeactivate, setPendingDeactivate] = useState<ManagedUser | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("Viewer");

  async function handleCreate() {
    setFormError(null);
    try {
      await createMutation.mutateAsync({ username: newUsername, email: newEmail, password: newPassword, role: newRole });
      setCreateOpen(false);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      setNewRole("Viewer");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create user");
    }
  }

  async function handleDeactivate() {
    if (!pendingDeactivate) return;
    await setActiveMutation.mutateAsync({ id: pendingDeactivate.id, isActive: false });
    setPendingDeactivate(null);
  }

  const columns: GridColDef<ManagedUser>[] = [
    { field: "id", headerName: "ID", width: 70 },
    { field: "username", headerName: "Username", flex: 1, minWidth: 140 },
    { field: "email", headerName: "Email", flex: 1.2, minWidth: 200 },
    {
      field: "roles",
      headerName: "Role",
      width: 170,
      renderCell: (params) => (
        <TextField
          select
          size="small"
          variant="standard"
          value={params.row.roles[0] ?? "Viewer"}
          disabled={params.row.id === currentUser?.id}
          onChange={(e) => setRolesMutation.mutate({ id: params.row.id, roles: [e.target.value] })}
          sx={{ minWidth: 150 }}
        >
          {ROLES.map((r) => (
            <MenuItem key={r} value={r}>
              {r}
            </MenuItem>
          ))}
        </TextField>
      ),
    },
    {
      field: "is_active",
      headerName: "Status",
      width: 120,
      renderCell: (params) => <StatusChip label={params.value ? "active" : "disabled"} />,
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Tooltip title={params.row.id === currentUser?.id ? "You can't change your own status" : params.row.is_active ? "Disable" : "Enable"}>
          <span>
            <IconButton
              size="small"
              disabled={params.row.id === currentUser?.id}
              color={params.row.is_active ? "error" : "success"}
              onClick={() =>
                params.row.is_active
                  ? setPendingDeactivate(params.row)
                  : setActiveMutation.mutate({ id: params.row.id, isActive: true })
              }
            >
              {params.row.is_active ? <BlockOutlinedIcon fontSize="small" /> : <CheckCircleOutlinedIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
      ),
    },
  ];

  return (
    <Box>
      <Stack direction="row" alignItems="flex-end" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" gap={1.5}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Users
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Admin-only. Backed by GET/PUT /users and POST /auth/register.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
          New user
        </Button>
      </Stack>

      {error && <ErrorState message={error.message} onRetry={() => refetch()} />}

      <Box sx={{ height: 480, width: "100%" }}>
        <DataGrid rows={users ?? []} columns={columns} loading={isLoading} disableRowSelectionOnClick hideFooter={(users?.length ?? 0) <= 10} />
      </Box>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Create user</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            {formError && <Alert severity="error">{formError}</Alert>}
            <TextField label="Username" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} autoFocus fullWidth />
            <TextField label="Email" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} fullWidth />
            <TextField label="Password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} fullWidth />
            <TextField select label="Role" value={newRole} onChange={(e) => setNewRole(e.target.value)} fullWidth>
              {ROLES.map((r) => (
                <MenuItem key={r} value={r}>
                  {r}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setCreateOpen(false)} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleCreate} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create user"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={pendingDeactivate !== null}
        title="Disable user"
        description={`Disable "${pendingDeactivate?.username}"? They won't be able to sign in until re-enabled.`}
        confirmLabel="Disable"
        destructive
        loading={setActiveMutation.isPending}
        onConfirm={handleDeactivate}
        onCancel={() => setPendingDeactivate(null)}
      />
    </Box>
  );
}
