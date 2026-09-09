import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./features/auth/LoginPage";

const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const CamerasPage = lazy(() => import("./features/cameras/CamerasPage").then((m) => ({ default: m.CamerasPage })));
const AnalyticsPage = lazy(() => import("./features/analytics/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })));
const IntelligencePage = lazy(() => import("./features/intelligence/IntelligencePage").then((m) => ({ default: m.IntelligencePage })));
const HealthPage = lazy(() => import("./features/health/HealthPage").then((m) => ({ default: m.HealthPage })));
const LiveMonitoringPage = lazy(() => import("./features/live-monitoring/LiveMonitoringPage").then((m) => ({ default: m.LiveMonitoringPage })));
const IncidentsPage = lazy(() => import("./features/incidents/IncidentsPage").then((m) => ({ default: m.IncidentsPage })));
const IncidentDetailPage = lazy(() => import("./features/incidents/IncidentDetailPage").then((m) => ({ default: m.IncidentDetailPage })));
const EventsPage = lazy(() => import("./features/events/EventsPage").then((m) => ({ default: m.EventsPage })));
const ReportsPage = lazy(() => import("./features/reports/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const ReportDetailPage = lazy(() => import("./features/reports/ReportDetailPage").then((m) => ({ default: m.ReportDetailPage })));
const NotificationsPage = lazy(() => import("./features/notifications/NotificationsPage").then((m) => ({ default: m.NotificationsPage })));
const UsersPage = lazy(() => import("./features/users/UsersPage").then((m) => ({ default: m.UsersPage })));
const SettingsPage = lazy(() => import("./features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })));

function RouteFallback() {
  return (
    <Box sx={{ display: "grid", placeItems: "center", height: "60vh" }}>
      <CircularProgress size={28} />
    </Box>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/dashboard"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <DashboardPage />
                </Suspense>
              }
            />
            <Route
              path="/live-monitoring"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <LiveMonitoringPage />
                </Suspense>
              }
            />
            <Route
              path="/cameras"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <CamerasPage />
                </Suspense>
              }
            />
            <Route
              path="/incidents"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <IncidentsPage />
                </Suspense>
              }
            />
            <Route
              path="/incidents/:id"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <IncidentDetailPage />
                </Suspense>
              }
            />
            <Route
              path="/events"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <EventsPage />
                </Suspense>
              }
            />
            <Route
              path="/reports"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <ReportsPage />
                </Suspense>
              }
            />
            <Route
              path="/reports/:id"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <ReportDetailPage />
                </Suspense>
              }
            />
            <Route
              path="/analytics"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <AnalyticsPage />
                </Suspense>
              }
            />
            <Route
              path="/intelligence"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <IntelligencePage />
                </Suspense>
              }
            />
            <Route
              path="/notifications"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <NotificationsPage />
                </Suspense>
              }
            />
            <Route
              path="/users"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <UsersPage />
                </Suspense>
              }
            />
            <Route
              path="/settings"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <SettingsPage />
                </Suspense>
              }
            />
            <Route
              path="/health"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <HealthPage />
                </Suspense>
              }
            />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  );
}
