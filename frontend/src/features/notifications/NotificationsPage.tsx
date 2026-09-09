import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Skeleton from "@mui/material/Skeleton";
import { useNavigate } from "react-router-dom";
import { useNotificationsList, useMarkNotificationRead, useMarkAllNotificationsRead } from "./useNotifications";
import { useNotificationSocket } from "./useNotificationSocket";
import { StatusChip } from "../../components/common/StatusChip";
import { ErrorState } from "../../components/common/ErrorState";

export function NotificationsPage() {
  const navigate = useNavigate();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { connected } = useNotificationSocket();
  const { data, isLoading, error, refetch } = useNotificationsList({ page_size: 50, unread_only: unreadOnly });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <Box>
      <Stack direction="row" alignItems="flex-end" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" gap={1.5}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Notifications
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Real-time via WebSocket ({connected ? "connected" : "reconnecting"}). Backed by GET /notifications.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <ToggleButtonGroup size="small" value={unreadOnly ? "unread" : "all"} exclusive onChange={(_e, v) => v && setUnreadOnly(v === "unread")}>
            <ToggleButton value="all">All</ToggleButton>
            <ToggleButton value="unread">Unread</ToggleButton>
          </ToggleButtonGroup>
          <Button size="small" variant="outlined" disabled={!data?.unread_count} onClick={() => markAllRead.mutate()}>
            Mark all read ({data?.unread_count ?? 0})
          </Button>
        </Stack>
      </Stack>

      {error && <ErrorState message={error.message} onRetry={() => refetch()} />}

      <Paper>
        {isLoading ? (
          <Box sx={{ p: 2 }}>
            <Skeleton height={60} />
            <Skeleton height={60} />
            <Skeleton height={60} />
          </Box>
        ) : data && data.items.length > 0 ? (
          <List disablePadding>
            {data.items.map((n) => (
              <ListItem
                key={n.id}
                divider
                sx={{ opacity: n.read ? 0.6 : 1, cursor: n.related_type === "report" ? "pointer" : "default" }}
                onClick={() => {
                  if (!n.read) markRead.mutate(n.id);
                  if (n.related_type === "report" && n.related_id) navigate(`/incidents/${n.related_id}`);
                }}
                secondaryAction={<StatusChip label={n.severity} />}
              >
                <ListItemText
                  primary={n.message}
                  secondary={n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                  slotProps={{ primary: { fontWeight: n.read ? 400 : 600 } }}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Box sx={{ p: 6, textAlign: "center" }}>
            <Typography variant="body1" fontWeight={600} gutterBottom>
              No notifications
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {unreadOnly ? "No unread notifications." : "New event/incident notifications will appear here in real time."}
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
}
