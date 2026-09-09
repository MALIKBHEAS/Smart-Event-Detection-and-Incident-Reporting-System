import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        mt: 4,
        py: 2,
        px: 1,
        borderTop: "1px solid",
        borderColor: "divider",
        display: "flex",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 1,
      }}
    >
      <Typography variant="caption" color="text.secondary">
        Sentinel SOC &middot; Smart Event Detection Platform
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Backend: FastAPI &middot; Frontend: React 19 + MUI
      </Typography>
    </Box>
  );
}
