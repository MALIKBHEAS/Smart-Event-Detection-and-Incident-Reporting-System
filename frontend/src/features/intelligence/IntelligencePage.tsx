import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Divider from "@mui/material/Divider";
import Table from "@mui/material/Table";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import TableBody from "@mui/material/TableBody";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { motion } from "framer-motion";
import {
  useAnalyticsRisk,
  useAnalyticsRecommendations,
  useAnalyticsSummary,
  useAnalyticsHotspots,
  useAnalyticsIncidents,
  useAnalyticsTrends,
} from "../../api/queries";
import { StatusChip } from "../../components/common/StatusChip";
import { severityColor } from "../../app/theme";

function riskGaugeColor(score: number) {
  if (score >= 75) return "#e5484d";
  if (score >= 50) return "#e2622f";
  if (score >= 25) return "#e6a13c";
  return "#2fb787";
}

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "up") return <TrendingUpIcon fontSize="small" sx={{ color: "#e5484d" }} />;
  if (direction === "down") return <TrendingDownIcon fontSize="small" sx={{ color: "#2fb787" }} />;
  return <TrendingFlatIcon fontSize="small" sx={{ color: "text.secondary" }} />;
}

export function IntelligencePage() {
  const { data: risk } = useAnalyticsRisk(30);
  const { data: recs } = useAnalyticsRecommendations(30);
  const { data: summary } = useAnalyticsSummary(24);
  const { data: hotspots } = useAnalyticsHotspots(30);
  const { data: incidents } = useAnalyticsIncidents(30);
  const { data: trends } = useAnalyticsTrends();

  const gaugeData = risk ? [{ value: risk.overall_risk_score, fill: riskGaugeColor(risk.overall_risk_score) }] : [];

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        AI Intelligence
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Rule-based analytics from the Intelligence &amp; Analytics module (risk scoring, pattern detection, and
        recommendations derived from stored events/incidents -- not a live ML model).
      </Typography>

      <Grid container spacing={2.5}>
        {/* Risk score gauge */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper component={motion.div} initial={{ opacity: 0 }} animate={{ opacity: 1 }} sx={{ p: 2.5, height: "100%", textAlign: "center" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
              Overall Risk Score
            </Typography>
            <Box sx={{ height: 200, position: "relative" }}>
              <ResponsiveContainer>
                <RadialBarChart innerRadius="70%" outerRadius="100%" data={gaugeData} startAngle={90} endAngle={-270}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
              <Box sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                <Box>
                  <Typography variant="h3" fontWeight={700}>
                    {risk?.overall_risk_score ?? "--"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    / 100
                  </Typography>
                </Box>
              </Box>
            </Box>
            {risk && <StatusChip label={risk.overall_risk_level} />}
          </Paper>
        </Grid>

        {/* Executive summary */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
              Executive Summary &middot; {summary?.window_label}
            </Typography>
            <Typography variant="body2" sx={{ mb: 2, lineHeight: 1.7 }}>
              {summary?.narrative ?? "Loading..."}
            </Typography>
            <Grid container spacing={2}>
              <Grid size={4}>
                <Typography variant="caption" color="text.secondary">Highest risk camera</Typography>
                <Typography variant="body2" fontWeight={600}>{summary?.highest_risk_camera ?? "--"}</Typography>
              </Grid>
              <Grid size={4}>
                <Typography variant="caption" color="text.secondary">Most frequent event</Typography>
                <Typography variant="body2" fontWeight={600}>{summary?.most_frequent_event ?? "--"}</Typography>
              </Grid>
              <Grid size={4}>
                <Typography variant="caption" color="text.secondary">Peak activity</Typography>
                <Typography variant="body2" fontWeight={600}>{summary?.peak_activity_window ?? "--"}</Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Camera ranking */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Camera Risk Ranking
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Camera</TableCell>
                  <TableCell align="right">Incidents</TableCell>
                  <TableCell align="right">Risk</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(risk?.by_camera ?? []).slice(0, 8).map((c) => (
                  <TableRow key={c.camera_id}>
                    <TableCell>{c.camera_name}</TableCell>
                    <TableCell align="right">{c.incident_count}</TableCell>
                    <TableCell align="right">
                      <StatusChip label={`${c.risk_level} (${c.risk_score})`} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Grid>

        {/* Hotspots: most dangerous camera / time */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Most Dangerous Camera &amp; Time
            </Typography>
            <Stack spacing={1.5} divider={<Divider />}>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">Camera</Typography>
                <Typography variant="body2" fontWeight={600}>{hotspots?.highest_risk_camera?.label ?? "--"}</Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">Hour</Typography>
                <Typography variant="body2" fontWeight={600}>{hotspots?.busiest_hour?.label ?? "--"}</Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">Day of week</Typography>
                <Typography variant="body2" fontWeight={600}>{hotspots?.most_dangerous_day?.label ?? "--"}</Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        {/* Pattern detection */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Pattern Detection
            </Typography>
            <Stack spacing={1.25}>
              {(incidents?.patterns ?? []).length === 0 && (
                <Typography variant="body2" color="text.secondary">No repeating patterns detected.</Typography>
              )}
              {(incidents?.patterns ?? []).map((p, i) => (
                <Box key={i} sx={{ p: 1.5, borderRadius: 1.5, border: "1px solid", borderColor: "divider" }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Chip size="small" label={p.kind.replace(/_/g, " ")} variant="outlined" sx={{ textTransform: "capitalize" }} />
                    <Typography variant="caption" color="text.secondary">{Math.round(p.strength * 100)}% of incidents</Typography>
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 0.75 }}>{p.description}</Typography>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Incident clusters */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Incident Clusters
            </Typography>
            <Stack spacing={1} sx={{ maxHeight: 260, overflowY: "auto" }}>
              {(incidents?.clusters ?? []).slice(0, 6).map((c) => (
                <Box key={c.report_id} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 0.75 }}>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>{c.camera_name ?? "Unknown camera"}</Typography>
                    <Typography variant="caption" color="text.secondary">{c.category} &middot; {c.occurrences} occurrences</Typography>
                  </Box>
                  <StatusChip label={c.severity} />
                </Box>
              ))}
              {(incidents?.clusters ?? []).length === 0 && (
                <Typography variant="body2" color="text.secondary">No incident clusters in this window.</Typography>
              )}
            </Stack>
          </Paper>
        </Grid>

        {/* Trend prediction (heuristic, not a model) */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle2" fontWeight={700}>
              Trend Direction
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
              Heuristic period-over-period comparison, not a forecasting model.
            </Typography>
            <Stack spacing={1.25}>
              {(trends?.trends ?? []).map((t) => (
                <Box key={t.label} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Typography variant="body2">{t.label}</Typography>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <TrendIcon direction={t.direction} />
                    <Typography variant="body2" fontWeight={600}>
                      {t.current} {t.change_pct != null ? `(${t.change_pct > 0 ? "+" : ""}${t.change_pct}%)` : ""}
                    </Typography>
                  </Stack>
                </Box>
              ))}
            </Stack>
          </Paper>
        </Grid>

        {/* Recommendations */}
        <Grid size={12}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Smart Recommendations
            </Typography>
            <Grid container spacing={1.5}>
              {(recs?.recommendations ?? []).map((r, i) => (
                <Grid size={{ xs: 12, md: 4 }} key={i}>
                  <Box sx={{ p: 1.75, borderRadius: 1.5, border: "1px solid", borderColor: "divider", height: "100%" }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
                      <Typography variant="body2" fontWeight={700}>{r.title}</Typography>
                      <Chip
                        size="small"
                        label={r.priority}
                        sx={{ bgcolor: `${severityColor(r.priority === "high" ? "high" : r.priority === "medium" ? "medium" : "low")}22` }}
                      />
                    </Stack>
                    <Typography variant="caption" color="text.secondary">{r.detail}</Typography>
                  </Box>
                </Grid>
              ))}
              {(recs?.recommendations ?? []).length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ px: 1 }}>
                  No recommendations right now -- fleet risk is within normal bounds.
                </Typography>
              )}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
