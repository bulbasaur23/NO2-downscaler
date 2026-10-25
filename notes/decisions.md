# Decisions and findings (through Phase 1.3a)

Status legend: LOCKED = decided with evidence. PROVISIONAL = leaning, needs a later test.
OPEN = not yet checked. PARKED = tried, failed, not pursued.

## D1. Target definition (from plan, unchanged)
- The model predicts the TROPOMI-retrieved tropospheric NO2 column (umol/m2),
  not surface NO2. Accuracy is reported against TROPOMI only.
- Stated in code, Parquet metadata, UI and README.

## D2. Grid, observed-cell rule, coverage
- Grid: 0.05 degree, cell_id = "iy_ix" from integer indices (no2.grid).
  Tested: edge points, bbox count (20 x 16 = 320), id uniqueness.
- GEE band native scale: 1113.2 m (resampled; the real pixel is ~5.5 x 3.5 km).
- Daily value per cell = mean of that day's granules, native scale, EPSG:4326.
  This is a per-pixel mean, not valid-area-weighted across granules. OPEN: revisit.
- A cell is OBSERVED if valid >= 0.50 (valid = fraction of cell area with a valid NO2
  pixel). LOCKED at 50%.
- IMPORTANT: 'valid' counts 1.1 km grid pixels, but the real retrieval footprint is
  ~5.5 x 3.5 km, so a 0.05 deg cell holds only a handful of independent retrievals. A
  high valid fraction measures coverage, not independent samples; noise does not
  average down.
- Threshold sensitivity, Jan 2024 Delhi, 9,920 cell-days: 30% -> 5,569 observed, mean
  166.0; 50% -> 5,387, mean 164.9; 70% -> 5,218, mean 163.8 (~1.3% in mean NO2). One
  winter month only. OPEN: repeat on the full export by season. obs_30/50/70 flags are
  in the Phase 0 Parquet (the Phase 1 raw files hold only 'valid').
- Cells with a value but valid < 0.5 (Jan 2024): 556 cell-days, mean 182.2 vs 164.9 for
  observed cells. Cause unresolved. Not used as targets. OPEN: within-day comparison.
- QA filtering (GEE dataset page, "OFFL L3 Product"): the L3 build applies
  tropospheric_NO2_column_number_density_validity > 50 (equivalent to qa_value > 0.5)
  before gridding. The page's example command is from a 2018 product ("a command like
  this"), so this is the documented rule, not verified per processor version. Not
  changeable per pixel (no qa_value band in the 12 bands). 0.5 is looser than the 0.75
  I recall as ESA's usual recommendation (from memory, unchecked): partly cloudy
  pixels may be retained. Feeds the clear-sky-bias caveat.
- L3 gridding: 0.01 degree bins (explains the 1113.2 m scale). Overlapping data is
  area-averaged into one mosaic per product.
- The NO2 mask is not shared across bands in the data we receive: cloud fraction and
  solar angles are present where NO2 is masked (2024-01-04 to 06). The cloud band is a
  separate signal for D6 reason codes.
- Doc note: solar_zenith_angle's description says "satellite" but the name and values
  (8-82 deg; 18-51 deg over Delhi) indicate the sun. no2.solar assumes the sun.
- Day-level status and cell-level observed are different rules. Example: 2024-01-13
  is "insufficient" (mean valid 0.46) but 200 of 320 cells have a value.
- Export rule (found Day 3): reduceRegions omits a property when the mean is null, and
  CSV export then drops the whole column. Every exported feature must carry every
  column. Missing values are written as -9999 and converted to NaN at load. The
  sentinel must never reach a model or a map.
- Missing solar angles in Jan 2024: 488 cells = 2024-01-28 (320, no_overpass) +
  01-13/14/15/31 (6/15/9/138, swath edge; matches 07b ang_valid).
- Coverage over the full window (scripts/22; 1,553 days; 369,242 of 496,960 cell-days,
  74%, have a NO2 value). Share of DAYS observed: monsoon (Jun-Sep) 48%, winter
  (Dec-Feb) 81%, post-monsoon (Oct-Nov) 81%, pre-monsoon (Mar-May) 89%. By month: Jul
  32%, Aug 36%, Sep 59%, Jan 67%, Jun 72%, others 80-92%. Monsoon is the thinnest
  season (the G0 note first said winter, from Jan 2024 alone: corrected). Clear-sky
  bias: monsoon values describe clear-sky conditions only. State in the README.
- Negative values (full window, scripts/22b/22c): 34 of 369,242 cell-days (0.009%), min
  -15.7 umol/m2 (product minimum is -0.0005375 mol/m2, ~-537 umol/m2). 32 of 34 fall in
  Mar-Sep (Jun 19, Jul 8); none in Oct-Feb. 10 distinct days, 30 cells; the five most
  negative are all 2023-06-15. 53% (~18) have valid >= 0.5, so the 50% rule does NOT
  screen them out. None of the 10 days is a short-granule day (13-14 granules), so
  archive holes are rejected as the cause. Day means of observed cells on those days
  are 29-54 umol/m2 (median overall 69.5): they occur on clean days. Working
  hypothesis (not proven): retrieval noise at low column amounts. The live app can
  target low-NO2 regions anywhere in India, so a rule for zero/negative values is
  needed before the log-transformed target (Phase 3): drop impossible targets, clip at
  a floor, or a zero-tolerant transform.
- Extreme values (scripts/22b/22c): quantiles 99% 352, 99.9% 620, 99.99% 922; max 1,157
  (2023-12-30). Top 100: 18 days, 60 cells, all Nov-Feb (Dec 51, Jan 33, Feb 10,
  Nov 6); 81 of 100 have valid >= 0.5. Mixed pattern: some multi-day builds
  (2023-01-18..21; 2023-12-30 follows a day averaging 291), some one-day jumps
  (2025-01-09: 109 -> 273 -> 141 with 315 cells; 2023-02-16; 2023-12-22), some with a
  coverage change (2024-01-30: 123 observed cells vs 320 the day before; 2023-12-30: 50
  cells). Real episode vs artefact NOT decided. DECISION: keep all values, trim
  nothing. Test in step 1.3d (BLH and wind on those days) and in Phase 3 by scoring with
  and without the top 1%.

## D3. Time window, processor versions, pipeline
- Version labels per granule: PROCESSOR_VERSION and ALGORITHM_VERSION.
- Algorithm versions and dates (scripts/03): 1.5.0 2021-07-01 to 2022-07-17 | 1.6.0
  2022-07-17 to 2024-11-16 | 1.7.0 2024-11-16 to 2025-11-22 | 1.8.0 2025-11-22 to
  2026-10-08. Processor versions inside: 1.6.0 = 2.4.0, 2.5.0, 2.6.0, 2.7.1; 1.7.0 =
  2.8.0; 1.8.0 = 02.09.01.
- Label format changed in late 2025 ("2.8.0" -> "02.09.01"). Compare numerically with
  no2.versions (tested), never as text. One-off dev label "03.00.DV" (1 granule,
  2025-12-21) is excluded in the pull.
- Monthly NO2 by algorithm version (scripts/04): no sharp step at 2022-07-17 or
  2025-11-22. At 2024-11-16 Dec and Jan are 15-30% lower, Feb is not: ambiguous.
- Control region (scripts/04b, Thar desert 71.0-72.0E, 26.0-26.8N, ~20 umol/m2): mean
  anomaly 1.5.0 -0.59, 1.6.0 +0.12, 1.7.0 +0.25, 1.8.0 +0.12. No version offset at
  1.6.0->1.7.0 (+0.13) or 1.7.0->1.8.0 (-0.13). The Delhi winter drop is not a general
  software shift. Limit: low-NO2 region; a change affecting only polluted, hazy scenes
  is not ruled out. The 1.8.0 version-shift test covers that.
- LOCKED window: 2022-07 to 2026-09 pulled (51 months). Training: algorithm 1.6.0 +
  1.7.0 (2022-07-17 to 2025-11-21). Version-shift test: algorithm 1.8.0 from 2025-11-23.
  Fixed chronological test: a later slice of the 1.6.0/1.7.0 data, chosen in Phase 2.
  No pre-2022-07-17 data (the 16 days of 2022-07-01..16 are labelled 1.5.0: exclude).
- RULE: exclude 2025-11-22 from training and from the version-shift test. Its label is
  mixed (1.7.0,1.8.0): the processor changed at 08:56 UTC, inside the 05:00-11:00 UTC
  label window, so that day's value is a per-pixel mean of two versions.
- Day counts by algorithm label (scripts/22): 1.6.0: 853 days (611 observed, 232
  insufficient, 10 no_overpass); 1.7.0: 364 days (254 / 105 / 5). Training total 1,217
  days, 865 observed (71%). 1.8.0 from 2025-11-23: 312 days (229 observed, 83
  insufficient, 0 no_overpass); including 2025-11-22: 313 days, 230 observed. Seven
  days have an empty label (2025-10-22..25, 2025-11-01..03): no granule in the label
  window, all no_overpass.
- Archive holes (scripts/03b, notes/archive_holes.csv): 60 of 3,022 days have fewer
  than 13 granules (typical 14). Clusters: 2023-05 to 2023-07 and 2025-10 to 2025-11.
  Zero-granule days: 2022-05-01 and 2025-11-01. In the window: 42 short days, only 17 of
  them no_overpass; 22 no_overpass days in total, 5 of them with a normal granule count
  (2023-01-29, 2023-11-24, 2024-01-28, 2024-12-27, 2025-10-06). A granule count predicts
  a Delhi gap only loosely: the status comes from the pixels.
- A granule is one orbit file (~14 per day); most do not touch Delhi. GEE getInfo() on a
  collection stops at 5,000 elements: query by month and use aggregate_array.
- Pipeline (scripts/20-21, src/no2/pull.py, runner.py, manifest.py): resumable per-month
  pull with a manifest, retries (2/4/8/16 s), atomic writes; a month is "done" only with
  exactly days x 320 unique cell-days. Interactive per-day pulls, raw output (no
  observed flags). Jan 2024 matches the Phase 0 export exactly (max difference 1e-13,
  labels identical), before and after the label filter change.
- Label filter: algo/proc per day come from granules starting 05:00-11:00 UTC only (Delhi
  granules start ~06:25-08:25 UTC, from 07b), not all ~14 global granules. Verified at
  the 2022-07-17 boundary (1.5.0/2.3.1, then 1.6.0/2.4.0). OPEN: replace with the
  version of the granule that actually covers the box.
- Full window verified (scripts/22): 51/51 months done, 496,960 rows = 1,553 days x 320,
  0 duplicates. 44.7 min for 48 months (47-74 s per month). 2026-10 excluded: the
  archive ends 2026-10-08 and a day with no granules is recorded as n_granules=0, which
  would read as no_overpass for dates after the archive end. Guard needed before
  extending.

## D4. Weather source and overpass matching
- Boundary layer height IS in GEE: ECMWF/ERA5/HOURLY band boundary_layer_height (28 km).
  ERA5-Land hourly (11 km) has no BLH. The CDS route is not needed. ECMWF/ERA5/DAILY has
  no data after mid-2025: unusable.
- Latest data 2026-10-13 for both hourly collections (6-day lag; the plan assumed 2-3
  months). OPEN: confirm whether the newest part is preliminary and later revised.
- Date-picker cap = earliest source = NO2 end date (2026-10-08 at time of writing).
- Humidity from dewpoint + temperature. Precipitation is accumulated in ERA5
  (total_precipitation); ERA5-Land has total_precipitation_hourly. Handle in 1.3b.
- Parity, ERA5 vs ERA5-Land, NCR box mean, 25 dates x 2 hours: wind r 0.99, rmse
  0.21-0.25 m/s; temperature r 0.99, rmse 1.2 K; pressure r 1.00; dewpoint r 0.955 with
  +2.3 K bias. Box averages only: within-box detail not tested.
- BLH seasonal shape (script 06, fixed hours 07/08 UTC, ~2 dates per month: indicative
  only): Dec-Jan ~670 m, May ~3,450 m. The May figure was NOT representative. Full-window
  mean BLH at the overpass (scripts/34), by calendar month (m): Jan 696, Feb 1,026, Mar
  1,437, Apr 2,544, May 2,268, Jun 1,833, Jul 954, Aug 947, Sep 1,095, Oct 1,217, Nov 1,137,
  Dec 777. One single-hour request (ERA5 + ERA5-Land): 1.6 s.
- PROVISIONAL choice: ERA5 single levels as the only weather source. Confirm with the
  Phase 3 ablation. ERA5 pixels are 0.25 degree: ~4 x 3 weather pixels over the box.
  Weather cannot explain differences between neighbouring cells; static layers and
  emitter exposure must.
- Overpass time over the NCR box is NOT constant. Granule start moves ~19 min earlier
  per day, then jumps ~100 min every ~5 days. The plan's "UTC hour from cell longitude"
  rule is replaced: observation time is derived from the solar zenith and azimuth
  (no2.solar, tested). Granule start is NOT the observation time (41 min earlier on
  average in Jan, 30 min in Jul).
- Full window (scripts/30): 1,531 of 1,553 days have a time; the 22 without angles match
  the count of no_overpass days (dates not compared). Range 06:33-08:59 UTC (07b, two
  months: 07:01-08:56). Median within-day spread of per-cell times 0.2 min; five dates
  match 07b to the minute (same formula and product: tests storage, not physics).
  Consecutive-day changes: 1,011 of 1,516 pairs in the -13..-25 min drift band, 123
  jumps > +60 min, 382 other (unexplained). Output: data/interim/obs_time_delhi.parquet.
- 154 days (10.1%) have a per-cell time spread > 15 min (p95 54 min, max 115; my guide
  was < 2%: wrong). On most such days p90-p10 is close to the full range: cells split
  into groups an hour apart. Hypothesis: two-granule overlap days (07b: 3 of 31 days in
  both Jan and Jul 2024). Alternative: the azimuth flaw below. Test: scripts/30b
  (PENDING).
- Flaw found (my error): the rule "average azimuth through sin/cos" was not followed:
  pull.py and the Phase 0 export store a plain mean of azimuth in degrees. It matters
  only where a cell's pixels straddle +-180 (sun nearly due south). The daily time uses
  the median across cells, which tolerates a minority of bad cells. If scripts/30b
  points to the flaw, re-pull with sin/cos.- 154 days (10.1%) have a per-cell time spread > 15 min (p95 54 min, max 115; my guide was
  < 2%: wrong). Cause (scripts/30b): two-orbit OVERLAP, not the azimuth flaw. Evidence: (1)
  the 3 flagged days in Jan/Jul 2024 are all two-granule days found independently by 07b;
  3 of the 6 two-granule days are flagged. In 07b the flagged three had a partly covering
  second granule (ang_valid 0.86, 0.85, 0.61), the unflagged three had both granules
  covering the box (1.00/1.00): partial overlap splits cells into groups an hour apart,
  full overlap gives every cell one blended time. n=6. (2) Flagged share is flat across
  calendar months (6-14%), no winter excess. (3) Flagged days show strong east-west
  structure (median rank correlation of cell time with longitude -0.69; 25% of cells > 10
  min from the day median, p95 55%); consistent with the later orbit lying west of the
  earlier one (from memory). Normal days: 0 cells off by > 10 min even at the p95 day
  (partly by construction). Latest five times (08:54-08:59) are all flagged; earliest
  five (06:33-07:00) are not, so the early end is real or a formula bias, not blending.
- Azimuth flaw (my error: pull.py stores a plain mean, not sin/cos): not supported as
  material. The days where it is most likely (observation near solar noon, ~06:35 UTC in
  late October by my arithmetic, e.g. 2025-10-29 at 06:33) are not flagged. No re-pull.
  Possible later bundle if re-pulling for other reasons: sin/cos azimuth, a per-cell
  count of contributing granules, the version of the covering granule.
- Fully overlapped days: the daily value is a mean of two observations ~100 min apart and
  the angle-derived time is a blend; weather at the blended time is a reasonable
  representative. Two-granule-day rule: use the mean (as pulled) and the per-cell time.
- Time-formula bias: Phase 0 granule-start offsets were 41 min (Jan) vs 30 min (Jul): an
  ~11 min seasonal difference suggests a formula bias of that order (~4% on BLH).
  Unverified.
- RULE (independent of the cause): weather is matched PER CELL using each cell's own
  observation time, linearly interpolated between the two bracketing ERA5 hours (BLH
  rose ~12% per hour on average). A single per-day time would be wrong by up to ~50 min
  for part of the box on ~10% of days (~10% on BLH).
- Two-granule days: the per-pixel daily mean blends two orbits ~100 min apart; the
  per-cell angle-derived time is a sensible blended time for that value.
- Solar angles exist on cloud-masked days (2024-01-04: NO2 0.00, angles 1.00). No
  granule (2024-01-28): status no_overpass.
- Store obs_utc_hour and n_granules in every row. A unit test for the timezone and the
  interpolation is required before the feature module is accepted.
  - - Weather pull (Phase 1.3b, scripts/31-33): hourly ERA5/HOURLY (u10, v10, t2m, d2m, sp, tp,
  blh), one series per ERA5 pixel, not per cell. Cells are mapped to pixels empirically
  (scripts/31: cells with identical sampled values share a pixel). Result: exactly 20
  pixels, all full rectangles; pixel edges at multiples of 0.25 deg (lon 77.00/77.25/77.50/
  77.75, lat 28.25/28.50/28.75), so the 0.05 deg grid NESTS in the ERA5 grid and no cell
  straddles two pixels (my earlier guess that edges cut through cells was wrong). Nine
  pixels hold 25 cells, three hold 20, the rest are edge slivers (corner pixel: 1 cell).
  Weather takes at most 20 distinct values per hour across the 320 cells: it cannot
  explain differences within a pixel. Weather for a cell = its pixel (nearest pixel, no
  spatial interpolation: bilinear would add smooth within-pixel gradients that act like
  coordinates). Window 2022-06 to 2026-09 (52 months; June 2022 gives the 48 h lags for the
  first day); 7-day chunks (5,000 element limit); manifest region "era5_delhi_ncr".
  Pulled in 16.6 min (~20 s per month), rows = hours x 20 exactly. Expected total 759,840.
- Jan 2024 check (scripts/33): no missing values; t2m 3-23 C, d2m below t2m, sp 985-1001
  hPa; BLH ~55-70 m at night, peak ~630-675 m at 8-11 UTC (8 UTC mean 674 m, matching
  script 06); tp profile by UTC hour is not monotonic, so hourly values and not a running
  total since 00 UTC (a January with 0.45 mm/day: noisy but the property is robust);
  min tp -0.00 (tiny negative: clipped to 0 in features). Pulled series equals the
  pixel-mapping sample exactly. Full-window check: see scripts/33.
- Feature definitions (src/no2/weather_features.py, 10 unit tests; my reading of the plan's
  "previous-day mean wind" and "24 h/48 h mean wind before the overpass"): values at the
  cell's observation time interpolated linearly between the bracketing ERA5 hours (UTC);
  u/v means over the previous UTC calendar day; trailing 24 h and 48 h means of the
  interpolated series ending at the observation time; ventilation = wind speed x BLH at the
  overpass; previous-day precipitation = sum over the previous UTC day (mm); humidity from
  t2m and d2m (Magnus). Missing observation time -> NaN features (22 no_overpass days).
  Cells without angles on a day with an overpass use the day's median time.
  Precipitation timestamp convention (hour ending at the timestamp vs starting) unverified;
  it only affects precip_ovp_mm slightly.
- Planned feature definitions (plan, D8; my reading of "previous-day" and "24 h/48 h before
  the overpass", settle in 1.3c): values at the cell's observation time interpolated
  between bracketing hours; u/v means over the previous UTC calendar day; trailing 24 h
  and 48 h means ending at the observation time; ventilation = wind speed x BLH at
  overpass; previous-day precipitation = sum over the previous UTC day. Humidity from
  t2m and d2m (Magnus). Precipitation accumulation convention: unverified (scripts/33).
- Full-window ERA5 check (scripts/33): 52/52 months, 759,840 rows = expected, 0 duplicates,
  no missing values except tp: 280 rows missing (14 hours x 20 pixels if all pixels share
  the same hours: unconfirmed, see scripts/35). Ranges plausible: t2m 3.4-47.3 C, d2m -5 to
  31 C, sp 964-1005 hPa, blh 10-5,321 m (median 199). BLH by UTC hour: night ~125-200 m,
  peak 1,348 m at 8 UTC. tp by UTC hour is not monotonic over 4 years: per-hour values,
  not a running total. Mean daily precipitation by month (mm/day): Jan 0.92, Feb 0.43,
  Mar 1.15, Apr 0.43, May 1.26, Jun 2.61, Jul 8.44, Aug 5.64, Sep 5.47, Oct 1.84, Nov 0.07,
  Dec 0.29 (~875 mm/yr by my arithmetic; not compared with station records; months are
  sampled over 4-5 years).
- Missing weather is never imputed: trailing windows and interpolations that touch a
  missing hour give NaN (only precip features are affected). The builder raises on a gap
  in the hourly time axis. Tests: tests/test_weather_features.py (14 tests, 30 in total).
- Weather features built (scripts/34, data/interim/weather_features_delhi.parquet; 496,960
  cell-days). Observation-time source: cell 476,109, day_median 13,811 (cell had no angles),
  none 7,040 (no_overpass days: features NaN). Extra missing beyond those: precip_prevday_mm
  640 (2022-08-02, 2024-02-02, the source gap); no other feature. Spot check: BLH feature
  equals a by-hand interpolation (445.25). Ranges: ws 0.02-9.5 m/s, t at overpass 10.5-47.2 C,
  rh 9-100% (clipped), blh 111-5,117 m (median 1,104), vent 13-28,840 m2/s (median 2,695),
  precip_prevday up to 190.8 mm (date to be checked: possibly the 28 June 2024 Delhi
  downpour, from memory, unverified).
- Value of per-cell timing (relative BLH difference, per-cell time vs one median time per
  day): normal days mean 0.0%, p95 0.1%, max 59%; flagged days mean 2.3%, median 0, p95
  13.4%, max 207%. ~0.5% of all cell-days differ by more than 13%. Per-cell rule kept
  (cheap, correct). Large ratios likely come from small BLH values (unchecked).
  - Within-month check (scripts/36b; 51 year-months with >= 8 days, 4-5 per calendar month;
  median across years): wind speed negative in 51 of 51 year-months (median -0.49; -0.21 to
  -0.69 by month); 24 h wind 98% negative (median -0.40); ventilation 88% negative (median
  -0.42), strongest Nov-Jan (-0.48 to -0.72), near zero in Apr, May, Sep; previous-day rain
  71% negative (median -0.25), strongest Sep -0.61, Oct -0.44, ~0 in dry months; BLH
  median -0.04, 55% negative: winter negative (Dec -0.32, Jan -0.40, Feb -0.22), Apr-Jun
  and Sep weakly positive (+0.16 to +0.28), others ~0.
  Reading: the pooled monsoon BLH correlation (+0.53) was mostly a seasonal confound
  (within monsoon months -0.13 to +0.27); a weak positive BLH relation remains in Apr-Jun
  and Sep, unexplained. Wind is the robust driver of the day-to-day signal; ventilation adds
  a little in Nov-Jan only. Wind direction not examined (speed only). Few year-months per
  calendar month: read the pattern, not neighbouring-month differences.

## D5. Quota
- Tier: Earth Engine noncommercial, one project only. Monthly cap 540,000 EECU-seconds
  (system limit, not adjustable). Daily quota set to 20,000 (visible in the console).
  The 50%/80% alert policy is unconfirmed; low priority at 0.14% of the cap.
- Phase 0 batch export, one month (31 days x 320 cells), sentinel version: 7.6 and 7.8
  EECU-seconds (wall time 80 s and 31 s: queue-dependent). The first version (4.2,
  16 s) dropped the no2 column and is superseded.
- Interactive per-day pull (Phase 1): daily counter 458 (2.29% of 20,000) at ~17:00 IST
  on 2026-10-21, after 51 month-pulls since the daily reset (assumed 12:30 IST;
  unverified). ~9 EECU-s per month pulled, consistent with the batch figure. Full Delhi
  window ~460 (0.09% of the monthly cap); three cities ~1,400.
- The monthly counter is NOT trusted: 637 -> 289 -> 689 -> 763 (it went down once and
  rose only +74 over a period the daily counter puts at 458). My earlier "~200 per
  month pulled" estimate came from it and is withdrawn.
- Per-day interactive pulls are affordable for Bengaluru and Kolkata (~45 min per city).
- NOT yet measured: weather extraction with lags, the full live request. Re-measure in
  1.3b. Quota log: notes/quota_log.csv (first export row superseded).

## D6. Error taxonomy
- Four distinct outcomes, never mixed: observed, insufficient (with reason code),
  no_overpass, system_error. "reconstructed" arrives with Model B.
- Day-level rule (no2.status, tested on real cases): no_overpass = no granule, or NO2
  and cloud both fully masked; insufficient = granule exists but valid area < 0.5;
  observed = valid area >= 0.5.
- Full window: 22 no_overpass days; Jan 2024: 18 observed, 12 insufficient, 1 no_overpass.
- system_error (GEE, weather or satellite-outage failure) is not implemented yet and must
  never be cached as data.

## D7. Demo setup
- LOCKED (plan default): local run plus pre-computed cached Delhi and Hyderabad polygons.
  A hosted public endpoint is a stretch goal, only if the measured quota cost allows it.

## CPCB / ground stations: PARKED
- CPCB portal: form-based per station/pollutant with several filters (CEEW 2021; 2020
  guide: ~1 week of 15-min data per download). No documented API in these sources. Both
  are old: current state not verified.
- Third-party mirrors: Princeton compilation (hourly 2015-2019, too early); OpenCity
  per-station CSVs for Delhi (15-min 2024-25, hourly 2017-2023, 39 stations, public
  domain, updated 2026-01-15, source cited as CPCB).
- Test (scripts/11, 11b, 11c): ITO station file: 68,985 rows of 15-minute data
  (2024-01-01 to 2025-12-31), NO2 present in 97%, median 59.4 ug/m3, max 499.2. Parse
  timestamps with format="ISO8601" (default parsing dropped 61% of rows).
- Timezone: timestamps are local time (IST) labelled +0000. Solar radiation peaks at
  as-written hour 12 (Shadipur) and 13 (Sirifort); real UTC would peak at 6-7. Inferred,
  not documented; +-1 h uncertainty. Sirifort NO2 looks inverted (cause unknown). SR
  sensors have offsets (Shadipur ~37 W/m2 at night). No station coordinates in the files.
- Comparison with the satellite (scripts/22c, 22d; days with >= 100 observed cells):
  daily Spearman -0.02 over 572 days (ITO at as-written hours 12-14); +0.37 (n=20) for
  Jan 2024. Monthly means (24 months): -0.15 (12-14h), +0.24 (24h). With n=24, values
  below ~0.4 are hard to tell from zero. Within-month daily Spearman: median +0.15, range
  -0.42 to +0.62, positive in 15 of 24 months (~15% chance under a coin flip). ITO
  shifted -1/+1 day: +0.03 / -0.00: no date-misalignment signal. ITO afternoon mean:
  ~24 ug/m3 in Mar-Jun 2025, ~66 in Jul-Oct 2025 (48 in Jul-Oct 2024), 32 in Nov 2025:
  a step not mirrored by the satellite (possible sensor change, unverified). The
  satellite's monthly cycle looks plausible (peak Dec-Jan, low Jul-Aug): plausibility,
  not validation.
- DECISION: ground validation is PARKED. Reopen only with documented station
  coordinates, a verified timestamp convention and a station with a plausible
  diurnal/seasonal profile. The model predicts and is validated against TROPOMI (D1).

## D8. Study area, water, static layers
- Delhi NCR bounding box: 76.80-77.80 E, 28.20-29.00 N, 320 cells (20 x 16). Grid stays
  0.05 degree (a 1 km grid would repeat one retrieval across many cells).
- Water: ESA WorldCover v200, class 80 (permanent water), 30 m scale, mean per cell. All
  320 cells are land; max water fraction 7.5% (Yamuna cells; not map-checked). Cutoffs
  10/90, 20/80, 30/70 give identical results, so the 20/80 guess is untested here.
  Revisit with Hyderabad and Bengaluru (Phase 5). Permanent water only.
- Static table: data/interim/cells_static.parquet (cell geometry, water_frac,
  water_class, emit_dist_km, emit_cap_50km_mw). Roads and elevation are still to be added
  (step 1.4).
- Phase 0 Parquet: data/interim/delhi_2024-01.parquet (with file metadata).
- Emitters:
  - Source: WRI Global Power Plant Database via GEE (WRI/GPPD/power_plants), frozen to
    config/emitters_india_fossil.csv (332 plants: 246 coal, 60 gas, 26 oil) with
    config/emitters_india_fossil.meta.txt. Feature code reads only the frozen file.
    India total in the asset: 845 plants.
  - Snapshot is old: generation columns end 2016, newest known plant in the Delhi area
    ~2012. Plants built since are missing; closed plants are still listed. No release
    field in the asset.
  - Verified closures, excluded via config/emitters_exclude.csv: BADARPUR (705 MW coal,
    shut 2018-10-15), RAJGHAT (135 MW coal, stopped 2015, formally closed 2019). Other
    plants are NOT individually verified. Check the plants near each new city (Phase 5).
  - Fossil only (Coal, Gas, Oil). Biomass (50) and cogeneration (1) excluded as small: a
    judgement. Industrial sources are not covered.
  - Largest sources near the box are OUTSIDE it: Indira Gandhi STPP (1,500 MW) and
    Mahatma Gandhi TPP (1,320 MW) ~0.4 deg west, Panipat (920 MW) north.
  - Features: emit_dist_km (nearest plant), emit_cap_50km_mw (capacity within 50 km;
    the radius is a guess).
  - Signal check (Jan 2024, Spearman vs mean observed NO2): emit_dist_km -0.77,
    emit_cap_50km_mw +0.46, distance to central Delhi (reference only) -0.72. CV 0.53 and
    0.39 (above the 0.3 near-constant flag). Partial correlation controlling for a
    hard-coded Delhi centre: -0.63 and +0.23. Controlling for a quadratic spatial
    surface: emit_dist -0.42, emit_cap -0.11; surface + centre distance: -0.46 / -0.32.
    emit_dist_km keeps ~-0.4 (borderline); emit_cap collapses and changes sign. One
    winter month, correlational, no model.
  - DECISION: KEEP emit_dist_km as a Phase 3 ablation candidate. DROP emit_cap_50km_mw
    from the first feature set (test capacity via a wind-aware exposure, not by tuning
    the radius). The column stays in cells_static.parquet but is unused.

## Open items
- 1.3a: scripts/30b (cause of the 10% flagged days); decide whether to re-pull azimuth.
- 1.3b-d: weather per cell at its own observation time, lags, BLH, precipitation
  (accumulated); add obs_utc_hour to the data; unit test for timezone and interpolation;
  BLH and wind on the extreme-value days; measure the full live request.
- D2: repeat the 50% threshold check by season on the full export; valid-area weighting
  across granules; within-day comparison for partial-coverage cells.
- D3: replace the 05:00-11:00 label window with the covering granule's version; guard for
  dates after the archive end; two-granule-day rule.
- D4: confirm whether ERA5's newest data is preliminary and later revised.
- 
- Phase 3: rule for zero/negative targets; robustness to extreme values.
- Alert policy at 50%/80%: unconfirmed, low priority.
- Verify the emitters near each new city before using emitter features (Phase 5).

## Gotchas found so far
- reduceRegions on a single-band image names the output property after the reducer
  ("mean"), not the band. Use Reducer.mean().setOutputs([...]).
- A null mean makes reduceRegions omit the property, and CSV export then drops the
  column. Use the sentinel rule in D2.
- GEE collection getInfo() is limited to 5,000 elements. Query by month.
- Granule counts are orbit files, not overpasses.
- Solar azimuth must be averaged via sin/cos (and was not, in pull.py: see D4).
- pandas default date parsing silently dropped 61% of the CPCB rows: use format="ISO8601".
- A timestamp label (+0000) can be wrong: check it against solar radiation or another
  physical signal before matching to satellite time.
- pytest collects *_test.py files anywhere: keep tests in tests/ (testpaths set).
- Series.corr(method="spearman") needs scipy; use a.rank().corr(b.rank()) instead.
- Validate command-line arguments before doing work (a trailing dot created a wrongly
  named file and a junk manifest row).
- The monthly quota counter is unreliable (went down once): trust the daily counter.
- - Earth Engine 403 USER_PROJECT_DENIED ("Caller does not have required permission to use
  project"): the stored login belongs to a different Google account than the project owner.
  Fix: `earthengine authenticate --force` and choose the owning account. gee.init() calls
  ee.Authenticate() on any failure, so a permission error shows up twice (the second copy is
  the same error, not a new one).