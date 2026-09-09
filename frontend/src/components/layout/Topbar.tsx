import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import MenuIcon from "@mui/icons-material/Menu";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import { useNavigate } from "react-router-dom";
import { useUiStore } from "../../app/uiStore";
import { useCameras, useHealth } from "../../api/queries";
import { StatusChip } from "../common/StatusChip";
import { NotificationMenu } from "./NotificationMenu";
import { ProfileMenu } from "./ProfileMenu";

export function Topbar() {
  const { toggleSidebar, themeMode, toggleThemeMode } = useUiStore();
  const { data: health } = useHealth();
  const { data: cameras } = useCameras();
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <AppBar position="sticky" elevation={0} color="transparent">
      <Toolbar sx={{ gap: 1.5 }}>
        <IconButton edge="start" onClick={toggleSidebar} sx={{ display: { xs: "inline-flex", md: "none" } }}>
          <MenuIcon />
        </IconButton>

        <Autocomplete
          size="small"
          options={cameras ?? []}
          getOptionLabel={(c) => c.name}
          onChange={(_e, value) => value && navigate("/cameras")}
          sx={{ width: { xs: 140, sm: 260 } }}
          renderInput={(params) => <TextField {...params} placeholder="Search cameras..." />}
        />

        <Box sx={{ flex: 1 }} />

        <Typography variant="body2" color="text.secondary" sx={{ display: { xs: "none", lg: "block" }, fontFamily: "monospace" }}>
          {now.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", year: "numeric", month: "short", day: "numeric" })}
        </Typography>

        <Tooltip title="Backend connection">
          <Box sx={{ display: { xs: "none", sm: "block" } }}>
            <StatusChip label={health ? `backend: ${health.status}` : "backend: connecting"} />
          </Box>
        </Tooltip>

        <Tooltip title="Active workers">
          <Box sx={{ display: { xs: "none", md: "block" } }}>
            <StatusChip label={health ? `${health.workers.active} workers` : "workers: --"} />
          </Box>
        </Tooltip>

        <Tooltip title={themeMode === "dark" ? "Switch to light" : "Switch to dark"}>
          <IconButton onClick={toggleThemeMode} size="small">
            {themeMode === "dark" ? <DarkModeOutlinedIcon fontSize="small" /> : <LightModeOutlinedIcon fontSize="small" />}
          </IconButton>
        </Tooltip>

        <NotificationMenu />
        <ProfileMenu />
      </Toolbar>
    </AppBar>
  );
}
