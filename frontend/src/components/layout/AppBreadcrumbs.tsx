import MuiBreadcrumbs from "@mui/material/Breadcrumbs";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { PAGE_TITLES } from "./navConfig";

export function AppBreadcrumbs() {
  const location = useLocation();
  const label = PAGE_TITLES[location.pathname] ?? "Overview";

  return (
    <MuiBreadcrumbs sx={{ fontSize: 13, mb: 1.5 }}>
      <Link component={RouterLink} to="/dashboard" underline="hover" color="text.secondary" fontSize={13}>
        Sentinel SOC
      </Link>
      <Typography fontSize={13} color="text.primary">
        {label}
      </Typography>
    </MuiBreadcrumbs>
  );
}
