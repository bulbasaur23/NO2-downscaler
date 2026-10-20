# Decisions and findings (Phase 0, through Day 3)

Status legend: LOCKED = decided with evidence. PROVISIONAL = leaning, needs a later test.
OPEN = not yet checked.

## D1. Target definition (from plan, unchanged)
- The model predicts the TROPOMI-retrieved tropospheric NO2 column (umol/m2),
  not surface NO2. Accuracy is reported against TROPOMI only.
- Stated in code, Parquet metadata, UI and README.

## D2. Grid and observed-cell rule
- Grid: 0.05 degree, cell_id = "iy_ix" from integer indices (no2.grid).
  Tested: edge points, bbox count (20 x 16 = 320), id uniqueness.
- GEE band native scale: 1113.2 m (resampled; the real pixel is ~5.5 x 3.5 km).
- Daily value per cell = mean of that day's granules, native scale, EPSG:4326.
  This is a per-pixel mean, not yet valid-area-weighted across granules. OPEN: revisit.
- A cell is OBSERVED if valid >= 0.50 (valid = fraction of cell area with a valid
  NO2 pixel). LOCKED at 50%.
- Threshold sensitivity, Jan 2024 Delhi, 9,920 cell-days:
  30% -> 5,569 observed, mean 166.0; 50% -> 5,387, mean 164.9; 70% -> 5,218, mean 163.8.
  Stable (~1.3% in mean NO2). One winter month only: repeat on the full export,
  especially summer. obs_30 / obs_50 / obs_70 flags are stored in the Parquet.
- Cells with a value but valid < 0.5: 556 cell-days, mean 182.2 vs 164.9 for observed
  cells. Cause unresolved (edge bias vs different days). Not used as targets.
  OPEN: within-day comparison on the full export.


- QA filtering (from the GEE dataset page, "OFFL L3 Product"): the L3 build applies
  tropospheric_NO2_column_number_density_validity > 50 (equivalent to qa_value > 0.5)
  before gridding. The page's example command is from a 2018 product ("a command like
  this"), so treat as the documented rule, not verified per processor version.
  Not changeable per pixel (no qa_value band in the 12 bands). 0.5 is looser than the
  0.75 I recall as ESA's usual recommendation for tropospheric NO2 (from memory,
  unchecked): partly cloudy pixels may be retained. Feeds the clear-sky-bias caveat.
- L3 gridding: 0.01 degree bins (explains the 1113.2 m scale; not the real resolution,
  ~5.5 x 3.5 km). Overlapping data area-averaged into one mosaic per product.
- The NO2 mask is not shared across bands in the data we receive: cloud fraction and
  solar angles are present where NO2 is masked (2024-01-04 to 06). The cloud band can
  therefore be used as a separate signal for D6 reason codes.
-- Negative values are retained in the product (tropospheric column min -0.0005375
  mol/m2, ~-537 umol/m2, approximate). Delhi NCR, Jan 2024 cell means: 5,943 values,
  min 24.1 umol/m2, 0 negatives, 0 below 20. One winter month only: re-check on the
  full export (monsoon). The live app can target low-NO2 regions anywhere in India, so
  a rule for zero/negative values is needed before the log-transformed target (Phase 3).

## D3. Time window and processor versions
- Version labels per granule: PROCESSOR_VERSION and ALGORITHM_VERSION.
- Algorithm versions and dates (NCR collection, from scripts/03_versions.py):
  1.5.0 2021-07-01 to 2022-07-17 | 1.6.0 2022-07-17 to 2024-11-16 |
  1.7.0 2024-11-16 to 2025-11-22 | 1.8.0 2025-11-22 to 2026-10-08.
  Processor versions inside: 1.6.0 = 2.4.0, 2.5.0, 2.6.0, 2.7.1; 1.7.0 = 2.8.0;
  1.8.0 = 02.09.01.
- Label format changed in late 2025 ("2.8.0" -> "02.09.01"). Compare numerically with
  no2.versions (tested), never as text. One-off dev label "03.00.DV" (1 granule,
  2025-12-21) is excluded.
- Monthly NO2 by algorithm version (scripts/04): no sharp step at 2022-07-17 or
  2025-11-22. At 2024-11-16 Dec and Jan are 15-30% lower, Feb is not. Ambiguous.
- Control region (scripts/04b, Thar desert 71.0-72.0E, 26.0-26.8N, ~20 umol/m2):
  mean anomaly 1.5.0 -0.59, 1.6.0 +0.12, 1.7.0 +0.25, 1.8.0 +0.12. No version offset
  at 1.6.0->1.7.0 (+0.13) or 1.7.0->1.8.0 (-0.13). The Delhi winter drop is therefore
  not a general software shift.
- Limit: the control region has low NO2. A change that matters only for polluted,
  hazy scenes is not ruled out. The 1.8.0 version-shift test covers that.
- LOCKED window: export from 2022-07-17 to the latest data (about 51 months).
  Training: algorithm 1.6.0 + 1.7.0 (2022-07-17 to 2025-11-21).
  Version-shift test: algorithm 1.8.0 (2025-11-22 onward).
  Fixed chronological test: a later slice of the 1.6.0/1.7.0 data, chosen in Phase 2.
  No pre-2022-07-17 data (1.5.0 is offset -0.59; earlier versions are lower still).
- Every row stores algo, proc and normalised proc.
- NO2 archive ends 2026-10-08 (collection through early October 2026).
- Archive holes (scripts/03b, notes/archive_holes.csv): 60 of 3,022 days have fewer
  than 13 granules (typical day: 14). Clusters: 2023-05 to 2023-07 (20 short days,
  inside the training window) and 2025-10 to 2025-11 (13 short days). Zero-granule
  days: 2022-05-01 and 2025-11-01. A granule count cannot say whether the Delhi
  orbit is missing: the per-day status from the pixels decides.
  OPEN: how many short days fall after 2025-11-22 (thickness of the version-shift test).
- A granule is one orbit file (~14 per day). Most do not touch Delhi, so "images on a
  day" is not "overpasses". GEE getInfo() on a collection stops at 5,000 elements:
  query by month and use aggregate_array.

## D4. Weather source and overpass matching
- Boundary layer height IS in GEE: ECMWF/ERA5/HOURLY band boundary_layer_height
  (28 km). ERA5-Land hourly (11 km) has no BLH. The CDS route is not needed.
  ECMWF/ERA5/DAILY has no data after mid-2025: unusable.
- Latest data 2026-10-13 for both hourly collections (6-day lag). The plan assumed
  2-3 months. OPEN: confirm whether the newest part is preliminary and later revised.
- Date-picker cap = earliest source = NO2 end date (2026-10-08 at time of writing).
- Humidity from dewpoint + temperature. Precipitation is accumulated in ERA5
  (total_precipitation); ERA5-Land has total_precipitation_hourly. Handle in Phase 1.
- Parity, ERA5 vs ERA5-Land, NCR box mean, 25 dates x 2 hours (50 rows): wind
  r 0.99, rmse 0.21-0.25 m/s (std 1.4-2.4); temperature r 0.99, rmse 1.2 K;
  pressure r 1.00; dewpoint r 0.955 with +2.3 K bias. Box averages only: within-box
  detail not tested.
- BLH seasonal shape sensible (indicative, fixed hours 07/08 UTC): Dec-Jan ~670 m,
  May ~3,450 m.
- One single-hour request (ERA5 + ERA5-Land): 1.6 s.
- PROVISIONAL choice: ERA5 single levels as the only weather source. Confirm with the
  Phase 3 feature ablation.
- ERA5 pixels are 0.25 degree: ~4 x 3 weather pixels over the box. Weather cannot
  explain differences between neighbouring cells; static layers and emitter exposure
  must.
- Overpass time over the NCR box is NOT constant. Observation time follows a
  sawtooth: granule start moves ~19 min earlier per day, then jumps ~100 min every
  ~5 days. Measured within one month: 07:01-08:56 UTC (spread 115 min, Jan 2024),
  07:06-08:55 UTC (spread 109 min, Jul 2024).
- The plan's "UTC hour from cell longitude" rule is replaced. Observation time is
  derived per day from the solar zenith and azimuth (no2.solar, tested). Azimuth is
  averaged through sin/cos, never directly.
- Weather is linearly interpolated between the two bracketing ERA5 hours at that time
  (BLH rose ~12% per hour on average).
- Granule start is NOT the observation time: it is 41.1 min earlier on average in
  Jan (std 4.3) and 30.3 min in Jul (std 0.5).
- Solar angles exist on cloud-masked days (2024-01-04: NO2 0.00, angles 1.00). A time
  is available for every day with a granule over the box. No granule (2024-01-28):
  status no_overpass.
- Two-granule days (3 per month, ~100 min apart): default rule is the granule with
  the larger NO2 valid fraction (angle coverage if neither has NO2). OPEN: revisit in
  Phase 1.
- Caveat: derived times are not independently verified. January scatter vs granule
  start is 4.3 min (std), worst case ~10-15 min, ~2-3% on BLH.
- Store obs_utc_hour and n_granules in every Parquet row. Unit test for the
  timezone / interpolation is required before the feature module is accepted.

## D5. Quota
- Tier: Earth Engine noncommercial, one project only.
- Monthly cap: 540,000 EECU-seconds (system limit, not adjustable).
- Daily quota was "unlimited" by default. Set to 20,000 as a runaway guard.
  OPEN: confirm the alert policy at 50% and 80% of the monthly cap exists.
- Used before the export test: 637 (0.12%).
- Live request (scripts/00, one day, 320 cells): 10.7 s wall time, includes Python
  start-up (upper bound, NO2 only). EECU cost not yet measured.
- One-month Delhi export, 31 days x 320 cells (NO2, cloud, angles, versions), with the
  sentinel fix: 7.6 and 7.8 EECU-seconds on two runs. Wall time 80 s and 31 s
  (queue-dependent, not a planning figure). Planning value: ~8 EECU-s per month.
  The first version (4.2 EECU-s, 16 s) dropped the no2 column and is superseded.
- Estimate: ~51 months = ~400 EECU-s for Delhi; ~1,200 for three cities (~0.2% of cap).
- NOT yet measured: weather extraction with lags, live requests, interactive calls.
  Re-measure in Phase 1.
- Quota log: notes/quota_log.csv (first export row is superseded).

## D6. Error taxonomy
- Four distinct outcomes, never mixed: observed, insufficient (with reason code),
  no_overpass, system_error. "reconstructed" arrives with Model B.
- Day-level rule (no2.status, tested on real cases):
  no_overpass = no granule, or NO2 and cloud both fully masked;
  insufficient = granule exists but valid area < 0.5;
  observed = valid area >= 0.5.
- 2024-01: 18 observed, 12 insufficient, 1 no_overpass (2024-01-28). Matches the
  independent scan in scripts/01.
- system_error (GEE, weather or satellite-outage failure) is not implemented yet and
  must never be cached as data.

## D7. Demo setup
- OPEN. Default per plan: local run plus pre-computed Delhi and Hyderabad polygons.

## D8. Study area, water, static layers
- Delhi NCR bounding box: 76.80-77.80 E, 28.20-29.00 N, 320 cells (20 x 16).
  Grid stays 0.05 degree (a 1 km grid would repeat one retrieval across many cells).
- Water: ESA WorldCover v200, class 80 (permanent water), 30 m scale, mean per cell.
  All 320 cells are land. Max water fraction 7.5% (cells along the Yamuna, lon
  77.2-77.3, lat 28.5-28.8; not map-checked). Cutoffs 10/90, 20/80, 30/70 give
  identical results, so the 20/80 guess is untested here. Revisit with Hyderabad and
  Bengaluru (Phase 5). Permanent water only: monsoon floodplain not captured.
- Static table: data/interim/cells_static.parquet (cell geometry, water_frac,
  water_class). Roads, elevation and emitter distance are still to be added.
- Phase 0 Parquet: data/interim/delhi_2024-01.parquet (with file metadata).
- Emitters: OPEN (Day 3).

## Open items before gate G0
- Emitter list and per-city counts (scripts/10).
- CPCB station access: automatic or manual? Drop if manual.
- D7 demo decision.
- Record the exact QA threshold and what the GEE collection already filters.
- Alert policy on the monthly quota.
- Short days after 2025-11-22.
- G0 one-page feasibility note.

## Gotchas found so far
- reduceRegions on a single-band image names the output property after the reducer
  ("mean"), not the band. Use Reducer.mean().setOutputs([...]).
- A null mean makes reduceRegions omit the property, and CSV export then drops the
  column. Use the sentinel rule in D2.
- GEE collection getInfo() is limited to 5,000 elements. Query by month.
- Granule counts are orbit files, not overpasses.
- Solar azimuth must be averaged via sin/cos.