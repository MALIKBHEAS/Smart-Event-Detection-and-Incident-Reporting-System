import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { NavLink, useLocation } from "react-router-dom";
import { useUiStore } from "../../app/uiStore";
import { NAV_ITEMS } from "./navConfig";

export const SIDEBAR_WIDTH_EXPANDED = 240;
export const SIDEBAR_WIDTH_COLLAPSED = 72;

export function Sidebar() {
  const { sidebarOpen, closeSidebar, sidebarCollapsed, toggleSidebarCollapsed } = useUiStore();
  const location = useLocation();
  const width = sidebarCollapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED;

  const content = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.25,
          px: sidebarCollapsed ? 1.5 : 2.25,
          py: 2.25,
          minHeight: 64,
        }}
      >
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: 1,
            flexShrink: 0,
            background: "linear-gradient(155deg, #3d8bfd, #2fb787)",
          }}
        />
        {!sidebarCollapsed && (
          <Box sx={{ overflow: "hidden" }}>
            <Typography variant="subtitle2" fontWeight={700} noWrap>
              Sentinel SOC
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              Surveillance Platform
            </Typography>
          </Box>
        )}
      </Box>

      <List sx={{ flex: 1, px: 1, py: 0 }}>
        {NAV_ITEMS.map((item) => {
          const active = location.pathname.startsWith(item.path);
          const button = (
            <ListItemButton
              key={item.path}
              component={NavLink}
              to={item.path}
              onClick={closeSidebar}
              selected={active}
              sx={{
                borderRadius: 1.5,
                mb: 0.5,
                minHeight: 40,
                justifyContent: sidebarCollapsed ? "center" : "flex-start",
                px: sidebarCollapsed ? 1 : 1.5,
                "&.Mui-selected": {
                  bgcolor: "action.selected",
                  boxShadow: (t) => `inset 2px 0 0 ${t.palette.primary.main}`,
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: sidebarCollapsed ? "auto" : 36, color: active ? "primary.light" : "text.secondary" }}>
                <item.icon fontSize="small" />
              </ListItemIcon>
              {!sidebarCollapsed && (
                <>
                  <ListItemText
                    primary={item.label}
                    slotProps={{ primary: { fontSize: 13.5, fontWeight: active ? 600 : 500 } }}
                  />
                  {!item.live && <Chip label="soon" size="small" variant="outlined" sx={{ height: 18, fontSize: 9.5 }} />}
                </>
              )}
            </ListItemButton>
          );
          return sidebarCollapsed ? (
            <Tooltip key={item.path} title={item.label} placement="right">
              {button}
            </Tooltip>
          ) : (
            button
          );
        })}
      </List>

      <Box sx={{ p: 1, display: { xs: "none", md: "block" } }}>
        <IconButton onClick={toggleSidebarCollapsed} size="small" sx={{ width: "100%", borderRadius: 1.5 }}>
          {sidebarCollapsed ? <ChevronRightIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
        </IconButton>
      </Box>
    </Box>
  );

  return (
    <>
      {/* Desktop: permanent drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width,
          flexShrink: 0,
          transition: "width 0.2s ease",
          "& .MuiDrawer-paper": { width, boxSizing: "border-box", transition: "width 0.2s ease", overflowX: "hidden" },
        }}
      >
        {content}
      </Drawer>

      {/* Mobile: temporary drawer */}
      <Drawer
        variant="temporary"
        open={sidebarOpen}
        onClose={closeSidebar}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { width: SIDEBAR_WIDTH_EXPANDED, boxSizing: "border-box" },
        }}
      >
        {content}
      </Drawer>
    </>
  );
}
