import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { cameraSchema, type CameraFormValues } from "./cameraSchema";
import type { Camera } from "../../api/types";

interface CameraFormDialogProps {
  open: boolean;
  initial: Camera | null;
  submitting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (values: CameraFormValues) => void;
}

export function CameraFormDialog({ open, initial, submitting, errorMessage, onCancel, onSubmit }: CameraFormDialogProps) {
  const isEdit = initial !== null;
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CameraFormValues>({
    resolver: zodResolver(cameraSchema),
    values: {
      name: initial?.name ?? "",
      rtsp_url: initial?.rtsp_url ?? "",
      location: initial?.location ?? "",
      enabled: initial?.enabled ?? true,
    },
  });

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{isEdit ? "Edit camera" : "Add camera"}</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Stack spacing={2.25} sx={{ mt: 0.5 }}>
            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Name" fullWidth autoFocus error={!!errors.name} helperText={errors.name?.message} />
              )}
            />
            <Controller
              name="rtsp_url"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="RTSP URL"
                  placeholder="rtsp://192.168.1.20:554/stream1"
                  fullWidth
                  error={!!errors.rtsp_url}
                  helperText={errors.rtsp_url?.message}
                />
              )}
            />
            <Controller
              name="location"
              control={control}
              render={({ field }) => <TextField {...field} label="Location" fullWidth placeholder="Building 2, west entrance" />}
            />
            <Controller
              name="enabled"
              control={control}
              render={({ field }) => (
                <FormControlLabel control={<Switch checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />} label="Enabled" />
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={submitting}>
            {submitting ? "Saving..." : isEdit ? "Save changes" : "Add camera"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
