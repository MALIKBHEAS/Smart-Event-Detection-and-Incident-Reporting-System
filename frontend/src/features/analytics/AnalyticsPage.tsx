import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Skeleton from "@mui/material/Skeleton";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  Legend,
} from "recharts";
import { useAnalyticsOverview, useAnalyticsTrends, useAnalyticsHotspots } from "../../api/queries";
import { ErrorState } from "../../components/common/ErrorState";

const PIE_COLORS = ["#3d8bfd", "#2fb787", "#e6a13c", "#e2622f", "#e5484d", "#8a7ee6", "#4dd0e1"];

function ChartCard({ title, subtitle, children, height = 300 }: { title: string; subtitle?: string; children: React.ReactNode; height?: number }) {
  return (
    <Paper sx={{ p: 2.5, height: "100%" }}>
      <Typography variant="subtitle2" fontWeight={700}>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
          {subtitle}
        </Typography>
      )}
      <Box sx={{ height, mt: 1 }}>{children}</Box>
    </Paper>
  );
}

export function AnalyticsPage() {
  const { data: overview, isLoading, error } = useAnalyticsOverview(30);
  const { data: trends } = useAnalyticsTrends();
  const { data: hotspots } = useAnalyticsHotspots(30);

  if (error) return <ErrorState message={error.message} />;

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        Analytics
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Aggregated from /analytics/overview, /analytics/trends, and /analytics/hotspots (last 30 days).
      </Typography>

      {isLoading ? (
        <Skeleton variant="rounded" height={400} />
      ) : (
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Incidents per day" subtitle="Daily incident volume">
              <ResponsiveContainer>
                <LineChart data={overview?.incidents_by_day ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232a35" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 11 }} stroke="#5b6576" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#5b6576" allowDecimals={false} />
                  <RTooltip contentStyle={{ background: "#171c25", border: "1px solid #232a35" }} />
                  <Line type="monotone" dataKey="count" stroke="#3d8bfd" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Incident trend" subtitle="Today vs yesterday, this week vs last week, this month vs last month">
              <ResponsiveContainer>
                <BarChart data={trends?.trends ?? []} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232a35" />
                  <XAxis type="number" tick={{ fontSize: 11 }} stroke="#5b6576" allowDecimals={false} />
                  <YAxis dataKey="label" type="category" width={140} tick={{ fontSize: 11 }} stroke="#5b6576" />
                  <RTooltip contentStyle={{ background: "#171c25", border: "1px solid #232a35" }} />
                  <Legend />
                  <Bar dataKey="current" fill="#3d8bfd" name="Current" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="previous" fill="#5b6576" name="Previous" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Top cameras" subtitle="Incidents by camera (30d)">
              <ResponsiveContainer>
                <BarChart data={overview?.incidents_by_camera.slice(0, 8) ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232a35" />
                  <XAxis dataKey="camera_name" tick={{ fontSize: 10 }} stroke="#5b6576" interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 11 }} stroke="#5b6576" allowDecimals={false} />
                  <RTooltip contentStyle={{ background: "#171c25", border: "1px solid #232a35" }} />
                  <Bar dataKey="count" fill="#2fb787" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Incidents by category" subtitle="FEATURE 2 classification breakdown">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={overview?.incidents_by_category ?? []}
                    dataKey="count"
                    nameKey="bucket"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                  >
                    {(overview?.incidents_by_category ?? []).map((_entry, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <RTooltip contentStyle={{ background: "#171c25", border: "1px solid #232a35" }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Severity distribution">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={overview?.incidents_by_severity ?? []} dataKey="count" nameKey="bucket" outerRadius={100}>
                    {(overview?.incidents_by_severity ?? []).map((_entry, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <RTooltip contentStyle={{ background: "#171c25", border: "1px solid #232a35" }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Hotspots" subtitle="Highest-risk camera, busiest hour, most dangerous day">
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2, height: "100%", justifyContent: "center" }}>
                {[hotspots?.highest_risk_camera, hotspots?.busiest_hour, hotspots?.most_dangerous_day]
                  .filter(Boolean)
                  .map((h, i) => (
                    <Box key={i} sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 1 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ textTransform: "capitalize" }}>
                          {h!.kind}
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {h!.label}
                        </Typography>
                      </Box>
                      <Typography variant="h6" color="primary.light">
                        {h!.share_pct}%
                      </Typography>
                    </Box>
                  ))}
                {!hotspots?.hotspots.length && (
                  <Typography variant="body2" color="text.secondary" textAlign="center">
                    Not enough data yet to identify hotspots.
                  </Typography>
                )}
              </Box>
            </ChartCard>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
