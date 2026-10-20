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
-Negative values are retained in the product (tropospheric column min -0.0005375
  mol/m2, ~-537 umol/m2, approximate). Delhi NCR, Jan 2024 cell means: 5,943 values,
  min 24.1 umol/m2, 0 negatives, 0 below 20. One winter month only: re-check on the
  full export (monsoon). The live app can target low-NO2 regions anywhere in India, so
  a rule for zero/negative values is needed before the log-transformed target (Phase 3).
- Doc note: solar_zenith_angle's description says "satellite" but the name and values
  (8-82 deg; 18-51 deg over Delhi) indicate the sun. no2.solar assumes the sun.
- Day-level status and cell-level observed are different rules. Example: 2024-01-13
  is "insufficient" (mean valid 0.46) but 200 of 320 cells have a value.
- Export rule (found Day 3): reduceRegions omits a property when the mean is null,
  and CSV export then drops the whole column. Every exported feature must carry every
  column. Missing values are written as -9999 and converted to NaN at load. The
  sentinel must never reach a model or a map.
- Verified: the 2024-01 batch export matches the interactive run for 2024-01-15
  exactly (NO2 and valid, difference 0.0; 311 cells with NO2 in both).
- Missing solar angles: 488 cells = 2024-01-28 (320, no_overpass) + 01-13/14/15/31
  (6/15/9/138, swath edge; matches 07b ang_valid 0.93/0.88/0.92/0.47).

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
- LOCKED (plan default): local run plus pre-computed cached Delhi and Hyderabad
  polygons. A hosted public endpoint is a stretch goal, only if the measured quota cost
  allows it.

## CPCB / ground stations (Day 3, provisional)
- CPCB portal: form-based per station/pollutant with several filters (CEEW 2021; 2020
  guide: ~1 week of 15-min data per download). No documented API in these sources.
  Both sources are old: current state not verified.
- Third-party mirrors: Princeton compilation (hourly 2015-2019, CC BY; too early);
  OpenCity per-station CSVs for Delhi (15-min 2024-25, hourly 2017-2023, 39 stations,
  public domain, last updated 2026-01-15, source cited as CPCB).
- Provisional: ground validation = OPTIONAL, Delhi only, via OpenCity CSVs.
  Not a model input. Surface NO2 (ug/m3) vs tropospheric column: correlation check only.
  Provenance: CPCB QC is undocumented; mirror values not treated as clean ground truth.
- Test (scripts/11_ground_check.py, 11b): ITO station, OpenCity del-ito-cpcb-2024-25.csv.
  68,985 rows of 15-minute data (2024-01-01 to 2025-12-31 23:30, ~98% of expected rows),
  1 unparsable timestamp, no duplicates, 29 columns. NO2 (ug/m3) present in 67,124 (97%);
  every month has at least ~87% of expected NO2 readings. Median 59.4, max 499.2
  (needs an outlier filter). Parse timestamps with format="ISO8601" (default parsing
  dropped 61% of rows).
- Timezone (scripts/11c): timestamps are local time (IST) labelled +0000. Solar radiation
  peaks at as-written hour 12 (Shadipur) and 13 (Sirifort); real UTC would peak at 6-7
  (local solar noon ~12:20 IST = ~06:50 UTC). ITO and Shadipur NO2 profiles agree
  (min hours 14-15, max 20-21). Inferred from data, not documented: check the OpenCity
  Data Dictionary. The two stations differ by 1 hour (possible start- vs end-of-interval
  stamping), so treat timing as +-1 h. Cost is small: ITO median NO2 changes ~5% per
  hour at as-written hours 12-14, against ~40-50% if the label were taken at face value.
- Sirifort NO2 looks inverted (median min at as-written hour 21, max at 15; 95% of
  readings present). Cause unknown. Do not use Sirifort NO2 until inspected.
- Radiation sensors have offsets (Shadipur ~37 W/m2 at night): use SR for peak timing only.
- Still missing: station latitude/longitude (do not guess; source from a station list),
  and the 2022-23 files. Overlap with the 1.8.0 version-shift test (from 2025-11-22) is
  ~40 days. Ground validation stays OPTIONAL (Delhi only, not a model input).

## D8. Study area, water, static layers
- Delhi NCR bounding box: 76.80-77.80 E, 28.20-29.00 N, 320 cells (20 x 16).
  Grid stays 0.05 degree (a 1 km grid would repeat one retrieval across many cells).
- Water: ESA WorldCover v200, class 80 (permanent water), 30 m scale, mean per cell.
  All 320 cells are land. Max water fraction 7.5% (cells along the Yamuna, lon
  77.2-77.3, lat 28.5-28.8; not map-checked). Cutoffs 10/90, 20/80, 30/70 give
  identical results, so the 20/80 guess is untested here. Revisit with Hyderabad and
  Bengaluru (Phase 5). Permanent water only: monsoon floodplain not captured.
- Static table: data/interim/cells_static.parquet (cell geometry, water_frac,
  water_class, emit_dist_km, emit_cap_50km_mw). Roads and elevation are still to be added.
- Phase 0 Parquet: data/interim/delhi_2024-01.parquet (with file metadata).
- Emitters (Day 3):
  - Source: WRI Global Power Plant Database via GEE (WRI/GPPD/power_plants), frozen to
    config/emitters_india_fossil.csv (332 plants: 246 coal, 60 gas, 26 oil) with
    config/emitters_india_fossil.meta.txt (asset, pull date, filter). Feature code reads
    only the frozen file, never the asset. India total in the asset: 845 plants.
  - Snapshot is old: generation columns end 2016, newest known plant in the Delhi area
    ~2012 (solar plants have comm_year 0). Plants built since are missing; closed plants
    are still listed. No release/version field in the asset.
  - Verified closures, excluded via config/emitters_exclude.csv:
    BADARPUR (705 MW coal): permanently shut 2018-10-15 (news reports, Oct 2018).
    RAJGHAT (135 MW coal): stopped 2015, formally closed 2019 (Delhi cabinet, GEM tracker).
    Other plants in the list are NOT individually verified as operating. Before adding
    Hyderabad, Bengaluru and Kolkata (Phase 5), check the plants near each.
  - Fossil only (Coal, Gas, Oil). Hydro, solar, nuclear and wind are not NOx sources.
    Biomass (50) and cogeneration (1) excluded as small: a judgement, easy to revisit.
    Industrial sources (kilns, steel, cement) are not covered by this dataset.
  - Largest sources near the box are OUTSIDE it: Indira Gandhi STPP (1,500 MW) and
    Mahatma Gandhi TPP (1,320 MW) ~0.4 deg west, Panipat (920 MW) north. Capacity
    matters as much as distance.
  - Features: emit_dist_km (nearest plant), emit_cap_50km_mw (capacity within 50 km;
    the radius is a guess). Superseded: the first emit_dist_km (20 plants including
    hydro, solar, nuclear and the two closed plants).
  - First signal check (Jan 2024, 320 cells, Spearman vs mean observed NO2): emit_dist_km
    -0.77, emit_cap_50km_mw +0.46, distance to central Delhi (reference only, not a
    feature) -0.72. Overlap with the urban core: emit_dist vs dist_center +0.56; cap vs
    dist_center -0.43. Coefficient of variation: emit_dist 0.53, emit_cap 0.39 (both above
    the 0.3 near-constant flag). 330 plants after exclusions, 12 near the box.
    Caveats: one winter month; neighbouring cells are autocorrelated so the effective
    sample is far below 320; plants sit in or near urban areas, so this is largely
    "urbanness". No significance test.
  - Partial correlation (rank-based, 320 cells, 11-21 observed days per cell, median 17).
    Controlling for distance to a hard-coded Delhi centre (28.63N, 77.22E): emit_dist_km
    -0.63, emit_cap_50km_mw +0.23. Controlling for a spatial surface (scripts/10d):
      plane (lat+lon):                 emit_dist -0.79, emit_cap +0.51
      quadratic surface:               emit_dist -0.42, emit_cap -0.11
      quadratic surface + centre dist: emit_dist -0.46, emit_cap -0.32
    emit_dist_km keeps ~-0.4 under the flexible surface (borderline vs. my pre-set
    ~0.4 guide). It may reflect sharp structure around plants, or local urban hotspots
    near them; not separable here. emit_cap_50km_mw collapses and changes sign: the raw
    +0.46 was mostly location. Heavy controls can also remove real signal from smooth
    features. One winter month, correlational, no model.
  - Decision: KEEP emit_dist_km as a Phase 3 ablation candidate. DROP emit_cap_50km_mw
    from the first feature set (test capacity via the wind-aware exposure instead, not
    by tuning the 50 km radius). The column stays in cells_static.parquet but is unused.

## Open items carried into Phase 1 (G0 met: see notes/g0_feasibility.md)
- Add obs_utc_hour to every row (the Phase 0 Parquet stores the angles, not the hour).
- Measure the full live request: weather with lags, and the EECU cost of interactive calls.
- Quota alert policy at 50% and 80% of the monthly cap: confirm it exists.
- Short archive days after 2025-11-22; the two-granule-day rule; repeat the 50% threshold
  and negative-value checks on the full export (summer, monsoon).
- D2: valid-area weighting across granules; within-day comparison for partial-coverage cells.
- D4: confirm whether ERA5's newest data is preliminary and later revised.
- Ground data: station coordinates, Sirifort NO2, OpenCity Data Dictionary timezone statement.
- Verify the emitters near each new city before using emitter features (Phase 5).

## Gotchas found so far
- reduceRegions on a single-band image names the output property after the reducer
  ("mean"), not the band. Use Reducer.mean().setOutputs([...]).
- A null mean makes reduceRegions omit the property, and CSV export then drops the
  column. Use the sentinel rule in D2.
- GEE collection getInfo() is limited to 5,000 elements. Query by month.
- Granule counts are orbit files, not overpasses.
- Solar azimuth must be averaged via sin/cos.
- pandas default date parsing silently dropped 61% of the CPCB rows: use format="ISO8601".
- A timestamp label (+0000) can be wrong: check it against solar radiation or another
  physical signal before matching to satellite time.