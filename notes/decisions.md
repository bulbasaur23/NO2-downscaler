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

## D4: matching weather to the overpass (locked Day 2)
- Observation time over the NCR box is not constant. It follows a sawtooth:
  granule start moves ~19 min earlier per day, then jumps ~100 min (one orbit)
  every ~5 days. Measured spread within one month: 115 min (Jan 2024),
  109 min (Jul 2024), range 07:01-08:56 UTC.
- The plan's 'UTC hour from cell longitude' rule is replaced. Time is derived
  per day from the granule's solar zenith/azimuth (no2.solar).
- Weather = linear interpolation between the two bracketing ERA5 hours at that
  time (BLH rose ~12% per hour on average in script 06).
- Solar angles exist on cloud-masked days (Jan 4-6 2024: NO2 0.00, angles 1.00),
  so a time is available for every day with a granule over the box.
- No granule over the box (e.g. 2024-01-28): status no_overpass, no time needed.
- Granule start is NOT the observation time (30-45 min earlier, offset varies).
- Two-granule days (3 per month, ~100 min apart): default rule is to use the
  granule with the larger NO2 valid fraction, or the larger angle coverage if
  neither has NO2. Revisit in Phase 1 (per-cell weighting is possible).
- Store obs_utc_hour and n_granules in every Parquet row.
- Caveat: derived times are not independently verified. Winter scatter vs
  granule start is 4.3 min (std), worst case ~10-15 min, ~2-3% on BLH.