import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert
      severity="error"
      action={onRetry ? <Button color="inherit" size="small" onClick={onRetry}>Retry</Button> : undefined}
      sx={{ mb: 2 }}
    >
      {message}
    </Alert>
  );
}
