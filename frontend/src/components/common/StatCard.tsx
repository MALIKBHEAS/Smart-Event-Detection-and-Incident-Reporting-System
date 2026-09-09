import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Skeleton from "@mui/material/Skeleton";
import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: string;
  accent?: string;
  loading?: boolean;
}

export function StatCard({ label, value, icon, hint, accent = "#3d8bfd", loading }: StatCardProps) {
  return (
    <Card
      component={motion.div}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      sx={{ height: "100%" }}
    >
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1 }}>
            {label}
          </Typography>
          {icon && (
            <Box
              sx={{
                width: 30,
                height: 30,
                borderRadius: 1.5,
                display: "grid",
                placeItems: "center",
                bgcolor: `${accent}22`,
                color: accent,
              }}
            >
              {icon}
            </Box>
          )}
        </Box>
        {loading ? (
          <Skeleton variant="text" width="60%" height={40} />
        ) : (
          <Typography variant="h4" fontWeight={700}>
            {value}
          </Typography>
        )}
        {hint && (
          <Typography variant="caption" color="text.secondary">
            {hint}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
