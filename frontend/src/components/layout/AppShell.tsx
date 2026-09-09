import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { AppBreadcrumbs } from "./AppBreadcrumbs";
import { Footer } from "./Footer";

export function AppShell() {
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <Topbar />
        <Container maxWidth="xl" sx={{ flex: 1, py: 3 }}>
          <AppBreadcrumbs />
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
          <Footer />
        </Container>
      </Box>
    </Box>
  );
}
