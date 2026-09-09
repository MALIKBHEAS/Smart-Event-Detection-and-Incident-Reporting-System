import { useState } from "react";
import { useNavigate } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import Avatar from "@mui/material/Avatar";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import { useAuth } from "../../auth/useAuth";

export function ProfileMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const initials = (user?.username ?? "??").slice(0, 2).toUpperCase();

  async function handleLogout() {
    setAnchorEl(null);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <>
      <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} size="small" sx={{ ml: 0.5 }}>
        <Avatar sx={{ width: 32, height: 32, fontSize: 13, bgcolor: "primary.main" }}>{initials}</Avatar>
      </IconButton>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="body2" fontWeight={600}>
            {user?.username}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
            {user?.email}
          </Typography>
          {user?.roles.map((role) => (
            <Chip key={role} label={role} size="small" variant="outlined" sx={{ mr: 0.5, mt: 0.5 }} />
          ))}
        </Box>
        <Divider />
        <MenuItem
          onClick={() => {
            setAnchorEl(null);
            navigate("/settings");
          }}
        >
          <ListItemIcon>
            <SettingsOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Sign out</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
}
