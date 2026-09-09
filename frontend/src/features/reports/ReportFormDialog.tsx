import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Report } from "../../api/types";

const reportSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  summary: z.string().min(1, "Summary is required").max(2048),
  severity: z.enum(["low", "medium", "high", "critical"]),
  status: z.enum(["open", "in_progress", "resolved", "closed"]),
});

export type ReportFormValues = z.infer<typeof reportSchema>;

interface ReportFormDialogProps {
  open: boolean;
  initial: Report | null;
  submitting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (values: ReportFormValues) => void;
}

export function ReportFormDialog({ open, initial, submitting, errorMessage, onCancel, onSubmit }: ReportFormDialogProps) {
  const isEdit = initial !== null;
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ReportFormValues>({
    resolver: zodResolver(reportSchema),
    values: {
      title: initial?.title ?? "",
      summary: initial?.summary ?? "",
      severity: (initial?.severity as ReportFormValues["severity"]) ?? "low",
      status: (initial?.status as ReportFormValues["status"]) ?? "open",
    },
  });

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Edit report" : "New report"}</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Stack spacing={2.25} sx={{ mt: 0.5 }}>
            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
            <Controller
              name="title"
              control={control}
              render={({ field }) => (
                <TextField {...field} label="Title" fullWidth autoFocus error={!!errors.title} helperText={errors.title?.message} />
              )}
            />
            <Controller
              name="summary"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Summary"
                  fullWidth
                  multiline
                  minRows={3}
                  error={!!errors.summary}
                  helperText={errors.summary?.message}
                />
              )}
            />
            <Stack direction="row" spacing={2}>
              <Controller
                name="severity"
                control={control}
                render={({ field }) => (
                  <TextField {...field} select label="Severity" fullWidth>
                    {["low", "medium", "high", "critical"].map((s) => (
                      <MenuItem key={s} value={s} sx={{ textTransform: "capitalize" }}>
                        {s}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <TextField {...field} select label="Status" fullWidth>
                    {["open", "in_progress", "resolved", "closed"].map((s) => (
                      <MenuItem key={s} value={s} sx={{ textTransform: "capitalize" }}>
                        {s.replace("_", " ")}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={submitting}>
            {submitting ? "Saving..." : isEdit ? "Save changes" : "Create report"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
