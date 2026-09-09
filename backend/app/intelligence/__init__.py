"""Intelligence & Analytics module.

Analyzes historical Event/Report/Camera data already persisted by the core
detection pipeline: statistics, classification, pattern/anomaly detection,
risk scoring, hotspots, trends, recommendations, and executive summaries.

This module is read-only with respect to the rest of the system -- it never
writes to Event/Report/Camera, and introduces no new tables. Everything is
computed on demand from existing data via aggregation queries.
"""
