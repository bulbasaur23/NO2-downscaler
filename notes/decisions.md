# Locked decisions (Stage 0)

## D3: time window and versions (locked Day 2)
- Evidence: monthly NO2 by algorithm version (notes/version_plot.png) showed no
  sharp step at 2022-07-17, 2024-11-16 or 2025-11-22 in Delhi NCR.
- Control region (Thar desert, 71.0-72.0E, 26.0-26.8N): mean anomaly 0.12 (1.6.0),
  0.25 (1.7.0), 0.12 (1.8.0) umol/m2. No version offset. Older 1.5.0: -0.59.
- Limit: control region has low NO2, so a polluted-scene-only change is not ruled
  out. The 1.8.0 version-shift test covers that.
- Training: algorithm 1.6.0 + 1.7.0 (2022-07-17 to 2025-11-21).
- Version-shift test: algorithm 1.8.0 (2025-11-22 onward).
- Every Parquet row stores algorithm and processor version. Labels normalised
  with no2.versions (format changed late 2025). '03.00.DV' (1 granule) excluded.
- Archive holes: notes/archive_holes.csv. Clusters: 2023-05 to 2023-07 (20 short
  days), 2025-10 to 2025-11 (13 short days, zero-granule day 2025-11-01).
- NO2 archive ends 2026-10-08 (date-picker cap will be set by weather, D4).