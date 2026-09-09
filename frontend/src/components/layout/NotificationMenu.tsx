import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import Badge from "@mui/material/Badge";
import Menu from "@mui/material/Menu";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Button from "@mui/material/Button";
import NotificationsOutlinedIcon from "@mui/icons-material/NotificationsOutlined";
import { useNavigate } from "react-router-dom";
import { useNotificationsList, useMarkNotificationRead, useMarkAllNotificationsRead } from "../../features/notifications/useNotifications";
import { useNotificationSocket } from "../../features/notifications/useNotificationSocket";

export function NotificationMenu() {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const { connected } = useNotificationSocket();
  const { data } = useNotificationsList({ page_size: 8 });
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const items = data?.items ?? [];

  function openRelated(relatedType: string | null, relatedId: number | null, id: number) {
    markRead.mutate(id);
    setAnchorEl(null);
    if (relatedType === "report" && relatedId) navigate(`/incidents/${relatedId}`);
  }

  return (
    <>
      <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} size="small">
        <Badge badgeContent={data?.unread_count ?? 0} color="error">
          <NotificationsOutlinedIcon fontSize="small" />
        </Badge>
      </IconButton>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)} slotProps={{ paper: { sx: { width: 360 } } }}>
        <Box sx={{ px: 2, py: 1.25, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="subtitle2" fontWeight={700}>
              Notifications
            </Typography>
            <Typography variant="caption" color={connected ? "success.main" : "text.secondary"}>
              {connected ? "Live" : "Reconnecting..."}
            </Typography>
          </Box>
          {(data?.unread_count ?? 0) > 0 && (
            <Button size="small" onClick={() => markAllRead.mutate()}>
              Mark all read
            </Button>
          )}
        </Box>
        <Divider />
        {items.length === 0 ? (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No notifications yet.
            </Typography>
          </Box>
        ) : (
          <List dense sx={{ maxHeight: 360, overflowY: "auto" }}>
            {items.map((n) => (
              <ListItemButton
                key={n.id}
                divider
                onClick={() => openRelated(n.related_type, n.related_id, n.id)}
                sx={{ opacity: n.read ? 0.6 : 1 }}
              >
                <ListItemText
                  primary={n.message}
                  secondary={n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                  slotProps={{ primary: { fontSize: 13, fontWeight: n.read ? 400 : 600 }, secondary: { fontSize: 11 } }}
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Menu>
    </>
  );
}
