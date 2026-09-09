import { createTheme, alpha } from "@mui/material/styles";

/**
 * Enterprise SOC dark theme: near-black surfaces, restrained blue/gray
 * chrome, and reserved severity colors (green/orange/red) used ONLY for
 * status/severity signaling -- never as decoration -- so operators can
 * trust the color coding.
 */

const palette = {
  bg: {
    default: "#0a0e14",
    paper: "#0d1117",
    elevated: "#161b22",
  },
  border: "#30363d",
  text: {
    primary: "#e6edf3",
    secondary: "#8b949e",
    disabled: "#6b7280",
  },
  brand: {
    main: "#00d9ff",
    light: "#5ce6ff",
    dark: "#0099b3",
  },
  severity: {
    low: "#00ff88",
    medium: "#ffb800",
    high: "#ff6b00",
    critical: "#ff3b3b",
    offline: "#6b7280",
  },
};

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: palette.brand.main, light: palette.brand.light, dark: palette.brand.dark },
    success: { main: palette.severity.low },
    warning: { main: palette.severity.medium },
    error: { main: palette.severity.critical },
    background: { default: palette.bg.default, paper: palette.bg.paper },
    text: { primary: palette.text.primary, secondary: palette.text.secondary, disabled: palette.text.disabled },
    divider: palette.border,
  },
  shape: { borderRadius: 4 }, // slightly sharper for a tactical feel
  typography: {
    fontFamily: '"Inter", "Segoe UI", sans-serif',
    h1: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    h2: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    h3: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    h4: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    h5: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    h6: { fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" },
    button: { fontFamily: '"IBM Plex Mono", monospace', textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" },
    body1: { fontFamily: '"Inter", sans-serif' },
    body2: { fontFamily: '"Inter", sans-serif' },
    subtitle1: { fontFamily: '"IBM Plex Mono", monospace', textTransform: "uppercase", letterSpacing: "0.05em" },
    subtitle2: { fontFamily: '"IBM Plex Mono", monospace', textTransform: "uppercase", letterSpacing: "0.05em" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage: `
            radial-gradient(1200px 600px at 100% -10%, ${alpha(palette.brand.main, 0.06)}, transparent),
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
          `,
          backgroundSize: "100% 100%, 40px 40px, 40px 40px",
        },
        "::-webkit-scrollbar": { width: 8, height: 8 },
        "::-webkit-scrollbar-thumb": { background: palette.border, borderRadius: 0 },
        "::-webkit-scrollbar-track": { background: "transparent" },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          border: `1px solid ${palette.border}`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: palette.bg.paper,
          border: `1px solid ${palette.border}`,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontSize: 12 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: palette.border },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: palette.bg.default, borderRight: `1px solid ${palette.border}` },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: alpha(palette.bg.default, 0.85),
          backdropFilter: "blur(10px)",
          backgroundImage: "none",
        },
      },
    },
  },
});

export const severityColor = (severity: string | undefined | null): string => {
  switch ((severity ?? "").toLowerCase()) {
    case "critical":
      return palette.severity.critical;
    case "high":
      return palette.severity.high;
    case "medium":
      return palette.severity.medium;
    case "low":
    case "healthy":
    case "online":
      return palette.severity.low;
    case "offline":
      return palette.severity.offline;
    default:
      return palette.text.disabled;
  }
};

export { palette };
