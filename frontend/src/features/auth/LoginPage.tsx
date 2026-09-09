import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Link from "@mui/material/Link";
import { motion } from "framer-motion";
import { useAuth } from "../../auth/useAuth";

export function LoginPage() {
  const { login, register, loginError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    const ok = mode === "login" ? await login(username.trim(), password) : await register(username.trim(), email.trim(), password);
    setSubmitting(false);
    if (ok) {
      navigate(redirectTo, { replace: true });
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "radial-gradient(60% 50% at 50% 0%, rgba(61,139,253,0.10), transparent), #0a0d12",
        p: 2,
      }}
    >
      <Paper
        component={motion.div}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        sx={{ width: 380, p: 4, borderRadius: 3 }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
          <Box sx={{ width: 32, height: 32, borderRadius: 1.5, background: "linear-gradient(155deg, #3d8bfd, #2fb787)" }} />
          <Box>
            <Typography variant="subtitle1" fontWeight={700}>
              Sentinel SOC
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Surveillance Platform
            </Typography>
          </Box>
        </Box>

        {mode === "register" && (
          <Alert severity="info" variant="outlined" sx={{ mb: 3, fontSize: 12.5 }}>
            The <strong>first</strong> account ever created becomes Admin
            automatically. After that, only an Admin can create new
            accounts (a Users management page is a planned follow-up).
          </Alert>
        )}

        {loginError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {loginError}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            sx={{ mb: 2 }}
          />
          {mode === "register" && (
            <TextField fullWidth type="email" label="Email" value={email} onChange={(e) => setEmail(e.target.value)} sx={{ mb: 2 }} />
          )}
          <TextField
            fullWidth
            type="password"
            label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 3 }}
          />
          <Button fullWidth type="submit" variant="contained" size="large" disabled={submitting}>
            {submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </Box>

        <Typography variant="caption" sx={{ display: "block", textAlign: "center", mt: 2.5, color: "text.secondary" }}>
          {mode === "login" ? (
            <>
              No account on this backend yet?{" "}
              <Link component="button" type="button" onClick={() => setMode("register")}>
                Create the first one
              </Link>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <Link component="button" type="button" onClick={() => setMode("login")}>
                Sign in instead
              </Link>
            </>
          )}
        </Typography>
      </Paper>
    </Box>
  );
}
